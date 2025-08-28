from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator
from .settings import settings

# Create engine with connection pooling using settings
engine = create_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,
    pool_recycle=settings.database.pool_recycle,
    echo=settings.database.echo
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create Base class for models
Base = declarative_base()

# Dependency để get database session
def get_db() -> Generator:
    """
    Database session dependency

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Database connection test
def test_db_connection() -> bool:
    """
    Test database connection

    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        print(f"Database URL: {settings.database.url}")
        return False

# Initialize database tables
def init_db():
    """
    Initialize database tables for appointment management
    """
    try:
        # Import all appointment models to ensure they are registered with Base
        from src.models.appointment import (
            Department, Doctor, DoctorAvailableSlot,
            Patient, Appointment
        )

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Appointment management database tables created successfully")

        if settings.database.echo:
            print(f"Database URL: {settings.database.url}")
            print(f"Pool size: {settings.database.pool_size}")

    except Exception as e:
        print(f"Failed to create appointment management database tables: {e}")
        print(f"Database URL: {settings.database.url}")
        raise