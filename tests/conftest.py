import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from uuid import uuid4
from decimal import Decimal

from app.database import Base, get_db
from app.main import app
from app.models.database_models import OrderDB, OrderItemDB, OrderStatus
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService
from app.models.pydantic_models import CreateOrderRequest, OrderItem

# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create a test database session"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database dependency override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def order_repository(test_db):
    """Create OrderRepository instance with test database"""
    return OrderRepository(test_db)

@pytest.fixture
def order_service(order_repository):
    """Create OrderService instance with test repository"""
    return OrderService(order_repository)

@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return CreateOrderRequest(
        customer_id="customer_123",
        items=[
            OrderItem(
                product_id="product_1",
                quantity=2,
                unit_price=Decimal("29.99")
            ),
            OrderItem(
                product_id="product_2",
                quantity=1,
                unit_price=Decimal("15.50")
            )
        ]
    )

@pytest.fixture
def sample_order_db(test_db):
    """Create a sample order in the database"""
    order = OrderDB(
        id=uuid4(),
        customer_id="customer_123",
        status=OrderStatus.PENDING,
        total_amount=Decimal("75.48")
    )
    test_db.add(order)
    
    # Add order items
    items = [
        OrderItemDB(
            order_id=order.id,
            product_id="product_1",
            quantity=2,
            unit_price=Decimal("29.99")
        ),
        OrderItemDB(
            order_id=order.id,
            product_id="product_2",
            quantity=1,
            unit_price=Decimal("15.50")
        )
    ]
    
    for item in items:
        test_db.add(item)
    
    test_db.commit()
    test_db.refresh(order)
    
    return order

# Hypothesis strategies for property-based testing
from hypothesis import strategies as st

@pytest.fixture
def order_item_strategy():
    """Hypothesis strategy for generating OrderItem objects"""
    return st.builds(
        OrderItem,
        product_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        quantity=st.integers(min_value=1, max_value=100),
        unit_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999.99"), places=2)
    )

@pytest.fixture
def create_order_request_strategy(order_item_strategy):
    """Hypothesis strategy for generating CreateOrderRequest objects"""
    return st.builds(
        CreateOrderRequest,
        customer_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        items=st.lists(order_item_strategy, min_size=1, max_size=10)
    )

# Test utilities
class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def create_test_order(db, customer_id="test_customer", status=OrderStatus.PENDING):
        """Create a test order in the database"""
        order = OrderDB(
            customer_id=customer_id,
            status=status,
            total_amount=Decimal("100.00")
        )
        db.add(order)
        db.flush()
        
        # Add a test item
        item = OrderItemDB(
            order_id=order.id,
            product_id="test_product",
            quantity=1,
            unit_price=Decimal("100.00")
        )
        db.add(item)
        db.commit()
        
        return order
    
    @staticmethod
    def assert_order_response_valid(order_response):
        """Assert that an order response has all required fields"""
        assert order_response.id is not None
        assert order_response.customer_id is not None
        assert order_response.status is not None
        assert order_response.total_amount is not None
        assert order_response.items is not None
        assert len(order_response.items) > 0
        assert order_response.created_at is not None
        assert order_response.updated_at is not None

@pytest.fixture
def test_utils():
    """Provide test utilities"""
    return TestUtils