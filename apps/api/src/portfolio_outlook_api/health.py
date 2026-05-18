"""Health response models and helpers."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str


def get_health_response() -> HealthResponse:
    return HealthResponse(status="ok", service="api", mode="paper-only")
