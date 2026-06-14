"""Settings endpoint voor operator-configureerbaar winstdoel (V1.2 §AZ).

``GET /settings/profit-target`` — huidige waarde (None → doctrine-default).
``PUT /settings/profit-target`` — operator zet een nieuwe waarde of
``null`` om naar de doctrine terug te vallen.

Toegestane range: 1.0 % t/m 50.0 %. Onder 1 % heeft TOB-cost een
groter aandeel dan de winst zelf; boven 50 % maakt de doctrine geen
voorstellen meer praktisch realistisch.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ai_trading_agent_storage import (
    RuntimeConfigRecord,
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.profit_target import (
    DOCTRINE_DEFAULT_PCT,
    get_profit_target_pct,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_MIN_PCT = Decimal("1")
_MAX_PCT = Decimal("50")


class ProfitTargetResponse(BaseModel):
    title_nl: str
    help_nl: str
    profit_target_pct: str
    is_doctrine_default: bool
    summary_nl: str


class ProfitTargetUpdateRequest(BaseModel):
    profit_target_pct: str | None


_HELP_NL = (
    "Operator-aanpasbaar winstdoel voor de profit-harvest doctrine. "
    "Default 4 % per CLAUDE.md §6.1. Verhogen geeft minder maar "
    "grotere SELL-suggesties; verlagen geeft sneller exits. Verkoop "
    "blijft een suggestie — de operator beslist."
)


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )
    assert storage.database_url is not None
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _default_record(now: datetime) -> RuntimeConfigRecord:
    return RuntimeConfigRecord(
        config_id="default",
        ibkr_enabled=False,
        ibkr_account_id=None,
        ibkr_host=None,
        ibkr_port=None,
        ibkr_client_id=None,
        ai_explanation_enabled=False,
        claude_ai_explanation_model=None,
        claude_ai_budget_monthly_eur=None,
        claude_ai_api_key=None,
        updated_at=now,
    )


def _summary(pct: Decimal, is_default: bool) -> str:
    if is_default:
        return (
            f"Doctrine-default {pct} % actief — geen operator-"
            "overschrijving ingesteld."
        )
    return f"Operator-keuze: {pct} % per trade."


def _to_response(pct: Decimal, *, is_default: bool) -> ProfitTargetResponse:
    return ProfitTargetResponse(
        title_nl="Winstdoel per trade",
        help_nl=_HELP_NL,
        profit_target_pct=str(pct),
        is_doctrine_default=is_default,
        summary_nl=_summary(pct, is_default),
    )


def _parse_pct(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="profit_target_pct moet een decimaal getal zijn.",
        ) from exc
    if value < _MIN_PCT or value > _MAX_PCT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"profit_target_pct moet tussen {_MIN_PCT} % en "
                f"{_MAX_PCT} % liggen."
            ),
        )
    return value


@router.get("/settings/profit-target", response_model=ProfitTargetResponse)
def get_profit_target_setting() -> ProfitTargetResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _to_response(DOCTRINE_DEFAULT_PCT, is_default=True)
    pct = get_profit_target_pct()
    return _to_response(pct, is_default=(pct == DOCTRINE_DEFAULT_PCT))


@router.put("/settings/profit-target", response_model=ProfitTargetResponse)
def update_profit_target_setting(
    payload: ProfitTargetUpdateRequest,
) -> ProfitTargetResponse:
    parsed = _parse_pct(payload.profit_target_pct)

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            now = datetime.now(UTC)
            existing = repo.get()
            base = existing if existing is not None else _default_record(now)
            updated = RuntimeConfigRecord(
                **{
                    **base.__dict__,
                    "profit_target_net_pct": parsed,
                    "updated_at": now,
                }
            )
            repo.upsert(updated)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("profit-target update storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    pct = parsed if parsed is not None else DOCTRINE_DEFAULT_PCT
    return _to_response(pct, is_default=(parsed is None))


__all__ = ["router"]
