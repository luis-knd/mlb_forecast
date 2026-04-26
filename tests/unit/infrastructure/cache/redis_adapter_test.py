import pickle
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.cache.redis_adapter import RedisAdapter


class TestRedisAdapter:
    @pytest.mark.asyncio
    async def test_connect_raises_cache_exception_on_pool_error(self, monkeypatch):
        # Given
        adapter = RedisAdapter()

        def _raise_from_url(*args, **kwargs):
            raise RuntimeError("no redis")

        monkeypatch.setattr(
            "infrastructure.cache.redis_adapter.redis.ConnectionPool.from_url",
            _raise_from_url,
        )

        # When / Then
        with pytest.raises(Exception, match="Redis connection error"):
            await adapter.connect()

    @pytest.mark.asyncio
    async def test_delete_pattern(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()

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

        async def mock_scan_iter(match):
            if False:
                yield

        adapter.redis_client.scan_iter = mock_scan_iter

        # When
        deleted_count = await adapter.delete_pattern("test:*")

        # Then
        assert deleted_count == 0
        adapter.redis_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_returns_default_on_miss(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.get.return_value = None

        # When
        result = await adapter.get("missing", default={"v": 1})

        # Then
        assert result == {"v": 1}

    @pytest.mark.asyncio
    async def test_get_returns_default_when_deserialization_fails(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.get.return_value = b"not-a-pickle"

        # When
        result = await adapter.get("broken", default=123)

        # Then
        assert result == 123

    @pytest.mark.asyncio
    async def test_get_returns_deserialized_value(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.get.return_value = pickle.dumps({"ok": True})

        # When
        result = await adapter.get("key")

        # Then
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_set_uses_setex(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.setex.return_value = True

        # When
        result = await adapter.set("k", {"a": 1}, ttl=10)

        # Then
        assert result is True
        adapter.redis_client.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_uses_default_ttl_when_none(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.setex.return_value = True

        # When
        result = await adapter.set("k", {"a": 1})

        # Then
        assert result is True
        _, ttl, _ = adapter.redis_client.setex.call_args.args
        assert isinstance(ttl, int)
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_exists_delete_and_clear_paths(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.exists.return_value = 1
        adapter.redis_client.delete.return_value = 2
        adapter.redis_client.keys.return_value = ["a", "b"]
        adapter.redis_client.flushdb.return_value = True

        # When
        exists = await adapter.exists("a")
        deleted = await adapter.delete("a")
        cleared_pattern = await adapter.clear(pattern="prefix:*")
        cleared_all = await adapter.clear()

        # Then
        assert exists is True
        assert deleted is True
        assert cleared_pattern == 2
        assert cleared_all == 1

    @pytest.mark.asyncio
    async def test_exists_delete_increment_decrement_handle_exceptions(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.exists.side_effect = RuntimeError("down")
        adapter.redis_client.delete.side_effect = RuntimeError("down")
        adapter.redis_client.incrby.side_effect = RuntimeError("down")
        adapter.redis_client.decrby.side_effect = RuntimeError("down")

        # When
        exists = await adapter.exists("a")
        deleted = await adapter.delete("a")
        inc = await adapter.increment("c")
        dec = await adapter.decrement("c")

        # Then
        assert exists is False
        assert deleted is False
        assert inc == 0
        assert dec == 0

    @pytest.mark.asyncio
    async def test_get_many_and_set_many_and_delete_many(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = MagicMock()
        adapter.redis_client.mget = AsyncMock(return_value=[pickle.dumps(1), None])

        pipe = MagicMock()
        pipe.setex = AsyncMock()
        pipe.execute = AsyncMock(return_value=[True, True])
        adapter.redis_client.pipeline.return_value = pipe
        adapter.redis_client.delete = AsyncMock(return_value=2)

        # When
        values = await adapter.get_many(["a", "b"])
        set_ok = await adapter.set_many({"a": 1, "b": 2}, ttl=5)
        deleted = await adapter.delete_many(["a", "b"])

        # Then
        assert values == {"a": 1, "b": None}
        assert set_ok is True
        assert deleted == 2

    @pytest.mark.asyncio
    async def test_get_many_handles_mget_failure(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.mget.side_effect = RuntimeError("boom")

        # When
        result = await adapter.get_many(["a", "b"])

        # Then
        assert result == {"a": None, "b": None}

    @pytest.mark.asyncio
    async def test_get_many_handles_invalid_pickled_value(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.mget.return_value = [b"bad", pickle.dumps("ok")]

        # When
        result = await adapter.get_many(["a", "b"])

        # Then
        assert result == {"a": None, "b": "ok"}

    @pytest.mark.asyncio
    async def test_increment_decrement_and_count_keys(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.incrby.return_value = 5
        adapter.redis_client.decrby.return_value = 4
        adapter.redis_client.dbsize.return_value = 33

        # When
        inc = await adapter.increment("count", 2)
        dec = await adapter.decrement("count", 1)
        keys = await adapter.count_keys()

        # Then
        assert inc == 5
        assert dec == 4
        assert keys == 33

    @pytest.mark.asyncio
    async def test_count_keys_returns_none_when_dbsize_errors(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.dbsize.side_effect = RuntimeError("db down")

        # When
        result = await adapter.count_keys()

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_list_keys_respects_limit_and_normalizes_bytes(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = MagicMock()

        async def _scan_iter(match, count):
            yield b"a"
            yield "b"
            yield b"c"

        adapter.redis_client.scan_iter = _scan_iter

        # When
        keys = await adapter.list_keys(pattern="*", limit=2)

        # Then
        assert keys == ["a", "b"]

    @pytest.mark.asyncio
    async def test_list_keys_handles_key_decode_error(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = MagicMock()

        class BrokenBytes(bytes):
            def decode(self, *args, **kwargs):
                raise UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")

        async def _scan_iter(match, count):
            yield BrokenBytes(b"x")

        adapter.redis_client.scan_iter = _scan_iter

        # When
        keys = await adapter.list_keys(pattern="*", limit=10)

        # Then
        assert keys == ["b'x'"]

    @pytest.mark.asyncio
    async def test_get_stats_returns_hit_rate(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.info.return_value = {
            "keyspace_hits": 9,
            "keyspace_misses": 1,
            "connected_clients": 5,
        }

        # When
        stats = await adapter.get_stats()

        # Then
        assert stats["keyspace_hits"] == 9
        assert stats["keyspace_misses"] == 1
        assert stats["hit_rate_percentage"] == 90.0

    @pytest.mark.asyncio
    async def test_disconnect_prefers_aclose_and_disconnects_pool(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.connection_pool = AsyncMock()

        # When
        await adapter.disconnect()

        # Then
        adapter.redis_client.aclose.assert_awaited_once()
        adapter.connection_pool.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_falls_back_to_close_when_no_aclose(self):
        # Given
        adapter = RedisAdapter()

        class _ClientWithoutAclose:
            async def close(self):
                return None

        class _Pool:
            async def disconnect(self):
                return None

        adapter.redis_client = _ClientWithoutAclose()
        adapter.connection_pool = _Pool()

        # When / Then
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_set_many_returns_false_when_pipeline_results_contain_false(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = MagicMock()
        pipe = MagicMock()
        pipe.setex = AsyncMock()
        pipe.execute = AsyncMock(return_value=[True, False])
        adapter.redis_client.pipeline.return_value = pipe

        # When
        result = await adapter.set_many({"a": 1, "b": 2}, ttl=5)

        # Then
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern_returns_zero_when_no_keys(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.keys.return_value = []

        # When
        cleared = await adapter.clear(pattern="none:*")

        # Then
        assert cleared == 0

    @pytest.mark.asyncio
    async def test_clear_returns_zero_on_redis_error(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.keys.side_effect = RuntimeError("down")

        # When
        result = await adapter.clear(pattern="x:*")

        # Then
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_stats_returns_error_payload_on_exception(self):
        # Given
        adapter = RedisAdapter()
        adapter.redis_client = AsyncMock()
        adapter.redis_client.info.side_effect = RuntimeError("broken")

        # When
        stats = await adapter.get_stats()

        # Then
        assert "error" in stats
