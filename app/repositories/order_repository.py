from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from decimal import Decimal

from app.database import get_db
from app.models.database_models import OrderDB, OrderItemDB, OrderStatusHistoryDB, OrderStatus
from app.models.pydantic_models import CreateOrderRequest, OrderResponse, OrderItem

class OrderNotFoundError(Exception):
    """Raised when an order is not found"""
    pass

class OrderRepository:
    """Repository for order data access operations"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def _get_db(self) -> Session:
        """Get database session"""
        if self.db:
            return self.db
        return next(get_db())
    
    def create_order(self, order_data: CreateOrderRequest) -> OrderResponse:
        """Create a new order with items"""
        db = self._get_db()
        
        try:
            # Calculate total amount
            total_amount = sum(
                item.quantity * item.unit_price 
                for item in order_data.items
            )
            
            # Create order
            db_order = OrderDB(
                customer_id=order_data.customer_id,
                status=OrderStatus.PENDING,
                total_amount=total_amount
            )
            
            db.add(db_order)
            db.flush()  # Get the order ID
            
            # Create order items
            db_items = []
            for item in order_data.items:
                db_item = OrderItemDB(
                    order_id=db_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                db_items.append(db_item)
                db.add(db_item)
            
            # Create initial status history
            status_history = OrderStatusHistoryDB(
                order_id=db_order.id,
                old_status=None,
                new_status=OrderStatus.PENDING,
                changed_by="system"
            )
            db.add(status_history)
            
            db.commit()
            
            # Convert to response model
            return self._convert_to_response(db_order, db_items)
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if not self.db:  # Only close if we created the session
                db.close()
    
    def get_order_by_id(self, order_id: Union[UUID, str]) -> Optional[OrderResponse]:
        """Get order by ID with all items"""
        db = self._get_db()
        
        try:
            # Convert UUID to string if needed
            order_id_str = str(order_id) if isinstance(order_id, UUID) else order_id
            
            db_order = db.query(OrderDB).options(
                joinedload(OrderDB.items)
            ).filter(OrderDB.id == order_id_str).first()
            
            if not db_order:
                return None
            
            return self._convert_to_response(db_order, db_order.items)
            
        finally:
            if not self.db:
                db.close()
    
    def list_orders(
        self, 
        status: Optional[OrderStatus] = None, 
        page: int = 1, 
        limit: int = 50
    ) -> tuple[List[OrderResponse], int]:
        """List orders with optional status filtering and pagination"""
        db = self._get_db()
        
        try:
            query = db.query(OrderDB).options(joinedload(OrderDB.items))
            
            # Apply status filter
            if status:
                query = query.filter(OrderDB.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            orders = query.order_by(desc(OrderDB.created_at)).offset(offset).limit(limit).all()
            
            # Convert to response models
            order_responses = [
                self._convert_to_response(order, order.items) 
                for order in orders
            ]
            
            return order_responses, total
            
        finally:
            if not self.db:
                db.close()
    
    def update_order_status(
        self, 
        order_id: Union[UUID, str], 
        new_status: OrderStatus, 
        changed_by: str = "system"
    ) -> bool:
        """Update order status and record in history"""
        db = self._get_db()
        
        try:
            # Convert UUID to string if needed
            order_id_str = str(order_id) if isinstance(order_id, UUID) else order_id
            
            db_order = db.query(OrderDB).filter(OrderDB.id == order_id_str).first()
            
            if not db_order:
                return False
            
            old_status = db_order.status
            
            # Update order status
            db_order.status = new_status
            
            # Record status change in history
            status_history = OrderStatusHistoryDB(
                order_id=order_id_str,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by
            )
            db.add(status_history)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if not self.db:
                db.close()
    
    def cancel_order(self, order_id: Union[UUID, str]) -> bool:
        """Cancel an order (only if PENDING)"""
        db = self._get_db()
        
        try:
            # Convert UUID to string if needed
            order_id_str = str(order_id) if isinstance(order_id, UUID) else order_id
            
            db_order = db.query(OrderDB).filter(OrderDB.id == order_id_str).first()
            
            if not db_order:
                raise OrderNotFoundError(f"Order {order_id} not found")
            
            if db_order.status != OrderStatus.PENDING:
                return False  # Cannot cancel non-pending orders
            
            # Update to cancelled status
            return self.update_order_status(order_id_str, OrderStatus.CANCELLED, "customer")
            
        finally:
            if not self.db:
                db.close()
    
    def get_pending_orders(self) -> List[OrderDB]:
        """Get all orders with PENDING status for background processing"""
        db = self._get_db()
        
        try:
            return db.query(OrderDB).filter(OrderDB.status == OrderStatus.PENDING).all()
        finally:
            if not self.db:
                db.close()
    
    def _convert_to_response(self, db_order: OrderDB, db_items: List[OrderItemDB]) -> OrderResponse:
        """Convert database models to response model"""
        items = [
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price
            )
            for item in db_items
        ]
        
        return OrderResponse(
            id=db_order.id,
            customer_id=db_order.customer_id,
            status=db_order.status,
            total_amount=db_order.total_amount,
            items=items,
            created_at=db_order.created_at,
            updated_at=db_order.updated_at
        )