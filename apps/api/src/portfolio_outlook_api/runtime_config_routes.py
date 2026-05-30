"""Editable IBKR connection + Claude AI settings API.

Surfaces the single ``runtime_config`` row (``config_id="default"``) so the
operator can edit the IBKR connection and the Claude AI explanation settings
from the dashboard Settings page instead of only via environment variables:

- ``GET /settings/connection``  -> current settings (DB row, or env defaults)
- ``PUT /settings/connection``  -> validate + upsert, return the saved values

The Claude API key is write-only: the response NEVER carries the value, only
``claude_ai_api_key_set: bool``. On PUT the key is optional — when omitted or
blank the previously-stored key is preserved.

Mirrors the storage-access patterns in ``error_routes.py``: ``_storage_provider()``
+ ``provider.checked_connection(...)`` + an explicit ``checked.connection.commit()``
on writes (the context manager does NOT auto-commit). The monetary budget is
serialised as a string so no float rounding leaks into the response.

``apply_runtime_config_overlay`` is the startup hook the API lifespan calls to
overlay the non-null DB values onto the settings singleton.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
from portfolio_outlook_api.universe_registry import (
    INDEX_CODE_LABELS_NL,
    LOCKED_INDEX_CODES,
    parse_index_codes,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_CONFIG_ID = "default"

# Worker-side IBKR defaults used purely for display when no DB row exists yet.
_DEFAULT_IBKR_HOST = "127.0.0.1"
_DEFAULT_IBKR_PORT = 7497
_DEFAULT_IBKR_CLIENT_ID = 1


class ConnectionSettingsResponse(BaseModel):
    ibkr_enabled: bool
    ibkr_account_id: str | None
    ibkr_host: str | None
    ibkr_port: int | None
    ibkr_client_id: int | None
    ai_explanation_enabled: bool
    claude_ai_explanation_model: str | None
    claude_ai_budget_monthly_eur: str | None
    # Write-only key: never return the value, only whether one is stored.
    claude_ai_api_key_set: bool


class UpdateConnectionSettingsRequest(BaseModel):
    ibkr_enabled: bool
    ibkr_account_id: str | None = None
    ibkr_host: str | None = None
    ibkr_port: int | None = None
    ibkr_client_id: int | None = None
    ai_explanation_enabled: bool
    claude_ai_explanation_model: str | None = None
    claude_ai_budget_monthly_eur: Decimal | None = None
    # Optional secret: only sent when the operator types a new key. When
    # omitted or blank, the existing stored key is preserved.
    claude_ai_api_key: str | None = None


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(status_code=503, detail="Opslag is niet beschikbaar.")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _budget_str(value: Decimal | None) -> str | None:
    """Canonical Decimal -> str: strip storage-scale padding (the column is
    ``Numeric(20, 6)`` so a stored ``50`` reads back as ``50.000000``) while
    keeping at least one fractional digit. Keeps the PUT response (built from
    the in-memory value) and a fresh GET (read back from the DB) identical, and
    never leaks a float."""

    if value is None:
        return None
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." not in text:
        text += ".0"
    return text


def _serialise(record: RuntimeConfigRecord) -> ConnectionSettingsResponse:
    return ConnectionSettingsResponse(
        ibkr_enabled=record.ibkr_enabled,
        ibkr_account_id=record.ibkr_account_id,
        ibkr_host=record.ibkr_host,
        ibkr_port=record.ibkr_port,
        ibkr_client_id=record.ibkr_client_id,
        ai_explanation_enabled=record.ai_explanation_enabled,
        claude_ai_explanation_model=record.claude_ai_explanation_model,
        claude_ai_budget_monthly_eur=_budget_str(record.claude_ai_budget_monthly_eur),
        claude_ai_api_key_set=bool(record.claude_ai_api_key),
    )


def _defaults_from_env() -> ConnectionSettingsResponse:
    """Fallback shown when no ``runtime_config`` row exists yet: the env/config
    defaults from the ``settings`` singleton plus the worker-side IBKR display
    defaults. The key value is never returned, only whether one is configured."""

    return ConnectionSettingsResponse(
        ibkr_enabled=bool(getattr(settings, "ibkr_enabled", False)),
        ibkr_account_id=getattr(settings, "ibkr_account_id_hint", None),
        ibkr_host=_DEFAULT_IBKR_HOST,
        ibkr_port=_DEFAULT_IBKR_PORT,
        ibkr_client_id=_DEFAULT_IBKR_CLIENT_ID,
        ai_explanation_enabled=bool(getattr(settings, "ai_explanation_enabled", False)),
        claude_ai_explanation_model=getattr(
            settings, "claude_ai_explanation_model", None
        ),
        claude_ai_budget_monthly_eur=_budget_str(
            getattr(settings, "claude_ai_budget_monthly_eur", None)
        ),
        claude_ai_api_key_set=bool(getattr(settings, "claude_ai_api_key", None)),
    )


@router.get("/settings/connection", response_model=ConnectionSettingsResponse)
def get_connection_settings() -> ConnectionSettingsResponse:
    provider = _storage_provider()
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
    if current is None:
        return _defaults_from_env()
    return _serialise(current)


@router.put("/settings/connection", response_model=ConnectionSettingsResponse)
def update_connection_settings(
    payload: UpdateConnectionSettingsRequest,
) -> ConnectionSettingsResponse:
    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            # Optional key: keep the previously-stored value unless a new
            # non-empty key is supplied. Never overwrite a stored key with None.
            new_key = payload.claude_ai_api_key
            if new_key is not None and new_key.strip():
                stored_key: str | None = new_key
            elif existing is not None:
                stored_key = existing.claude_ai_api_key
            else:
                stored_key = None
            try:
                record = RuntimeConfigRecord(
                    config_id=_CONFIG_ID,
                    ibkr_enabled=payload.ibkr_enabled,
                    ibkr_account_id=payload.ibkr_account_id,
                    ibkr_host=payload.ibkr_host,
                    ibkr_port=payload.ibkr_port,
                    ibkr_client_id=payload.ibkr_client_id,
                    ai_explanation_enabled=payload.ai_explanation_enabled,
                    claude_ai_explanation_model=payload.claude_ai_explanation_model,
                    claude_ai_budget_monthly_eur=payload.claude_ai_budget_monthly_eur,
                    claude_ai_api_key=stored_key,
                    updated_at=now,
                )
            except (ValueError, InvalidOperation) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            repo.upsert(record)
            checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _serialise(record)


# ---- Universe-scan multi-select -----------------------------------------


class UniverseScanIndexOption(BaseModel):
    code: str
    label_nl: str


class UniverseScanSettingsResponse(BaseModel):
    selected_codes: list[str]
    available_codes: list[UniverseScanIndexOption]
    help_nl: str


class UpdateUniverseScanSettingsRequest(BaseModel):
    selected_codes: list[str]


def _available_codes_payload() -> list[UniverseScanIndexOption]:
    return [
        UniverseScanIndexOption(code=code, label_nl=INDEX_CODE_LABELS_NL[code])
        for code in sorted(LOCKED_INDEX_CODES)
    ]


def _selected_codes_payload(stored: str | None) -> list[str]:
    """Decode the runtime_config CSV column to a list, honouring env fallback.

    Empty / null DB value falls back to the env-var
    ``universe_scan_index_codes`` setting; if that's also empty, returns
    ``[]`` so the UI shows nothing selected.
    """

    raw = (stored or "").strip()
    if not raw:
        raw = (settings.universe_scan_index_codes or "").strip()
    if not raw:
        return []
    try:
        return list(parse_index_codes(raw))
    except ValueError:
        # Bad persisted value — surface as empty rather than crash the GET.
        return []


@router.get("/settings/universe-scan", response_model=UniverseScanSettingsResponse)
def get_universe_scan_settings() -> UniverseScanSettingsResponse:
    """Operator's selected scan markets + the full list to choose from."""

    provider = _storage_provider()
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
    stored = current.universe_scan_index_codes if current is not None else None
    return UniverseScanSettingsResponse(
        selected_codes=_selected_codes_payload(stored),
        available_codes=_available_codes_payload(),
        help_nl=(
            "Kies welke beurzen het systeem dagelijks moet scannen. Niets "
            "geselecteerd valt terug op de oude vaste set (``universe_set``)."
        ),
    )


