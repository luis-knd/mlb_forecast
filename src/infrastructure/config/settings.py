"""
Application settings.
This module defines the application settings using Pydantic's BaseSettings class.
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = os.getenv("APP_NAME", "MLB Forecast API")
    API_VERSION: str = "1.0.0"

    # Environment settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_NAME: str = os.getenv("APP_NAME", "MLB Forecast API")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./mlb_forecast.db")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
    REDIS_TIMEOUT: int = int(os.getenv("REDIS_TIMEOUT", "5"))

    # MLB API settings
    MLB_API_BASE_URL: str = os.getenv("MLB_API_BASE_URL", "https://statsapi.mlb.com/api")
    MLB_API_VERSION: str = os.getenv("MLB_API_VERSION", "v1")
    MLB_API_TIMEOUT: int = int(os.getenv("MLB_API_TIMEOUT", "10"))
    MLB_API_MAX_RETRIES: int = int(os.getenv("MLB_API_MAX_RETRIES", "2"))
    MLB_API_BACKOFF_FACTOR: float = float(os.getenv("MLB_API_BACKOFF_FACTOR", "0.5"))
    MLB_PLAYER_STATS_ALL_GROUPS_CONCURRENCY: int = int(os.getenv("MLB_PLAYER_STATS_ALL_GROUPS_CONCURRENCY", "2"))

    # ML model settings
    MODEL_DIR: str = "models"  # TODO this does not exist yet
    DEFAULT_MODEL_VERSION: str = "1.0.0"
    ML_MODEL_RETRAIN_INTERVAL: int = int(os.getenv("ML_MODEL_RETRAIN_INTERVAL", "86400"))
    ML_MIN_GAMES_FOR_PREDICTION: int = int(os.getenv("ML_MIN_GAMES_FOR_PREDICTION", "10"))

    # Cache settings
    CACHE_DEFAULT_TTL: int = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
    CACHE_GAMES_TTL: int = int(os.getenv("CACHE_GAMES_TTL", "1800"))
    CACHE_STATS_TTL: int = int(os.getenv("CACHE_STATS_TTL", "7200"))

    # API rate limiting
    API_RATE_LIMIT_CALLS: int = int(os.getenv("API_RATE_LIMIT_CALLS", "100"))
    API_RATE_LIMIT_WINDOW: int = int(os.getenv("API_RATE_LIMIT_WINDOW", "60"))

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "allow"}


# Create settings instance
settings = Settings()
