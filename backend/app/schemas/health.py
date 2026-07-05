"""Health endpoint response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import AppEnvironment


class RootResponse(BaseModel):
    """Root service information response."""

    app_name: str
    environment: AppEnvironment
    version: str
    docs_url: str
    health_url: str


class HealthResponse(BaseModel):
    """Overall health response."""

    app_name: str
    environment: AppEnvironment
    version: str
    status: Literal["ok"]
    timestamp: datetime


class ReadyResponse(BaseModel):
    """Readiness response."""

    status: Literal["ready"]
    checks: dict[str, str]


class LiveResponse(BaseModel):
    """Liveness response."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "alive"}]})

    status: Literal["alive"]
    timestamp: datetime