@router.put(
    "/settings/universe-scan", response_model=UniverseScanSettingsResponse
)
def update_universe_scan_settings(
    payload: UpdateUniverseScanSettingsRequest,
) -> UniverseScanSettingsResponse:
    """Persist the operator's multi-select. Validates against
    ``LOCKED_INDEX_CODES``; unknown codes raise HTTP 422."""

    # Validate by reusing the same parser the scan runner uses.
    csv = ",".join(payload.selected_codes)
    try:
        cleaned = parse_index_codes(csv)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                # Carry over the existing IBKR/AI fields untouched. Operators
                # editing the scan list shouldn't accidentally clobber the
                # connection settings.
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=",".join(cleaned) if cleaned else None,
            )
            repo.upsert(record)
            checked.connection.commit()
            # Reflect the new selection on the running settings singleton so
            # the next scan picks it up without an API restart.
            settings.universe_scan_index_codes = ",".join(cleaned)
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return UniverseScanSettingsResponse(
        selected_codes=list(cleaned),
        available_codes=_available_codes_payload(),
        help_nl=(
            "Kies welke beurzen het systeem dagelijks moet scannen. Niets "
            "geselecteerd valt terug op de oude vaste set (``universe_set``)."
        ),
    )


# ---- Order policy + suggestion filters (Settings UI PR A) ---------------


class OrderPolicySettingsResponse(BaseModel):
    """Operator-editable defaults for action-draft sizing + the suggestion
    portfolio-context gate. Strings on the wire so Decimal precision
    survives the round trip and the form stays parser-friendly."""

    default_buy_value_eur: str
    default_top_up_pct: str
    default_reduce_pct: str
    max_sector_pct: str
    cost_dominates_ratio: str
    suggestion_valid_minutes: int
    help_nl: str


class UpdateOrderPolicySettingsRequest(BaseModel):
    default_buy_value_eur: Decimal
    default_top_up_pct: Decimal
    default_reduce_pct: Decimal
    max_sector_pct: Decimal
    cost_dominates_ratio: Decimal
    suggestion_valid_minutes: int


_ORDER_POLICY_HELP_NL = (
    "Standaard koop-/verminder-bedragen + diversificatie- en kostengates "
    "die de morgenchain en de Action Draft composer toepassen. "
    "Suggesties zijn altijd alleen-lezen advies — niets wordt automatisch "
    "geplaatst."
)


def _decimal_text(value: Decimal | str) -> str:
    """Stable string form for a Decimal-valued setting (handles both stored
    Decimals and env-var strings)."""

    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def _order_policy_payload(record: RuntimeConfigRecord | None) -> OrderPolicySettingsResponse:
    if record is None:
        return OrderPolicySettingsResponse(
            default_buy_value_eur=_decimal_text(settings.action_drafts_default_buy_value),
            default_top_up_pct=_decimal_text(settings.action_drafts_top_up_pct),
            default_reduce_pct=_decimal_text(settings.action_drafts_reduce_pct),
            max_sector_pct=_decimal_text(settings.max_sector_pct),
            cost_dominates_ratio=_decimal_text(settings.cost_dominates_ratio),
            suggestion_valid_minutes=settings.suggestions_valid_minutes,
            help_nl=_ORDER_POLICY_HELP_NL,
        )
    return OrderPolicySettingsResponse(
        default_buy_value_eur=_decimal_text(
            record.default_buy_value_eur
            if record.default_buy_value_eur is not None
            else settings.action_drafts_default_buy_value
        ),
        default_top_up_pct=_decimal_text(
            record.default_top_up_pct
            if record.default_top_up_pct is not None
            else settings.action_drafts_top_up_pct
        ),
        default_reduce_pct=_decimal_text(
            record.default_reduce_pct
            if record.default_reduce_pct is not None
            else settings.action_drafts_reduce_pct
        ),
        max_sector_pct=_decimal_text(
            record.max_sector_pct
            if record.max_sector_pct is not None
            else settings.max_sector_pct
        ),
        cost_dominates_ratio=_decimal_text(
            record.cost_dominates_ratio
            if record.cost_dominates_ratio is not None
            else settings.cost_dominates_ratio
        ),
        suggestion_valid_minutes=(
            record.suggestion_valid_minutes
            if record.suggestion_valid_minutes is not None
            else settings.suggestions_valid_minutes
        ),
        help_nl=_ORDER_POLICY_HELP_NL,
    )


@router.get(
    "/settings/order-policy", response_model=OrderPolicySettingsResponse
)
def get_order_policy_settings() -> OrderPolicySettingsResponse:
    provider = _storage_provider()
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
    return _order_policy_payload(current)


@router.put(
    "/settings/order-policy", response_model=OrderPolicySettingsResponse
)
def update_order_policy_settings(
    payload: UpdateOrderPolicySettingsRequest,
) -> OrderPolicySettingsResponse:
    if payload.default_buy_value_eur <= 0:
        raise HTTPException(
            status_code=422, detail="Standaard koopbedrag moet groter zijn dan 0."
        )
    if not (Decimal("0") < payload.default_top_up_pct <= Decimal("100")):
        raise HTTPException(
            status_code=422,
            detail="Bijkoop-percentage moet tussen 0 en 100 liggen.",
        )
    if not (Decimal("0") < payload.default_reduce_pct <= Decimal("100")):
        raise HTTPException(
            status_code=422,
            detail="Verminder-percentage moet tussen 0 en 100 liggen.",
        )
    if not (Decimal("0") < payload.max_sector_pct <= Decimal("100")):
        raise HTTPException(
            status_code=422,
            detail="Sectorconcentratie-cap moet tussen 0 en 100 liggen.",
        )
    if payload.cost_dominates_ratio <= Decimal("0"):
        raise HTTPException(
            status_code=422,
            detail="Kosten-vs-rendement drempel moet groter zijn dan 0.",
        )
    if payload.suggestion_valid_minutes <= 0:
        raise HTTPException(
            status_code=422,
            detail="Suggestiegeldigheid moet groter zijn dan 0 minuten.",
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=payload.default_buy_value_eur,
                default_top_up_pct=payload.default_top_up_pct,
                default_reduce_pct=payload.default_reduce_pct,
                max_sector_pct=payload.max_sector_pct,
                cost_dominates_ratio=payload.cost_dominates_ratio,
                suggestion_valid_minutes=payload.suggestion_valid_minutes,
                ensemble_weight_strategy=(
                    existing.ensemble_weight_strategy if existing else None
                ),
                gbm_drift_window_days=(
                    existing.gbm_drift_window_days if existing else None
                ),
                action_draft_approval_valid_minutes=(
                    existing.action_draft_approval_valid_minutes
                    if existing
                    else None
                ),
                ai_explanation_provider_code=(
                    existing.ai_explanation_provider_code if existing else None
                ),
                sharpe_strong_threshold=(
                    existing.sharpe_strong_threshold if existing else None
                ),
                sharpe_slight_threshold=(
                    existing.sharpe_slight_threshold if existing else None
                ),
                forecast_horizon_trading_days=(
                    existing.forecast_horizon_trading_days if existing else None
                ),
                forecast_ensemble_enabled=(
                    existing.forecast_ensemble_enabled if existing else None
                ),
                suggestions_risk_profile=(
                    existing.suggestions_risk_profile if existing else None
                ),
                universe_set=existing.universe_set if existing else None,
                market_data_provider=(
                    existing.market_data_provider if existing else None
                ),
                market_data_sync_enabled=(
                    existing.market_data_sync_enabled if existing else None
                ),
                ibkr_market_data_enabled=(
                    existing.ibkr_market_data_enabled if existing else None
                ),
                ibkr_market_data_type=(
                    existing.ibkr_market_data_type if existing else None
                ),
            )
            repo.upsert(record)
            checked.connection.commit()
            # Reflect on the running settings singleton.
            settings.action_drafts_default_buy_value = str(
                payload.default_buy_value_eur
            )
            settings.action_drafts_top_up_pct = str(payload.default_top_up_pct)
            settings.action_drafts_reduce_pct = str(payload.default_reduce_pct)
            settings.max_sector_pct = str(payload.max_sector_pct)
            settings.cost_dominates_ratio = str(payload.cost_dominates_ratio)
            settings.suggestions_valid_minutes = payload.suggestion_valid_minutes
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _order_policy_payload(record)


