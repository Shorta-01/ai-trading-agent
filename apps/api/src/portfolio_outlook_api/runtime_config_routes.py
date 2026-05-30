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
