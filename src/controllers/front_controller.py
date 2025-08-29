from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.controllers.appointment_controller import router as appointment_router
from config.settings import settings
from config.database import test_db_connection, init_db
from config.database_utils import (
    get_database_info,
    diagnose_database_issues
)
from src.services.event_publisher import get_event_publisher
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with settings
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting {settings.app.title} v{settings.app.version}")
    logger.info(f"Database URL: {settings.database.url}")
    logger.info(f"RabbitMQ Host: {settings.rabbitmq.host}:{settings.rabbitmq.port}")
    logger.info(f"Debug mode: {settings.app.debug}")

    try:
        # Test database connection
        if test_db_connection():
            logger.info("Database connection successful")
            init_db()
            logger.info("Database tables initialized")
            db_info = get_database_info()
            logger.info(f"Database: {db_info.get('driver', 'unknown')} - {db_info.get('status', 'unknown')}")
        else:
            logger.error("Database connection failed - check your database configuration")
            db_diagnosis = diagnose_database_issues()
            logger.error(f"Database diagnosis: {db_diagnosis}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    try:
        # Initialize RabbitMQ connection
        event_publisher = get_event_publisher()
        if event_publisher.connection and not event_publisher.connection.is_closed:
            logger.info("RabbitMQ connection successful")
        else:
            logger.warning("RabbitMQ connection failed - events will not be published")
    except Exception as e:
        logger.error(f"RabbitMQ initialization failed: {e}")

    yield

    # Shutdown logic
    logger.info("Shutting down application")

    try:
        # Close RabbitMQ connection
        event_publisher = get_event_publisher()
        event_publisher.close()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection: {e}")

app = FastAPI(
    title=settings.app.title,
    description=settings.app.description,
    version=settings.app.version,
    debug=settings.app.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8085"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include appointment router
app.include_router(appointment_router)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app.title}",
        "version": settings.app.version,
        "status": "running",
        "microservice": "Appointment Management"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check with database and RabbitMQ diagnostics"""
    db_status = "healthy" if test_db_connection() else "unhealthy"

    # Check RabbitMQ connection
    rabbitmq_status = "healthy"
    try:
        event_publisher = get_event_publisher()
        if not event_publisher._is_connection_healthy():
            rabbitmq_status = "unhealthy"
    except Exception:
        rabbitmq_status = "unhealthy"

    overall_status = "healthy" if db_status == "healthy" and rabbitmq_status == "healthy" else "degraded"

    health_data = {
        "status": overall_status,
        "version": settings.app.version,
        "microservice": "Appointment Management",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
        "message": "Service is running",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

    # Add detailed database info if available
    try:
        db_info = get_database_info()
        health_data["database_details"] = {
            "driver": db_info.get("driver"),
            "pool_size": settings.database.pool_size,
            "schema": "appointment_mgmt"
        }
    except Exception as e:
        health_data["database_error"] = str(e)

    # Add RabbitMQ details
    health_data["rabbitmq_details"] = {
        "host": settings.rabbitmq.host,
        "port": settings.rabbitmq.port,
        "exchange": settings.rabbitmq.exchange_name,
        "queues": ["appointment.confirmed", "appointment.cancelled"]
    }

    return health_data

@app.get("/diagnosis")
async def database_diagnosis():
    """Detailed database diagnosis endpoint"""
    return diagnose_database_issues()

# @app.get("/events/test")
# async def test_event_publishing():
#     """Test endpoint để kiểm tra RabbitMQ event publishing"""
#     try:
#         event_publisher = get_event_publisher()
#
#         # Test event data
#         test_appointment_data = {
#             "id": 9999,
#             "patient_id": 1,
#             "patient_name": "Test Patient",
#             "doctor_id": 1,
#             "doctor_name": "Test Doctor",
#             "department_id": 1,
#             "department_name": "Test Department",
#             "appointment_date": __import__("datetime").date.today(),
#             "appointment_time": __import__("datetime").time(14, 30),
#             "reason": "Test appointment for event publishing",
#             "is_emergency": False,
#             "confirmed_at": __import__("datetime").datetime.now(),
#             "confirmed_by": 1
#         }
#
#         success = event_publisher.publish_appointment_confirmed_today(test_appointment_data)
#
#         return {
#             "message": "Test confirmed event published" if success else "Failed to publish test event",
#             "success": success,
#             "event_type": "appointment_confirmed",
#             "event_data": test_appointment_data,
#             "timestamp": __import__("datetime").datetime.now().isoformat()
#         }
#
#     except Exception as e:
#         return {
#             "message": f"Error testing event publishing: {str(e)}",
#             "success": False,
#             "timestamp": __import__("datetime").datetime.now().isoformat()
#         }