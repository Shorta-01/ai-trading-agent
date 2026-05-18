"""Worker health helpers."""

from pydantic import BaseModel


class WorkerHealthResponse(BaseModel):
    status: str
    service: str
    mode: str


def get_worker_health() -> WorkerHealthResponse:
    return WorkerHealthResponse(status="ok", service="worker", mode="paper-only")
