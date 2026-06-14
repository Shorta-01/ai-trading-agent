"""SELL-loop sweep (V1.2 §BF / CLAUDE.md §6.2 + §6.3).

Wires the existing pure-Python evaluators into een production
sweep die periodiek over alle geopende posities loopt en SELL-
suggestie kaartjes naar storage schrijft. De evaluators zijn:

* :func:`portfolio_outlook_portfolio.evaluate_take_profit_signal`
  (§6.3 — +4% intraday check)
* :func:`portfolio_outlook_portfolio.evaluate_hold_position_review`
  (§6.2 — 6m+ combo-trigger forecast verzwakt EN positie in
  verlies)

Beide evaluators waren tot V1.2 alleen via unit-tests gedekt. Deze
sweep brengt ze in productie zodat de dashboard-UI eindelijk een
levende lijst van SELL-suggesties heeft.

Doctrine-borging:

* CLAUDE.md §2 — de sweep schrijft alleen kaartjes; geen automatische
  orders. ``safe_for_action_drafts=False`` blijft hard op de kaartjes.
* CLAUDE.md §11 — SELL-monitoring draait door tijdens software-pauze.
  Deze sweep checkt expliciet GEEN pauze-flag.
* CLAUDE.md §6.1 — target_net_pct (default +4 %) komt uit de
  runtime-config (`profit_target_routes` / §AZ), zodat de operator
  hem kan bijstellen zonder code-deploy.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from ai_trading_agent_storage import (
    SELL_SIGNAL_ACTION_HOLD,
    SELL_SIGNAL_ACTION_SUGGEST_SELL,
    SELL_SIGNAL_KIND_HOLD_REVIEW,
    SELL_SIGNAL_KIND_TAKE_PROFIT,
    SaveSellSignalCardRequest,
    SqlAlchemySellSignalCardRepository,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import (
    asset_forecasts,
    ibkr_position_snapshots,
    ibkr_sync_runs,
    sell_signal_cards,
)
from ai_trading_agent_storage.migration_readiness import MigrationReadinessReport
from portfolio_outlook_portfolio import (
    HOLD_ACTION_SUGGEST_SELL,
    SIGNAL_SUGGEST_SELL,
    HoldPositionReviewInputs,
    TakeProfitSignalInputs,
    evaluate_hold_position_review,
    evaluate_take_profit_signal,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)


# Locked default — overrides komen later via runtime-config wanneer
# de operator bij voorkeur dubbel-monitoring wil (b.v. positie ouder
# dan 30 dagen → take-profit check elke 5 min, jonger → elke 30 min).
DEFAULT_TARGET_NET_PCT: Decimal = Decimal("4")
DEFAULT_LOSS_FLOOR_PCT: Decimal = Decimal("-5")
DEFAULT_HORIZON_REVIEW_START_DAYS: int = 180

# Fallback voor de single-paper-account die V1 ondersteunt.
DEFAULT_IBKR_ACCOUNT_REF: str = "paper"


@dataclass(frozen=True)
class _PositionRow:
    """Posities-aggregaat zoals de sweep ze leest uit
    ``ibkr_position_snapshots`` (latest sync_run).
    """

    symbol: str
    currency: str
    quantity: int
    average_cost: Decimal
    received_at: datetime


@dataclass(frozen=True)
class _ForecastRow:
    """Minimale forecast-projectie zoals de sweep ze nodig heeft."""

    forecast_id: str
    symbol: str
    current_price: Decimal
    p50_price: Decimal
    horizon_days: int
    prob_gain: Decimal | None


@dataclass(frozen=True)
class SellSignalSweepResult:
    """Aggregaat van één sweep-fire.

    Bedoeld voor de API-respons en het audit-log; bevat alleen
    deterministische tellers — geen broker-state, geen
    operator-secrets.
    """

    started_at: datetime
    completed_at: datetime
    positions_evaluated: int
    take_profit_cards_upserted: int
    hold_review_cards_upserted: int
    skipped_no_forecast: int
    skipped_no_position: int
    error_text: str | None


def _latest_sync_run_id(connection: Any) -> str | None:
    row = (
        connection.execute(
            select(ibkr_sync_runs.c.sync_run_id)
            .order_by(ibkr_sync_runs.c.started_at.desc())
            .limit(1)
        )
        .first()
    )
    if row is None:
        return None
    return str(row[0])


def _load_positions(connection: Any) -> tuple[_PositionRow, ...]:
    """Lees de huidige positie-snapshot — niet-gerealiseerde holdings
    die de sweep moet monitoren.
    """

    sync_run_id = _latest_sync_run_id(connection)
    if sync_run_id is None:
        return ()
    rows = (
        connection.execute(
            select(
                ibkr_position_snapshots.c.symbol,
                ibkr_position_snapshots.c.currency,
                ibkr_position_snapshots.c.quantity,
                ibkr_position_snapshots.c.average_cost,
                ibkr_position_snapshots.c.received_at,
            )
            .where(ibkr_position_snapshots.c.sync_run_id == sync_run_id)
            .where(ibkr_position_snapshots.c.quantity != 0)
        )
        .all()
    )
    out: list[_PositionRow] = []
    for symbol, currency, quantity, average_cost, received_at in rows:
        if symbol is None or quantity is None or average_cost is None:
            continue
        qty = int(Decimal(quantity))
        if qty <= 0:
            # SELL-loop monitort alleen long-posities; shorts vallen
            # buiten doctrine (CLAUDE.md §15 — geen leverage, geen
            # shorts).
            continue
        out.append(
            _PositionRow(
                symbol=str(symbol),
                currency=str(currency or "USD"),
                quantity=qty,
                average_cost=Decimal(average_cost),
                received_at=received_at,
            )
        )
    return tuple(out)


def _load_latest_forecasts_by_symbol(
    connection: Any,
) -> dict[str, _ForecastRow]:
    """Lees per symbool de laatst-gegenereerde ``asset_forecasts`` rij.

    Eén query met ``ORDER BY symbol ASC, generated_at DESC`` en
    pak in Python het eerste voorkomen per symbool. Synchroon
    gehouden met de orchestrator-leg implementatie zodat beide
    consistent zijn.
    """

    rows = (
        connection.execute(
            select(
                asset_forecasts.c.forecast_id,
                asset_forecasts.c.symbol,
                asset_forecasts.c.current_price,
                asset_forecasts.c.p50_price,
                asset_forecasts.c.horizon_days,
                asset_forecasts.c.prob_gain,
            ).order_by(
                asset_forecasts.c.symbol.asc(),
                asset_forecasts.c.generated_at.desc(),
            )
        )
        .all()
    )
    latest: dict[str, _ForecastRow] = {}
    for forecast_id, symbol, current_price, p50_price, horizon, prob_gain in rows:
        if symbol is None or symbol in latest:
            continue
        latest[str(symbol)] = _ForecastRow(
            forecast_id=str(forecast_id),
            symbol=str(symbol),
            current_price=Decimal(current_price),
            p50_price=Decimal(p50_price),
            horizon_days=int(horizon) if horizon is not None else 90,
            prob_gain=(
                Decimal(prob_gain) if prob_gain is not None else None
            ),
        )
    return latest


def _quantise(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _days_held(received_at: datetime, today: date) -> int:
    """Best-effort days_held op basis van de meest-recente positie-
    snapshot. Een echte ``entry_date`` zit nog niet in de mirror —
    follow-up §BG kan dit aanvullen met execution-lots.
    """

    snap_date = received_at.date() if isinstance(received_at, datetime) else today
    delta = today - snap_date
    return max(delta.days, 0)


def _open_signal_actions_by_kind(
    connection: Any,
    *,
    ibkr_account_ref: str,
    symbol: str,
) -> dict[str, str]:
    """Lookup de actuele ``action`` per ``signal_kind`` voor dit
    symbool. De sweep gebruikt dit om ``reset_dismissal`` te zetten
    wanneer een hold→suggest_sell of suggest_sell→hold transitie
    plaatsvindt (CLAUDE.md §6.3: na transitie moet de operator het
    hernieuwde signaal te zien krijgen, zelfs als hij eerder
    dismissed).
    """

    rows = (
        connection.execute(
            select(
                sell_signal_cards.c.signal_kind,
                sell_signal_cards.c.action,
            )
            .where(sell_signal_cards.c.ibkr_account_ref == ibkr_account_ref)
            .where(sell_signal_cards.c.symbol == symbol)
        )
        .all()
    )
    return {str(kind): str(action) for kind, action in rows}


def _readiness_from(readiness: Any) -> MigrationReadinessReport:
    return readiness  # type: ignore[no-any-return]


def _evaluate_take_profit_card(
    *,
    position: _PositionRow,
    forecast: _ForecastRow,
    target_net_pct: Decimal,
    evaluated_at: datetime,
    ibkr_account_ref: str,
    previous_action: str | None,
) -> SaveSellSignalCardRequest:
    inputs = TakeProfitSignalInputs(
        ticker=position.symbol,
        entry_price=position.average_cost,
        current_price=forecast.current_price,
        quantity=position.quantity,
        target_net_pct=target_net_pct,
    )
    result = evaluate_take_profit_signal(inputs)
    action = (
        SELL_SIGNAL_ACTION_SUGGEST_SELL
        if result.action == SIGNAL_SUGGEST_SELL
        else SELL_SIGNAL_ACTION_HOLD
    )
    reset = previous_action is not None and previous_action != action
    return SaveSellSignalCardRequest(
        card_id=f"sscv_{uuid4().hex}",
        ibkr_account_ref=ibkr_account_ref,
        symbol=position.symbol,
        currency=position.currency,
        signal_kind=SELL_SIGNAL_KIND_TAKE_PROFIT,
        action=action,
        entry_price=position.average_cost,
        current_price=forecast.current_price,
        quantity=position.quantity,
        current_pct_return=_quantise(result.current_pct_return),
        target_pct=_quantise(result.target_pct),
        target_reached=result.target_reached,
        days_held=None,
        forecast_id=forecast.forecast_id,
        forecaster_above_target=None,
        position_in_loss=None,
        short_term_p50=forecast.p50_price,
        short_term_horizon_days=forecast.horizon_days,
        short_term_prob_above_pct=(
            (forecast.prob_gain * Decimal("100"))
            if forecast.prob_gain is not None
            else None
        ),
        expected_net_proceeds_eur=None,
        headline_nl=result.headline_nl,
        detail_nl=result.detail_nl,
        evaluated_at=evaluated_at,
        reset_dismissal=reset,
    )


def _evaluate_hold_review_card(
    *,
    position: _PositionRow,
    forecast: _ForecastRow,
    today: date,
    target_net_pct: Decimal,
    loss_floor_pct: Decimal,
    horizon_review_start_days: int,
    evaluated_at: datetime,
    ibkr_account_ref: str,
    previous_action: str | None,
) -> SaveSellSignalCardRequest:
    days_held = _days_held(position.received_at, today)
    inputs = HoldPositionReviewInputs(
        ticker=position.symbol,
        entry_price=position.average_cost,
        current_price=forecast.current_price,
        days_held=days_held,
        forecast_p50=forecast.p50_price,
        target_net_pct=target_net_pct,
        horizon_review_start_days=horizon_review_start_days,
        loss_floor_pct=loss_floor_pct,
    )
    result = evaluate_hold_position_review(inputs)
    action = (
        SELL_SIGNAL_ACTION_SUGGEST_SELL
        if result.action == HOLD_ACTION_SUGGEST_SELL
        else SELL_SIGNAL_ACTION_HOLD
    )
    reset = previous_action is not None and previous_action != action
    headline = (
        f"REVIEW — {position.symbol}: outlook verslechterd na 6+ maanden"
        if action == SELL_SIGNAL_ACTION_SUGGEST_SELL
        else f"{position.symbol}: 6m+ hold-review nog niet getrigger'd"
    )
    return SaveSellSignalCardRequest(
        card_id=f"sscv_{uuid4().hex}",
        ibkr_account_ref=ibkr_account_ref,
        symbol=position.symbol,
        currency=position.currency,
        signal_kind=SELL_SIGNAL_KIND_HOLD_REVIEW,
        action=action,
        entry_price=position.average_cost,
        current_price=forecast.current_price,
        quantity=position.quantity,
        current_pct_return=_quantise(result.current_pct_return),
        target_pct=_quantise(target_net_pct),
        target_reached=None,
        days_held=days_held,
        forecast_id=forecast.forecast_id,
        forecaster_above_target=result.forecaster_above_target,
        position_in_loss=result.position_in_loss,
        short_term_p50=forecast.p50_price,
        short_term_horizon_days=forecast.horizon_days,
        short_term_prob_above_pct=(
            (forecast.prob_gain * Decimal("100"))
            if forecast.prob_gain is not None
            else None
        ),
        expected_net_proceeds_eur=None,
        headline_nl=headline,
        detail_nl=result.blocking_reason_nl,
        evaluated_at=evaluated_at,
        reset_dismissal=reset,
    )


def _cleanup_stale_cards(
    repo: SqlAlchemySellSignalCardRepository,
    *,
    current_symbols: set[str],
    ibkr_account_ref: str = DEFAULT_IBKR_ACCOUNT_REF,
) -> None:
    """Verwijder kaartjes waarvan het symbool niet meer in de actuele
    positie-snapshot voorkomt — de positie is gesloten en het kaartje
    moet niet meer op het dashboard staan.
    """

    existing = repo.list_all(ibkr_account_ref=ibkr_account_ref)
    for card in existing.records:
        if card.symbol not in current_symbols:
            repo.delete_for_position(
                ibkr_account_ref=ibkr_account_ref,
                symbol=card.symbol,
            )


def run_sell_signal_sweep(
    *,
    database_url: str,
    target_net_pct: Decimal = DEFAULT_TARGET_NET_PCT,
    loss_floor_pct: Decimal = DEFAULT_LOSS_FLOOR_PCT,
    horizon_review_start_days: int = DEFAULT_HORIZON_REVIEW_START_DAYS,
    ibkr_account_ref: str = DEFAULT_IBKR_ACCOUNT_REF,
    now: Callable[[], datetime] | None = None,
    today: Callable[[], date] | None = None,
) -> SellSignalSweepResult:
    """Run één sweep-tick: lees posities + forecasts, evalueer per
    positie beide signalen, upsert resulterende kaartjes.

    De call is idempotent — herhaalde calls met dezelfde state geven
    dezelfde uitkomst. Operator-dismissals blijven sticky tot het
    signaal materieel verandert (hold↔suggest_sell transitie).

    CLAUDE.md §11 — bewust géén pauze-check; SELL-monitoring draait
    door tijdens software-pauze.
    """

    if not database_url:
        return SellSignalSweepResult(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            positions_evaluated=0,
            take_profit_cards_upserted=0,
            hold_review_cards_upserted=0,
            skipped_no_forecast=0,
            skipped_no_position=0,
            error_text="database_url ontbreekt; sweep overgeslagen.",
        )

    _now = now or (lambda: datetime.now(UTC))
    _today = today or (lambda: datetime.now(UTC).date())
    started_at = _now()

    positions_evaluated = 0
    take_profit_upserted = 0
    hold_review_upserted = 0
    skipped_no_forecast = 0
    skipped_no_position = 0
    error_text: str | None = None

    provider = StorageConnectionProvider(
        build_database_connection_settings(database_url)
    )
    try:
        with provider.checked_connection(require_writable=True) as checked:
            connection = checked.connection
            readiness = _readiness_from(checked.readiness)

            positions = _load_positions(connection)
            repo = SqlAlchemySellSignalCardRepository(connection, readiness)
            if not positions:
                # CLAUDE.md §6 — geen openstaande posities betekent
                # ook geen actieve SELL-suggesties. Verwijder eventueel
                # achtergebleven kaartjes (positie net gesloten).
                _cleanup_stale_cards(repo, current_symbols=set())
                connection.commit()
                skipped_no_position = 1
                return SellSignalSweepResult(
                    started_at=started_at,
                    completed_at=_now(),
                    positions_evaluated=0,
                    take_profit_cards_upserted=0,
                    hold_review_cards_upserted=0,
                    skipped_no_forecast=0,
                    skipped_no_position=1,
                    error_text=None,
                )

            forecasts_by_symbol = _load_latest_forecasts_by_symbol(connection)
            current_today = _today()
            evaluated_at = _now()

            for position in positions:
                positions_evaluated += 1
                forecast = forecasts_by_symbol.get(position.symbol)
                if forecast is None:
                    skipped_no_forecast += 1
                    logger.info(
                        "SELL sweep skip %s — geen forecast in storage",
                        position.symbol,
                    )
                    continue

                previous_actions = _open_signal_actions_by_kind(
                    connection,
                    ibkr_account_ref=ibkr_account_ref,
                    symbol=position.symbol,
                )

                take_profit_request = _evaluate_take_profit_card(
                    position=position,
                    forecast=forecast,
                    target_net_pct=target_net_pct,
                    evaluated_at=evaluated_at,
                    ibkr_account_ref=ibkr_account_ref,
                    previous_action=previous_actions.get(
                        SELL_SIGNAL_KIND_TAKE_PROFIT
                    ),
                )
                repo.upsert(take_profit_request)
                take_profit_upserted += 1

                hold_review_request = _evaluate_hold_review_card(
                    position=position,
                    forecast=forecast,
                    today=current_today,
                    target_net_pct=target_net_pct,
                    loss_floor_pct=loss_floor_pct,
                    horizon_review_start_days=horizon_review_start_days,
                    evaluated_at=evaluated_at,
                    ibkr_account_ref=ibkr_account_ref,
                    previous_action=previous_actions.get(
                        SELL_SIGNAL_KIND_HOLD_REVIEW
                    ),
                )
                repo.upsert(hold_review_request)
                hold_review_upserted += 1

            # Cleanup: verwijder kaartjes voor symbolen die niet meer
            # in de huidige snapshot voorkomen (positie gesloten).
            _cleanup_stale_cards(
                repo,
                current_symbols={position.symbol for position in positions},
                ibkr_account_ref=ibkr_account_ref,
            )

            connection.commit()
    except Exception as exc:  # noqa: BLE001 — boundary catch
        logger.exception("SELL sweep raised an exception")
        error_text = f"{type(exc).__name__}: {exc}"

    completed_at = _now()
    return SellSignalSweepResult(
        started_at=started_at,
        completed_at=completed_at,
        positions_evaluated=positions_evaluated,
        take_profit_cards_upserted=take_profit_upserted,
        hold_review_cards_upserted=hold_review_upserted,
        skipped_no_forecast=skipped_no_forecast,
        skipped_no_position=skipped_no_position,
        error_text=error_text,
    )


__all__ = [
    "DEFAULT_HORIZON_REVIEW_START_DAYS",
    "DEFAULT_IBKR_ACCOUNT_REF",
    "DEFAULT_LOSS_FLOOR_PCT",
    "DEFAULT_TARGET_NET_PCT",
    "SellSignalSweepResult",
    "run_sell_signal_sweep",
]
