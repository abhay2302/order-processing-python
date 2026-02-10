from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, Union
from uuid import UUID
import logging

from app.services.order_service import OrderService, OrderNotFoundError, OrderCancellationError, InvalidOrderStatusError
from app.repositories.order_repository import OrderRepository
from app.models.database_models import OrderStatus
from app.models.pydantic_models import (
    CreateOrderRequest, 
    OrderResponse, 
    OrderListResponse,
    OrderStatusUpdate,
    ErrorResponse
)
from app.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Dependency to get OrderService instance"""
    repository = OrderRepository(db)
    return OrderService(repository)

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description="Create a new order with multiple items"
)
async def create_order(
    order_data: CreateOrderRequest,
    order_service: OrderService = Depends(get_order_service)
):
    """Create a new order"""
    try:
        logger.info(f"Creating order for customer: {order_data.customer_id}")
        order = order_service.create_order(order_data)
        return order
    except ValueError as e:
        logger.warning(f"Validation error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Retrieve order details by order ID"
)
async def get_order(
    order_id: Union[UUID, str],
    order_service: OrderService = Depends(get_order_service)
):
    """Get order by ID"""
    try:
        logger.info(f"Retrieving order: {order_id}")
        order = order_service.get_order(order_id)
        return order
    except OrderNotFoundError as e:
        logger.warning(f"Order not found: {order_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/",
    response_model=OrderListResponse,
    summary="List orders",
    description="List all orders with optional status filtering and pagination"
)
async def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Number of orders per page"),
    order_service: OrderService = Depends(get_order_service)
):
    """List orders with optional filtering and pagination"""
    try:
        logger.info(f"Listing orders - status: {status}, page: {page}, limit: {limit}")
        orders = order_service.list_orders(status, page, limit)
        return orders
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put(
    "/{order_id}/status",
    response_model=dict,
    summary="Update order status",
    description="Update order status (for manual status changes)"
)
async def update_order_status(
    order_id: Union[UUID, str],
    status_update: OrderStatusUpdate,
    order_service: OrderService = Depends(get_order_service)
):
    """Update order status"""
    try:
        logger.info(f"Updating order {order_id} status to {status_update.status}")
        success = order_service.update_order_status(
            order_id, 
            status_update.status, 
            status_update.changed_by or "api_user"
        )
        
        if success:
            return {"message": f"Order status updated to {status_update.status}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update order status"
            )
            
    except OrderNotFoundError as e:
        logger.warning(f"Order not found: {order_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidOrderStatusError as e:
        logger.warning(f"Invalid status transition for order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating order {order_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete(
    "/{order_id}",
    response_model=dict,
    summary="Cancel order",
    description="Cancel an order (only if status is PENDING)"
)
async def cancel_order(
    order_id: Union[UUID, str],
    order_service: OrderService = Depends(get_order_service)
):
    """Cancel an order"""
    try:
        logger.info(f"Cancelling order: {order_id}")
        success = order_service.cancel_order(order_id)
        
        if success:
            return {"message": f"Order {order_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel order"
            )
            
    except OrderNotFoundError as e:
        logger.warning(f"Order not found: {order_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except OrderCancellationError as e:
        logger.warning(f"Cannot cancel order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )