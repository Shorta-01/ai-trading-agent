"""SELL-suggestie kaartjes endpoints (V1.2 §BF / CLAUDE.md §6).

Drie endpoints voor het dashboard:

* ``GET /sell-signals`` — actieve SELL-suggestie kaartjes
  (``action='suggest_sell' AND dismissed_at IS NULL``).
* ``POST /sell-signals/{card_id}/dismiss`` — operator klikt
  "verwijder uit lijst". Sticky tot het signaal materieel
  verandert (CLAUDE.md §6.3 — opnieuw rijzen na dismiss).
* ``POST /sell-signals/sweep`` — handmatige trigger voor de sweep
  (worker-cron of operator-knop). Returnt teller-aggregaat.

CLAUDE.md §2 fundamenteel principe: de kaartjes zijn ADVIES — geen
order, geen action-draft auto-promotie. ``safe_for_action_drafts``
blijft hard ``False`` op elke kaart.

CLAUDE.md §11 fundamenteel principe: de sweep checkt geen
pauze-flag. SELL-monitoring blijft draaien tijdens pauze.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    SellSignalCardRecord,
    SqlAlchemySellSignalCardRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.sell_signal_sweep import (
    DEFAULT_HORIZON_REVIEW_START_DAYS,
    DEFAULT_IBKR_ACCOUNT_REF,
    DEFAULT_LOSS_FLOOR_PCT,
    DEFAULT_TARGET_NET_PCT,
    SellSignalSweepResult,
    run_sell_signal_sweep,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SellSignalCardResponse(BaseModel):
    card_id: str
    ibkr_account_ref: str
    symbol: str
    currency: str
    signal_kind: str
    action: str
    entry_price: str
    current_price: str
    quantity: int
    current_pct_return: str
    target_pct: str | None
    target_reached: bool | None
    days_held: int | None
    forecast_id: str | None
    forecaster_above_target: bool | None
    position_in_loss: bool | None
    short_term_p50: str | None
    short_term_horizon_days: int | None
    short_term_prob_above_pct: str | None
    expected_net_proceeds_eur: str | None
    headline_nl: str
    detail_nl: str
    first_generated_at: str
    last_evaluated_at: str
    dismissed_at: str | None
    dismissed_reason: str | None


class SellSignalListResponse(BaseModel):
    title_nl: str
    help_nl: str
    cards: list[SellSignalCardResponse]


class DismissRequest(BaseModel):
    reason: str | None = None


class SellSignalSweepResponse(BaseModel):
    started_at: str
    completed_at: str
    positions_evaluated: int
    take_profit_cards_upserted: int
    hold_review_cards_upserted: int
    skipped_no_forecast: int
    skipped_no_position: int
    error_text: str | None


_HELP_NL = (
    "SELL-suggestie kaartjes. De software toont kaartjes wanneer een "
    "positie de +4 %-target raakt (CLAUDE.md §6.3) of na 6+ maanden "
    "de combo-trigger oplevert (CLAUDE.md §6.2 — forecast verzwakt "
    "EN positie in verlies). Elk kaartje is enkel ADVIES; de operator "
    "beslist altijd of hij verkoopt."
)


def _decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _datetime_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _to_response(card: SellSignalCardRecord) -> SellSignalCardResponse:
    return SellSignalCardResponse(
        card_id=card.card_id,
        ibkr_account_ref=card.ibkr_account_ref,
        symbol=card.symbol,
        currency=card.currency,
        signal_kind=card.signal_kind,
        action=card.action,
        entry_price=format(card.entry_price, "f"),
        current_price=format(card.current_price, "f"),
        quantity=card.quantity,
        current_pct_return=format(card.current_pct_return, "f"),
        target_pct=_decimal_to_str(card.target_pct),
        target_reached=card.target_reached,
        days_held=card.days_held,
        forecast_id=card.forecast_id,
        forecaster_above_target=card.forecaster_above_target,
        position_in_loss=card.position_in_loss,
        short_term_p50=_decimal_to_str(card.short_term_p50),
        short_term_horizon_days=card.short_term_horizon_days,
        short_term_prob_above_pct=_decimal_to_str(card.short_term_prob_above_pct),
        expected_net_proceeds_eur=_decimal_to_str(card.expected_net_proceeds_eur),
        headline_nl=card.headline_nl,
        detail_nl=card.detail_nl,
        first_generated_at=card.first_generated_at.isoformat(),
        last_evaluated_at=card.last_evaluated_at.isoformat(),
        dismissed_at=_datetime_to_str(card.dismissed_at),
        dismissed_reason=card.dismissed_reason,
    )


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


@router.get("/sell-signals", response_model=SellSignalListResponse)
def list_active_sell_signals(
    account_ref: str | None = None,
) -> SellSignalListResponse:
    """Lijst actieve SELL-suggestie kaartjes."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return SellSignalListResponse(
            title_nl="SELL-suggesties",
            help_nl=_HELP_NL,
            cards=[],
        )
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemySellSignalCardRepository(
                checked.connection, checked.readiness
            )
            result = repo.list_active(ibkr_account_ref=account_ref)
    except StorageConnectionError as exc:
        logger.warning("sell-signals read storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    return SellSignalListResponse(
        title_nl="SELL-suggesties",
        help_nl=_HELP_NL,
        cards=[_to_response(card) for card in result.records],
    )


