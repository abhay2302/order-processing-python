from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
from contextlib import asynccontextmanager

from app.api.orders import router as orders_router
from app.background.scheduler import OrderStatusUpdater
from app.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    global scheduler
    
    # Startup
    logger.info("Starting Order Processing System...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Start background scheduler
    try:
        from app.services.order_service import OrderService
        from app.repositories.order_repository import OrderRepository
        
        order_repository = OrderRepository()
        order_service = OrderService(order_repository)
        scheduler = OrderStatusUpdater(order_service)
        scheduler.start()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Order Processing System...")
    if scheduler:
        scheduler.stop()
        logger.info("Background scheduler stopped")

# Create FastAPI application
app = FastAPI(
    title="E-commerce Order Processing System",
    description="A backend system for handling e-commerce order processing",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response

# Include routers
app.include_router(orders_router, prefix="/orders", tags=["orders"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the UI at root
from fastapi.responses import FileResponse

@app.get("/")
async def serve_ui():
    """Serve the main UI"""
    return FileResponse("static/index.html")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "order-processing-system",
        "version": "1.0.0"
    }

# API info endpoint
@app.get("/api")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "E-commerce Order Processing System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ui": "/"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )