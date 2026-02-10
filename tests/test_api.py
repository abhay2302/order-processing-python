import pytest
from uuid import uuid4
from decimal import Decimal
import json

from app.models.database_models import OrderStatus

class TestOrderAPI:
    """Test cases for Order API endpoints"""
    
    def test_create_order_success(self, client, sample_order_data):
        """Test successful order creation via API"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        response = client.post(
            "/orders/",
            json=order_dict
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["customer_id"] == sample_order_data.customer_id
        assert data["status"] == "PENDING"
        assert float(data["total_amount"]) == 75.48
        assert len(data["items"]) == 2
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_order_validation_error(self, client):
        """Test order creation with validation errors"""
        invalid_order_data = {
            "customer_id": "",  # Empty customer ID
            "items": []  # Empty items list
        }
        
        response = client.post(
            "/orders/",
            json=invalid_order_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_order_business_logic_error(self, client):
        """Test order creation with business logic errors"""
        invalid_order_data = {
            "customer_id": "customer_123",
            "items": [
                {
                    "product_id": "product_1",
                    "quantity": -1,  # Invalid quantity (negative)
                    "unit_price": 10.00
                }
            ]
        }
        
        response = client.post(
            "/orders/",
            json=invalid_order_data
        )
        
        # Pydantic validation will catch this as 422, not 400
        assert response.status_code == 422
    
    def test_get_order_success(self, client, sample_order_data):
        """Test successful order retrieval via API"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order first
        create_response = client.post(
            "/orders/",
            json=order_dict
        )
        order_id = create_response.json()["id"]
        
        # Retrieve order
        response = client.get(f"/orders/{order_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == order_id
        assert data["customer_id"] == sample_order_data.customer_id
        assert data["status"] == "PENDING"
    
    def test_get_order_not_found(self, client):
        """Test order retrieval with non-existent ID"""
        non_existent_id = str(uuid4())
        
        response = client.get(f"/orders/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_order_invalid_uuid(self, client):
        """Test order retrieval with invalid UUID format"""
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/orders/{invalid_id}")
        
        assert response.status_code == 422  # Validation error
    
    def test_list_orders_success(self, client, sample_order_data):
        """Test successful order listing via API"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create multiple orders
        client.post("/orders/", json=order_dict)
        
        order2_data = {
            "customer_id": "customer_456",
            "items": [
                {
                    "product_id": "product_3",
                    "quantity": 1,
                    "unit_price": 50.00
                }
            ]
        }
        client.post("/orders/", json=order2_data)
        
        # List orders
        response = client.get("/orders/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "orders" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_next" in data
        assert "has_prev" in data
        
        assert data["total"] == 2
        assert len(data["orders"]) == 2
        assert data["page"] == 1
        assert data["limit"] == 50
        assert data["has_next"] is False
        assert data["has_prev"] is False
    
    def test_list_orders_with_status_filter(self, client, sample_order_data):
        """Test order listing with status filter"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order
        create_response = client.post("/orders/", json=order_dict)
        order_id = create_response.json()["id"]
        
        # Update order status
        client.put(
            f"/orders/{order_id}/status",
            json={"status": "PROCESSING"}
        )
        
        # Create another order (will be PENDING)
        order2_data = {
            "customer_id": "customer_456",
            "items": [
                {
                    "product_id": "product_3",
                    "quantity": 1,
                    "unit_price": 50.00
                }
            ]
        }
        client.post("/orders/", json=order2_data)
        
        # Filter by PENDING status
        response = client.get("/orders/?status=PENDING")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["orders"]) == 1
        assert data["orders"][0]["status"] == "PENDING"
    
    def test_list_orders_pagination(self, client):
        """Test order listing with pagination"""
        # Create multiple orders
        for i in range(5):
            order_data = {
                "customer_id": f"customer_{i}",
                "items": [
                    {
                        "product_id": f"product_{i}",
                        "quantity": 1,
                        "unit_price": 10.00
                    }
                ]
            }
            client.post("/orders/", json=order_data)
        
        # Test first page
        response = client.get("/orders/?page=1&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["orders"]) == 2
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False
    
    def test_update_order_status_success(self, client, sample_order_data):
        """Test successful order status update"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order
        create_response = client.post("/orders/", json=order_dict)
        order_id = create_response.json()["id"]
        
        # Update status
        response = client.put(
            f"/orders/{order_id}/status",
            json={"status": "PROCESSING", "changed_by": "test_user"}
        )
        
        assert response.status_code == 200
        assert "updated" in response.json()["message"]
        
        # Verify status was updated
        get_response = client.get(f"/orders/{order_id}")
        assert get_response.json()["status"] == "PROCESSING"
    
    def test_update_order_status_invalid_transition(self, client, sample_order_data):
        """Test order status update with invalid transition"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order
        create_response = client.post("/orders/", json=order_dict)
        order_id = create_response.json()["id"]
        
        # Try invalid transition (PENDING -> DELIVERED)
        response = client.put(
            f"/orders/{order_id}/status",
            json={"status": "DELIVERED"}
        )
        
        assert response.status_code == 409
        assert "Invalid status transition" in response.json()["detail"]
    
    def test_update_order_status_not_found(self, client):
        """Test order status update for non-existent order"""
        non_existent_id = str(uuid4())
        
        response = client.put(
            f"/orders/{non_existent_id}/status",
            json={"status": "PROCESSING"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_cancel_order_success(self, client, sample_order_data):
        """Test successful order cancellation"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order
        create_response = client.post("/orders/", json=order_dict)
        order_id = create_response.json()["id"]
        
        # Cancel order
        response = client.delete(f"/orders/{order_id}")
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
        
        # Verify order was cancelled
        get_response = client.get(f"/orders/{order_id}")
        assert get_response.json()["status"] == "CANCELLED"
    
    def test_cancel_order_not_pending(self, client, sample_order_data):
        """Test cancellation of non-pending order"""
        # Convert Decimal to float for JSON serialization
        order_dict = sample_order_data.model_dump()
        for item in order_dict["items"]:
            item["unit_price"] = float(item["unit_price"])
        
        # Create order
        create_response = client.post("/orders/", json=order_dict)
        order_id = create_response.json()["id"]
        
        # Update to PROCESSING
        client.put(
            f"/orders/{order_id}/status",
            json={"status": "PROCESSING"}
        )
        
        # Try to cancel
        response = client.delete(f"/orders/{order_id}")
        
        assert response.status_code == 409
        assert "Cannot cancel order with status PROCESSING" in response.json()["detail"]
    
    def test_cancel_order_not_found(self, client):
        """Test cancellation of non-existent order"""
        non_existent_id = str(uuid4())
        
        response = client.delete(f"/orders/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "order-processing-system"
        assert data["version"] == "1.0.0"
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data