"""
Centralized response handler for REST API endpoints.
Implements standardized JSON responses following REST best practices.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ResponseStatus(str, Enum):
    """Response status enumeration."""

    SUCCESS = "success"
    ERROR = "error"


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for complex types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, BaseModel):
            return obj.model_dump()
        elif hasattr(obj, "__dict__"):
            return {key: value for key, value in obj.__dict__.items() if not key.startswith("_")}
        return super().default(obj)


@dataclass
class APIResponse:
    """Standardized API response structure."""

    status: ResponseStatus
    code: int
    data: Optional[Union[Dict[str, Any], List[Any], Any]] = None
    errors: Optional[List[str]] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format with proper serialization."""
        # Use FastAPI's jsonable_encoder for initial conversion
        serialized_data = jsonable_encoder(self.data) if self.data is not None else None

        result = {
            "status": self.status.value,
            "code": self.code,
            "data": serialized_data,
            "errors": self.errors or [],
        }

        if self.message:
            result["message"] = self.message

        return result


class ResponseHandler:
    """Centralized response handler for consistent API responses."""

    @staticmethod
    def success(
        data: Optional[Union[Dict[str, Any], List[Any], Any]] = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
    ) -> JSONResponse:
        """
        Create a successful response.

        Args:
            data: Response data payload
            message: Optional success message
            status_code: HTTP status code (default: 200)

        Returns:
            JSONResponse: Standardized success response
        """
        response = APIResponse(status=ResponseStatus.SUCCESS, code=status_code, data=data, message=message)

        # Use custom JSON encoder for proper serialization
        content = json.loads(json.dumps(response.to_dict(), cls=CustomJSONEncoder))

        return JSONResponse(status_code=status_code, content=content)

    @staticmethod
    def error(
        errors: Union[str, List[str]],
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> JSONResponse:
        """
        Create an error response.

        Args:
            errors: Error messages (string or list of strings)
            status_code: HTTP status code (default: 500)
            message: Optional error message
            data: Optional additional data

        Returns:
            JSONResponse: Standardized error response
        """
        if isinstance(errors, str):
            errors = [errors]

        response = APIResponse(status=ResponseStatus.ERROR, code=status_code, data=data, errors=errors, message=message)

        # Use custom JSON encoder for proper serialization
        content = json.loads(json.dumps(response.to_dict(), cls=CustomJSONEncoder))

        return JSONResponse(status_code=status_code, content=content)

    @staticmethod
    def not_found(resource: str = "Resource", identifier: Optional[Union[str, int]] = None) -> JSONResponse:
        """
        Create a 404 not found response.

        Args:
            resource: Name of the resource that was not found
            identifier: Optional identifier that was searched for

        Returns:
            JSONResponse: Standardized 404 response
        """
        if identifier:
            message = f"{resource} with ID {identifier} not found"
        else:
            message = f"{resource} not found"

        return ResponseHandler.error(
            errors=[message], status_code=status.HTTP_404_NOT_FOUND, message="Resource not found"
        )

    @staticmethod
    def bad_request(errors: Union[str, List[str]], message: str = "Invalid request") -> JSONResponse:
        """
        Create a 400 bad request response.

        Args:
            errors: Validation error messages
            message: Optional error message

        Returns:
            JSONResponse: Standardized 400 response
        """
        return ResponseHandler.error(errors=errors, status_code=status.HTTP_400_BAD_REQUEST, message=message)

    @staticmethod
    def created(data: Optional[Any] = None, message: str = "Resource created successfully") -> JSONResponse:
        """
        Create a 201 created response.

        Args:
            data: Created resource data
            message: Success message

        Returns:
            JSONResponse: Standardized 201 response
        """
        return ResponseHandler.success(data=data, message=message, status_code=status.HTTP_201_CREATED)

    @staticmethod
    def no_content(message: str = "Operation completed successfully") -> JSONResponse:
        """
        Create a 204 no content response.

        Args:
            message: Success message

        Returns:
            JSONResponse: Standardized 204 response
        """
        return ResponseHandler.success(message=message, status_code=status.HTTP_204_NO_CONTENT)
