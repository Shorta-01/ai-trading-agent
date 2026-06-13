"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ai_trading_agent_storage import (
    SqlAlchemyRuntimeConfigRepository,
    SqlAlchemySchedulerRunRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import FastAPI

from portfolio_outlook_api.action_draft import (
    router as action_draft_router,
)
from portfolio_outlook_api.asset_listings import router as asset_listings_router
from portfolio_outlook_api.asset_master import router as asset_master_router
from portfolio_outlook_api.belasting_routes import (
    router as belasting_router,
)
from portfolio_outlook_api.config import settings
from portfolio_outlook_api.decision_package_routes import (
    router as decision_package_routes_router,
)
from portfolio_outlook_api.digest_routes import (
    router as digest_router,
)
from portfolio_outlook_api.earnings_routes import (
    router as earnings_router,
)
from portfolio_outlook_api.error_routes import (
    router as error_log_router,
)
from portfolio_outlook_api.error_routes import (
    unhandled_exception_handler,
)
from portfolio_outlook_api.explanation_batch_routes import (
    router as explanation_batch_router,
)
from portfolio_outlook_api.forecast_routes import (
    router as forecast_routes_router,
)
from portfolio_outlook_api.health import HealthResponse, get_health_response
from portfolio_outlook_api.ibkr_connection_routes import (
    router as ibkr_connection_router,
)
from portfolio_outlook_api.ibkr_submission import (
    router as ibkr_submission_router,
)
from portfolio_outlook_api.macro_snapshot_routes import (
    router as macro_snapshot_router,
)
from portfolio_outlook_api.market_data_runtime_routes import (
    router as market_data_runtime_router,
)
from portfolio_outlook_api.market_events_routes import (
    router as market_events_router,
)
from portfolio_outlook_api.notification_routes import (
    router as notification_router,
)
from portfolio_outlook_api.orchestrator_verdicts_routes import (
    router as orchestrator_verdicts_router,
)
from portfolio_outlook_api.portfolio_nav_history_routes import (
    router as portfolio_nav_history_router,
)
from portfolio_outlook_api.predictor_performance_routes import (
    router as predictor_performance_router,
)
from portfolio_outlook_api.rapporten_routes import (
    router as rapporten_router,
)
from portfolio_outlook_api.reconciliation import (
    router as reconciliation_router,
)
from portfolio_outlook_api.request_audit import router as request_audit_router
from portfolio_outlook_api.research_ai_extraction_routes import (
    router as research_ai_extraction_router,
)
from portfolio_outlook_api.research_sources import router as research_sources_router
from portfolio_outlook_api.risk_limits_routes import (
    router as risk_limits_router,
)
from portfolio_outlook_api.runtime_config_routes import (
    apply_runtime_config_overlay,
)
from portfolio_outlook_api.runtime_config_routes import (
    router as runtime_config_router,
)
from portfolio_outlook_api.scheduler import build_scheduler, install_default_jobs
from portfolio_outlook_api.scheduler_routes import (
    router as scheduler_v127_router,
)
from portfolio_outlook_api.sector_spread_routes import (
    router as sector_spread_router,
)
from portfolio_outlook_api.status_routes import router as status_router
from portfolio_outlook_api.suggestions_grid_routes import (
    router as suggestions_grid_router,
)
from portfolio_outlook_api.tob_routes import (
    router as tob_router,
)
from portfolio_outlook_api.watchlist import router as watchlist_router
from portfolio_outlook_api.watchlist_confirmation_routes import (
    router as watchlist_confirmation_router,
)
from portfolio_outlook_api.watchlist_preferences_routes import (
    router as watchlist_preferences_router,
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


def _overlay_runtime_config() -> None:
    """Read the editable ``runtime_config`` row and overlay it onto settings.

    Best-effort: any storage problem is logged and swallowed so it can never
    crash API startup. The worker-side IBKR host/port/client_id overlay is a
    follow-up tied to the durable worker session.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            record = repo.get()
        if record is not None:
            apply_runtime_config_overlay(settings, record)
            logger.info("runtime config overlay applied")
    except Exception:  # noqa: BLE001 — startup must never crash on storage
        logger.exception("Kon runtime-config overlay niet toepassen.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _overlay_runtime_config()
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
app.include_router(research_ai_extraction_router)
app.include_router(asset_master_router)
app.include_router(asset_listings_router)
app.include_router(watchlist_router)
app.include_router(request_audit_router)
app.include_router(ibkr_connection_router)
app.include_router(scheduler_v127_router)
app.include_router(watchlist_confirmation_router)
app.include_router(market_data_runtime_router)
app.include_router(forecast_routes_router)
app.include_router(decision_package_routes_router)
app.include_router(action_draft_router)
app.include_router(ibkr_submission_router)
app.include_router(reconciliation_router)
app.include_router(portfolio_nav_history_router)
app.include_router(error_log_router)
app.include_router(risk_limits_router)
app.include_router(runtime_config_router)
app.include_router(suggestions_grid_router)
app.include_router(market_events_router)
app.include_router(digest_router)
app.include_router(orchestrator_verdicts_router)
app.include_router(notification_router)
app.include_router(explanation_batch_router)
app.include_router(predictor_performance_router)
app.include_router(rapporten_router)
app.include_router(tob_router)
app.include_router(earnings_router)
app.include_router(watchlist_preferences_router)
app.include_router(macro_snapshot_router)
app.include_router(belasting_router)
app.include_router(sector_spread_router)

# Auto-capture: record any unhandled exception in the central error log.
app.add_exception_handler(Exception, unhandled_exception_handler)