# ---- Scheduler cadence (Settings UI PR B) -------------------------------


class SchedulerSettingsResponse(BaseModel):
    """Operator-editable scheduler cadence — currently the API-side cron
    + the IBKR read-only sync interval. Worker-side sweep settings are
    a separate overlay (the worker reads its own env vars at startup)."""

    scheduler_daily_briefing_cron: str
    ibkr_sync_interval_minutes: int
    help_nl: str


class UpdateSchedulerSettingsRequest(BaseModel):
    scheduler_daily_briefing_cron: str
    ibkr_sync_interval_minutes: int


_SCHEDULER_HELP_NL = (
    "Wanneer de morgenbriefing klaarstaat en hoe vaak het systeem "
    "IBKR-posities bijwerkt. Wijzigingen in de cron-uitdrukking gelden "
    "vanaf de eerstvolgende API-herstart; de sync-cadans neemt direct "
    "effect bij de volgende tick."
)


def _scheduler_payload(record: RuntimeConfigRecord | None) -> SchedulerSettingsResponse:
    cron = (
        record.scheduler_daily_briefing_cron
        if record is not None and record.scheduler_daily_briefing_cron is not None
        else settings.scheduler_daily_briefing_cron
    )
    interval = (
        record.ibkr_sync_interval_minutes
        if record is not None and record.ibkr_sync_interval_minutes is not None
        else settings.ibkr_sync_interval_minutes
    )
    return SchedulerSettingsResponse(
        scheduler_daily_briefing_cron=cron,
        ibkr_sync_interval_minutes=interval,
        help_nl=_SCHEDULER_HELP_NL,
    )


def _validate_five_field_cron(expression: str) -> None:
    """Mirror the API scheduler's own cron-parse to reject malformed
    expressions at save time, and to refuse the 06:00 collision with
    the worker's locked pre-briefing slot."""

    from portfolio_outlook_api.scheduler import _parse_cron

    try:
        _parse_cron(expression, settings.scheduler_timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/settings/scheduler", response_model=SchedulerSettingsResponse
)
def get_scheduler_settings() -> SchedulerSettingsResponse:
    provider = _storage_provider()
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
    return _scheduler_payload(current)


@router.put(
    "/settings/scheduler", response_model=SchedulerSettingsResponse
)
def update_scheduler_settings(
    payload: UpdateSchedulerSettingsRequest,
) -> SchedulerSettingsResponse:
    _validate_five_field_cron(payload.scheduler_daily_briefing_cron)
    if payload.ibkr_sync_interval_minutes < 1:
        raise HTTPException(
            status_code=422,
            detail="IBKR-sync interval moet minstens 1 minuut zijn.",
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=(
                    existing.default_buy_value_eur if existing else None
                ),
                default_top_up_pct=(
                    existing.default_top_up_pct if existing else None
                ),
                default_reduce_pct=(
                    existing.default_reduce_pct if existing else None
                ),
                max_sector_pct=existing.max_sector_pct if existing else None,
                cost_dominates_ratio=(
                    existing.cost_dominates_ratio if existing else None
                ),
                suggestion_valid_minutes=(
                    existing.suggestion_valid_minutes if existing else None
                ),
                scheduler_daily_briefing_cron=payload.scheduler_daily_briefing_cron,
                ibkr_sync_interval_minutes=payload.ibkr_sync_interval_minutes,
                ensemble_weight_strategy=(
                    existing.ensemble_weight_strategy if existing else None
                ),
                gbm_drift_window_days=(
                    existing.gbm_drift_window_days if existing else None
                ),
                action_draft_approval_valid_minutes=(
                    existing.action_draft_approval_valid_minutes
                    if existing
                    else None
                ),
                ai_explanation_provider_code=(
                    existing.ai_explanation_provider_code if existing else None
                ),
                sharpe_strong_threshold=(
                    existing.sharpe_strong_threshold if existing else None
                ),
                sharpe_slight_threshold=(
                    existing.sharpe_slight_threshold if existing else None
                ),
                forecast_horizon_trading_days=(
                    existing.forecast_horizon_trading_days if existing else None
                ),
                forecast_ensemble_enabled=(
                    existing.forecast_ensemble_enabled if existing else None
                ),
                suggestions_risk_profile=(
                    existing.suggestions_risk_profile if existing else None
                ),
                universe_set=existing.universe_set if existing else None,
                market_data_provider=(
                    existing.market_data_provider if existing else None
                ),
                market_data_sync_enabled=(
                    existing.market_data_sync_enabled if existing else None
                ),
                ibkr_market_data_enabled=(
                    existing.ibkr_market_data_enabled if existing else None
                ),
                ibkr_market_data_type=(
                    existing.ibkr_market_data_type if existing else None
                ),
            )
            repo.upsert(record)
            checked.connection.commit()
            settings.scheduler_daily_briefing_cron = payload.scheduler_daily_briefing_cron
            settings.ibkr_sync_interval_minutes = payload.ibkr_sync_interval_minutes
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _scheduler_payload(record)


# ---- Data windows (Settings UI PR C) ------------------------------------


class DataWindowSettingsResponse(BaseModel):
    """Operator-editable data-window knobs that govern how much history
    the morning chain pulls + caches."""

    forecast_history_lookback_days: int
    forecast_minimum_bars_required: int
    daily_briefing_lookback_hours: int
    universe_scan_cache_ttl_hours: int
    help_nl: str


class UpdateDataWindowSettingsRequest(BaseModel):
    forecast_history_lookback_days: int
    forecast_minimum_bars_required: int
    daily_briefing_lookback_hours: int
    universe_scan_cache_ttl_hours: int


