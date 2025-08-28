"""
Database utilities and helper functions
"""
from sqlalchemy import text
from .database import engine
from .settings import settings
import logging

logger = logging.getLogger(__name__)

def get_database_info() -> dict:
    """
    Get detailed database information

    Returns:
        Dict with database details
    """
    try:
        with engine.connect() as connection:
            # Get database type and version
            result = connection.execute(text("SELECT version()"))
            version_info = result.fetchone()[0] if result else "Unknown"

            return {
                "url": settings.database.url,
                "driver": engine.dialect.name,
                "version": version_info,
                "pool_size": settings.database.pool_size,
                "max_overflow": settings.database.max_overflow,
                "pool_recycle": settings.database.pool_recycle,
                "echo": settings.database.echo,
                "status": "connected"
            }
    except Exception as e:
        return {
            "url": settings.database.url,
            "driver": engine.dialect.name if engine else "Unknown",
            "error": str(e),
            "status": "disconnected"
        }

def get_connection_pool_status() -> dict:
    """
    Get connection pool status

    Returns:
        Dict with pool information
    """
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
    except Exception as e:
        return {"error": str(e)}

def diagnose_database_issues() -> dict:
    """
    Comprehensive database diagnosis

    Returns:
        Dict with diagnosis results
    """
    diagnosis = {
        "timestamp": str(__import__("datetime").datetime.now()),
        "settings": {
            "url": settings.database.url,
            "pool_size": settings.database.pool_size,
            "echo": settings.database.echo
        }
    }

    # Test basic connection
    try:
        from .database import test_db_connection
        diagnosis["connection_test"] = {"status": test_db_connection()}
    except Exception as e:
        diagnosis["connection_test"] ={"status": False}
        diagnosis["connection_error"] = str(e)

    # Get database info
    diagnosis["database_info"] = get_database_info()

    # Pool status
    diagnosis["pool_status"] = get_connection_pool_status()

    return diagnosis