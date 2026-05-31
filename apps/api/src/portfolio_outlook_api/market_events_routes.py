"""Market-aware scheduler settings endpoint (PR J).

Replaces the worker's legacy ``hour="7-21"`` dumb hourly cadence with
per-followed-market cron fires. This endpoint shows the operator which
markets will fire (resolved from their universe-scan selection) and
lets them toggle close-digest / open-alert fires on or off.

Mirrors the existing pattern: one ``GET`` returns the resolved
schedule + current toggle state, one ``PUT`` persists the toggles
onto the ``runtime_config`` row used by both the API overlay and the
worker overlay.

The actual cron registration happens in
``apps/worker/.../scheduler.py::_register_market_event_jobs`` at
worker startup — these settings only persist the operator's choice;
they don't fire jobs themselves.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    RuntimeConfigRecord,
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_CONFIG_ID = "default"


# ---------------------------------------------------------------------------
# Locked-session catalog — duplicated from ``apps/worker/.../market_hours.py``
# because the API shouldn't import from the worker process. Keep these in
# sync: the worker registers cron jobs from its copy, the API reports the
# resolved schedule from this copy. A parity test guards the sync.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MarketSession:
    code: str
    label_nl: str
    timezone: str
    open_hour: int
    open_minute: int
    close_hour: int
    close_minute: int
    index_codes: tuple[str, ...]


_LOCKED_SESSIONS: tuple[_MarketSession, ...] = (
    _MarketSession(
        code="EURONEXT",
        label_nl="Euronext — Brussel, Amsterdam, Parijs",
        timezone="Europe/Brussels",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("BEL20", "AEX", "CAC40"),
    ),
    _MarketSession(
        code="XETRA",
        label_nl="Deutsche Börse Xetra (Frankfurt)",
        timezone="Europe/Berlin",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("DAX40",),
    ),
    _MarketSession(
        code="LSE",
        label_nl="London Stock Exchange",
        timezone="Europe/London",
        open_hour=8,
        open_minute=0,
        close_hour=16,
        close_minute=30,
        index_codes=("FTSE100",),
    ),
    _MarketSession(
        code="BORSA_ITALIANA",
        label_nl="Borsa Italiana (Milaan)",
        timezone="Europe/Rome",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("FTSEMIB",),
    ),
    _MarketSession(
        code="BME",
        label_nl="Bolsa de Madrid",
        timezone="Europe/Madrid",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("IBEX35",),
    ),
    _MarketSession(
        code="NASDAQ_OMX",
        label_nl="Nasdaq Stockholm (Nordic 30)",
        timezone="Europe/Stockholm",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("NORDIC30",),
    ),
    _MarketSession(
        code="SIX",
        label_nl="SIX Swiss Exchange (Zürich)",
        timezone="Europe/Zurich",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("SLI",),
    ),
    _MarketSession(
        code="US_EQUITIES",
        label_nl="NYSE & Nasdaq (VS)",
        timezone="America/New_York",
        open_hour=9,
        open_minute=30,
        close_hour=16,
        close_minute=0,
        index_codes=("SP100", "NASDAQ100", "RUSSELL1000", "RUSSELL2000"),
    ),
)


_CLOSE_BUFFER_MINUTES = 15
_OPEN_BUFFER_MINUTES = 5


def _resolve_sessions(codes: Iterable[str]) -> tuple[_MarketSession, ...]:
    selected = {c.upper().strip() for c in codes if c}
    if not selected:
        return ()
    return tuple(
        session
        for session in _LOCKED_SESSIONS
        if any(c in selected for c in session.index_codes)
    )


def _bump(hour: int, minute: int, delta_minutes: int) -> tuple[int, int]:
    total = minute + delta_minutes
    overflow_hours, new_minute = divmod(total, 60)
    return (hour + overflow_hours) % 24, new_minute


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class MarketEventFire(BaseModel):
    """One scheduled cron fire for the operator's followed universe."""

    market_code: str
    market_label_nl: str
    timezone: str
    event_kind: str  # "open" | "close"
    fire_hour: int
    fire_minute: int


class MarketEventsSettingsResponse(BaseModel):
    """GET payload for the Markt-events settings section."""

    per_market_close_digest_enabled: bool
    per_market_open_alerts_enabled: bool
    universe_codes_selected: list[str]
    active_sessions: list[str]
    fires: list[MarketEventFire]
    help_nl: str


class UpdateMarketEventsSettingsRequest(BaseModel):
    per_market_close_digest_enabled: bool
    per_market_open_alerts_enabled: bool


