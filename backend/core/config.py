from pydantic_settings import BaseSettings
from typing import Optional
import os
import secrets
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with security validation"""

    # Application
    APP_NAME: str = "AI CFO Suite - Phoenix"
    APP_VERSION: str = "3.0.1"
    APP_URL: str = "http://localhost:3000"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, staging, production

    # Database
    DATABASE_URL: str = "postgresql://aicfo:aicfo_secure_pass_2025@localhost:5432/aicfo_db"

    # Qdrant Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_PREFIX: str = "aicfo_"

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_ENABLED: bool = True

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "aicfo-documents"
    MINIO_SECURE: bool = False

    # AI Models
    OPENROUTER_API_KEY: Optional[str] = None  # Required for LLM access
    HUGGINGFACE_TOKEN: Optional[str] = None
    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL: str = "BAAI/bge-reranker-base"
    DEFAULT_LLM_MODEL: str = "gpt-4-turbo"  # OpenRouter model key

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 10
    RERANK_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.7

    # Agent Settings
    AGENT_TIMEOUT: int = 300  # 5 minutes
    MAX_ITERATIONS: int = 10

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-32-bytes-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # i18n (Internationalization)
    DEFAULT_LANGUAGE: str = "fr"  # French by default
    SUPPORTED_LANGUAGES: list = ["fr", "en"]  # French and English

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


def validate_production_settings(settings: Settings):
    """
    Validate that production settings are secure

    Raises:
        ValueError: If critical security settings are not configured properly
    """
    if settings.ENVIRONMENT == "production":
        errors = []

        # Check SECRET_KEY
        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            errors.append("SECRET_KEY must be set to a secure random value in production")

        if len(settings.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")

        # Check ENCRYPTION_KEY
        if settings.ENCRYPTION_KEY == "your-encryption-key-32-bytes-long":
            errors.append("ENCRYPTION_KEY must be set to a secure random value in production")

        if len(settings.ENCRYPTION_KEY) != 32:
            errors.append("ENCRYPTION_KEY must be exactly 32 bytes long for Fernet encryption")

        # Check OPENROUTER_API_KEY
        if not settings.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required in production")

        # Check DEBUG is disabled
        if settings.DEBUG:
            errors.append("DEBUG must be False in production")

        # Check database URL
        if "localhost" in settings.DATABASE_URL:
            logger.warning("DATABASE_URL contains 'localhost' - ensure this is intentional in production")

        # Check default passwords
        if settings.MINIO_ACCESS_KEY == "minioadmin" and settings.MINIO_SECRET_KEY == "minioadmin123":
            errors.append("MinIO credentials must be changed from defaults in production")

        if errors:
            error_message = "\n".join([f"  - {error}" for error in errors])
            raise ValueError(
                f"\n{'='*80}\n"
                f"PRODUCTION SECURITY VALIDATION FAILED\n"
                f"{'='*80}\n"
                f"{error_message}\n"
                f"{'='*80}\n"
                f"Please set these environment variables in your .env file or environment.\n"
                f"Example:\n"
                f"  SECRET_KEY={secrets.token_urlsafe(32)}\n"
                f"  ENCRYPTION_KEY={secrets.token_urlsafe(24)}\n"
                f"{'='*80}\n"
            )

        logger.info("✅ Production security validation passed")

    elif settings.ENVIRONMENT == "staging":
        # Warnings for staging
        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            logger.warning("⚠️  Using default SECRET_KEY in staging environment")

        if not settings.OPENROUTER_API_KEY:
            logger.warning("⚠️  OPENROUTER_API_KEY not set - LLM features will not work")

    else:
        # Development mode
        logger.info(f"🔧 Running in {settings.ENVIRONMENT} mode")

        # Auto-generate secrets if using defaults (dev only)
        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            settings.SECRET_KEY = secrets.token_urlsafe(32)
            logger.info("Generated temporary SECRET_KEY for development")

        if settings.ENCRYPTION_KEY == "your-encryption-key-32-bytes-long":
            settings.ENCRYPTION_KEY = secrets.token_urlsafe(24)  # 32 bytes base64 encoded
            logger.info("Generated temporary ENCRYPTION_KEY for development")


# Initialize settings
settings = Settings()

# Validate settings on import
try:
    validate_production_settings(settings)
except ValueError as e:
    logger.error(str(e))
    if settings.ENVIRONMENT == "production":
        raise  # Fail hard in production
    else:
        logger.warning("Continuing with invalid production settings (development mode)")


# Export helper function for generating secure keys
def generate_secret_key() -> str:
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)


def generate_encryption_key() -> str:
    """Generate a secure encryption key (32 bytes for Fernet)"""
    return secrets.token_urlsafe(24)  # 24 bytes = 32 bytes base64 encoded
