import pytest
from hypothesis import given, strategies as st, assume
from decimal import Decimal
from uuid import uuid4

from app.services.order_service import OrderService
from app.models.database_models import OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderItem

class TestOrderProperties:
    """Property-based tests for order processing system"""
    
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from decimal import Decimal
from uuid import uuid4

from app.services.order_service import OrderService
from app.repositories.order_repository import OrderRepository
from app.models.database_models import OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderItem

class TestOrderProperties:
    """Property-based tests for order processing system"""
    
    @given(st.lists(
        st.builds(
            OrderItem,
            product_id=st.text(min_size=1, max_size=50),
            quantity=st.integers(min_value=1, max_value=100),
            unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
        ),
        min_size=1,
        max_size=10
    ))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_order_total_calculation_correctness(self, test_db, items):
        """
        Property Test 1: Order total calculation correctness
        **Validates: Requirements 1.5**
        
        Property: The total amount of an order equals the sum of (quantity × unit_price) for all items
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Arrange
        customer_id = "test_customer"
        order_data = CreateOrderRequest(customer_id=customer_id, items=items)
        
        # Calculate expected total
        expected_total = sum(item.quantity * item.unit_price for item in items)
        
        # Act
        order = order_service.create_order(order_data)
        
        # Assert
        assert order.total_amount == expected_total, (
            f"Order total {order.total_amount} does not match expected {expected_total} "
            f"for items: {[(item.quantity, item.unit_price) for item in items]}"
        )
    
    @given(st.sampled_from([
        (OrderStatus.PENDING, OrderStatus.PROCESSING),
        (OrderStatus.PENDING, OrderStatus.CANCELLED),
        (OrderStatus.PROCESSING, OrderStatus.SHIPPED),
        (OrderStatus.PROCESSING, OrderStatus.CANCELLED),
        (OrderStatus.SHIPPED, OrderStatus.DELIVERED)
    ]))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_status_transition_validity(self, test_db, status_transition):
        """
        Property Test 2: Status transition validity
        **Validates: Requirements 3.5**
        
        Property: Order status transitions follow the valid workflow: 
        PENDING → PROCESSING → SHIPPED → DELIVERED, with CANCELLED allowed from PENDING/PROCESSING
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        current_status, new_status = status_transition
        
        # Test that valid transitions are allowed
        is_valid = order_service._is_valid_status_transition(current_status, new_status)
        assert is_valid is True, f"Valid transition {current_status} → {new_status} was rejected"
    
    @given(st.sampled_from([
        (OrderStatus.PENDING, OrderStatus.SHIPPED),
        (OrderStatus.PENDING, OrderStatus.DELIVERED),
        (OrderStatus.PROCESSING, OrderStatus.DELIVERED),
        (OrderStatus.SHIPPED, OrderStatus.PENDING),
        (OrderStatus.SHIPPED, OrderStatus.PROCESSING),
        (OrderStatus.DELIVERED, OrderStatus.PENDING),
        (OrderStatus.DELIVERED, OrderStatus.PROCESSING),
        (OrderStatus.DELIVERED, OrderStatus.SHIPPED),
        (OrderStatus.CANCELLED, OrderStatus.PENDING),
        (OrderStatus.CANCELLED, OrderStatus.PROCESSING),
        (OrderStatus.CANCELLED, OrderStatus.SHIPPED),
        (OrderStatus.CANCELLED, OrderStatus.DELIVERED)
    ]))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_invalid_status_transitions(self, test_db, invalid_transition):
        """
        Property Test 2b: Invalid status transitions are rejected
        **Validates: Requirements 3.5**
        
        Property: Invalid status transitions are always rejected
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        current_status, new_status = invalid_transition
        
        # Test that invalid transitions are rejected
        is_valid = order_service._is_valid_status_transition(current_status, new_status)
        assert is_valid is False, f"Invalid transition {current_status} → {new_status} was allowed"
    
    @given(st.sampled_from([OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_cancellation_rules_enforcement(self, test_db, non_pending_status):
        """
        Property Test 3: Cancellation rules enforcement
        **Validates: Requirements 5.1, 5.3**
        
        Property: Orders can only be cancelled when status is PENDING
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Create an order
        order_data = CreateOrderRequest(
            customer_id="test_customer",
            items=[OrderItem(product_id="test_product", quantity=1, unit_price=Decimal("10.00"))]
        )
        order = order_service.create_order(order_data)
        
        # Update to non-pending status
        if non_pending_status != OrderStatus.PENDING:
            # For valid transitions, update step by step
            if non_pending_status == OrderStatus.PROCESSING:
                order_service.update_order_status(order.id, OrderStatus.PROCESSING)
            elif non_pending_status == OrderStatus.SHIPPED:
                order_service.update_order_status(order.id, OrderStatus.PROCESSING)
                order_service.update_order_status(order.id, OrderStatus.SHIPPED)
            elif non_pending_status == OrderStatus.DELIVERED:
                order_service.update_order_status(order.id, OrderStatus.PROCESSING)
                order_service.update_order_status(order.id, OrderStatus.SHIPPED)
                order_service.update_order_status(order.id, OrderStatus.DELIVERED)
            elif non_pending_status == OrderStatus.CANCELLED:
                order_service.update_order_status(order.id, OrderStatus.CANCELLED)
        
        # Try to cancel - should fail for non-pending orders
        from app.services.order_service import OrderCancellationError
        with pytest.raises(OrderCancellationError):
            order_service.cancel_order(order.id)
    
    def test_property_cancellation_rules_pending_success(self, test_db):
        """
        Property Test 3b: PENDING orders can be cancelled
        **Validates: Requirements 5.1**
        
        Property: Orders with PENDING status can always be cancelled
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Create an order (will be PENDING by default)
        order_data = CreateOrderRequest(
            customer_id="test_customer",
            items=[OrderItem(product_id="test_product", quantity=1, unit_price=Decimal("10.00"))]
        )
        order = order_service.create_order(order_data)
        
        # Should be able to cancel
        success = order_service.cancel_order(order.id)
        assert success is True
        
        # Verify it was cancelled
        cancelled_order = order_service.get_order(order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED
    
    @given(st.builds(
        CreateOrderRequest,
        customer_id=st.text(min_size=1, max_size=50),
        items=st.lists(
            st.builds(
                OrderItem,
                product_id=st.text(min_size=1, max_size=50),
                quantity=st.integers(min_value=1, max_value=100),
                unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
            ),
            min_size=1,
            max_size=5
        )
    ))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_order_persistence_and_retrieval(self, test_db, order_data):
        """
        Property Test 4: Order persistence and retrieval
        **Validates: Requirements 2.1**
        
        Property: Created orders can always be retrieved with identical data
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Create order
        created_order = order_service.create_order(order_data)
        
        # Retrieve order
        retrieved_order = order_service.get_order(created_order.id)
        
        # Assert all data is identical
        assert retrieved_order.id == created_order.id
        assert retrieved_order.customer_id == created_order.customer_id
        assert retrieved_order.status == created_order.status
        assert retrieved_order.total_amount == created_order.total_amount
        assert len(retrieved_order.items) == len(created_order.items)
        
        # Check items match
        for retrieved_item, created_item in zip(retrieved_order.items, created_order.items):
            assert retrieved_item.product_id == created_item.product_id
            assert retrieved_item.quantity == created_item.quantity
            assert retrieved_item.unit_price == created_item.unit_price
    
    def test_property_background_job_idempotency(self, test_db):
        """
        Property Test 5: Background job idempotency
        **Validates: Requirements 3.2, 3.3**
        
        Property: Running the background job multiple times produces the same result
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Create multiple PENDING orders
        orders = []
        for i in range(3):
            order_data = CreateOrderRequest(
                customer_id=f"customer_{i}",
                items=[OrderItem(product_id=f"product_{i}", quantity=1, unit_price=Decimal("10.00"))]
            )
            order = order_service.create_order(order_data)
            orders.append(order)
        
        # Run background job first time
        processed_count_1 = order_service.process_pending_orders()
        
        # Verify orders were updated to PROCESSING
        for order in orders:
            updated_order = order_service.get_order(order.id)
            assert updated_order.status == OrderStatus.PROCESSING
        
        # Run background job second time (should be idempotent)
        processed_count_2 = order_service.process_pending_orders()
        
        # Should process 0 orders the second time (all are already PROCESSING)
        assert processed_count_2 == 0
        
        # Verify orders are still PROCESSING (unchanged)
        for order in orders:
            updated_order = order_service.get_order(order.id)
            assert updated_order.status == OrderStatus.PROCESSING
        
        # First run should have processed all orders
        assert processed_count_1 == len(orders)
    
    @given(st.lists(
        st.builds(
            OrderItem,
            product_id=st.text(min_size=1, max_size=50),
            quantity=st.integers(min_value=1, max_value=100),
            unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
        ),
        min_size=1,
        max_size=10
    ))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_order_total_always_positive(self, test_db, items):
        """
        Additional Property: Order total is always positive for valid orders
        
        Property: Any valid order must have a positive total amount
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Arrange
        customer_id = "test_customer"
        order_data = CreateOrderRequest(customer_id=customer_id, items=items)
        
        # Act
        order = order_service.create_order(order_data)
        
        # Assert
        assert order.total_amount > 0, f"Order total {order.total_amount} is not positive"
    
    @given(st.builds(
        CreateOrderRequest,
        customer_id=st.text(min_size=1, max_size=50),
        items=st.lists(
            st.builds(
                OrderItem,
                product_id=st.text(min_size=1, max_size=50),
                quantity=st.integers(min_value=1, max_value=100),
                unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
            ),
            min_size=1,
            max_size=5
        )
    ))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_new_orders_always_pending(self, test_db, order_data):
        """
        Additional Property: New orders always start with PENDING status
        
        Property: All newly created orders must have PENDING status
        """
        # Create fresh service instance for each test
        order_repository = OrderRepository(test_db)
        order_service = OrderService(order_repository)
        
        # Act
        order = order_service.create_order(order_data)
        
        # Assert
        assert order.status == OrderStatus.PENDING, f"New order has status {order.status} instead of PENDING"