_DATA_WINDOW_HELP_NL = (
    "Hoeveel marktdata-historie het model gebruikt, hoeveel koersdagen "
    "minimaal nodig zijn, welk tijdvenster de morgenbriefing samenvat en "
    "hoe lang scan-resultaten in cache blijven. Hogere lookback = "
    "robuustere modellen maar meer EODHD-calls."
)


def _data_window_payload(
    record: RuntimeConfigRecord | None,
) -> DataWindowSettingsResponse:
    history = (
        record.forecast_history_lookback_days
        if record is not None and record.forecast_history_lookback_days is not None
        else settings.forecast_history_lookback_days
    )
    minimum = (
        record.forecast_minimum_bars_required
        if record is not None and record.forecast_minimum_bars_required is not None
        else settings.forecast_minimum_bars_required
    )
    briefing = (
        record.daily_briefing_lookback_hours
        if record is not None and record.daily_briefing_lookback_hours is not None
        else settings.daily_briefing_lookback_hours
    )
    ttl = (
        record.universe_scan_cache_ttl_hours
        if record is not None and record.universe_scan_cache_ttl_hours is not None
        else settings.universe_scan_cache_ttl_hours
    )
    return DataWindowSettingsResponse(
        forecast_history_lookback_days=history,
        forecast_minimum_bars_required=minimum,
        daily_briefing_lookback_hours=briefing,
        universe_scan_cache_ttl_hours=ttl,
        help_nl=_DATA_WINDOW_HELP_NL,
    )


@router.get(
    "/settings/data-windows", response_model=DataWindowSettingsResponse
)
def get_data_window_settings() -> DataWindowSettingsResponse:
    provider = _storage_provider()
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
    return _data_window_payload(current)


@router.put(
    "/settings/data-windows", response_model=DataWindowSettingsResponse
)
def update_data_window_settings(
    payload: UpdateDataWindowSettingsRequest,
) -> DataWindowSettingsResponse:
    if payload.forecast_history_lookback_days < 1:
        raise HTTPException(
            status_code=422, detail="Voorspellings-lookback moet ≥ 1 dag zijn."
        )
    if payload.forecast_minimum_bars_required < 1:
        raise HTTPException(
            status_code=422, detail="Minimum koersdagen moet ≥ 1 zijn."
        )
    if payload.forecast_minimum_bars_required > payload.forecast_history_lookback_days:
        raise HTTPException(
            status_code=422,
            detail="Minimum koersdagen mag niet groter zijn dan de lookback.",
        )
    if payload.daily_briefing_lookback_hours < 1:
        raise HTTPException(
            status_code=422, detail="Briefing-tijdvenster moet ≥ 1 uur zijn."
        )
    if payload.universe_scan_cache_ttl_hours < 0:
        raise HTTPException(
            status_code=422, detail="Scan-cache TTL moet ≥ 0 uur zijn."
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=(
                    existing.default_buy_value_eur if existing else None
                ),
                default_top_up_pct=(
                    existing.default_top_up_pct if existing else None
                ),
                default_reduce_pct=(
                    existing.default_reduce_pct if existing else None
                ),
                max_sector_pct=existing.max_sector_pct if existing else None,
                cost_dominates_ratio=(
                    existing.cost_dominates_ratio if existing else None
                ),
                suggestion_valid_minutes=(
                    existing.suggestion_valid_minutes if existing else None
                ),
                scheduler_daily_briefing_cron=(
                    existing.scheduler_daily_briefing_cron if existing else None
                ),
                ibkr_sync_interval_minutes=(
                    existing.ibkr_sync_interval_minutes if existing else None
                ),
                forecast_history_lookback_days=payload.forecast_history_lookback_days,
                forecast_minimum_bars_required=payload.forecast_minimum_bars_required,
                daily_briefing_lookback_hours=payload.daily_briefing_lookback_hours,
                universe_scan_cache_ttl_hours=payload.universe_scan_cache_ttl_hours,
                ensemble_weight_strategy=(
                    existing.ensemble_weight_strategy if existing else None
                ),
                gbm_drift_window_days=(
                    existing.gbm_drift_window_days if existing else None
                ),
                action_draft_approval_valid_minutes=(
                    existing.action_draft_approval_valid_minutes
                    if existing
                    else None
                ),
                ai_explanation_provider_code=(
                    existing.ai_explanation_provider_code if existing else None
                ),
                sharpe_strong_threshold=(
                    existing.sharpe_strong_threshold if existing else None
                ),
                sharpe_slight_threshold=(
                    existing.sharpe_slight_threshold if existing else None
                ),
                forecast_horizon_trading_days=(
                    existing.forecast_horizon_trading_days if existing else None
                ),
                forecast_ensemble_enabled=(
                    existing.forecast_ensemble_enabled if existing else None
                ),
                suggestions_risk_profile=(
                    existing.suggestions_risk_profile if existing else None
                ),
                universe_set=existing.universe_set if existing else None,
                market_data_provider=(
                    existing.market_data_provider if existing else None
                ),
                market_data_sync_enabled=(
                    existing.market_data_sync_enabled if existing else None
                ),
                ibkr_market_data_enabled=(
                    existing.ibkr_market_data_enabled if existing else None
                ),
                ibkr_market_data_type=(
                    existing.ibkr_market_data_type if existing else None
                ),
            )
            repo.upsert(record)
            checked.connection.commit()
            settings.forecast_history_lookback_days = payload.forecast_history_lookback_days
            settings.forecast_minimum_bars_required = payload.forecast_minimum_bars_required
            settings.daily_briefing_lookback_hours = payload.daily_briefing_lookback_hours
            settings.universe_scan_cache_ttl_hours = payload.universe_scan_cache_ttl_hours
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _data_window_payload(record)


# ---- Worker sweeps + EODHD (Settings UI PR D) ---------------------------


class WorkerSweepSettingsResponse(BaseModel):
    """Operator-editable worker-side knobs. The values are persisted on
    the same ``runtime_config`` row the API overlays at startup; the
    worker reads the same row at its own startup so the operator
    edits show up after the worker is restarted (interval-job
    registration) and immediately for the per-tick reads (retry
    attempts, alert threshold)."""

    sweep_interval_seconds: int
    sweep_retry_max_attempts: int
    sweep_retry_backoff_seconds: str
    sweep_alert_after_consecutive_errors: int
    eodhd_rate_limit_per_second: int
    help_nl: str


class UpdateWorkerSweepSettingsRequest(BaseModel):
    sweep_interval_seconds: int
    sweep_retry_max_attempts: int
    sweep_retry_backoff_seconds: Decimal
    sweep_alert_after_consecutive_errors: int
    eodhd_rate_limit_per_second: int


_WORKER_SWEEP_HELP_NL = (
    "Worker-zijde sweep cadens, in-tick retry-instellingen en de "
    "EODHD-rate limit. Wijzigingen in de sweep-interval nemen effect "
    "vanaf de eerstvolgende worker-restart; retry, alert-drempel en "
    "rate-limit nemen direct effect bij de volgende tick."
)


