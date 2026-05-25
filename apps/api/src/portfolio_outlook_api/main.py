"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ai_trading_agent_storage import (
    SqlAlchemySchedulerRunRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import FastAPI

from portfolio_outlook_api.asset_listings import router as asset_listings_router
from portfolio_outlook_api.asset_master import router as asset_master_router
from portfolio_outlook_api.config import settings
from portfolio_outlook_api.health import HealthResponse, get_health_response
from portfolio_outlook_api.ibkr_connection_routes import (
    router as ibkr_connection_router,
)
from portfolio_outlook_api.market_data_runtime_routes import (
    router as market_data_runtime_router,
)
from portfolio_outlook_api.request_audit import router as request_audit_router
from portfolio_outlook_api.research_sources import router as research_sources_router
from portfolio_outlook_api.scheduler import build_scheduler, install_default_jobs
from portfolio_outlook_api.scheduler_routes import (
    router as scheduler_v127_router,
)
from portfolio_outlook_api.status_routes import router as status_router
from portfolio_outlook_api.watchlist import router as watchlist_router
from portfolio_outlook_api.watchlist_confirmation_routes import (
    router as watchlist_confirmation_router,
)

logger = logging.getLogger(__name__)


def _scheduler_repo_factory() -> SqlAlchemySchedulerRunRepository | None:
    """Build a fresh scheduler-run repository per fire, or return ``None``.

    Each scheduled fire opens a short-lived storage connection. If
    storage is unavailable the run is logged in memory only; the job
    still executes.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return None
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            return SqlAlchemySchedulerRunRepository(
                checked.connection, checked.readiness
            )
    except StorageConnectionError:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler = build_scheduler(settings)
    if scheduler is not None:
        install_default_jobs(
            scheduler,
            settings,
            repo_factory=_scheduler_repo_factory,
        )
        scheduler.start()
        logger.info("scheduler started")
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("scheduler stopped")


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.version,
    }


@app.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return get_health_response()


app.include_router(status_router)
app.include_router(research_sources_router)
app.include_router(asset_master_router)
app.include_router(asset_listings_router)
app.include_router(watchlist_router)
app.include_router(request_audit_router)
app.include_router(ibkr_connection_router)
app.include_router(scheduler_v127_router)
app.include_router(watchlist_confirmation_router)
app.include_router(market_data_runtime_router)
