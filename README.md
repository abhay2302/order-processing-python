# E-commerce Order Processing System

A robust backend system for handling e-commerce order processing with automated status updates, comprehensive testing, and property-based validation.

## 🚀 Features

- **Order Management**: Create, retrieve, update, and cancel orders
- **Automated Status Updates**: Background job updates PENDING orders to PROCESSING every 5 minutes
- **Status Workflow**: PENDING → PROCESSING → SHIPPED → DELIVERED (with CANCELLED option)
- **Comprehensive Testing**: Unit tests, integration tests, and property-based tests
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Database Support**: SQLite for development, PostgreSQL for production
- **Background Jobs**: APScheduler for automated order processing

## 📋 Requirements

- Python 3.8+
- SQLite (development) or PostgreSQL (production)
- Virtual environment (recommended)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd order-processing-system
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations** (optional for SQLite):
   ```bash
   alembic upgrade head
   ```

## 🚀 Quick Start

### Start the Application

```bash
python run_app.py
```

The application will start on `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Test the System

```bash
python test_app.py
```

## 📚 API Endpoints

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders/` | Create a new order |
| GET | `/orders/{order_id}` | Get order by ID |
| GET | `/orders/` | List orders (with optional status filter) |
| PUT | `/orders/{order_id}/status` | Update order status |
| DELETE | `/orders/{order_id}` | Cancel order (PENDING only) |

### Example Usage

#### Create Order
```bash
curl -X POST "http://localhost:8000/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer_123",
    "items": [
      {
        "product_id": "laptop",
        "quantity": 1,
        "unit_price": 999.99
      },
      {
        "product_id": "mouse",
        "quantity": 2,
        "unit_price": 25.50
      }
    ]
  }'
```

#### Get Order
```bash
curl "http://localhost:8000/orders/{order_id}"
```

#### List Orders
```bash
curl "http://localhost:8000/orders/?status=PENDING&page=1&limit=10"
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests
pytest tests/test_repository.py tests/test_service.py -v

# API tests
pytest tests/test_api.py -v

# Property-based tests
pytest tests/test_properties.py -v
```

### Property-Based Tests

The system includes comprehensive property-based tests that validate:

1. **Order Total Calculation**: Ensures total equals sum of (quantity × unit_price)
2. **Status Transition Validity**: Validates proper status workflow
3. **Cancellation Rules**: Orders can only be cancelled when PENDING
4. **Order Persistence**: Created orders can always be retrieved identically
5. **Background Job Idempotency**: Multiple job runs produce consistent results

## 🏗️ Architecture

```
┌─────────────────┐
│   API Layer     │  (FastAPI)
├─────────────────┤
│ Business Logic  │  (Service Classes)
├─────────────────┤
│ Data Access     │  (Repository Pattern)
├─────────────────┤
│   Database      │  (SQLite/PostgreSQL)
└─────────────────┘
```

### Key Components

- **Models**: Pydantic models for request/response validation
- **Repository**: Data access layer with SQLAlchemy
- **Service**: Business logic and validation
- **API**: FastAPI endpoints with automatic documentation
- **Background Jobs**: APScheduler for automated processing

## 📊 Database Schema

### Orders Table
- `id`: UUID primary key
- `customer_id`: Customer identifier
- `status`: Order status (PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
- `total_amount`: Calculated total amount
- `created_at`, `updated_at`: Timestamps

### Order Items Table
- `id`: UUID primary key
- `order_id`: Foreign key to orders
- `product_id`: Product identifier
- `quantity`: Item quantity
- `unit_price`: Price per unit

### Order Status History Table
- `id`: UUID primary key
- `order_id`: Foreign key to orders
- `old_status`, `new_status`: Status transition
- `changed_at`: Timestamp
- `changed_by`: Who made the change

## ⚙️ Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string (default: SQLite)
- `LOG_LEVEL`: Logging level (default: INFO)

### Development
```bash
export DATABASE_URL="sqlite:///./order_processing.db"
```

### Production
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/order_processing"
```

## 🔄 Background Jobs

The system includes an automated background job that:
- Runs every 5 minutes
- Updates all PENDING orders to PROCESSING status
- Maintains idempotency (safe to run multiple times)
- Includes comprehensive error handling and logging

## 🛡️ Error Handling

The system includes comprehensive error handling:
- **Validation Errors**: 422 Unprocessable Entity
- **Business Logic Errors**: 400 Bad Request
- **Not Found**: 404 Not Found
- **Conflicts**: 409 Conflict (invalid status transitions)
- **Server Errors**: 500 Internal Server Error

## 📈 Performance

- **Order Creation**: < 200ms response time
- **Order Retrieval**: < 100ms response time
- **Order Listing**: < 500ms response time (up to 1000 orders)
- **Database Optimization**: Proper indexing and connection pooling
- **Pagination**: Efficient handling of large datasets

## 🔒 Security

- Input validation on all endpoints
- SQL injection protection via parameterized queries
- Rate limiting middleware
- Request size limits
- Comprehensive logging for security monitoring

## 🚀 Deployment

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_app.py"]
```

### Production Checklist
- [ ] Set up PostgreSQL database
- [ ] Configure environment variables
- [ ] Set up reverse proxy (nginx)
- [ ] Configure logging and monitoring
- [ ] Set up database backups
- [ ] Configure SSL/TLS

## 📝 Development

### Project Structure
```
order-processing-system/
├── app/
│   ├── api/           # FastAPI endpoints
│   ├── background/    # Background job scheduler
│   ├── models/        # Pydantic and SQLAlchemy models
│   ├── repositories/  # Data access layer
│   ├── services/      # Business logic
│   ├── database.py    # Database configuration
│   └── main.py        # FastAPI application
├── tests/             # Test suite
├── alembic/           # Database migrations
├── requirements.txt   # Python dependencies
├── run_app.py        # Application startup script
└── test_app.py       # Manual testing script
```

### Adding New Features

1. **Add Models**: Update Pydantic and SQLAlchemy models
2. **Update Repository**: Add data access methods
3. **Update Service**: Add business logic
4. **Add API Endpoints**: Create FastAPI routes
5. **Write Tests**: Add unit, integration, and property-based tests
6. **Update Documentation**: Update API docs and README

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the test suite for usage examples
- Run `python test_app.py` for a comprehensive system test

---

**Built with ❤️ using FastAPI, SQLAlchemy, and modern Python practices**