def _worker_sweep_payload(
    record: RuntimeConfigRecord | None,
) -> WorkerSweepSettingsResponse:
    # Pull each field from runtime_config if set, otherwise fall back to
    # the worker-side env-default. The API doesn't have the worker's
    # settings singleton in-process; we hard-code the worker's
    # ``IbkrSettings`` defaults here so the GET returns a sensible
    # baseline when no row has been saved yet.
    sweep_interval = (
        record.sweep_interval_seconds
        if record is not None and record.sweep_interval_seconds is not None
        else 60
    )
    retries = (
        record.sweep_retry_max_attempts
        if record is not None and record.sweep_retry_max_attempts is not None
        else 3
    )
    backoff = (
        record.sweep_retry_backoff_seconds
        if record is not None and record.sweep_retry_backoff_seconds is not None
        else Decimal("2.0")
    )
    alert = (
        record.sweep_alert_after_consecutive_errors
        if record is not None
        and record.sweep_alert_after_consecutive_errors is not None
        else 3
    )
    rate_limit = (
        record.eodhd_rate_limit_per_second
        if record is not None and record.eodhd_rate_limit_per_second is not None
        else 10
    )
    return WorkerSweepSettingsResponse(
        sweep_interval_seconds=sweep_interval,
        sweep_retry_max_attempts=retries,
        sweep_retry_backoff_seconds=_decimal_text(backoff),
        sweep_alert_after_consecutive_errors=alert,
        eodhd_rate_limit_per_second=rate_limit,
        help_nl=_WORKER_SWEEP_HELP_NL,
    )


@router.get(
    "/settings/worker-sweeps", response_model=WorkerSweepSettingsResponse
)
def get_worker_sweep_settings() -> WorkerSweepSettingsResponse:
    provider = _storage_provider()
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
    return _worker_sweep_payload(current)


@router.put(
    "/settings/worker-sweeps", response_model=WorkerSweepSettingsResponse
)
def update_worker_sweep_settings(
    payload: UpdateWorkerSweepSettingsRequest,
) -> WorkerSweepSettingsResponse:
    if payload.sweep_interval_seconds < 1:
        raise HTTPException(
            status_code=422, detail="Sweep-interval moet ≥ 1 seconde zijn."
        )
    if payload.sweep_retry_max_attempts < 1:
        raise HTTPException(
            status_code=422, detail="Sweep-retry pogingen moet ≥ 1 zijn."
        )
    if payload.sweep_retry_backoff_seconds < Decimal("0"):
        raise HTTPException(
            status_code=422, detail="Sweep-retry backoff moet ≥ 0 seconden zijn."
        )
    if payload.sweep_alert_after_consecutive_errors < 1:
        raise HTTPException(
            status_code=422,
            detail="Alert-drempel moet ≥ 1 opeenvolgende fout zijn.",
        )
    if payload.eodhd_rate_limit_per_second < 1:
        raise HTTPException(
            status_code=422,
            detail="EODHD rate-limit moet ≥ 1 request/seconde zijn.",
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=(
                    existing.default_buy_value_eur if existing else None
                ),
                default_top_up_pct=(
                    existing.default_top_up_pct if existing else None
                ),
                default_reduce_pct=(
                    existing.default_reduce_pct if existing else None
                ),
                max_sector_pct=existing.max_sector_pct if existing else None,
                cost_dominates_ratio=(
                    existing.cost_dominates_ratio if existing else None
                ),
                suggestion_valid_minutes=(
                    existing.suggestion_valid_minutes if existing else None
                ),
                scheduler_daily_briefing_cron=(
                    existing.scheduler_daily_briefing_cron if existing else None
                ),
                ibkr_sync_interval_minutes=(
                    existing.ibkr_sync_interval_minutes if existing else None
                ),
                forecast_history_lookback_days=(
                    existing.forecast_history_lookback_days if existing else None
                ),
                forecast_minimum_bars_required=(
                    existing.forecast_minimum_bars_required if existing else None
                ),
                daily_briefing_lookback_hours=(
                    existing.daily_briefing_lookback_hours if existing else None
                ),
                universe_scan_cache_ttl_hours=(
                    existing.universe_scan_cache_ttl_hours if existing else None
                ),
                sweep_interval_seconds=payload.sweep_interval_seconds,
                sweep_retry_max_attempts=payload.sweep_retry_max_attempts,
                sweep_retry_backoff_seconds=payload.sweep_retry_backoff_seconds,
                sweep_alert_after_consecutive_errors=(
                    payload.sweep_alert_after_consecutive_errors
                ),
                eodhd_rate_limit_per_second=payload.eodhd_rate_limit_per_second,
                ensemble_weight_strategy=(
                    existing.ensemble_weight_strategy if existing else None
                ),
                gbm_drift_window_days=(
                    existing.gbm_drift_window_days if existing else None
                ),
                action_draft_approval_valid_minutes=(
                    existing.action_draft_approval_valid_minutes
                    if existing
                    else None
                ),
                ai_explanation_provider_code=(
                    existing.ai_explanation_provider_code if existing else None
                ),
                sharpe_strong_threshold=(
                    existing.sharpe_strong_threshold if existing else None
                ),
                sharpe_slight_threshold=(
                    existing.sharpe_slight_threshold if existing else None
                ),
                forecast_horizon_trading_days=(
                    existing.forecast_horizon_trading_days if existing else None
                ),
                forecast_ensemble_enabled=(
                    existing.forecast_ensemble_enabled if existing else None
                ),
                suggestions_risk_profile=(
                    existing.suggestions_risk_profile if existing else None
                ),
                universe_set=existing.universe_set if existing else None,
                market_data_provider=(
                    existing.market_data_provider if existing else None
                ),
                market_data_sync_enabled=(
                    existing.market_data_sync_enabled if existing else None
                ),
                ibkr_market_data_enabled=(
                    existing.ibkr_market_data_enabled if existing else None
                ),
                ibkr_market_data_type=(
                    existing.ibkr_market_data_type if existing else None
                ),
            )
            repo.upsert(record)
            checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _worker_sweep_payload(record)


# ---- Advanced "power-user" settings (Settings UI PR E) -----------------


_ALLOWED_ENSEMBLE_STRATEGIES = ("equal_weight", "auto")
_ALLOWED_AI_EXPLANATION_PROVIDERS = ("stub", "claude")


class AdvancedSettingsResponse(BaseModel):
    """Tier-2 power-user knobs surfaced behind the "Geavanceerde
    instellingen" accordion. Each value falls back to the API
    settings-singleton default (env-var) when no DB row has been saved."""

    ensemble_weight_strategy: str
    gbm_drift_window_days: int | None
    action_draft_approval_valid_minutes: int
    ai_explanation_provider_code: str
    sharpe_strong_threshold: str
    sharpe_slight_threshold: str
    help_nl: str


class UpdateAdvancedSettingsRequest(BaseModel):
    ensemble_weight_strategy: str
    gbm_drift_window_days: int | None = None
    action_draft_approval_valid_minutes: int
    ai_explanation_provider_code: str
    sharpe_strong_threshold: Decimal
    sharpe_slight_threshold: Decimal


_ADVANCED_HELP_NL = (
    "Geavanceerde instellingen voor power-users. Pas alleen aan als je "
    "weet wat je doet — verkeerde waarden kunnen voorspellingen of "
    "order-uitleg uit balans brengen. Laat in twijfel staan op de "
    "ingebouwde standaard."
)


