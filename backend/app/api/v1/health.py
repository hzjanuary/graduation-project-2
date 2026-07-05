"""Health and service information routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.core.dependencies import provide_settings
from app.schemas import HealthResponse, LiveResponse, ReadyResponse, RootResponse

API_VERSION = "0.1.0"
SettingsDependency = Annotated[Settings, Depends(provide_settings)]

router = APIRouter(tags=["health"])


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@router.get("/", response_model=RootResponse)
async def root(settings: SettingsDependency) -> RootResponse:
    """Return basic service information."""
    return RootResponse(
        app_name=settings.app_name,
        environment=settings.app_env,
        version=API_VERSION,
        docs_url="/docs",
        health_url="/health",
    )


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDependency) -> HealthResponse:
    """Return overall service health."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        version=API_VERSION,
        timestamp=utc_now(),
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """Return lightweight readiness until external clients are implemented."""
    return ReadyResponse(
        status="ready",
        checks={
            "application": "ready",
            "external_services": "not_configured",
        },
    )


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    """Return liveness status."""
    return LiveResponse(status="alive", timestamp=utc_now())
