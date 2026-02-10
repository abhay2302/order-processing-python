from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./order_processing.db"  # Default to SQLite for development
)

# For testing, use SQLite in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"

def get_database_url(testing: bool = False) -> str:
    return TEST_DATABASE_URL if testing else DATABASE_URL

def create_database_engine(testing: bool = False):
    url = get_database_url(testing)
    
    if "sqlite" in url:
        # SQLite configuration
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
    else:
        # PostgreSQL configuration for production
        engine = create_engine(
            url,
            pool_size=20,
            max_overflow=0,
            echo=False
        )
    
    return engine

# Create engine and session factory
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()