def _advanced_payload(
    record: RuntimeConfigRecord | None,
) -> AdvancedSettingsResponse:
    strategy = (
        record.ensemble_weight_strategy
        if record is not None and record.ensemble_weight_strategy is not None
        else settings.ensemble_weight_strategy
    )
    drift_window = (
        record.gbm_drift_window_days
        if record is not None and record.gbm_drift_window_days is not None
        else settings.gbm_drift_window_days
    )
    approval_minutes = (
        record.action_draft_approval_valid_minutes
        if record is not None
        and record.action_draft_approval_valid_minutes is not None
        else settings.action_draft_approval_valid_minutes
    )
    provider = (
        record.ai_explanation_provider_code
        if record is not None and record.ai_explanation_provider_code is not None
        else settings.ai_explanation_provider_code
    )
    sharpe_strong = (
        record.sharpe_strong_threshold
        if record is not None and record.sharpe_strong_threshold is not None
        else Decimal(str(settings.sharpe_strong_threshold))
    )
    sharpe_slight = (
        record.sharpe_slight_threshold
        if record is not None and record.sharpe_slight_threshold is not None
        else Decimal(str(settings.sharpe_slight_threshold))
    )
    return AdvancedSettingsResponse(
        ensemble_weight_strategy=strategy,
        gbm_drift_window_days=drift_window,
        action_draft_approval_valid_minutes=approval_minutes,
        ai_explanation_provider_code=provider,
        sharpe_strong_threshold=_decimal_text(sharpe_strong),
        sharpe_slight_threshold=_decimal_text(sharpe_slight),
        help_nl=_ADVANCED_HELP_NL,
    )


@router.get("/settings/advanced", response_model=AdvancedSettingsResponse)
def get_advanced_settings() -> AdvancedSettingsResponse:
    provider = _storage_provider()
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
    return _advanced_payload(current)


@router.put("/settings/advanced", response_model=AdvancedSettingsResponse)
def update_advanced_settings(
    payload: UpdateAdvancedSettingsRequest,
) -> AdvancedSettingsResponse:
    if payload.ensemble_weight_strategy not in _ALLOWED_ENSEMBLE_STRATEGIES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ensemble-strategie moet 'equal_weight' of 'auto' zijn."
            ),
        )
    if payload.ai_explanation_provider_code not in _ALLOWED_AI_EXPLANATION_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail="AI-uitleg provider moet 'stub' of 'claude' zijn.",
        )
    if (
        payload.gbm_drift_window_days is not None
        and payload.gbm_drift_window_days < 1
    ):
        raise HTTPException(
            status_code=422,
            detail="GBM drift-venster moet ≥ 1 dag zijn (of leeglaten).",
        )
    if payload.action_draft_approval_valid_minutes < 1:
        raise HTTPException(
            status_code=422,
            detail="Goedkeuringsvenster moet ≥ 1 minuut zijn.",
        )
    if payload.sharpe_strong_threshold <= Decimal("0"):
        raise HTTPException(
            status_code=422,
            detail="Sharpe-sterk drempel moet > 0 zijn.",
        )
    if payload.sharpe_slight_threshold <= Decimal("0"):
        raise HTTPException(
            status_code=422,
            detail="Sharpe-licht drempel moet > 0 zijn.",
        )
    if payload.sharpe_slight_threshold >= payload.sharpe_strong_threshold:
        raise HTTPException(
            status_code=422,
            detail=(
                "Sharpe-licht drempel moet lager zijn dan de Sharpe-sterk drempel."
            ),
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=(
                    existing.default_buy_value_eur if existing else None
                ),
                default_top_up_pct=(
                    existing.default_top_up_pct if existing else None
                ),
                default_reduce_pct=(
                    existing.default_reduce_pct if existing else None
                ),
                max_sector_pct=existing.max_sector_pct if existing else None,
                cost_dominates_ratio=(
                    existing.cost_dominates_ratio if existing else None
                ),
                suggestion_valid_minutes=(
                    existing.suggestion_valid_minutes if existing else None
                ),
                scheduler_daily_briefing_cron=(
                    existing.scheduler_daily_briefing_cron if existing else None
                ),
                ibkr_sync_interval_minutes=(
                    existing.ibkr_sync_interval_minutes if existing else None
                ),
                forecast_history_lookback_days=(
                    existing.forecast_history_lookback_days if existing else None
                ),
                forecast_minimum_bars_required=(
                    existing.forecast_minimum_bars_required if existing else None
                ),
                daily_briefing_lookback_hours=(
                    existing.daily_briefing_lookback_hours if existing else None
                ),
                universe_scan_cache_ttl_hours=(
                    existing.universe_scan_cache_ttl_hours if existing else None
                ),
                sweep_interval_seconds=(
                    existing.sweep_interval_seconds if existing else None
                ),
                sweep_retry_max_attempts=(
                    existing.sweep_retry_max_attempts if existing else None
                ),
                sweep_retry_backoff_seconds=(
                    existing.sweep_retry_backoff_seconds if existing else None
                ),
                sweep_alert_after_consecutive_errors=(
                    existing.sweep_alert_after_consecutive_errors
                    if existing
                    else None
                ),
                eodhd_rate_limit_per_second=(
                    existing.eodhd_rate_limit_per_second if existing else None
                ),
                ensemble_weight_strategy=payload.ensemble_weight_strategy,
                gbm_drift_window_days=payload.gbm_drift_window_days,
                action_draft_approval_valid_minutes=(
                    payload.action_draft_approval_valid_minutes
                ),
                ai_explanation_provider_code=payload.ai_explanation_provider_code,
                sharpe_strong_threshold=payload.sharpe_strong_threshold,
                sharpe_slight_threshold=payload.sharpe_slight_threshold,
                forecast_horizon_trading_days=(
                    existing.forecast_horizon_trading_days if existing else None
                ),
                forecast_ensemble_enabled=(
                    existing.forecast_ensemble_enabled if existing else None
                ),
                suggestions_risk_profile=(
                    existing.suggestions_risk_profile if existing else None
                ),
                universe_set=existing.universe_set if existing else None,
                market_data_provider=(
                    existing.market_data_provider if existing else None
                ),
                market_data_sync_enabled=(
                    existing.market_data_sync_enabled if existing else None
                ),
                ibkr_market_data_enabled=(
                    existing.ibkr_market_data_enabled if existing else None
                ),
                ibkr_market_data_type=(
                    existing.ibkr_market_data_type if existing else None
                ),
            )
            repo.upsert(record)
            checked.connection.commit()
            settings.ensemble_weight_strategy = payload.ensemble_weight_strategy
            settings.gbm_drift_window_days = payload.gbm_drift_window_days
            settings.action_draft_approval_valid_minutes = (
                payload.action_draft_approval_valid_minutes
            )
            settings.ai_explanation_provider_code = (
                payload.ai_explanation_provider_code
            )
            settings.sharpe_strong_threshold = float(payload.sharpe_strong_threshold)
            settings.sharpe_slight_threshold = float(payload.sharpe_slight_threshold)
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _advanced_payload(record)


# ---- Forecast & market behaviour (Settings UI PR G) --------------------


_ALLOWED_UNIVERSE_SETS = ("SP500", "EU600", "ALL_5K")
_ALLOWED_RISK_PROFILES = ("Voorzichtig", "Gebalanceerd", "Groei")
_ALLOWED_MARKET_DATA_PROVIDERS = ("none", "eodhd", "ibkr")
_ALLOWED_IBKR_MARKET_DATA_TYPES = ("delayed", "realtime", "delayed_frozen", "frozen")


class ForecastMarketSettingsResponse(BaseModel):
    """Operator-facing forecast horizon, ensemble toggle, risk profile,
    locked-universe pick, and market-data feed toggles. Each value falls
    back to the env-var default when no DB row has been saved."""

    forecast_horizon_trading_days: int
    forecast_ensemble_enabled: bool
    suggestions_risk_profile: str
    universe_set: str
    market_data_provider: str
    market_data_sync_enabled: bool
    ibkr_market_data_enabled: bool
    ibkr_market_data_type: str
    help_nl: str


