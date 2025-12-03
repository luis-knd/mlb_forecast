from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests"""
    return MagicMock()


@pytest.fixture
def mock_cache():
    """Mock cache adapter for unit tests"""
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = None
    cache.clear.return_value = None
    return cache


@pytest.fixture
def mock_repository():
    """Mock repository for use case testing"""
    return AsyncMock()