_MARKET_EVENTS_HELP_NL = (
    "Markt-bewuste scheduler: in plaats van elk uur tussen 07:00 en "
    "21:00 een lege fire produceren, vuurt het systeem alleen wanneer "
    "een markt die je volgt opent of sluit. De close-digest geeft je "
    "een einde-dag samenvatting per markt; open-alerts zijn optioneel "
    "voor wie wil weten of een overnachte gap belangrijk is. "
    "Wijzigingen nemen effect bij de volgende worker-restart."
)


def _build_fires(
    sessions: tuple[_MarketSession, ...],
    *,
    close_enabled: bool,
    open_enabled: bool,
) -> list[MarketEventFire]:
    fires: list[MarketEventFire] = []
    for session in sessions:
        if close_enabled:
            hour, minute = _bump(
                session.close_hour, session.close_minute, _CLOSE_BUFFER_MINUTES
            )
            fires.append(
                MarketEventFire(
                    market_code=session.code,
                    market_label_nl=session.label_nl,
                    timezone=session.timezone,
                    event_kind="close",
                    fire_hour=hour,
                    fire_minute=minute,
                )
            )
        if open_enabled:
            hour, minute = _bump(
                session.open_hour, session.open_minute, _OPEN_BUFFER_MINUTES
            )
            fires.append(
                MarketEventFire(
                    market_code=session.code,
                    market_label_nl=session.label_nl,
                    timezone=session.timezone,
                    event_kind="open",
                    fire_hour=hour,
                    fire_minute=minute,
                )
            )
    return fires


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage_disabled")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _market_events_payload(
    record: RuntimeConfigRecord | None,
) -> MarketEventsSettingsResponse:
    close_enabled = (
        record.scheduler_per_market_close_digest_enabled
        if record is not None
        and record.scheduler_per_market_close_digest_enabled is not None
        else settings.scheduler_per_market_close_digest_enabled
    )
    open_enabled = (
        record.scheduler_per_market_open_alerts_enabled
        if record is not None
        and record.scheduler_per_market_open_alerts_enabled is not None
        else settings.scheduler_per_market_open_alerts_enabled
    )
    raw_codes = (
        record.universe_scan_index_codes
        if record is not None and record.universe_scan_index_codes is not None
        else settings.universe_scan_index_codes
    )
    codes = [c.strip() for c in (raw_codes or "").split(",") if c.strip()]
    sessions = _resolve_sessions(codes)
    return MarketEventsSettingsResponse(
        per_market_close_digest_enabled=close_enabled,
        per_market_open_alerts_enabled=open_enabled,
        universe_codes_selected=codes,
        active_sessions=[s.label_nl for s in sessions],
        fires=_build_fires(
            sessions,
            close_enabled=close_enabled,
            open_enabled=open_enabled,
        ),
        help_nl=_MARKET_EVENTS_HELP_NL,
    )


@router.get(
    "/settings/market-events",
    response_model=MarketEventsSettingsResponse,
)
def get_market_events_settings() -> MarketEventsSettingsResponse:
    provider = _storage_provider() if (
        settings.storage.enabled and settings.storage.database_url
    ) else None
    if provider is None:
        return _market_events_payload(None)
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            current = repo.get()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _market_events_payload(current)


@router.put(
    "/settings/market-events",
    response_model=MarketEventsSettingsResponse,
)
def update_market_events_settings(
    payload: UpdateMarketEventsSettingsRequest,
) -> MarketEventsSettingsResponse:
    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            # Build the full record preserving every other field — this
            # keeps the existing carry-over pattern that prevents one
            # PUT from wiping another section's settings.
            record = _carry_existing_into_record(
                existing,
                now=now,
                close_enabled=payload.per_market_close_digest_enabled,
                open_enabled=payload.per_market_open_alerts_enabled,
            )
            repo.upsert(record)
            checked.connection.commit()
            settings.scheduler_per_market_close_digest_enabled = (
                payload.per_market_close_digest_enabled
            )
            settings.scheduler_per_market_open_alerts_enabled = (
                payload.per_market_open_alerts_enabled
            )
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _market_events_payload(record)