@router.post(
    "/sell-signals/{card_id}/dismiss",
    response_model=SellSignalCardResponse,
)
def dismiss_sell_signal(card_id: str, request: DismissRequest) -> SellSignalCardResponse:
    """Operator: verwijder een SELL-suggestie uit de lijst."""

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySellSignalCardRepository(
                checked.connection, checked.readiness
            )
            existing = repo.get(card_id=card_id)
            if existing is None:
                raise HTTPException(
                    status_code=404, detail="SELL-kaartje niet gevonden."
                )
            repo.dismiss(
                card_id=card_id,
                dismissed_at=datetime.now(UTC),
                reason=request.reason,
            )
            checked.connection.commit()
            updated = repo.get(card_id=card_id)
            if updated is None:  # pragma: no cover — race protection
                raise HTTPException(
                    status_code=404, detail="SELL-kaartje verdween na dismiss."
                )
            return _to_response(updated)
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("sell-signals dismiss storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc


@router.post("/sell-signals/sweep", response_model=SellSignalSweepResponse)
def trigger_sell_signal_sweep() -> SellSignalSweepResponse:
    """Handmatige trigger voor de SELL-loop sweep.

    De worker-scheduler roept dit elke 15 min aan tijdens
    market-hours; de operator kan het via de UI handmatig
    triggeren voor een verse evaluatie. De endpoint checkt
    bewust GEEN pauze-flag — CLAUDE.md §11 vraagt dat de
    SELL-monitor blijft draaien.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )

    target_net_pct = _read_profit_target_pct() or DEFAULT_TARGET_NET_PCT
    result: SellSignalSweepResult = run_sell_signal_sweep(
        database_url=storage.database_url,
        target_net_pct=target_net_pct,
        loss_floor_pct=DEFAULT_LOSS_FLOOR_PCT,
        horizon_review_start_days=DEFAULT_HORIZON_REVIEW_START_DAYS,
        ibkr_account_ref=DEFAULT_IBKR_ACCOUNT_REF,
    )
    return SellSignalSweepResponse(
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat(),
        positions_evaluated=result.positions_evaluated,
        take_profit_cards_upserted=result.take_profit_cards_upserted,
        hold_review_cards_upserted=result.hold_review_cards_upserted,
        skipped_no_forecast=result.skipped_no_forecast,
        skipped_no_position=result.skipped_no_position,
        error_text=result.error_text,
    )


def _read_profit_target_pct() -> Decimal | None:
    """Lees de operator-doctrine winst-target uit de runtime-config
    (V1.2 §AZ). Wanneer niet geconfigureerd, valt de sweep terug
    op de §6.1 default van +4 %.

    Lazy import zodat de sell-signal module zelf geen harde
    afhankelijkheid op profit_target heeft (test-friendly).
    """

    try:
        from portfolio_outlook_api.profit_target import get_profit_target_pct
    except ImportError:
        return None
    try:
        return get_profit_target_pct()
    except Exception:  # noqa: BLE001 — fallback to default on any error
        logger.exception("profit_target read failed; using default 4%")
        return None


__all__ = ["router"]
