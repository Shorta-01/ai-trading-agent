"""Prediction Diary orchestrator.

Builds one ``PredictionDiaryEntryRecord`` per persisted suggestion. The
*issued* forecast comes from the suggestion's linked ``AssetForecastRecord``;
the *realised* prices come from the persisted EOD bars (Slice 3's
``market_data_bars`` table). Outcome labels are produced by the pure-Python
rule engine in ``packages/portfolio/prediction_diary_eval`` — AI never
assigns the label.

This module is the only path that writes diary rows. Each row is upserted
by ``suggestion_id`` so the diary keeps the latest realised values per
suggestion.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetForecastRecord,
    AssetSuggestionRecord,
    MarketDataBarRecord,
    PredictionDiaryEntryRecord,
)
from portfolio_outlook_portfolio import (
    DEFAULT_INCONCLUSIVE_TOLERANCE_PCT,
    evaluate_diary_outcomes,
)

logger = logging.getLogger(__name__)


# Locked horizons (calendar-day approximations; the matcher picks the
# closest preceding-or-equal EOD bar to handle weekends/holidays).
HORIZON_1D_DAYS = 1
HORIZON_1W_DAYS = 7
HORIZON_1M_DAYS = 30


@dataclass(frozen=True)
class PredictionDiaryReport:
    requested_at: datetime
    completed_at: datetime
    suggestion_total: int
    entry_total: int
    entries_persisted: int
    entries_skipped_no_forecast: int
    entries_failed: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _DiaryRepoProtocol(Protocol):
    def upsert_prediction_diary_entry(
        self, record: PredictionDiaryEntryRecord
    ) -> object: ...


def _index_bars_by_date(
    bars: Iterable[MarketDataBarRecord],
) -> dict[str, dict[date, Decimal]]:
    """Build a {conid: {bar_date: close_price}} map.

    Only ``close_price`` is used for the realised-price lookup. EOD bars
    skip non-trading days, so the matcher walks back at most 7 calendar
    days to find the most recent preceding bar.
    """

    index: dict[str, dict[date, Decimal]] = {}
    for bar in bars:
        if not bar.ibkr_conid:
            continue
        index.setdefault(bar.ibkr_conid, {})[bar.bar_date] = bar.close_price
    return index


def _realised_price_at(
    bars_for_conid: dict[date, Decimal] | None,
    *,
    target_date: date,
    look_back_days: int = 7,
) -> Decimal | None:
    if not bars_for_conid:
        return None
    for offset in range(look_back_days + 1):
        candidate = target_date - timedelta(days=offset)
        price = bars_for_conid.get(candidate)
        if price is not None:
            return price
    return None


def _build_entry(
    *,
    suggestion: AssetSuggestionRecord,
    forecast: AssetForecastRecord,
    bars_for_conid: dict[date, Decimal] | None,
    inconclusive_tolerance_pct: Decimal,
    now: datetime,
) -> PredictionDiaryEntryRecord:
    issued_date = suggestion.generated_at.date()
    realised_1d = _realised_price_at(
        bars_for_conid, target_date=issued_date + timedelta(days=HORIZON_1D_DAYS)
    )
    realised_1w = _realised_price_at(
        bars_for_conid, target_date=issued_date + timedelta(days=HORIZON_1W_DAYS)
    )
    realised_1m = _realised_price_at(
        bars_for_conid, target_date=issued_date + timedelta(days=HORIZON_1M_DAYS)
    )
    evaluation = evaluate_diary_outcomes(
        issued_price=forecast.current_price,
        issued_p10_price=forecast.p10_price,
        issued_p50_price=forecast.p50_price,
        issued_p90_price=forecast.p90_price,
        issued_prob_gain=forecast.prob_gain,
        realized_price_1d=realised_1d,
        realized_price_1w=realised_1w,
        realized_price_1m=realised_1m,
        inconclusive_tolerance_pct=inconclusive_tolerance_pct,
    )
    return PredictionDiaryEntryRecord(
        entry_id=f"diary_{uuid4().hex}",
        suggestion_id=suggestion.suggestion_id,
        forecast_id=suggestion.forecast_id,
        ibkr_conid=suggestion.ibkr_conid,
        symbol=suggestion.symbol,
        currency=suggestion.currency,
        issued_at=suggestion.generated_at,
        issued_action_label=suggestion.action_label,
        issued_action_label_nl=suggestion.action_label_nl,
        issued_confidence_label=suggestion.confidence_label,
        issued_horizon_days=forecast.horizon_days,
        issued_price=forecast.current_price,
        issued_p10_price=forecast.p10_price,
        issued_p50_price=forecast.p50_price,
        issued_p90_price=forecast.p90_price,
        issued_prob_gain=forecast.prob_gain,
        issued_prob_loss=forecast.prob_loss,
        user_decision=None,
        realized_price_1d=evaluation.horizon_1d.realized_price,
        realized_price_1w=evaluation.horizon_1w.realized_price,
        realized_price_1m=evaluation.horizon_1m.realized_price,
        realized_return_pct_1d=evaluation.horizon_1d.realized_return_pct,
        realized_return_pct_1w=evaluation.horizon_1w.realized_return_pct,
        realized_return_pct_1m=evaluation.horizon_1m.realized_return_pct,
        outcome_label_1d=evaluation.horizon_1d.outcome_label,
        outcome_label_1w=evaluation.horizon_1w.outcome_label,
        outcome_label_1m=evaluation.horizon_1m.outcome_label,
        outcome_explanation_nl=evaluation.explanation_nl,
        last_evaluated_at=now,
        created_at=now,
        updated_at=now,
    )


def evaluate_prediction_diary(
    *,
    suggestions: Iterable[AssetSuggestionRecord],
    forecasts_by_id: dict[str, AssetForecastRecord],
    bars: Iterable[MarketDataBarRecord],
    repo: _DiaryRepoProtocol,
    inconclusive_tolerance_pct: Decimal = DEFAULT_INCONCLUSIVE_TOLERANCE_PCT,
) -> PredictionDiaryReport:
    """Persist one diary entry per suggestion that has a linked forecast."""

    requested_at = datetime.now(UTC)
    bars_by_conid = _index_bars_by_date(bars)
    now = datetime.now(UTC)

    total = 0
    persisted = 0
    skipped_no_forecast = 0
    failed = 0
    failures: list[dict[str, str]] = []

    for suggestion in suggestions:
        total += 1
        if not suggestion.forecast_id:
            skipped_no_forecast += 1
            failures.append(
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "reason": "no_linked_forecast",
                }
            )
            continue
        forecast = forecasts_by_id.get(suggestion.forecast_id)
        if forecast is None:
            skipped_no_forecast += 1
            failures.append(
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "reason": "forecast_not_found",
                }
            )
            continue
        try:
            entry = _build_entry(
                suggestion=suggestion,
                forecast=forecast,
                bars_for_conid=bars_by_conid.get(suggestion.ibkr_conid),
                inconclusive_tolerance_pct=inconclusive_tolerance_pct,
                now=now,
            )
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "reason": "entry_build_error",
                    "detail": str(exc),
                }
            )
            continue
        try:
            repo.upsert_prediction_diary_entry(entry)
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "reason": "persistence_error",
                    "detail": str(exc),
                }
            )
            continue
        persisted += 1

    completed_at = datetime.now(UTC)
    if total == 0:
        status_nl = "Geen suggesties beschikbaar"
        help_nl = "Voer eerst een suggestions-sync uit."
    elif persisted == 0:
        status_nl = "Geen Prediction Diary entries opgeslagen"
        help_nl = "Controleer failures voor ontbrekende forecasts of fouten."
    elif failed or skipped_no_forecast:
        status_nl = "Prediction Diary gedeeltelijk voltooid"
        help_nl = "Sommige suggesties hadden geen gekoppelde forecast."
    else:
        status_nl = "Prediction Diary voltooid"
        help_nl = "Alle suggesties hebben een entry."

    return PredictionDiaryReport(
        requested_at=requested_at,
        completed_at=completed_at,
        suggestion_total=total,
        entry_total=total,
        entries_persisted=persisted,
        entries_skipped_no_forecast=skipped_no_forecast,
        entries_failed=failed,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )


def serialize_prediction_diary_entry_for_response(
    record: PredictionDiaryEntryRecord,
) -> dict[str, object]:
    return {
        "entry_id": record.entry_id,
        "suggestion_id": record.suggestion_id,
        "forecast_id": record.forecast_id,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "currency": record.currency,
        "issued_at": record.issued_at.isoformat(),
        "issued_action_label": record.issued_action_label,
        "issued_action_label_nl": record.issued_action_label_nl,
        "issued_confidence_label": record.issued_confidence_label,
        "issued_horizon_days": record.issued_horizon_days,
        "issued_price": str(record.issued_price),
        "issued_p10_price": str(record.issued_p10_price),
        "issued_p50_price": str(record.issued_p50_price),
        "issued_p90_price": str(record.issued_p90_price),
        "issued_prob_gain": str(record.issued_prob_gain),
        "issued_prob_loss": str(record.issued_prob_loss),
        "user_decision": record.user_decision,
        "realized_price_1d": str(record.realized_price_1d) if record.realized_price_1d else None,
        "realized_price_1w": str(record.realized_price_1w) if record.realized_price_1w else None,
        "realized_price_1m": str(record.realized_price_1m) if record.realized_price_1m else None,
        "realized_return_pct_1d": (
            str(record.realized_return_pct_1d)
            if record.realized_return_pct_1d is not None
            else None
        ),
        "realized_return_pct_1w": (
            str(record.realized_return_pct_1w)
            if record.realized_return_pct_1w is not None
            else None
        ),
        "realized_return_pct_1m": (
            str(record.realized_return_pct_1m)
            if record.realized_return_pct_1m is not None
            else None
        ),
        "outcome_label_1d": record.outcome_label_1d,
        "outcome_label_1w": record.outcome_label_1w,
        "outcome_label_1m": record.outcome_label_1m,
        "outcome_explanation_nl": record.outcome_explanation_nl,
        "last_evaluated_at": record.last_evaluated_at.isoformat(),
        "safe_for_self_learning": False,
        "safe_for_model_retraining": False,
    }
