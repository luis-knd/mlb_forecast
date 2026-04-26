from unittest.mock import AsyncMock

import pytest

from interface.rest import system_routes
from interface.rest.exception_handlers import DomainExceptions


@pytest.mark.asyncio
async def test_clear_cache_rejects_invalid_pattern_type(monkeypatch):
    # Given
    use_cases = {"clear_cache": AsyncMock()}

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError):
        await system_routes.clear_cache(pattern=123, use_cases=use_cases)


@pytest.mark.asyncio
async def test_health_check_raises_external_service_error_when_unhealthy():
    # Given
    use_cases = {
        "health_check": AsyncMock(execute=AsyncMock(return_value={"status": "unhealthy", "issues": ["db down"]}))
    }

    # When / Then
    with pytest.raises(DomainExceptions.ExternalServiceError):
        await system_routes.health_check(db=object(), use_cases=use_cases)


@pytest.mark.asyncio
async def test_health_check_falls_back_when_dto_conversion_fails(monkeypatch):
    # Given
    use_cases = {"health_check": AsyncMock(execute=AsyncMock(return_value={"status": "healthy"}))}
    monkeypatch.setattr(system_routes, "HealthCheckDTO", lambda **kwargs: (_ for _ in ()).throw(ValueError("bad dto")))

    captured = {}

    def _success(*, data, message):
        captured["data"] = data
        captured["message"] = message
        return {"ok": True}

    monkeypatch.setattr(system_routes.ResponseHandler, "success", _success)

    # When
    response = await system_routes.health_check(db=object(), use_cases=use_cases)

    # Then
    assert response == {"ok": True}
    assert captured["data"] == {"status": "healthy"}


@pytest.mark.asyncio
async def test_app_info_and_cache_stats_routes(monkeypatch):
    # Given
    use_cases = {
        "get_app_info": AsyncMock(execute=AsyncMock(return_value={"name": "app"})),
        "get_cache_stats": AsyncMock(execute=AsyncMock(return_value={"keys": 1})),
    }

    monkeypatch.setattr(system_routes.ResponseHandler, "success", lambda **kwargs: kwargs)

    # When
    info_result = await system_routes.app_info(db=object(), use_cases=use_cases)
    cache_result = await system_routes.get_cache_stats(include_keys=True, pattern="*", limit=5, use_cases=use_cases)

    # Then
    assert info_result["data"]["application_info"] == {"name": "app"}
    assert cache_result["data"]["cache_stats"] == {"keys": 1}


@pytest.mark.asyncio
async def test_clear_cache_with_pattern_and_health_dto_success(monkeypatch):
    # Given
    use_cases = {
        "clear_cache": AsyncMock(execute=AsyncMock(return_value={"cleared": 2})),
        "health_check": AsyncMock(
            execute=AsyncMock(
                return_value={
                    "status": "healthy",
                    "version": "1",
                    "database": "ok",
                    "cache": "ok",
                    "ml_model": "ok",
                }
            )
        ),
    }
    monkeypatch.setattr(system_routes.ResponseHandler, "success", lambda **kwargs: kwargs)

    # When
    clear_result = await system_routes.clear_cache(pattern="mlb:*", use_cases=use_cases)
    health_result = await system_routes.health_check(db=object(), use_cases=use_cases)

    # Then
    assert clear_result["message"] == "Cache cleared with pattern: mlb:*"
    assert health_result["message"] == "System health check completed successfully"
