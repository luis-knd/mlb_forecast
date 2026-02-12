from unittest.mock import AsyncMock

import pytest

from src.infrastructure.cache.redis_adapter import RedisAdapter


class TestRedisAdapter:
    @pytest.mark.asyncio
    async def test_delete_pattern(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()

        # Mock scan_iter to return a few keys
        async def mock_scan_iter(match):
            yield b"key1"
            yield b"key2"

        adapter.redis_client.scan_iter = mock_scan_iter
        adapter.redis_client.delete.return_value = 2

        # When
        deleted_count = await adapter.delete_pattern("test:*")

        # Then
        assert deleted_count == 2
        adapter.redis_client.delete.assert_called_once_with(b"key1", b"key2")

    @pytest.mark.asyncio
    async def test_delete_pattern_no_keys(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()

        # Mock scan_iter to yield nothing
        async def mock_scan_iter(match):
            if False:
                yield

        adapter.redis_client.scan_iter = mock_scan_iter

        # When
        deleted_count = await adapter.delete_pattern("test:*")

        # Then
        assert deleted_count == 0
        adapter.redis_client.delete.assert_not_called()
