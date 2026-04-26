from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.cache import cache_provider
from infrastructure.cache.redis_adapter import CacheException


@pytest.fixture(autouse=True)
def reset_cache_adapter():
    cache_provider._cache_adapter = None
    yield
    cache_provider._cache_adapter = None


def test_get_cache_adapter_reuses_singleton(monkeypatch):
    # Given
    fake_adapter = MagicMock()
    monkeypatch.setattr(cache_provider, "RedisAdapter", MagicMock(return_value=fake_adapter))

    # When
    first = cache_provider.get_cache_adapter()
    second = cache_provider.get_cache_adapter()

    # Then
    assert first is fake_adapter
    assert second is fake_adapter
    cache_provider.RedisAdapter.assert_called_once_with()


@pytest.mark.asyncio
async def test_connect_cache_connects_when_client_is_missing(monkeypatch):
    # Given
    adapter = MagicMock(redis_client=None)
    adapter.connect = AsyncMock()
    monkeypatch.setattr(cache_provider, "get_cache_adapter", MagicMock(return_value=adapter))

    # When
    await cache_provider.connect_cache()

    # Then
    adapter.connect.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_connect_cache_skips_when_already_connected(monkeypatch):
    # Given
    adapter = MagicMock(redis_client=object())
    adapter.connect = AsyncMock()
    monkeypatch.setattr(cache_provider, "get_cache_adapter", MagicMock(return_value=adapter))

    # When
    await cache_provider.connect_cache()

    # Then
    adapter.connect.assert_not_called()


@pytest.mark.asyncio
async def test_connect_cache_handles_cache_exception_with_warning(monkeypatch):
    # Given
    adapter = MagicMock(redis_client=None)
    adapter.connect = AsyncMock(side_effect=CacheException("redis unavailable"))
    warning_spy = MagicMock()
    monkeypatch.setattr(cache_provider, "get_cache_adapter", MagicMock(return_value=adapter))
    monkeypatch.setattr(cache_provider.logger, "warning", warning_spy)

    # When
    await cache_provider.connect_cache()

    # Then
    adapter.connect.assert_awaited_once_with()
    warning_spy.assert_called_once()
    assert "Skipping Redis connection at startup" in warning_spy.call_args[0][0]


@pytest.mark.asyncio
async def test_disconnect_cache_disconnects_when_client_exists(monkeypatch):
    # Given
    adapter = MagicMock(redis_client=object())
    adapter.disconnect = AsyncMock()
    monkeypatch.setattr(cache_provider, "get_cache_adapter", MagicMock(return_value=adapter))

    # When
    await cache_provider.disconnect_cache()

    # Then
    adapter.disconnect.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_disconnect_cache_handles_errors_with_warning(monkeypatch):
    # Given
    monkeypatch.setattr(cache_provider, "get_cache_adapter", MagicMock(side_effect=RuntimeError("boom")))
    warning_spy = MagicMock()
    monkeypatch.setattr(cache_provider.logger, "warning", warning_spy)

    # When
    await cache_provider.disconnect_cache()

    # Then
    warning_spy.assert_called_once()
    assert "Error disconnecting Redis at shutdown" in warning_spy.call_args[0][0]
