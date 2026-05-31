"""Worker-side ``runtime_config`` overlay (Settings UI PR D).

Mirrors the API-side ``apply_runtime_config_overlay`` but for the
worker's ``IbkrSettings.sweep_*`` and ``EodhdSettings.rate_limit_per_second``
values. Called from ``start_worker()`` before ``_start_scheduler()`` so
the scheduler's interval-job registration picks up the operator's
sweep cadence; the per-tick reads (retry attempts, alert threshold)
flow through immediately on any tick after a save.

The function is best-effort: if storage is unreachable the worker
falls back to env-var defaults and logs a single warning. Boot is
never blocked over operator-overlay availability.
"""

from __future__ import annotations

import logging

from ai_trading_agent_storage import (
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.config import Settings

logger = logging.getLogger(__name__)


def apply_worker_runtime_config_overlay(settings_obj: Settings) -> None:
    """Read ``runtime_config`` and push the non-null worker-side values
    onto ``settings_obj.ibkr`` / ``settings_obj.eodhd``.

    Safe to call when storage is disabled or unreachable — that simply
    leaves the env-var defaults in place.
    """

    storage = settings_obj.storage
    if not storage.enabled or not storage.database_url:
        logger.info(
            "runtime_config overlay overgeslagen: opslag uitgeschakeld of "
            "zonder DATABASE_URL — env-var defaults blijven actief."
        )
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
    except StorageConnectionError as exc:
        logger.warning(
            "runtime_config overlay kon opslag niet bereiken: %s — "
            "env-var defaults blijven actief.",
            exc,
        )
        return
    if record is None:
        # No persisted overlay yet — env defaults stay in effect.
        return

    ibkr = settings_obj.ibkr
    if record.sweep_interval_seconds is not None:
        ibkr.sweep_interval_seconds = record.sweep_interval_seconds
    if record.sweep_retry_max_attempts is not None:
        ibkr.sweep_retry_max_attempts = record.sweep_retry_max_attempts
    if record.sweep_retry_backoff_seconds is not None:
        # Pydantic ``IbkrSettings.sweep_retry_backoff_seconds`` is a
        # float; cast the storage Decimal back to float for parity.
        ibkr.sweep_retry_backoff_seconds = float(
            record.sweep_retry_backoff_seconds
        )
    if record.sweep_alert_after_consecutive_errors is not None:
        ibkr.sweep_alert_after_consecutive_errors = (
            record.sweep_alert_after_consecutive_errors
        )
    if record.eodhd_rate_limit_per_second is not None:
        settings_obj.eodhd.rate_limit_per_second = (
            record.eodhd_rate_limit_per_second
        )
    # Settings UI PR H — worker-side execution gates. Applied at worker
    # startup so the next scheduler tick / sweep registration picks up
    # the operator's choices. The API-side
    # ``ibkr_paper_order_submission_enabled`` field is overlaid on the
    # API settings singleton by ``apply_runtime_config_overlay`` and is
    # not consumed by the worker.
    if record.submission_sweep_enabled is not None:
        ibkr.submission_sweep_enabled = record.submission_sweep_enabled
    if record.cancel_sweep_enabled is not None:
        ibkr.cancel_sweep_enabled = record.cancel_sweep_enabled
    if record.morning_chain_after_pre_briefing is not None:
        settings_obj.scheduler.morning_chain_after_pre_briefing = (
            record.morning_chain_after_pre_briefing
        )
    # Market-aware scheduler (PR J). The worker reads the operator's
    # selected universe + the close/open toggles so the cron
    # registration in :meth:`PortfolioScheduler._register_market_event_jobs`
    # fires the right set per the operator's followed markets.
    if record.universe_scan_index_codes is not None:
        settings_obj.scheduler.universe_scan_index_codes = (
            record.universe_scan_index_codes
        )
    if record.scheduler_per_market_close_digest_enabled is not None:
        settings_obj.scheduler.per_market_close_digest_enabled = (
            record.scheduler_per_market_close_digest_enabled
        )
    if record.scheduler_per_market_open_alerts_enabled is not None:
        settings_obj.scheduler.per_market_open_alerts_enabled = (
            record.scheduler_per_market_open_alerts_enabled
        )


__all__ = ["apply_worker_runtime_config_overlay"]
