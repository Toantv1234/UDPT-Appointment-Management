import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

class DatabaseConfig(BaseModel):
    """Database configuration settings"""
    url: str = Field(default="postgresql://postgres:postgres@localhost:5432/postgres")
    pool_size: int = Field(default=10, ge=1, le=50)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_recycle: int = Field(default=300, ge=60)
    echo: bool = Field(default=False)

class RedisConfig(BaseModel):
    """Redis configuration settings"""
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: Optional[str] = Field(default=None)

class MongoConfig(BaseModel):
    """MongoDB configuration settings"""
    host: str = Field(default="localhost")
    port: int = Field(default=27017, ge=1, le=65535)
    database: str = Field(default="hospital-management")
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)

class AppConfig(BaseModel):
    """Application configuration settings"""
    title: str = Field(default="Hospital Management System API")
    description: str = Field(default="Backend API for Hospital Management System")
    version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=True)

    # Security
    secret_key: str = Field(default="your-secret-key-here")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)

class Settings(BaseModel):
    """Main settings class"""
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    mongo: MongoConfig = MongoConfig()

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

# Load settings from environment
def get_settings() -> Settings:
    load_dotenv("../.env")
    """
    Get application settings with environment variable overrides

    Environment variable examples:
    - APP__DEBUG=true
    - DATABASE__URL=postgresql://user:pass@localhost/db
    - REDIS__HOST=redis-server
    """
    # Load database URL with multiple fallbacks
    database_url = (
            os.getenv("DATABASE__URL") or
            os.getenv("DATABASE_URL") or
            "postgresql://postgres:postgres@localhost:5432/postgres"
    )

    return Settings(
        app=AppConfig(
            debug=os.getenv("APP__DEBUG", "false").lower() == "true",
            host=os.getenv("APP__HOST", "127.0.0.1"),
            port=int(os.getenv("APP__PORT", "8000")),
            secret_key=os.getenv("APP__SECRET_KEY", "your-secret-key-here"),
        ),
        database=DatabaseConfig(
            url=database_url,
            pool_size=int(os.getenv("DATABASE__POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DATABASE__MAX_OVERFLOW", "20")),
            pool_recycle=int(os.getenv("DATABASE__POOL_RECYCLE", "300")),
            echo=os.getenv("DATABASE__ECHO", "false").lower() == "true",
        ),
        redis=RedisConfig(
            host=os.getenv("REDIS__HOST", "localhost"),
            port=int(os.getenv("REDIS__PORT", "6379")),
            password=os.getenv("REDIS__PASSWORD"),
        ),
        mongo=MongoConfig(
            host=os.getenv("MONGO__HOST", "localhost"),
            port=int(os.getenv("MONGO__PORT", "27017")),
            database=os.getenv("MONGO__DATABASE", "hospital-management"),
            username=os.getenv("MONGO__USERNAME"),
            password=os.getenv("MONGO__PASSWORD"),
        )
    )

# Global settings instance
settings = get_settings()