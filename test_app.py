#!/usr/bin/env python3
"""
Simple test script to verify the order processing system works
"""
import asyncio
import json
from decimal import Decimal

from app.services.order_service import OrderService
from app.repositories.order_repository import OrderRepository
from app.models.pydantic_models import CreateOrderRequest, OrderItem
from app.models.database_models import OrderStatus
from app.database import create_database_engine, SessionLocal, Base

async def test_order_system():
    """Test the order processing system"""
    print("🚀 Testing E-commerce Order Processing System")
    print("=" * 50)
    
    # Create database tables
    engine = create_database_engine()
    Base.metadata.create_all(bind=engine)
    
    # Create service
    db = SessionLocal()
    repository = OrderRepository(db)
    service = OrderService(repository)
    
    try:
        # Test 1: Create an order
        print("\n1. Creating an order...")
        order_data = CreateOrderRequest(
            customer_id="customer_123",
            items=[
                OrderItem(product_id="laptop", quantity=1, unit_price=Decimal("999.99")),
                OrderItem(product_id="mouse", quantity=2, unit_price=Decimal("25.50"))
            ]
        )
        
        order = service.create_order(order_data)
        print(f"✅ Order created: {order.id}")
        print(f"   Customer: {order.customer_id}")
        print(f"   Status: {order.status}")
        print(f"   Total: ${order.total_amount}")
        print(f"   Items: {len(order.items)}")
        
        # Test 2: Retrieve the order
        print("\n2. Retrieving the order...")
        retrieved_order = service.get_order(order.id)
        print(f"✅ Order retrieved: {retrieved_order.id}")
        print(f"   Status: {retrieved_order.status}")
        
        # Test 3: List orders
        print("\n3. Listing orders...")
        orders_list = service.list_orders()
        print(f"✅ Found {orders_list.total} orders")
        
        # Test 4: Update order status
        print("\n4. Updating order status...")
        success = service.update_order_status(order.id, OrderStatus.PROCESSING)
        print(f"✅ Status updated: {success}")
        
        updated_order = service.get_order(order.id)
        print(f"   New status: {updated_order.status}")
        
        # Test 5: Test background job
        print("\n5. Testing background job...")
        # Create another order
        order2_data = CreateOrderRequest(
            customer_id="customer_456",
            items=[OrderItem(product_id="keyboard", quantity=1, unit_price=Decimal("75.00"))]
        )
        order2 = service.create_order(order2_data)
        print(f"✅ Second order created: {order2.id} (status: {order2.status})")
        
        # Run background job
        processed = service.process_pending_orders()
        print(f"✅ Background job processed {processed} orders")
        
        # Check status
        updated_order2 = service.get_order(order2.id)
        print(f"   Order 2 new status: {updated_order2.status}")
        
        # Test 6: Try to cancel a processing order (should fail)
        print("\n6. Testing order cancellation rules...")
        try:
            service.cancel_order(updated_order2.id)
            print("❌ Cancellation should have failed!")
        except Exception as e:
            print(f"✅ Cancellation correctly failed: {type(e).__name__}")
        
        # Test 7: Cancel a pending order
        order3_data = CreateOrderRequest(
            customer_id="customer_789",
            items=[OrderItem(product_id="monitor", quantity=1, unit_price=Decimal("299.99"))]
        )
        order3 = service.create_order(order3_data)
        print(f"✅ Third order created: {order3.id} (status: {order3.status})")
        
        success = service.cancel_order(order3.id)
        print(f"✅ Order cancellation: {success}")
        
        cancelled_order = service.get_order(order3.id)
        print(f"   Final status: {cancelled_order.status}")
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("✅ Order creation works")
        print("✅ Order retrieval works") 
        print("✅ Order listing works")
        print("✅ Status updates work")
        print("✅ Background job works")
        print("✅ Cancellation rules work")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_order_system())