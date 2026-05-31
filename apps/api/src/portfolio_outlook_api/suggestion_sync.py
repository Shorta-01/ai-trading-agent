"""Suggestion sync orchestrator.

Reads the latest persisted ``AssetForecastRecord`` per asset, applies the
deterministic Dutch label translator (``baseline_label_translator``) and
persists one ``AssetSuggestionRecord`` per (conid, forecast).

Hard contract:
* AI never decides the label — Python rules over evidence-gated inputs only.
* Suggestions never auto-promote to action drafts or orders.
* Every persisted record has ``safe_for_action_drafts``,
  ``safe_for_orders`` and ``safe_for_broker_submission`` set to ``False``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetForecastRecord,
    AssetSuggestionRecord,
    IbkrPositionSnapshotRecord,
)
from portfolio_outlook_portfolio import (
    BASELINE_LABEL_TRANSLATOR_MODEL_CODE,
    BASELINE_LABEL_TRANSLATOR_MODEL_VERSION,
    BaselineForecast,
    HistoricalBar,
    PortfolioContext,
    SuggestionDecision,
    SuggestionInputs,
    apply_portfolio_context_gates,
    translate_forecast_to_label,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SuggestionSyncReport:
    requested_at: datetime
    completed_at: datetime
    model_code: str
    model_version: str
    risk_profile: str
    suggestion_total: int
    suggestion_persisted: int
    suggestion_failed: int
    held_positions: int
    cold_start_positions: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _AssetSuggestionRepoProtocol(Protocol):
    def save_asset_suggestion(self, record: AssetSuggestionRecord) -> object: ...
    def expire_stale_asset_suggestions(self, *, now: datetime) -> int: ...


def _forecast_record_to_baseline_dataclass(
    record: AssetForecastRecord,
) -> BaselineForecast:
    """Adapt a stored forecast record back into the translator's input type.

    The translator only reads scalar fields, so an empty bar list is fine
    here — the historical-bar info is already collapsed into the forecast.
    """

    _ = HistoricalBar  # narrow import-time check; not actually used.
    return BaselineForecast(
        horizon_days=record.horizon_days,
        data_points_used=record.data_points_used,
        history_first_bar_date=record.history_first_bar_date,
        history_last_bar_date=record.history_last_bar_date,
        current_price=record.current_price,
        expected_return_pct=record.expected_return_pct,
        p10_price=record.p10_price,
        p50_price=record.p50_price,
        p90_price=record.p90_price,
        prob_gain=record.prob_gain,
        prob_loss=record.prob_loss,
        prob_loss_gt_5pct=record.prob_loss_gt_5pct,
        prob_loss_gt_10pct=record.prob_loss_gt_10pct,
        prob_gain_gt_5pct=record.prob_gain_gt_5pct,
        prob_gain_gt_10pct=record.prob_gain_gt_10pct,
        expected_volatility_annual=record.expected_volatility_annual,
        downside_risk_score=record.downside_risk_score,
        confidence_score=record.confidence_score,
        direction_label=record.direction_label,
        direction_label_nl=record.direction_label_nl,
        explanation_nl=record.explanation_nl,
        status=record.status,
        blocking_reason=record.blocking_reason,
        model_code=record.model_code,
        model_version=record.model_version,
    )


def _build_suggestion_record(
    *,
    forecast: AssetForecastRecord,
    decision: SuggestionDecision,
    generated_at: datetime,
    valid_until: datetime,
) -> AssetSuggestionRecord:
    # Mirror the headline forecast numbers onto the suggestion so the V1
    # grid can render without a forecast join.
    expected_return = getattr(forecast, "expected_return_pct", None)
    prob_gain = getattr(forecast, "prob_gain", None)
    return AssetSuggestionRecord(
        suggestion_id=f"suggestion_{uuid4().hex}",
        ibkr_conid=forecast.ibkr_conid,
        symbol=forecast.symbol,
        currency=forecast.currency,
        forecast_id=forecast.forecast_id,
        model_code=BASELINE_LABEL_TRANSLATOR_MODEL_CODE,
        model_version=BASELINE_LABEL_TRANSLATOR_MODEL_VERSION,
        generated_at=generated_at,
        valid_until=valid_until,
        risk_profile=decision.risk_profile,
        has_position=decision.has_position,
        action_label=decision.action_label,
        action_label_nl=decision.action_label_nl,
        confidence_label=decision.confidence_label,
        confidence_label_nl=decision.confidence_label_nl,
        confidence_score=decision.confidence_score,
        rationale_nl=decision.rationale_nl,
        drivers_json=decision.drivers or None,
        blockers_json=decision.blockers or None,
        status=decision.status,
        blocking_reason=decision.blocking_reason,
        branch_reason_nl=decision.branch_reason_nl,
        downgrade_reason_nl=decision.downgrade_reason_nl,
        top_driver_nl=decision.top_driver_nl,
        blocking_reason_nl=decision.blocking_reason_nl,
        expected_return_pct=(
            Decimal(str(expected_return)) if expected_return is not None else None
        ),
        prob_gain_pct=(
            (Decimal(str(prob_gain)) * Decimal("100"))
            if prob_gain is not None
            else None
        ),
    )


def sync_suggestions(
    *,
    forecasts: list[AssetForecastRecord],
    positions: list[IbkrPositionSnapshotRecord],
    risk_profile: str,
    repo: _AssetSuggestionRepoProtocol,
    valid_minutes: int,
    portfolio_context_resolver: Callable[[str], PortfolioContext] | None = None,
) -> SuggestionSyncReport:
    """Run one suggestion cycle and persist one record per forecast."""

    requested_at = datetime.now(UTC)
    # #7 — expire yesterday's still-``ready`` rows before generating today's.
    # Idempotent on the cutoff; keeps stale ``Bekijken`` from silting up the
    # watchlist forever. Failure here is non-fatal — the new cycle proceeds.
    try:
        repo.expire_stale_asset_suggestions(now=requested_at)
    except Exception:  # noqa: BLE001 — never fail a sync over hygiene
        pass
    held_conids = {
        (p.conid or "").strip() for p in positions if (p.conid or "").strip()
    }
    held_count = 0
    cold_count = 0
    persisted = 0
    failed = 0
    failures: list[dict[str, str]] = []

    for forecast in forecasts:
        conid = (forecast.ibkr_conid or "").strip()
        if not conid:
            failed += 1
            failures.append(
                {
                    "kind": "suggestion",
                    "forecast_id": forecast.forecast_id,
                    "reason": "missing_conid",
                }
            )
            continue
        has_position = conid in held_conids
        if has_position:
            held_count += 1
        else:
            cold_count += 1
        baseline = _forecast_record_to_baseline_dataclass(forecast)
        decision = translate_forecast_to_label(
            SuggestionInputs(
                forecast=baseline,
                risk_profile=risk_profile,
                has_position=has_position,
            )
        )
        # #3 — portfolio-context gate: when a resolver is wired in, ask it
        # for the live position/sector/cost state and let the gate
        # downgrade Kopen / Langzaam bijkopen to Bekijken if the trade
        # is irresponsible given the rest of the portfolio. Caller-side
        # resolver is optional; absent it the gate is a no-op.
        if portfolio_context_resolver is not None:
            try:
                context = portfolio_context_resolver(conid)
            except Exception:  # noqa: BLE001 — gate is best-effort
                context = PortfolioContext()
            decision = apply_portfolio_context_gates(decision, context)
        generated_at = datetime.now(UTC)
        valid_until = generated_at + timedelta(minutes=valid_minutes)
        record = _build_suggestion_record(
            forecast=forecast,
            decision=decision,
            generated_at=generated_at,
            valid_until=valid_until,
        )
        try:
            repo.save_asset_suggestion(record)
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "kind": "suggestion",
                    "conid": conid,
                    "reason": "persistence_error",
                    "detail": str(exc),
                }
            )
            continue
        persisted += 1

    completed_at = datetime.now(UTC)
    if persisted == 0 and forecasts:
        status_nl = "Suggesties niet opgeslagen"
        help_nl = "Geen suggesties opgeslagen; controleer failures."
    elif persisted == 0:
        status_nl = "Geen voorspellingen beschikbaar"
        help_nl = "Voer eerst een forecast-sync uit; daarna kunnen suggesties worden gegenereerd."
    elif failed > 0:
        status_nl = "Suggesties gedeeltelijk voltooid"
        help_nl = (
            "Sommige suggesties zijn niet opgeslagen; "
            "details staan in 'failures'."
        )
    else:
        status_nl = "Suggesties voltooid"
        help_nl = "Alle suggesties zijn opgeslagen."

    return SuggestionSyncReport(
        requested_at=requested_at,
        completed_at=completed_at,
        model_code=BASELINE_LABEL_TRANSLATOR_MODEL_CODE,
        model_version=BASELINE_LABEL_TRANSLATOR_MODEL_VERSION,
        risk_profile=risk_profile,
        suggestion_total=len(forecasts),
        suggestion_persisted=persisted,
        suggestion_failed=failed,
        held_positions=held_count,
        cold_start_positions=cold_count,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )


def serialize_suggestion_for_response(
    record: AssetSuggestionRecord,
) -> dict[str, object]:
    return {
        "suggestion_id": record.suggestion_id,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "currency": record.currency,
        "forecast_id": record.forecast_id,
        "model_code": record.model_code,
        "model_version": record.model_version,
        "generated_at": record.generated_at.isoformat(),
        "valid_until": record.valid_until.isoformat(),
        "risk_profile": record.risk_profile,
        "has_position": record.has_position,
        "action_label": record.action_label,
        "action_label_nl": record.action_label_nl,
        "confidence_label": record.confidence_label,
        "confidence_label_nl": record.confidence_label_nl,
        "confidence_score": str(record.confidence_score),
        "rationale_nl": record.rationale_nl,
        "drivers": list(record.drivers_json or ()),
        "blockers": list(record.blockers_json or ()),
        "status": record.status,
        "blocking_reason": record.blocking_reason,
        "branch_reason_nl": record.branch_reason_nl,
        "downgrade_reason_nl": record.downgrade_reason_nl,
        "top_driver_nl": record.top_driver_nl,
        "blocking_reason_nl": record.blocking_reason_nl,
        "expected_return_pct": (
            str(record.expected_return_pct)
            if record.expected_return_pct is not None
            else None
        ),
        "prob_gain_pct": (
            str(record.prob_gain_pct)
            if record.prob_gain_pct is not None
            else None
        ),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
    }
