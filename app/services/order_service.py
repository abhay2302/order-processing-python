from typing import List, Optional, Union
from uuid import UUID
import logging

from app.repositories.order_repository import OrderRepository, OrderNotFoundError
from app.models.database_models import OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderResponse, OrderListResponse

logger = logging.getLogger(__name__)

class InvalidOrderStatusError(Exception):
    """Raised when an invalid order status transition is attempted"""
    pass

class OrderCancellationError(Exception):
    """Raised when order cancellation fails"""
    pass

class OrderService:
    """Service layer for order business logic"""
    
    def __init__(self, repository: OrderRepository):
        self.repository = repository
    
    def create_order(self, order_data: CreateOrderRequest) -> OrderResponse:
        """Create a new order with business logic validation"""
        logger.info(f"Creating order for customer: {order_data.customer_id}")
        
        # Validate business rules
        self._validate_order_data(order_data)
        
        try:
            order = self.repository.create_order(order_data)
            logger.info(f"Order created successfully: {order.id}")
            return order
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise e
    
    def get_order(self, order_id: Union[UUID, str]) -> OrderResponse:
        """Get order by ID with validation"""
        logger.info(f"Retrieving order: {order_id}")
        
        order = self.repository.get_order_by_id(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            raise OrderNotFoundError(f"Order {order_id} not found")
        
        return order
    
    def list_orders(
        self, 
        status: Optional[OrderStatus] = None, 
        page: int = 1, 
        limit: int = 50
    ) -> OrderListResponse:
        """List orders with pagination and filtering"""
        logger.info(f"Listing orders - status: {status}, page: {page}, limit: {limit}")
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 50
        
        orders, total = self.repository.list_orders(status, page, limit)
        
        # Calculate pagination info
        has_next = (page * limit) < total
        has_prev = page > 1
        
        return OrderListResponse(
            orders=orders,
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )
    
    def cancel_order(self, order_id: Union[UUID, str]) -> bool:
        """Cancel an order with business logic validation"""
        logger.info(f"Cancelling order: {order_id}")
        
        try:
            # Check if order exists and get current status
            order = self.repository.get_order_by_id(order_id)
            if not order:
                raise OrderNotFoundError(f"Order {order_id} not found")
            
            # Validate cancellation rules
            if order.status != OrderStatus.PENDING:
                logger.warning(f"Cannot cancel order {order_id} with status {order.status}")
                raise OrderCancellationError(
                    f"Cannot cancel order with status {order.status}. "
                    "Only PENDING orders can be cancelled."
                )
            
            success = self.repository.cancel_order(order_id)
            if success:
                logger.info(f"Order cancelled successfully: {order_id}")
            else:
                logger.error(f"Failed to cancel order: {order_id}")
            
            return success
            
        except (OrderNotFoundError, OrderCancellationError):
            raise
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise e
    
    def update_order_status(
        self, 
        order_id: Union[UUID, str], 
        new_status: OrderStatus, 
        changed_by: str = "system"
    ) -> bool:
        """Update order status with validation"""
        logger.info(f"Updating order {order_id} status to {new_status}")
        
        # Get current order
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise OrderNotFoundError(f"Order {order_id} not found")
        
        # Validate status transition
        if not self._is_valid_status_transition(order.status, new_status):
            raise InvalidOrderStatusError(
                f"Invalid status transition from {order.status} to {new_status}"
            )
        
        success = self.repository.update_order_status(order_id, new_status, changed_by)
        if success:
            logger.info(f"Order {order_id} status updated to {new_status}")
        
        return success
    
    def process_pending_orders(self) -> int:
        """Background job method to update PENDING orders to PROCESSING"""
        logger.info("Processing pending orders...")
        
        try:
            pending_orders = self.repository.get_pending_orders()
            processed_count = 0
            
            for order in pending_orders:
                try:
                    success = self.repository.update_order_status(
                        order.id, 
                        OrderStatus.PROCESSING, 
                        "background_job"
                    )
                    if success:
                        processed_count += 1
                        logger.debug(f"Updated order {order.id} to PROCESSING")
                except Exception as e:
                    logger.error(f"Failed to update order {order.id}: {e}")
                    continue
            
            logger.info(f"Processed {processed_count} pending orders")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing pending orders: {e}")
            raise e
    
    def _validate_order_data(self, order_data: CreateOrderRequest) -> None:
        """Validate order data according to business rules"""
        if not order_data.items:
            raise ValueError("Order must contain at least one item")
        
        total_amount = sum(item.quantity * item.unit_price for item in order_data.items)
        if total_amount <= 0:
            raise ValueError("Order total must be greater than 0")
        
        # Validate individual items
        for item in order_data.items:
            if item.quantity <= 0:
                raise ValueError(f"Item {item.product_id} quantity must be positive")
            if item.unit_price <= 0:
                raise ValueError(f"Item {item.product_id} unit price must be positive")
    
    def _is_valid_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """Validate if status transition is allowed"""
        # Define valid transitions
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],  # Terminal state
            OrderStatus.CANCELLED: []   # Terminal state
        }
        
        return new_status in valid_transitions.get(current_status, [])