def _carry_existing_into_record(
    existing: RuntimeConfigRecord | None,
    *,
    now: datetime,
    close_enabled: bool,
    open_enabled: bool,
) -> RuntimeConfigRecord:
    """Build a fresh ``RuntimeConfigRecord`` carrying every existing
    field forward except the two we're updating. Matches the carry-over
    pattern used by every other ``/settings/*`` PUT — saving one
    section never wipes another's persisted values."""

    def _carry(name: str, default: Any = None) -> Any:
        if existing is None:
            return default
        return getattr(existing, name, default)

    return RuntimeConfigRecord(
        config_id=_CONFIG_ID,
        ibkr_enabled=_carry("ibkr_enabled", False),
        ibkr_account_id=_carry("ibkr_account_id"),
        ibkr_host=_carry("ibkr_host"),
        ibkr_port=_carry("ibkr_port"),
        ibkr_client_id=_carry("ibkr_client_id"),
        ai_explanation_enabled=_carry("ai_explanation_enabled", False),
        claude_ai_explanation_model=_carry("claude_ai_explanation_model"),
        claude_ai_budget_monthly_eur=_carry("claude_ai_budget_monthly_eur"),
        claude_ai_api_key=_carry("claude_ai_api_key"),
        updated_at=now,
        universe_scan_index_codes=_carry("universe_scan_index_codes"),
        default_buy_value_eur=_carry("default_buy_value_eur"),
        default_top_up_pct=_carry("default_top_up_pct"),
        default_reduce_pct=_carry("default_reduce_pct"),
        max_sector_pct=_carry("max_sector_pct"),
        cost_dominates_ratio=_carry("cost_dominates_ratio"),
        suggestion_valid_minutes=_carry("suggestion_valid_minutes"),
        scheduler_daily_briefing_cron=_carry("scheduler_daily_briefing_cron"),
        ibkr_sync_interval_minutes=_carry("ibkr_sync_interval_minutes"),
        forecast_history_lookback_days=_carry("forecast_history_lookback_days"),
        forecast_minimum_bars_required=_carry("forecast_minimum_bars_required"),
        daily_briefing_lookback_hours=_carry("daily_briefing_lookback_hours"),
        universe_scan_cache_ttl_hours=_carry("universe_scan_cache_ttl_hours"),
        sweep_interval_seconds=_carry("sweep_interval_seconds"),
        sweep_retry_max_attempts=_carry("sweep_retry_max_attempts"),
        sweep_retry_backoff_seconds=_carry("sweep_retry_backoff_seconds"),
        sweep_alert_after_consecutive_errors=_carry(
            "sweep_alert_after_consecutive_errors"
        ),
        eodhd_rate_limit_per_second=_carry("eodhd_rate_limit_per_second"),
        ensemble_weight_strategy=_carry("ensemble_weight_strategy"),
        gbm_drift_window_days=_carry("gbm_drift_window_days"),
        action_draft_approval_valid_minutes=_carry(
            "action_draft_approval_valid_minutes"
        ),
        ai_explanation_provider_code=_carry("ai_explanation_provider_code"),
        sharpe_strong_threshold=_carry("sharpe_strong_threshold"),
        sharpe_slight_threshold=_carry("sharpe_slight_threshold"),
        forecast_horizon_trading_days=_carry("forecast_horizon_trading_days"),
        forecast_ensemble_enabled=_carry("forecast_ensemble_enabled"),
        suggestions_risk_profile=_carry("suggestions_risk_profile"),
        universe_set=_carry("universe_set"),
        market_data_provider=_carry("market_data_provider"),
        market_data_sync_enabled=_carry("market_data_sync_enabled"),
        ibkr_market_data_enabled=_carry("ibkr_market_data_enabled"),
        ibkr_market_data_type=_carry("ibkr_market_data_type"),
        ibkr_paper_order_submission_enabled=_carry(
            "ibkr_paper_order_submission_enabled"
        ),
        submission_sweep_enabled=_carry("submission_sweep_enabled"),
        cancel_sweep_enabled=_carry("cancel_sweep_enabled"),
        morning_chain_after_pre_briefing=_carry(
            "morning_chain_after_pre_briefing"
        ),
        forecast_valid_minutes=_carry("forecast_valid_minutes"),
        decision_packages_valid_minutes=_carry(
            "decision_packages_valid_minutes"
        ),
        prediction_diary_inconclusive_tolerance_pct=_carry(
            "prediction_diary_inconclusive_tolerance_pct"
        ),
        gbm_regime_shift_enabled=_carry("gbm_regime_shift_enabled"),
        gbm_regime_shift_threshold_pct=_carry(
            "gbm_regime_shift_threshold_pct"
        ),
        scheduler_per_market_close_digest_enabled=close_enabled,
        scheduler_per_market_open_alerts_enabled=open_enabled,
    )


__all__ = [
    "MarketEventFire",
    "MarketEventsSettingsResponse",
    "UpdateMarketEventsSettingsRequest",
    "router",
]
