"""Risk-limits (behavioural guardrail) settings API — Task 138.

Surfaces the per-account behavioural guardrail thresholds
(daily approval cap, cool-down, anti-revenge, soft/hard drawdown,
FOMO drift) as an editable settings panel for the dashboard:

- ``GET /settings/risk-limits``  -> current-or-default guardrails
- ``PUT /settings/risk-limits``  -> validate + upsert, return saved values

Mirrors the storage-access patterns in ``error_routes.py``:
``_storage_provider()`` + ``provider.checked_connection(...)`` + an
explicit ``checked.connection.commit()`` on writes (the context
manager does NOT auto-commit). Decimal fields are serialised as
strings so no float rounding leaks into the response.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ai_trading_agent_storage import (
    BehaviouralGuardrailSettings,
    SqlAlchemyBehaviouralGuardrailSettingsRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Fallback account id when no hint is configured (mirrors action_draft.py
# convention but never 404s — the guardrail panel always has a target).
_DEFAULT_ACCOUNT_ID = "DEFAULT"


class RiskLimitsResponse(BaseModel):
    ibkr_account_id: str
    daily_max_approvals: int
    cooldown_seconds: int
    anti_revenge_window_hours: int
    anti_revenge_loss_threshold_pct: str
    soft_drawdown_pct: str
    soft_drawdown_window_days: int
    hard_drawdown_pct: str
    hard_drawdown_window_days: int
    fomo_drift_pct: str
    last_updated_at: str


class UpdateRiskLimitsRequest(BaseModel):
    daily_max_approvals: int
    cooldown_seconds: int
    anti_revenge_window_hours: int
    anti_revenge_loss_threshold_pct: Decimal
    soft_drawdown_pct: Decimal
    soft_drawdown_window_days: int
    hard_drawdown_pct: Decimal
    hard_drawdown_window_days: int
    fomo_drift_pct: Decimal


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(status_code=503, detail="Opslag is niet beschikbaar.")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _configured_account_id() -> str:
    """Resolve the IBKR account id hint, falling back to ``DEFAULT``.

    Mirrors ``action_draft.py:_configured_account_id`` but never returns
    ``None`` — the guardrail panel always operates on a concrete row.
    """

    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return _DEFAULT_ACCOUNT_ID
    text = str(hint).strip()
    return text or _DEFAULT_ACCOUNT_ID


def _decimal_str(value: Decimal) -> str:
    """Canonical Decimal -> str: strip storage scale padding (the column is
    ``Numeric(8, 4)`` so a stored ``2.5`` reads back as ``2.5000``) while
    keeping at least one fractional digit. This makes the PUT response (built
    from the in-memory object) and a fresh GET (read back from the DB) return
    identical strings, and never leaks a float."""

    normalized = value.normalize()
    text = format(normalized, "f")
    if "." not in text:
        text += ".0"
    return text


def _serialise(settings_row: BehaviouralGuardrailSettings) -> RiskLimitsResponse:
    return RiskLimitsResponse(
        ibkr_account_id=settings_row.ibkr_account_id,
        daily_max_approvals=settings_row.daily_max_approvals,
        cooldown_seconds=settings_row.cooldown_seconds,
        anti_revenge_window_hours=settings_row.anti_revenge_window_hours,
        anti_revenge_loss_threshold_pct=_decimal_str(
            settings_row.anti_revenge_loss_threshold_pct
        ),
        soft_drawdown_pct=_decimal_str(settings_row.soft_drawdown_pct),
        soft_drawdown_window_days=settings_row.soft_drawdown_window_days,
        hard_drawdown_pct=_decimal_str(settings_row.hard_drawdown_pct),
        hard_drawdown_window_days=settings_row.hard_drawdown_window_days,
        fomo_drift_pct=_decimal_str(settings_row.fomo_drift_pct),
        last_updated_at=settings_row.last_updated_at.isoformat(),
    )


@router.get("/settings/risk-limits", response_model=RiskLimitsResponse)
def get_risk_limits() -> RiskLimitsResponse:
    provider = _storage_provider()
    account_id = _configured_account_id()
    now = datetime.now(UTC)
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
                checked.connection, checked.readiness
            )
            current = repo.get_or_default(ibkr_account_id=account_id, now=now)
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _serialise(current)


@router.put("/settings/risk-limits", response_model=RiskLimitsResponse)
def update_risk_limits(payload: UpdateRiskLimitsRequest) -> RiskLimitsResponse:
    account_id = _configured_account_id()
    now = datetime.now(UTC)
    try:
        new_settings = BehaviouralGuardrailSettings(
            ibkr_account_id=account_id,
            daily_max_approvals=payload.daily_max_approvals,
            cooldown_seconds=payload.cooldown_seconds,
            anti_revenge_window_hours=payload.anti_revenge_window_hours,
            anti_revenge_loss_threshold_pct=payload.anti_revenge_loss_threshold_pct,
            soft_drawdown_pct=payload.soft_drawdown_pct,
            soft_drawdown_window_days=payload.soft_drawdown_window_days,
            hard_drawdown_pct=payload.hard_drawdown_pct,
            hard_drawdown_window_days=payload.hard_drawdown_window_days,
            fomo_drift_pct=payload.fomo_drift_pct,
            last_updated_at=now,
        )
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
                checked.connection, checked.readiness
            )
            saved = repo.upsert(new_settings)
            checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return _serialise(saved)
