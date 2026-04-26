from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from interface.rest import main as rest_main


@pytest.mark.asyncio
async def test_root_endpoint_returns_success_response(monkeypatch):
    # Given
    monkeypatch.setattr(rest_main.ResponseHandler, "success", lambda **kwargs: kwargs)

    # When
    response = await rest_main.root()

    # Then
    assert response["message"] == "Welcome to MLB Forecast API"
    assert "docs" in response["data"]


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown(monkeypatch):
    # Given
    monkeypatch.setattr(rest_main, "create_tables", MagicMock())
    monkeypatch.setattr(rest_main, "connect_cache", AsyncMock())
    monkeypatch.setattr(rest_main, "disconnect_cache", AsyncMock())
    monkeypatch.setattr(rest_main.ml_model_adapter, "load_model", AsyncMock(side_effect=RuntimeError("missing")))

    @asynccontextmanager
    async def _ctx():
        async with rest_main.lifespan(rest_main.app):
            yield

    # When
    async with _ctx():
        pass

    # Then
    rest_main.create_tables.assert_called_once()
    rest_main.connect_cache.assert_awaited_once()
    rest_main.disconnect_cache.assert_awaited_once()
