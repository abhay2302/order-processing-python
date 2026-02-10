from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from datetime import datetime
import enum

from app.database import Base

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class OrderDB(Base):
    """Database model for orders"""
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String(255), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistoryDB", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OrderDB(id={self.id}, customer_id={self.customer_id}, status={self.status}, total_amount={self.total_amount})>"

class OrderItemDB(Base):
    """Database model for order items"""
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    order = relationship("OrderDB", back_populates="items")
    
    def __repr__(self):
        return f"<OrderItemDB(id={self.id}, product_id={self.product_id}, quantity={self.quantity}, unit_price={self.unit_price})>"

class OrderStatusHistoryDB(Base):
    """Database model for order status history (audit trail)"""
    __tablename__ = "order_status_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(SQLEnum(OrderStatus), nullable=True)
    new_status = Column(SQLEnum(OrderStatus), nullable=False)
    changed_at = Column(DateTime, default=func.now(), nullable=False)
    changed_by = Column(String(255), nullable=True)  # For future use (user/system identification)
    
    # Relationships
    order = relationship("OrderDB", back_populates="status_history")
    
    def __repr__(self):
        return f"<OrderStatusHistoryDB(id={self.id}, order_id={self.order_id}, old_status={self.old_status}, new_status={self.new_status})>"