#!/usr/bin/env python3
"""
Startup script for the E-commerce Order Processing System
"""
import uvicorn
import os

if __name__ == "__main__":
    # Set environment variables for development
    os.environ.setdefault("DATABASE_URL", "sqlite:///./order_processing.db")
    
    print("🚀 Starting E-commerce Order Processing System")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("📋 Orders API: http://localhost:8000/orders")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )