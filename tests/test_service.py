import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import Mock, patch

from app.services.order_service import OrderService, OrderNotFoundError, OrderCancellationError, InvalidOrderStatusError
from app.models.database_models import OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderItem, OrderResponse

class TestOrderService:
    """Test cases for OrderService"""
    
    def test_create_order_success(self, order_service, sample_order_data):
        """Test successful order creation"""
        order = order_service.create_order(sample_order_data)
        
        assert order.id is not None
        assert order.customer_id == sample_order_data.customer_id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == Decimal("75.48")
        assert len(order.items) == 2
    
    def test_create_order_validation_empty_items(self, order_service):
        """Test order creation with empty items list"""
        order_data = CreateOrderRequest(
            customer_id="customer_123",
            items=[]
        )
        
        with pytest.raises(ValueError, match="Order must contain at least one item"):
            order_service.create_order(order_data)
    
    def test_create_order_validation_zero_total(self, order_service):
        """Test order creation with zero total amount"""
        order_data = CreateOrderRequest(
            customer_id="customer_123",
            items=[
                OrderItem(product_id="product_1", quantity=0, unit_price=Decimal("10.00"))
            ]
        )
        
        with pytest.raises(ValueError, match="Item product_1 quantity must be positive"):
            order_service.create_order(order_data)
    
    def test_create_order_validation_negative_price(self, order_service):
        """Test order creation with negative unit price"""
        order_data = CreateOrderRequest(
            customer_id="customer_123",
            items=[
                OrderItem(product_id="product_1", quantity=1, unit_price=Decimal("-10.00"))
            ]
        )
        
        with pytest.raises(ValueError, match="Item product_1 unit price must be positive"):
            order_service.create_order(order_data)
    
    def test_get_order_success(self, order_service, sample_order_data):
        """Test successful order retrieval"""
        created_order = order_service.create_order(sample_order_data)
        retrieved_order = order_service.get_order(created_order.id)
        
        assert retrieved_order.id == created_order.id
        assert retrieved_order.customer_id == created_order.customer_id
    
    def test_get_order_not_found(self, order_service):
        """Test order retrieval with non-existent ID"""
        non_existent_id = uuid4()
        
        with pytest.raises(OrderNotFoundError, match=f"Order {non_existent_id} not found"):
            order_service.get_order(non_existent_id)
    
    def test_list_orders_success(self, order_service, sample_order_data):
        """Test successful order listing"""
        # Create multiple orders
        order1 = order_service.create_order(sample_order_data)
        order2_data = CreateOrderRequest(
            customer_id="customer_456",
            items=[OrderItem(product_id="product_3", quantity=1, unit_price=Decimal("50.00"))]
        )
        order2 = order_service.create_order(order2_data)
        
        result = order_service.list_orders()
        
        assert result.total == 2
        assert len(result.orders) == 2
        assert result.page == 1
        assert result.limit == 50
        assert result.has_next is False
        assert result.has_prev is False
    
    def test_list_orders_pagination(self, order_service):
        """Test order listing with pagination"""
        # Create multiple orders
        for i in range(5):
            order_data = CreateOrderRequest(
                customer_id=f"customer_{i}",
                items=[OrderItem(product_id=f"product_{i}", quantity=1, unit_price=Decimal("10.00"))]
            )
            order_service.create_order(order_data)
        
        # Test pagination
        result = order_service.list_orders(page=1, limit=2)
        
        assert result.total == 5
        assert len(result.orders) == 2
        assert result.page == 1
        assert result.limit == 2
        assert result.has_next is True
        assert result.has_prev is False
        
        # Test second page
        result_page2 = order_service.list_orders(page=2, limit=2)
        assert result_page2.has_prev is True
    
    def test_list_orders_invalid_pagination(self, order_service):
        """Test order listing with invalid pagination parameters"""
        # Test with invalid page (should default to 1)
        result = order_service.list_orders(page=0, limit=50)
        assert result.page == 1
        
        # Test with invalid limit (should default to 50)
        result = order_service.list_orders(page=1, limit=200)
        assert result.limit == 50
    
    def test_cancel_order_success(self, order_service, sample_order_data):
        """Test successful order cancellation"""
        order = order_service.create_order(sample_order_data)
        
        success = order_service.cancel_order(order.id)
        
        assert success is True
        
        # Verify order status
        cancelled_order = order_service.get_order(order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED
    
    def test_cancel_order_not_found(self, order_service):
        """Test cancellation of non-existent order"""
        non_existent_id = uuid4()
        
        with pytest.raises(OrderNotFoundError, match=f"Order {non_existent_id} not found"):
            order_service.cancel_order(non_existent_id)
    
    def test_cancel_order_not_pending(self, order_service, sample_order_data):
        """Test cancellation of non-pending order"""
        order = order_service.create_order(sample_order_data)
        
        # Update to PROCESSING
        order_service.update_order_status(order.id, OrderStatus.PROCESSING)
        
        # Try to cancel
        with pytest.raises(OrderCancellationError, match="Cannot cancel order with status PROCESSING"):
            order_service.cancel_order(order.id)
    
    def test_update_order_status_success(self, order_service, sample_order_data):
        """Test successful order status update"""
        order = order_service.create_order(sample_order_data)
        
        success = order_service.update_order_status(order.id, OrderStatus.PROCESSING)
        
        assert success is True
        
        # Verify status update
        updated_order = order_service.get_order(order.id)
        assert updated_order.status == OrderStatus.PROCESSING
    
    def test_update_order_status_invalid_transition(self, order_service, sample_order_data):
        """Test invalid status transition"""
        order = order_service.create_order(sample_order_data)
        
        # Try to go directly from PENDING to DELIVERED (invalid)
        with pytest.raises(InvalidOrderStatusError, match="Invalid status transition from PENDING to DELIVERED"):
            order_service.update_order_status(order.id, OrderStatus.DELIVERED)
    
    def test_update_order_status_not_found(self, order_service):
        """Test status update for non-existent order"""
        non_existent_id = uuid4()
        
        with pytest.raises(OrderNotFoundError, match=f"Order {non_existent_id} not found"):
            order_service.update_order_status(non_existent_id, OrderStatus.PROCESSING)
    
    def test_process_pending_orders(self, order_service):
        """Test background job processing of pending orders"""
        # Create multiple orders with different statuses
        order1_data = CreateOrderRequest(
            customer_id="customer_1",
            items=[OrderItem(product_id="product_1", quantity=1, unit_price=Decimal("10.00"))]
        )
        order2_data = CreateOrderRequest(
            customer_id="customer_2",
            items=[OrderItem(product_id="product_2", quantity=1, unit_price=Decimal("20.00"))]
        )
        order3_data = CreateOrderRequest(
            customer_id="customer_3",
            items=[OrderItem(product_id="product_3", quantity=1, unit_price=Decimal("30.00"))]
        )
        
        order1 = order_service.create_order(order1_data)
        order2 = order_service.create_order(order2_data)
        order3 = order_service.create_order(order3_data)
        
        # Update one order to PROCESSING manually
        order_service.update_order_status(order3.id, OrderStatus.PROCESSING)
        
        # Process pending orders
        processed_count = order_service.process_pending_orders()
        
        # Should have processed 2 orders (order1 and order2)
        assert processed_count == 2
        
        # Verify orders were updated
        updated_order1 = order_service.get_order(order1.id)
        updated_order2 = order_service.get_order(order2.id)
        updated_order3 = order_service.get_order(order3.id)
        
        assert updated_order1.status == OrderStatus.PROCESSING
        assert updated_order2.status == OrderStatus.PROCESSING
        assert updated_order3.status == OrderStatus.PROCESSING  # Already was PROCESSING
    
    def test_valid_status_transitions(self, order_service):
        """Test all valid status transitions"""
        # Test PENDING -> PROCESSING
        assert order_service._is_valid_status_transition(OrderStatus.PENDING, OrderStatus.PROCESSING) is True
        
        # Test PENDING -> CANCELLED
        assert order_service._is_valid_status_transition(OrderStatus.PENDING, OrderStatus.CANCELLED) is True
        
        # Test PROCESSING -> SHIPPED
        assert order_service._is_valid_status_transition(OrderStatus.PROCESSING, OrderStatus.SHIPPED) is True
        
        # Test PROCESSING -> CANCELLED
        assert order_service._is_valid_status_transition(OrderStatus.PROCESSING, OrderStatus.CANCELLED) is True
        
        # Test SHIPPED -> DELIVERED
        assert order_service._is_valid_status_transition(OrderStatus.SHIPPED, OrderStatus.DELIVERED) is True
    
    def test_invalid_status_transitions(self, order_service):
        """Test invalid status transitions"""
        # Test PENDING -> SHIPPED (skip PROCESSING)
        assert order_service._is_valid_status_transition(OrderStatus.PENDING, OrderStatus.SHIPPED) is False
        
        # Test PENDING -> DELIVERED (skip PROCESSING and SHIPPED)
        assert order_service._is_valid_status_transition(OrderStatus.PENDING, OrderStatus.DELIVERED) is False
        
        # Test DELIVERED -> any status (terminal state)
        assert order_service._is_valid_status_transition(OrderStatus.DELIVERED, OrderStatus.PENDING) is False
        assert order_service._is_valid_status_transition(OrderStatus.DELIVERED, OrderStatus.PROCESSING) is False
        
        # Test CANCELLED -> any status (terminal state)
        assert order_service._is_valid_status_transition(OrderStatus.CANCELLED, OrderStatus.PENDING) is False
        assert order_service._is_valid_status_transition(OrderStatus.CANCELLED, OrderStatus.PROCESSING) is False