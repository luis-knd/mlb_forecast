"""
REST API routes for system operations and administration.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.use_cases.system_use_cases import (
    ClearCacheUseCase,
    GetAppInfoUseCase,
    GetCacheStatsUseCase,
    HealthCheckUseCase,
    SystemRuntimeConfig,
)
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.config.settings import settings
from infrastructure.db.database import get_db
from interface.rest.exception_handlers import DomainExceptions
from interface.rest.generated.models.models import (
    AppInfoResponse,
    BadRequest,
    CacheClearResponse,
    CacheStatsResponse,
    HealthCheckDTO,
    HealthCheckResponse,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    UnprocessableEntity,
)
from interface.rest.response_handler import ResponseHandler

router = APIRouter()


def get_system_use_cases(db: Session = Depends(get_db)):
    """Get system use cases with dependencies."""
    cache_adapter = get_cache_adapter()
    runtime_config = SystemRuntimeConfig(
        app_name=settings.APP_NAME,
        api_version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        api_prefix=settings.API_V1_STR,
        cache_default_ttl=settings.CACHE_DEFAULT_TTL,
        mlb_api_base_url=settings.MLB_API_BASE_URL,
        mlb_api_version=settings.MLB_API_VERSION,
    )

    return {
        "get_cache_stats": GetCacheStatsUseCase(cache_adapter),
        "clear_cache": ClearCacheUseCase(cache_adapter),
        "health_check": HealthCheckUseCase(cache_adapter, runtime_config),
        "get_app_info": GetAppInfoUseCase(cache_adapter, runtime_config),
    }


@router.get(
    "/cache/stats",
    tags=["System"],
    response_model=CacheStatsResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def get_cache_stats(
    include_keys: bool = Query(False, description="Include a sample of keys in stats output"),
    pattern: str | None = Query(None, description="Pattern to match keys when include_keys=true (e.g., 'mlb:*')"),
    limit: int = Query(100, ge=1, le=10000, description="Max number of keys to list when include_keys=true"),
    use_cases: dict = Depends(get_system_use_cases),
) -> JSONResponse:
    """
    Get cache statistics for monitoring and debugging purposes.

    Returns detailed information about the cache system including hit rates,
    memory usage, and key statistics.

    Args:
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with cache statistics
    """
    get_cache_stats_use_case = use_cases["get_cache_stats"]
    cache_stats = await get_cache_stats_use_case.execute(include_keys=include_keys, pattern=pattern, limit=limit)

    return ResponseHandler.success(
        data={"cache_stats": cache_stats, "retrieved_at": datetime.now().isoformat()},
        message="Cache statistics retrieved successfully",
    )


@router.delete(
    "/cache",
    tags=["System"],
    response_model=CacheClearResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def clear_cache(
    pattern: str | None = Query(None, description="Pattern to clear specific cache keys (e.g., 'mlb:teams:*')"),
    use_cases: dict = Depends(get_system_use_cases),
) -> JSONResponse:
    """
    Clear cache keys based on a provided pattern.

    Removes cache entries matching the specified pattern. If no pattern is provided,
    clears all cache entries. Use with caution in production environments.

    Args:
        pattern: Optional pattern to match cache keys for selective clearing
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with operation results

    Raises:
        DomainExceptions.InvalidDataError: If pattern format is invalid
    """
    if pattern and not isinstance(pattern, str):
        raise DomainExceptions.InvalidDataError("Cache pattern must be a valid string")

    clear_cache_use_case = use_cases["clear_cache"]
    result = await clear_cache_use_case.execute(pattern=pattern)

    operation_message = f"Cache cleared with pattern: {pattern}" if pattern else "All cache cleared"

    return ResponseHandler.success(
        data={
            "operation": "cache_clear",
            "pattern": pattern,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        },
        message=operation_message,
    )


@router.get(
    "/health",
    tags=["System"],
    response_model=HealthCheckResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def health_check(
    db: Session = Depends(get_db),
    use_cases: dict = Depends(get_system_use_cases),
) -> JSONResponse:
    """
    Comprehensive system health check endpoint.

    Performs health checks on all critical system components including database,
    cache, and external services. Returns detailed status information.

    Args:
        db: Database session dependency
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with health status

    Raises:
        DomainExceptions.ExternalServiceError: If critical services are unavailable
    """
    health_check_use_case = use_cases["health_check"]

    try:
        health_status = await health_check_use_case.execute(db)

        # Check if system is unhealthy
        if health_status.get("status") == "unhealthy":
            critical_issues = health_status.get("issues", [])
            raise DomainExceptions.ExternalServiceError(
                "System Health", f"System is unhealthy: {'; '.join(critical_issues)}"
            )

        # Convert to DTO if health_status structure allows it
        try:
            health_dto = HealthCheckDTO(
                status=health_status.get("status", "unknown"),
                timestamp=datetime.now(),
                version=health_status.get("version", "unknown"),
                database=health_status.get("database", "unknown"),
                cache=health_status.get("cache", "unknown"),
                ml_model=health_status.get("ml_model", "unknown"),
            )

            return ResponseHandler.success(data=health_dto, message="System health check completed successfully")
        except Exception:
            # Fallback to raw health_status if DTO conversion fails
            return ResponseHandler.success(data=health_status, message="System health check completed successfully")
    finally:
        # Do not disconnect the shared cache adapter here; handled by app lifespan
        pass


@router.get(
    "/info",
    tags=["System"],
    response_model=AppInfoResponse,
    responses={
        "400": {"model": BadRequest},
        "404": {"model": NotFound},
        "422": {"model": UnprocessableEntity},
        "500": {"model": InternalServerError},
        "503": {"model": ServiceUnavailable},
    },
)
async def app_info(
    db: Session = Depends(get_db),
    use_cases: dict = Depends(get_system_use_cases),
) -> JSONResponse:
    """
    Get comprehensive application information and metadata.

    Returns detailed information about the application including version,
    configuration, runtime statistics, and system capabilities.

    Args:
        db: Database session dependency
        use_cases: Dependency injected dictionary containing use cases

    Returns:
        JSONResponse: Standardized response with application information
    """
    get_app_info_use_case = use_cases["get_app_info"]
    app_info = await get_app_info_use_case.execute(db)

    return ResponseHandler.success(
        data={"application_info": app_info, "retrieved_at": datetime.now().isoformat()},
        message="Application information retrieved successfully",
    )
