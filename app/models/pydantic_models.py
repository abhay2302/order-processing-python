from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from enum import Enum

from app.models.database_models import OrderStatus

class OrderItem(BaseModel):
    """Pydantic model for order items"""
    product_id: str = Field(..., min_length=1, max_length=255, description="Product identifier")
    quantity: int = Field(..., gt=0, description="Quantity of the product")
    unit_price: Decimal = Field(..., gt=0, decimal_places=2, description="Unit price of the product")
    
    @validator('unit_price')
    def validate_unit_price(cls, v):
        if v <= 0:
            raise ValueError('Unit price must be greater than 0')
        return round(v, 2)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class CreateOrderRequest(BaseModel):
    """Request model for creating a new order"""
    customer_id: str = Field(..., min_length=1, max_length=255, description="Customer identifier")
    items: List[OrderItem] = Field(..., min_items=1, description="List of order items")
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Order must contain at least one item')
        return v

class OrderResponse(BaseModel):
    """Response model for order data"""
    id: Union[UUID, str]
    customer_id: str
    status: OrderStatus
    total_amount: Decimal
    items: List[OrderItem]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class OrderListResponse(BaseModel):
    """Response model for order listing"""
    orders: List[OrderResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool

class OrderStatusUpdate(BaseModel):
    """Request model for updating order status"""
    status: OrderStatus
    changed_by: Optional[str] = Field(None, max_length=255, description="Who changed the status")

class OrderStatusHistoryResponse(BaseModel):
    """Response model for order status history"""
    id: Union[UUID, str]
    order_id: Union[UUID, str]
    old_status: Optional[OrderStatus]
    new_status: OrderStatus
    changed_at: datetime
    changed_by: Optional[str]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str
    error_code: Optional[str] = None
    
class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    detail: str
    errors: List[dict]

# Request/Response models for specific endpoints
class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str

class RootResponse(BaseModel):
    """Root endpoint response model"""
    message: str
    version: str
    docs: str
    health: str