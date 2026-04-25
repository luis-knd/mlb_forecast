import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.use_cases.system_use_cases import (
    ClearCacheUseCase,
    GetAppInfoUseCase,
    GetCacheStatsUseCase,
    HealthCheckUseCase,
    SystemException,
    SystemRuntimeConfig,
)


class _CacheWithDiagnostics:
    def __init__(self):
        self.get_stats = AsyncMock(return_value={"keyspace_hits": 20, "keyspace_misses": 5, "used_memory": 123})
        self.list_keys = AsyncMock(return_value=["a", "b"])
        self.count_keys = AsyncMock(return_value=2)


def _runtime_config() -> SystemRuntimeConfig:
    return SystemRuntimeConfig(
        app_name="mlb_forecast",
        api_version="1.0.0",
        environment="test",
        debug=False,
        api_prefix="/api/v1",
        cache_default_ttl=3600,
        mlb_api_base_url="https://statsapi.mlb.com",
        mlb_api_version="v1",
    )


def test_normalize_stats_computes_totals_and_hit_rate_when_not_provided():
    # Given
    raw_stats = {"keyspace_hits": 9, "keyspace_misses": 1}

    # When
    normalized = GetCacheStatsUseCase._normalize_stats(raw_stats)

    # Then
    assert normalized["total_requests"] == 10
    assert normalized["hit_rate_percentage"] == 90.0


def test_get_introspection_port_rejects_cache_without_diagnostics_methods():
    # Given
    use_case = GetCacheStatsUseCase(cache_adapter=object())

    # When / Then
    with pytest.raises(SystemException, match="does not support cache diagnostics"):
        use_case._get_introspection_port()


def test_get_cache_stats_execute_with_keys_and_limit_bounding():
    # Given
    cache = _CacheWithDiagnostics()
    use_case = GetCacheStatsUseCase(cache_adapter=cache)

    # When
    stats = asyncio.run(use_case.execute(include_keys=True, pattern="mlb:*", limit=50000))

    # Then
    assert stats["total_keys"] == 2
    assert stats["keys_pattern"] == "mlb:*"
    assert stats["keys_returned"] == 2
    assert stats["keys"] == ["a", "b"]
    cache.list_keys.assert_awaited_once_with("mlb:*", 10000)


def test_get_cache_stats_execute_handles_count_key_errors_safely():
    # Given
    cache = _CacheWithDiagnostics()
    cache.count_keys.side_effect = RuntimeError("count failed")
    use_case = GetCacheStatsUseCase(cache_adapter=cache)

    # When
    stats = asyncio.run(use_case.execute(include_keys=False))

    # Then
    assert stats["total_keys"] is None


def test_clear_cache_execute_with_specific_pattern():
    # Given
    cache = AsyncMock(clear=AsyncMock(return_value=7))
    use_case = ClearCacheUseCase(cache_adapter=cache)

    # When
    result = asyncio.run(use_case.execute(pattern="games:*"))

    # Then
    assert result["success"] is True
    assert result["deleted_keys"] == 7
    assert result["pattern"] == "games:*"
    cache.clear.assert_awaited_once_with("games:*")


def test_clear_cache_execute_without_pattern_clears_default_groups():
    # Given
    cache = AsyncMock(clear=AsyncMock(side_effect=[1, 2, 3, 4, 5]))
    use_case = ClearCacheUseCase(cache_adapter=cache)

    # When
    result = asyncio.run(use_case.execute(pattern=None))

    # Then
    assert result["success"] is True
    assert result["deleted_keys"] == 15
    assert cache.clear.await_count == 5


def test_health_check_execute_marks_healthy_when_db_and_cache_work():
    # Given
    db = MagicMock()
    cache = AsyncMock(set=AsyncMock(), delete=AsyncMock())
    use_case = HealthCheckUseCase(cache_adapter=cache, runtime_config=_runtime_config())

    # When
    result = asyncio.run(use_case.execute(db=db))

    # Then
    assert result["status"] == "healthy"
    assert result["database"] == "connected"
    assert result["cache"] == "connected"
    assert result["ml_model"] == "not_implemented"


def test_health_check_execute_marks_unhealthy_when_dependencies_fail():
    # Given
    db = MagicMock()
    db.execute.side_effect = RuntimeError("db down")
    cache = AsyncMock(set=AsyncMock(side_effect=RuntimeError("cache down")), delete=AsyncMock())
    use_case = HealthCheckUseCase(cache_adapter=cache, runtime_config=_runtime_config())

    # When
    result = asyncio.run(use_case.execute(db=db))

    # Then
    assert result["status"] == "unhealthy"
    assert result["database"] == "disconnected"
    assert result["cache"] == "disconnected"


def test_get_app_info_execute_reports_connectivity_flags():
    # Given
    db = MagicMock()
    cache = AsyncMock(set=AsyncMock(), delete=AsyncMock())
    use_case = GetAppInfoUseCase(cache_adapter=cache, runtime_config=_runtime_config())

    # When
    info = asyncio.run(use_case.execute(db=db))

    # Then
    assert info["app_name"] == "mlb_forecast"
    assert info["database_connected"] is True
    assert info["cache_connected"] is True
    assert info["configuration"]["cache_default_ttl"] == 3600


def test_get_app_info_execute_handles_db_or_cache_disconnected():
    # Given
    db = MagicMock()
    db.execute.side_effect = RuntimeError("db down")
    cache = AsyncMock(set=AsyncMock(side_effect=RuntimeError("cache down")), delete=AsyncMock())
    use_case = GetAppInfoUseCase(cache_adapter=cache, runtime_config=_runtime_config())

    # When
    info = asyncio.run(use_case.execute(db=db))

    # Then
    assert info["database_connected"] is False
    assert info["cache_connected"] is False
