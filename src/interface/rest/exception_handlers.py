"""
Exception handlers for centralized error management.
Implements consistent error handling across the application.
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.domain.exceptions import (
    ExternalServiceError,
    GameNotFoundError,
    InvalidDataError,
    PlayerNotFoundError,
    TeamNotFoundError,
)
from src.interface.rest.response_handler import ResponseHandler


class ExceptionHandlerMiddleware:
    """Centralized exception handling middleware."""

    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle HTTP exceptions with standardized responses.

        Args:
            request: FastAPI request object
            exc: HTTP exception instance

        Returns:
            JSONResponse: Standardized error response
        """
        logging.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

        return ResponseHandler.error(
            errors=[exc.detail] if isinstance(exc.detail, str) else exc.detail,
            status_code=exc.status_code,
            message=f"HTTP {exc.status_code} Error",
        )

    @staticmethod
    async def validation_exception_handler(request: Request, exc: Exception) -> Response:
        """
        Handle Pydantic validation exceptions.

        Args:
            request: FastAPI request object
            exc: Exception instance (expected to be ValidationError)

        Returns:
            Response: Standardized validation error response
        """
        if not isinstance(exc, ValidationError):
            logging.error(f"Expected ValidationError, got {type(exc).__name__}: {exc}")
            return ResponseHandler.error(
                errors=["Validation failed"],
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid request data",
            )

        logging.warning(f"Validation Error: {exc.errors()}")

        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"{field}: {message}")

        return ResponseHandler.bad_request(
            errors=errors,
            message="Validation failed",
        )

    @staticmethod
    async def sqlalchemy_exception_handler(request: Request, exc: Exception) -> Response:
        """
        Handle SQLAlchemy database exceptions.

        Args:
            request: FastAPI request object
            exc: Exception instance (expected to be SQLAlchemyError)

        Returns:
            Response: Standardized database error response
        """
        if not isinstance(exc, SQLAlchemyError):
            logging.error(f"Expected SQLAlchemyError, got {type(exc).__name__}: {exc}")
            return ResponseHandler.error(
                errors=["Database operation failed"],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
            )

        logging.error(f"Database Error: {str(exc)}")

        if isinstance(exc, IntegrityError):
            return ResponseHandler.bad_request(
                errors=["Data integrity constraint violation"],
                message="Invalid data provided",
            )

        return ResponseHandler.error(
            errors=["Database operation failed"],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
        )

    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception) -> Response:
        """
        Handle general unhandled exceptions.

        Args:
            request: FastAPI request object
            exc: General exception

        Returns:
            Response: Standardized server error response
        """
        logging.error(f"Unhandled Exception: {type(exc).__name__} - {str(exc)}")

        return ResponseHandler.error(
            errors=["An unexpected error occurred"],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
        )


class DomainExceptions:
    """Domain-specific exceptions for business logic errors."""

    TeamNotFoundError = TeamNotFoundError
    PlayerNotFoundError = PlayerNotFoundError
    GameNotFoundError = GameNotFoundError
    InvalidDataError = InvalidDataError
    ExternalServiceError = ExternalServiceError


async def domain_exception_handler(request: Request, exc: Exception) -> Response:
    """
    Handle domain-specific exceptions.

    Args:
        request: FastAPI request object
        exc: Domain exception

    Returns:
        Response: Appropriate error response based on exception type
    """
    if isinstance(exc, DomainExceptions.TeamNotFoundError):
        return ResponseHandler.not_found("Team", exc.team_id)

    elif isinstance(exc, DomainExceptions.PlayerNotFoundError):
        return ResponseHandler.not_found("Player", exc.player_id)

    elif isinstance(exc, DomainExceptions.GameNotFoundError):
        return ResponseHandler.not_found("Game", exc.game_id)

    elif isinstance(exc, DomainExceptions.InvalidDataError):
        return ResponseHandler.bad_request(
            errors=[str(exc)],
            message="Invalid data provided",
        )

    elif isinstance(exc, DomainExceptions.ExternalServiceError):
        logging.error(f"External service error: {exc.service} - {str(exc)}")
        return ResponseHandler.error(
            errors=[f"External service unavailable: {exc.service}"],
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Service temporarily unavailable",
        )

    # If it's not a known domain exception, let the general handler take care of it
    return await ExceptionHandlerMiddleware.general_exception_handler(request, exc)
