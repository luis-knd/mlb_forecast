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

from src.infrastructure.cache.cache_provider import connect_cache, disconnect_cache
from src.infrastructure.config.settings import settings
from src.infrastructure.db.database import create_tables
from src.infrastructure.ml.model_adapter import MLModelAdapter
from src.interface.rest.exception_handlers import DomainExceptions, ExceptionHandlerMiddleware, domain_exception_handler
from src.interface.rest.generated.models.models import RootResponse
from src.interface.rest.response_handler import ResponseHandler
from src.interface.rest.routes import router as api_router

# Initialize ML model (cache handled by cache_provider)
ml_model_adapter = MLModelAdapter()


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
    # MLB Predictions Backend API

    Enterprise-grade MLB game prediction platform delivering real-time analytics and machine learning insights.

    ## 🚀 Core Features

    ### ⚾ **Data Ingestion Pipeline**
    - Real-time game results from official MLB APIs
    - Historical statistics and performance metrics
    - Live game schedules and league standings
    - Automated data validation and cleansing

    ### 🤖 **Advanced Machine Learning**
    - Probabilistic game outcome predictions
    - Total runs and score forecasting
    - Player performance analytics
    - Continuous model training and optimization

    ### ⚡ **High-Performance Architecture**
    - Multi-layer Redis caching system
    - Optimized database queries with indexing
    - Asynchronous processing for scalability
    - Sub-second API response times

    ### 📊 **Analytics & Insights**
    - Team performance trending
    - Head-to-head historical analysis
    - Weather impact on game outcomes
    - Injury reports integration

    ## 🔧 Technical Stack

    - **Framework**: FastAPI with async/await patterns
    - **Database**: PostgreSQL with optimized schemas
    - **Cache**: Redis for high-speed data retrieval
    - **ML**: Scikit-learn with automated retraining
    - **Architecture**: Hexagonal/Clean architecture principles

    ## 📈 API Capabilities

    - Hexagonal architecture for modularity
    - RESTful endpoints with OpenAPI documentation
    - Real-time prediction scoring
    - Batch prediction processing
    - Model performance monitoring
    - Comprehensive error handling and logging

    ## 📝 API Response Format

    All endpoints return responses in the following standardized format:

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
