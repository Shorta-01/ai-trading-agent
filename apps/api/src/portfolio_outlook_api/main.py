"""FastAPI application entrypoint."""

from fastapi import FastAPI

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.health import HealthResponse, get_health_response
from portfolio_outlook_api.research_sources import router as research_sources_router
from portfolio_outlook_api.status_routes import router as status_router

app = FastAPI(title=settings.app_name, version=settings.version)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.version,
        "mode": "paper-only",
    }


@app.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return get_health_response()


app.include_router(status_router)
app.include_router(research_sources_router)
