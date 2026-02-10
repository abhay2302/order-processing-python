import pytest
from uuid import uuid4
from decimal import Decimal

from app.repositories.order_repository import OrderRepository, OrderNotFoundError
from app.models.database_models import OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderItem

class TestOrderRepository:
    """Test cases for OrderRepository"""
    
    def test_create_order_success(self, order_repository, sample_order_data):
        """Test successful order creation"""
        order = order_repository.create_order(sample_order_data)
        
        assert order.id is not None
        assert order.customer_id == sample_order_data.customer_id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == Decimal("75.48")  # 2*29.99 + 1*15.50
        assert len(order.items) == 2
        assert order.created_at is not None
        assert order.updated_at is not None
    
    def test_create_order_calculates_total_correctly(self, order_repository):
        """Test that order total is calculated correctly"""
        order_data = CreateOrderRequest(
            customer_id="customer_123",
            items=[
                OrderItem(product_id="product_1", quantity=3, unit_price=Decimal("10.00")),
                OrderItem(product_id="product_2", quantity=2, unit_price=Decimal("25.50"))
            ]
        )
        
        order = order_repository.create_order(order_data)
        expected_total = Decimal("3") * Decimal("10.00") + Decimal("2") * Decimal("25.50")
        
        assert order.total_amount == expected_total
    
    def test_get_order_by_id_success(self, order_repository, sample_order_data):
        """Test successful order retrieval by ID"""
        created_order = order_repository.create_order(sample_order_data)
        retrieved_order = order_repository.get_order_by_id(created_order.id)
        
        assert retrieved_order is not None
        assert retrieved_order.id == created_order.id
        assert retrieved_order.customer_id == created_order.customer_id
        assert retrieved_order.status == created_order.status
        assert retrieved_order.total_amount == created_order.total_amount
        assert len(retrieved_order.items) == len(created_order.items)
    
    def test_get_order_by_id_not_found(self, order_repository):
        """Test order retrieval with non-existent ID"""
        non_existent_id = uuid4()
        order = order_repository.get_order_by_id(non_existent_id)
        
        assert order is None
    
    def test_list_orders_no_filter(self, order_repository, sample_order_data):
        """Test listing all orders without filter"""
        # Create multiple orders
        order1 = order_repository.create_order(sample_order_data)
        order2_data = CreateOrderRequest(
            customer_id="customer_456",
            items=[OrderItem(product_id="product_3", quantity=1, unit_price=Decimal("50.00"))]
        )
        order2 = order_repository.create_order(order2_data)
        
        orders, total = order_repository.list_orders()
        
        assert total == 2
        assert len(orders) == 2
        # Orders should be sorted by created_at desc (newest first)
        assert orders[0].id == order2.id  # Most recent first
        assert orders[1].id == order1.id
    
    def test_list_orders_with_status_filter(self, order_repository, sample_order_data):
        """Test listing orders with status filter"""
        # Create orders with different statuses
        order1 = order_repository.create_order(sample_order_data)
        order2_data = CreateOrderRequest(
            customer_id="customer_456",
            items=[OrderItem(product_id="product_3", quantity=1, unit_price=Decimal("50.00"))]
        )
        order2 = order_repository.create_order(order2_data)
        
        # Update one order to PROCESSING
        order_repository.update_order_status(order2.id, OrderStatus.PROCESSING)
        
        # Filter by PENDING status
        pending_orders, total = order_repository.list_orders(status=OrderStatus.PENDING)
        
        assert total == 1
        assert len(pending_orders) == 1
        assert pending_orders[0].id == order1.id
        assert pending_orders[0].status == OrderStatus.PENDING
    
    def test_list_orders_pagination(self, order_repository):
        """Test order listing with pagination"""
        # Create multiple orders
        for i in range(5):
            order_data = CreateOrderRequest(
                customer_id=f"customer_{i}",
                items=[OrderItem(product_id=f"product_{i}", quantity=1, unit_price=Decimal("10.00"))]
            )
            order_repository.create_order(order_data)
        
        # Test first page
        orders_page1, total = order_repository.list_orders(page=1, limit=2)
        assert total == 5
        assert len(orders_page1) == 2
        
        # Test second page
        orders_page2, total = order_repository.list_orders(page=2, limit=2)
        assert total == 5
        assert len(orders_page2) == 2
        
        # Ensure different orders on different pages
        page1_ids = {order.id for order in orders_page1}
        page2_ids = {order.id for order in orders_page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_update_order_status_success(self, order_repository, sample_order_data):
        """Test successful order status update"""
        order = order_repository.create_order(sample_order_data)
        
        success = order_repository.update_order_status(order.id, OrderStatus.PROCESSING)
        
        assert success is True
        
        # Verify status was updated
        updated_order = order_repository.get_order_by_id(order.id)
        assert updated_order.status == OrderStatus.PROCESSING
    
    def test_update_order_status_not_found(self, order_repository):
        """Test order status update with non-existent order"""
        non_existent_id = uuid4()
        
        success = order_repository.update_order_status(non_existent_id, OrderStatus.PROCESSING)
        
        assert success is False
    
    def test_cancel_order_success(self, order_repository, sample_order_data):
        """Test successful order cancellation"""
        order = order_repository.create_order(sample_order_data)
        
        success = order_repository.cancel_order(order.id)
        
        assert success is True
        
        # Verify order was cancelled
        cancelled_order = order_repository.get_order_by_id(order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED
    
    def test_cancel_order_not_pending(self, order_repository, sample_order_data):
        """Test cancellation of non-pending order"""
        order = order_repository.create_order(sample_order_data)
        
        # Update to PROCESSING first
        order_repository.update_order_status(order.id, OrderStatus.PROCESSING)
        
        # Try to cancel - should fail
        success = order_repository.cancel_order(order.id)
        
        assert success is False
    
    def test_cancel_order_not_found(self, order_repository):
        """Test cancellation of non-existent order"""
        non_existent_id = uuid4()
        
        with pytest.raises(OrderNotFoundError):
            order_repository.cancel_order(non_existent_id)
    
    def test_get_pending_orders(self, order_repository):
        """Test retrieval of pending orders"""
        # Create orders with different statuses
        order1_data = CreateOrderRequest(
            customer_id="customer_1",
            items=[OrderItem(product_id="product_1", quantity=1, unit_price=Decimal("10.00"))]
        )
        order2_data = CreateOrderRequest(
            customer_id="customer_2",
            items=[OrderItem(product_id="product_2", quantity=1, unit_price=Decimal("20.00"))]
        )
        
        order1 = order_repository.create_order(order1_data)
        order2 = order_repository.create_order(order2_data)
        
        # Update one to PROCESSING
        order_repository.update_order_status(order2.id, OrderStatus.PROCESSING)
        
        # Get pending orders
        pending_orders = order_repository.get_pending_orders()
        
        assert len(pending_orders) == 1
        assert pending_orders[0].id == order1.id
        assert pending_orders[0].status == OrderStatus.PENDING