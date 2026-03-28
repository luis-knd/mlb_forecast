"""
Main FastAPI application entry point using hexagonal architecture.
This module initializes the FastAPI application, sets up middleware, and includes routers.
"""

import logging
import logging.config
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.cache.cache_provider import connect_cache, disconnect_cache
from infrastructure.config.settings import settings
from infrastructure.db.database import create_tables
from infrastructure.ml.model_adapter import MLModelAdapter
from interface.rest.exception_handlers import DomainExceptions, ExceptionHandlerMiddleware, domain_exception_handler
from interface.rest.generated.models.models import RootResponse
from interface.rest.response_handler import ResponseHandler
from interface.rest.routes import router as api_router

# Initialize ML model (cache handled by cache_provider)
ml_model_adapter = MLModelAdapter()
OPENAPI_TAG_METADATA = [
    {
        "name": "Teams",
        "description": "Team catalogue, lookup endpoints and team-focused operations.",
    },
    {
        "name": "Games",
        "description": "Game schedule, retrieval and game-related ingestion workflows.",
    },
    {
        "name": "Players",
        "description": "Player lookup, hydration and player-focused operations.",
    },
    {
        "name": "Stats",
        "description": "Read-only statistical views served from persisted data.",
    },
    {
        "name": "Predictions",
        "description": "Prediction generation and prediction retrieval endpoints.",
    },
    {
        "name": "Data Ingestion",
        "description": "Write-oriented endpoints that ingest or refresh external MLB data.",
    },
    {
        "name": "System",
        "description": "Operational endpoints for health, cache and runtime diagnostics.",
    },
    {
        "name": "ML Model",
        "description": "Machine learning maintenance operations such as retraining.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    This handles startup and shutdown events.
    """
    # Startup
    logging.info("Starting application...")

    # Create database tables
    create_tables()

    # Connect to Redis via singleton provider
    await connect_cache()

    # Initialize ML model
    try:
        await ml_model_adapter.load_model(f"{settings.MODEL_DIR}/current_model.pkl")
        logging.info("ML model loaded successfully")
    except Exception as e:
        logging.warning(f"Could not load ML model: {e}")

    yield

    # Shutdown
    logging.info("Shutting down application...")

    # Disconnect from Redis via singleton provider
    await disconnect_cache()


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    # MLB Forecast API

    Backend API for MLB forecasts, persisted stats retrieval, and ingestion workflows backed by PostgreSQL,
    Redis, and MLB StatsAPI integrations.

    ## Main domains

    - Teams and team season stats
    - Games and schedules
    - Players and persisted player stats
    - Predictions
    - Data ingestion and ML maintenance
    - System diagnostics for health, cache, and runtime information

    ## Contract

    - `openapi/openapi.yml` is the design-first contract for public endpoints.
    - The static contract and the OpenAPI served by FastAPI should stay aligned.

    ## Response envelope

    All JSON endpoints return the standard response envelope:

    ```json
    {
        "status": "success|error",
        "code": 200,
        "data": {},
        "errors": [],
        "message": "Optional descriptive message"
    }
    ```
    """,
    version=settings.API_VERSION,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAG_METADATA,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
            },
        },
        "handlers": {
            "console": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
            }
        },
    }
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", response_model=RootResponse)
async def root():
    """Root endpoint providing basic information about the API."""
    return ResponseHandler.success(
        data={
            "message": "MLB Forecast Backend API",
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        },
        message="Welcome to MLB Forecast API",
    )


# Centralized Exception Handlers
app.add_exception_handler(ValidationError, ExceptionHandlerMiddleware.validation_exception_handler)  # type: ignore
app.add_exception_handler(HTTPException, ExceptionHandlerMiddleware.http_exception_handler)  # type: ignore
app.add_exception_handler(SQLAlchemyError, ExceptionHandlerMiddleware.sqlalchemy_exception_handler)  # type: ignore

# Domain exceptions
for exception_class in [
    DomainExceptions.TeamNotFoundError,
    DomainExceptions.PlayerNotFoundError,
    DomainExceptions.GameNotFoundError,
    DomainExceptions.InvalidDataError,
    DomainExceptions.ExternalServiceError,
]:
    app.add_exception_handler(exception_class, domain_exception_handler)

# General exception handlers (keep these last)
app.add_exception_handler(Exception, ExceptionHandlerMiddleware.general_exception_handler)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