class UpdateForecastMarketSettingsRequest(BaseModel):
    forecast_horizon_trading_days: int
    forecast_ensemble_enabled: bool
    suggestions_risk_profile: str
    universe_set: str
    market_data_provider: str
    market_data_sync_enabled: bool
    ibkr_market_data_enabled: bool
    ibkr_market_data_type: str


_FORECAST_MARKET_HELP_NL = (
    "Voorspellings- en marktdata-instellingen. Horizon bepaalt hoe ver "
    "vooruit de modellen kijken; ensemble combineert meerdere predictors. "
    "Universum-set en marktdata-feeds bepalen welke prijzen het systeem "
    "gebruikt voor scans en suggesties."
)


def _forecast_market_payload(
    record: RuntimeConfigRecord | None,
) -> ForecastMarketSettingsResponse:
    horizon = (
        record.forecast_horizon_trading_days
        if record is not None and record.forecast_horizon_trading_days is not None
        else settings.forecast_horizon_trading_days
    )
    ensemble = (
        record.forecast_ensemble_enabled
        if record is not None and record.forecast_ensemble_enabled is not None
        else settings.forecast_ensemble_enabled
    )
    risk_profile = (
        record.suggestions_risk_profile
        if record is not None and record.suggestions_risk_profile is not None
        else settings.suggestions_risk_profile
    )
    universe = (
        record.universe_set
        if record is not None and record.universe_set is not None
        else settings.universe_set
    )
    md_provider = (
        record.market_data_provider
        if record is not None and record.market_data_provider is not None
        else settings.market_data_provider
    )
    md_sync = (
        record.market_data_sync_enabled
        if record is not None and record.market_data_sync_enabled is not None
        else settings.market_data_sync_enabled
    )
    ibkr_md_enabled = (
        record.ibkr_market_data_enabled
        if record is not None and record.ibkr_market_data_enabled is not None
        else settings.ibkr_market_data_enabled
    )
    ibkr_md_type = (
        record.ibkr_market_data_type
        if record is not None and record.ibkr_market_data_type is not None
        else settings.ibkr_market_data_type
    )
    return ForecastMarketSettingsResponse(
        forecast_horizon_trading_days=horizon,
        forecast_ensemble_enabled=ensemble,
        suggestions_risk_profile=risk_profile,
        universe_set=universe,
        market_data_provider=md_provider,
        market_data_sync_enabled=md_sync,
        ibkr_market_data_enabled=ibkr_md_enabled,
        ibkr_market_data_type=ibkr_md_type,
        help_nl=_FORECAST_MARKET_HELP_NL,
    )


@router.get(
    "/settings/forecast-market",
    response_model=ForecastMarketSettingsResponse,
)
def get_forecast_market_settings() -> ForecastMarketSettingsResponse:
    provider = _storage_provider()
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
    return _forecast_market_payload(current)


@router.put(
    "/settings/forecast-market",
    response_model=ForecastMarketSettingsResponse,
)
def update_forecast_market_settings(
    payload: UpdateForecastMarketSettingsRequest,
) -> ForecastMarketSettingsResponse:
    if payload.forecast_horizon_trading_days < 1:
        raise HTTPException(
            status_code=422,
            detail="Voorspellings-horizon moet ≥ 1 handelsdag zijn.",
        )
    if payload.suggestions_risk_profile not in _ALLOWED_RISK_PROFILES:
        raise HTTPException(
            status_code=422,
            detail="Risico-profiel moet 'Voorzichtig', 'Gebalanceerd' of 'Groei' zijn.",
        )
    if payload.universe_set not in _ALLOWED_UNIVERSE_SETS:
        raise HTTPException(
            status_code=422,
            detail="Universum-set moet 'SP500', 'EU600' of 'ALL_5K' zijn.",
        )
    if payload.market_data_provider not in _ALLOWED_MARKET_DATA_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail="Marktdata-provider moet 'none', 'eodhd' of 'ibkr' zijn.",
        )
    if payload.ibkr_market_data_type not in _ALLOWED_IBKR_MARKET_DATA_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                "IBKR marktdata-type moet 'delayed', 'realtime', "
                "'delayed_frozen' of 'frozen' zijn."
            ),
        )

    now = datetime.now(UTC)
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get()
            record = RuntimeConfigRecord(
                config_id=_CONFIG_ID,
                ibkr_enabled=existing.ibkr_enabled if existing else False,
                ibkr_account_id=existing.ibkr_account_id if existing else None,
                ibkr_host=existing.ibkr_host if existing else None,
                ibkr_port=existing.ibkr_port if existing else None,
                ibkr_client_id=existing.ibkr_client_id if existing else None,
                ai_explanation_enabled=(
                    existing.ai_explanation_enabled if existing else False
                ),
                claude_ai_explanation_model=(
                    existing.claude_ai_explanation_model if existing else None
                ),
                claude_ai_budget_monthly_eur=(
                    existing.claude_ai_budget_monthly_eur if existing else None
                ),
                claude_ai_api_key=existing.claude_ai_api_key if existing else None,
                updated_at=now,
                universe_scan_index_codes=(
                    existing.universe_scan_index_codes if existing else None
                ),
                default_buy_value_eur=(
                    existing.default_buy_value_eur if existing else None
                ),
                default_top_up_pct=(
                    existing.default_top_up_pct if existing else None
                ),
                default_reduce_pct=(
                    existing.default_reduce_pct if existing else None
                ),
                max_sector_pct=existing.max_sector_pct if existing else None,
                cost_dominates_ratio=(
                    existing.cost_dominates_ratio if existing else None
                ),
                suggestion_valid_minutes=(
                    existing.suggestion_valid_minutes if existing else None
                ),
                scheduler_daily_briefing_cron=(
                    existing.scheduler_daily_briefing_cron if existing else None
                ),
                ibkr_sync_interval_minutes=(
                    existing.ibkr_sync_interval_minutes if existing else None
                ),
                forecast_history_lookback_days=(
                    existing.forecast_history_lookback_days if existing else None
                ),
                forecast_minimum_bars_required=(
                    existing.forecast_minimum_bars_required if existing else None
                ),
                daily_briefing_lookback_hours=(
                    existing.daily_briefing_lookback_hours if existing else None
                ),
                universe_scan_cache_ttl_hours=(
                    existing.universe_scan_cache_ttl_hours if existing else None
                ),
                sweep_interval_seconds=(
                    existing.sweep_interval_seconds if existing else None
                ),
                sweep_retry_max_attempts=(
                    existing.sweep_retry_max_attempts if existing else None
                ),
                sweep_retry_backoff_seconds=(
                    existing.sweep_retry_backoff_seconds if existing else None
                ),
                sweep_alert_after_consecutive_errors=(
                    existing.sweep_alert_after_consecutive_errors
                    if existing
                    else None
                ),
                eodhd_rate_limit_per_second=(
                    existing.eodhd_rate_limit_per_second if existing else None
                ),
                ensemble_weight_strategy=(
                    existing.ensemble_weight_strategy if existing else None
                ),
                gbm_drift_window_days=(
                    existing.gbm_drift_window_days if existing else None
                ),
                action_draft_approval_valid_minutes=(
                    existing.action_draft_approval_valid_minutes
                    if existing
                    else None
                ),
                ai_explanation_provider_code=(
                    existing.ai_explanation_provider_code if existing else None
                ),
                sharpe_strong_threshold=(
                    existing.sharpe_strong_threshold if existing else None
                ),
                sharpe_slight_threshold=(
                    existing.sharpe_slight_threshold if existing else None
                ),
                forecast_horizon_trading_days=payload.forecast_horizon_trading_days,
                forecast_ensemble_enabled=payload.forecast_ensemble_enabled,
                suggestions_risk_profile=payload.suggestions_risk_profile,
                universe_set=payload.universe_set,
                market_data_provider=payload.market_data_provider,
                market_data_sync_enabled=payload.market_data_sync_enabled,
                ibkr_market_data_enabled=payload.ibkr_market_data_enabled,
                ibkr_market_data_type=payload.ibkr_market_data_type,
            )
            repo.upsert(record)
            checked.connection.commit()
            settings.forecast_horizon_trading_days = (
                payload.forecast_horizon_trading_days
            )
            settings.forecast_ensemble_enabled = payload.forecast_ensemble_enabled
            settings.suggestions_risk_profile = payload.suggestions_risk_profile
            settings.universe_set = payload.universe_set
            settings.market_data_provider = payload.market_data_provider
            settings.market_data_sync_enabled = payload.market_data_sync_enabled
            settings.ibkr_market_data_enabled = payload.ibkr_market_data_enabled
            settings.ibkr_market_data_type = payload.ibkr_market_data_type
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _forecast_market_payload(record)


