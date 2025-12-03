"""
Pytest configuration and fixtures for testing.

This module provides common fixtures used across all tests,
including the FastAPI test client and mock dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.interface.rest.main import app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.

    This fixture provides a TestClient instance that can be used
    to make HTTP requests to the application during testing.
    """
    # Mock the lifespan dependencies to avoid actual connections during testing
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_cache_adapter():
    """Mock cache adapter for testing."""
    mock_adapter = AsyncMock()
    mock_adapter.get.return_value = None
    mock_adapter.set.return_value = None
    mock_adapter.delete.return_value = None
    mock_adapter.connect.return_value = None
    mock_adapter.disconnect.return_value = None
    return mock_adapter


@pytest.fixture
def mock_ml_model_adapter():
    """Mock ML model adapter for testing."""
    mock_adapter = AsyncMock()
    mock_adapter.load_model.return_value = None
    mock_adapter.predict.return_value = {"prediction": 0.75}
    return mock_adapter


@pytest.fixture
def mock_database():
    """Mock database session for testing."""
    mock_db = MagicMock()
    return mock_db