def apply_runtime_config_overlay(
    settings_obj: Any, record: RuntimeConfigRecord
) -> None:
    """Overlay the non-null ``runtime_config`` values onto the settings object.

    Called at API startup so the operator-edited IBKR account + Claude AI
    settings take effect without an env change. Only non-null values are
    overlaid, so an empty field never clobbers a configured default.

    Worker-side IBKR host/port/client_id overlay is OUT OF SCOPE here — that is
    a follow-up tied to the durable worker session (the worker is not modified).
    """

    if record.ibkr_account_id is not None:
        settings_obj.ibkr_account_id_hint = record.ibkr_account_id
    if record.claude_ai_api_key is not None:
        settings_obj.claude_ai_api_key = record.claude_ai_api_key
    if record.claude_ai_explanation_model is not None:
        settings_obj.claude_ai_explanation_model = record.claude_ai_explanation_model
    if record.claude_ai_budget_monthly_eur is not None:
        settings_obj.claude_ai_budget_monthly_eur = record.claude_ai_budget_monthly_eur
    # ``ai_explanation_enabled`` is a non-null boolean column; the persisted
    # operator choice always wins once a row exists.
    settings_obj.ai_explanation_enabled = record.ai_explanation_enabled
    if record.universe_scan_index_codes is not None:
        settings_obj.universe_scan_index_codes = record.universe_scan_index_codes
    # Settings UI PR A — push operator-edited order policy onto the
    # singleton so the next morning chain / action-draft sync picks it
    # up without an API restart. Each null leaves the env-default alone.
    if record.default_buy_value_eur is not None:
        settings_obj.action_drafts_default_buy_value = str(
            record.default_buy_value_eur
        )
    if record.default_top_up_pct is not None:
        settings_obj.action_drafts_top_up_pct = str(record.default_top_up_pct)
    if record.default_reduce_pct is not None:
        settings_obj.action_drafts_reduce_pct = str(record.default_reduce_pct)
    if record.max_sector_pct is not None:
        settings_obj.max_sector_pct = str(record.max_sector_pct)
    if record.cost_dominates_ratio is not None:
        settings_obj.cost_dominates_ratio = str(record.cost_dominates_ratio)
    if record.suggestion_valid_minutes is not None:
        settings_obj.suggestions_valid_minutes = record.suggestion_valid_minutes
    # Settings UI PR B — scheduler-cadence overlay. Takes effect on the
    # next API restart for the in-process scheduler (the cron is read at
    # ``install_default_jobs`` time); ``ibkr_sync_interval_minutes`` is
    # read each scheduled tick, so a save flows through immediately.
    if record.scheduler_daily_briefing_cron is not None:
        settings_obj.scheduler_daily_briefing_cron = record.scheduler_daily_briefing_cron
    if record.ibkr_sync_interval_minutes is not None:
        settings_obj.ibkr_sync_interval_minutes = record.ibkr_sync_interval_minutes
    # Settings UI PR C — data-window overlay.
    if record.forecast_history_lookback_days is not None:
        settings_obj.forecast_history_lookback_days = (
            record.forecast_history_lookback_days
        )
    if record.forecast_minimum_bars_required is not None:
        settings_obj.forecast_minimum_bars_required = (
            record.forecast_minimum_bars_required
        )
    if record.daily_briefing_lookback_hours is not None:
        settings_obj.daily_briefing_lookback_hours = (
            record.daily_briefing_lookback_hours
        )
    if record.universe_scan_cache_ttl_hours is not None:
        settings_obj.universe_scan_cache_ttl_hours = (
            record.universe_scan_cache_ttl_hours
        )
    # Settings UI PR D — worker-side sweep + EODHD values are also
    # written here so the API's GET /settings/worker-sweeps reads back
    # the operator-edited values without an extra storage hop. The
    # WORKER reads the same row via apply_worker_runtime_config_overlay
    # at its own startup; the API just mirrors the columns for display.
    # Settings UI PR E — Tier-2 advanced overlay. Each null falls back
    # to the env-default; these power-user knobs live behind the
    # collapsed "Geavanceerde instellingen" accordion in the UI.
    if record.ensemble_weight_strategy is not None:
        settings_obj.ensemble_weight_strategy = record.ensemble_weight_strategy
    if record.gbm_drift_window_days is not None:
        settings_obj.gbm_drift_window_days = record.gbm_drift_window_days
    if record.action_draft_approval_valid_minutes is not None:
        settings_obj.action_draft_approval_valid_minutes = (
            record.action_draft_approval_valid_minutes
        )
    if record.ai_explanation_provider_code is not None:
        settings_obj.ai_explanation_provider_code = record.ai_explanation_provider_code
    # Settings UI PR F — Sharpe direction-label thresholds. Stored as
    # Decimal in the DB; the GBM path expects float. Null leaves the
    # env-default (1.0 / 0.3) in place.
    if record.sharpe_strong_threshold is not None:
        settings_obj.sharpe_strong_threshold = float(record.sharpe_strong_threshold)
    if record.sharpe_slight_threshold is not None:
        settings_obj.sharpe_slight_threshold = float(record.sharpe_slight_threshold)
    # Settings UI PR G — forecast & market-behaviour overlay. Each null
    # leaves the env-default in place.
    if record.forecast_horizon_trading_days is not None:
        settings_obj.forecast_horizon_trading_days = (
            record.forecast_horizon_trading_days
        )
    if record.forecast_ensemble_enabled is not None:
        settings_obj.forecast_ensemble_enabled = record.forecast_ensemble_enabled
    if record.suggestions_risk_profile is not None:
        settings_obj.suggestions_risk_profile = record.suggestions_risk_profile
    if record.universe_set is not None:
        settings_obj.universe_set = record.universe_set
    if record.market_data_provider is not None:
        settings_obj.market_data_provider = record.market_data_provider
    if record.market_data_sync_enabled is not None:
        settings_obj.market_data_sync_enabled = record.market_data_sync_enabled
    if record.ibkr_market_data_enabled is not None:
        settings_obj.ibkr_market_data_enabled = record.ibkr_market_data_enabled
    if record.ibkr_market_data_type is not None:
        settings_obj.ibkr_market_data_type = record.ibkr_market_data_type
