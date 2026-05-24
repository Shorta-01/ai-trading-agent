"""Decision Package sync orchestrator.

Bundles the upstream evidence chain (position + cash snapshot, market-data
snapshot, FX snapshot if applicable, baseline forecast, locked-label
suggestion) into one immutable, content-hashed
``AssetDecisionPackageRecord`` per (conid, generated_at) and persists it.

Hard contract — from
``docs/product/release-1-functional-workflow-blueprint.md §6``:

* A Decision Package is the **gate** before any future action draft.
* Packages are append-only / immutable once written. New versions become
  new rows.
* AI never authors the package. This orchestrator only assembles
  Python-computed evidence.
* Safety booleans (``safe_for_action_drafts``, ``safe_for_orders``,
  ``safe_for_broker_submission``) remain hard-False.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    AssetForecastRecord,
    AssetSuggestionRecord,
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    MarketDataLatestSnapshotRecord,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionPackageSyncReport:
    requested_at: datetime
    completed_at: datetime
    risk_profile: str
    package_total: int
    package_persisted: int
    package_failed: int
    package_skipped_missing_inputs: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _DecisionPackageRepoProtocol(Protocol):
    def save_asset_decision_package(
        self, record: AssetDecisionPackageRecord
    ) -> object: ...


def _decimal_or_none_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _compute_content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_audit_links(
    *,
    position: IbkrPositionSnapshotRecord | None,
    cash: IbkrAccountCashSnapshotRecord | None,
    market: MarketDataLatestSnapshotRecord | None,
    fx: FxRateSnapshotRecord | None,
    forecast: AssetForecastRecord | None,
    suggestion: AssetSuggestionRecord | None,
) -> tuple[str, ...]:
    items: list[str] = []
    if position is not None:
        items.append(f"position_snapshot:{position.snapshot_id}")
    if cash is not None:
        items.append(f"cash_snapshot:{cash.snapshot_id}")
    if market is not None:
        items.append(f"market_data_snapshot:{market.snapshot_id}")
    if fx is not None:
        items.append(f"fx_rate_snapshot:{fx.snapshot_id}")
    if forecast is not None:
        items.append(f"forecast:{forecast.forecast_id}")
    if suggestion is not None:
        items.append(f"suggestion:{suggestion.suggestion_id}")
    return tuple(items)


def _build_gate_outcomes(
    *,
    market: MarketDataLatestSnapshotRecord | None,
    forecast: AssetForecastRecord | None,
    suggestion: AssetSuggestionRecord,
    fx_required: bool,
    fx: FxRateSnapshotRecord | None,
) -> tuple[str, ...]:
    outcomes: list[str] = []
    if market is not None:
        outcomes.append(f"market_data:{market.freshness_status}")
    else:
        outcomes.append("market_data:missing")
    if forecast is not None and forecast.status == "ready":
        outcomes.append("forecast:ready")
    elif forecast is not None:
        outcomes.append(f"forecast:{forecast.status}")
    else:
        outcomes.append("forecast:missing")
    outcomes.append(f"suggestion:{suggestion.status}")
    if fx_required:
        if fx is None:
            outcomes.append("fx_rate:missing")
        else:
            outcomes.append(f"fx_rate:{fx.freshness_status}")
    return tuple(outcomes)


@dataclass(frozen=True)
class _AssemblyContext:
    suggestion: AssetSuggestionRecord
    forecast: AssetForecastRecord | None
    position: IbkrPositionSnapshotRecord | None
    cash: IbkrAccountCashSnapshotRecord | None
    market: MarketDataLatestSnapshotRecord | None
    fx: FxRateSnapshotRecord | None
    fx_required: bool


def build_decision_package_record(
    context: _AssemblyContext,
    *,
    risk_profile: str,
    generated_at: datetime,
    valid_until: datetime,
) -> AssetDecisionPackageRecord:
    """Assemble one immutable Decision Package from the upstream evidence.

    The function is pure: it does no I/O and is deterministic given the same
    inputs and ``generated_at``. ``content_hash`` is computed from the
    audit-relevant fields only (timestamps that vary across runs are still
    included so a re-run after data changes produces a new hash).
    """

    suggestion = context.suggestion
    forecast = context.forecast
    position = context.position
    cash = context.cash
    market = context.market
    fx = context.fx

    hash_payload: dict[str, object] = {
        "ibkr_conid": suggestion.ibkr_conid,
        "symbol": suggestion.symbol,
        "currency": suggestion.currency,
        "risk_profile": risk_profile,
        "generated_at": generated_at.isoformat(),
        "position_snapshot_id": position.snapshot_id if position else None,
        "cash_snapshot_id": cash.snapshot_id if cash else None,
        "market_snapshot_id": market.snapshot_id if market else None,
        "fx_snapshot_id": fx.snapshot_id if fx else None,
        "forecast_id": forecast.forecast_id if forecast else None,
        "suggestion_id": suggestion.suggestion_id,
        "action_label": suggestion.action_label,
        "suggestion_status": suggestion.status,
    }
    content_hash = _compute_content_hash(hash_payload)

    explanation = (
        f"Decision Package voor {suggestion.symbol}: action label "
        f"{suggestion.action_label_nl} bij vertrouwen "
        f"{suggestion.confidence_label_nl}, op basis van baseline-voorspelling "
        "en opgeslagen positie/cash/markt/FX-evidence. Geen action draft, "
        "geen order, geen broker submission."
    )

    fx_pair_value = fx.pair if fx is not None else None
    fx_rate_value = fx.rate if fx is not None else None
    fx_freshness_value = fx.freshness_status if fx is not None else None

    return AssetDecisionPackageRecord(
        decision_package_id=f"dp_{uuid4().hex}",
        content_hash=content_hash,
        ibkr_conid=suggestion.ibkr_conid,
        symbol=suggestion.symbol,
        currency=suggestion.currency,
        risk_profile=risk_profile,
        generated_at=generated_at,
        valid_until=valid_until,
        position_snapshot_id=position.snapshot_id if position else None,
        position_quantity=position.quantity if position else None,
        position_average_cost=position.average_cost if position else None,
        cash_snapshot_id=cash.snapshot_id if cash else None,
        cash_base_currency=cash.base_currency if cash else None,
        cash_amount=cash.cash if cash else None,
        market_snapshot_id=market.snapshot_id if market else None,
        market_last_price=market.last_price if market else None,
        market_freshness_status=market.freshness_status if market else None,
        market_provider_code=market.provider_code if market else None,
        market_provider_as_of=market.provider_as_of if market else None,
        fx_pair=fx_pair_value,
        fx_rate=fx_rate_value,
        fx_freshness_status=fx_freshness_value,
        forecast_id=forecast.forecast_id if forecast else None,
        forecast_model_code=forecast.model_code if forecast else None,
        forecast_model_version=forecast.model_version if forecast else None,
        forecast_horizon_days=forecast.horizon_days if forecast else None,
        forecast_p10_price=forecast.p10_price if forecast else None,
        forecast_p50_price=forecast.p50_price if forecast else None,
        forecast_p90_price=forecast.p90_price if forecast else None,
        forecast_prob_gain=forecast.prob_gain if forecast else None,
        forecast_prob_loss=forecast.prob_loss if forecast else None,
        forecast_expected_return_pct=forecast.expected_return_pct if forecast else None,
        forecast_expected_volatility_annual=(
            forecast.expected_volatility_annual if forecast else None
        ),
        forecast_downside_risk_score=forecast.downside_risk_score if forecast else None,
        forecast_confidence_score=forecast.confidence_score if forecast else None,
        suggestion_id=suggestion.suggestion_id,
        suggestion_model_code=suggestion.model_code,
        suggestion_action_label=suggestion.action_label,
        suggestion_action_label_nl=suggestion.action_label_nl,
        suggestion_confidence_label=suggestion.confidence_label,
        suggestion_confidence_label_nl=suggestion.confidence_label_nl,
        suggestion_status=suggestion.status,
        has_position=suggestion.has_position,
        gate_outcomes_json=_build_gate_outcomes(
            market=market,
            forecast=forecast,
            suggestion=suggestion,
            fx_required=context.fx_required,
            fx=fx,
        ),
        evidence_links_json=None,
        audit_links_json=_build_audit_links(
            position=position,
            cash=cash,
            market=market,
            fx=fx,
            forecast=forecast,
            suggestion=suggestion,
        ),
        rationale_nl=suggestion.rationale_nl,
        explanation_nl=explanation,
        status=(
            "blocked"
            if suggestion.status == "blocked"
            else ("control_needed" if suggestion.status == "control_needed" else "ready")
        ),
        blocking_reason=suggestion.blocking_reason,
    )


def sync_decision_packages(
    *,
    suggestions: list[AssetSuggestionRecord],
    forecasts_by_id: dict[str, AssetForecastRecord],
    positions_by_conid: dict[str, IbkrPositionSnapshotRecord],
    cash_by_currency: dict[str, IbkrAccountCashSnapshotRecord],
    market_by_conid: dict[str, MarketDataLatestSnapshotRecord],
    fx_by_pair: dict[str, FxRateSnapshotRecord],
    base_currency: str | None,
    risk_profile: str,
    repo: _DecisionPackageRepoProtocol,
    valid_minutes: int,
) -> DecisionPackageSyncReport:
    """Build and persist one Decision Package per suggestion."""

    requested_at = datetime.now(UTC)
    persisted = 0
    failed = 0
    skipped = 0
    failures: list[dict[str, str]] = []

    for suggestion in suggestions:
        conid = (suggestion.ibkr_conid or "").strip()
        if not conid:
            failed += 1
            failures.append({"reason": "missing_conid", "suggestion_id": suggestion.suggestion_id})
            continue

        forecast = (
            forecasts_by_id.get(suggestion.forecast_id)
            if suggestion.forecast_id
            else None
        )
        position = positions_by_conid.get(conid)
        market = market_by_conid.get(conid)
        currency = (suggestion.currency or "").upper()
        cash = cash_by_currency.get(currency) if currency else None
        fx_required = bool(base_currency and currency and currency != base_currency)
        fx_key = f"{currency}/{base_currency}" if fx_required and base_currency else None
        fx = fx_by_pair.get(fx_key) if fx_key else None

        if suggestion.status == "ready" and (forecast is None or market is None):
            # Ready suggestions must have their forecast + market evidence;
            # if the evidence chain is incomplete we skip with a recorded
            # reason rather than persisting a half-evidenced package.
            skipped += 1
            failures.append(
                {
                    "reason": "incomplete_evidence_chain",
                    "suggestion_id": suggestion.suggestion_id,
                    "missing_forecast": "true" if forecast is None else "false",
                    "missing_market_snapshot": "true" if market is None else "false",
                }
            )
            continue

        generated_at = datetime.now(UTC)
        valid_until = generated_at + timedelta(minutes=valid_minutes)
        context = _AssemblyContext(
            suggestion=suggestion,
            forecast=forecast,
            position=position,
            cash=cash,
            market=market,
            fx=fx,
            fx_required=fx_required,
        )
        record = build_decision_package_record(
            context,
            risk_profile=risk_profile,
            generated_at=generated_at,
            valid_until=valid_until,
        )
        try:
            repo.save_asset_decision_package(record)
        except Exception as exc:
            failed += 1
            failures.append(
                {
                    "reason": "persistence_error",
                    "suggestion_id": suggestion.suggestion_id,
                    "detail": str(exc),
                }
            )
            continue
        persisted += 1

    completed_at = datetime.now(UTC)
    if persisted == 0 and not suggestions:
        status_nl = "Geen suggesties beschikbaar"
        help_nl = (
            "Decision Packages bouwen op de laatste suggesties; voer eerst een "
            "suggesties-sync uit."
        )
    elif persisted == 0:
        status_nl = "Geen Decision Packages opgeslagen"
        help_nl = "Controleer failures voor ontbrekende evidence-onderdelen."
    elif failed or skipped:
        status_nl = "Decision Packages gedeeltelijk voltooid"
        help_nl = (
            "Sommige packages konden niet worden opgeslagen wegens ontbrekende "
            "evidence; details staan in 'failures'."
        )
    else:
        status_nl = "Decision Packages voltooid"
        help_nl = "Alle Decision Packages zijn opgeslagen."

    return DecisionPackageSyncReport(
        requested_at=requested_at,
        completed_at=completed_at,
        risk_profile=risk_profile,
        package_total=len(suggestions),
        package_persisted=persisted,
        package_failed=failed,
        package_skipped_missing_inputs=skipped,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )


def serialize_decision_package_for_response(
    record: AssetDecisionPackageRecord,
) -> dict[str, object]:
    return {
        "decision_package_id": record.decision_package_id,
        "content_hash": record.content_hash,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "currency": record.currency,
        "risk_profile": record.risk_profile,
        "generated_at": record.generated_at.isoformat(),
        "valid_until": record.valid_until.isoformat(),
        "position_snapshot_id": record.position_snapshot_id,
        "position_quantity": _decimal_or_none_str(record.position_quantity),
        "position_average_cost": _decimal_or_none_str(record.position_average_cost),
        "cash_snapshot_id": record.cash_snapshot_id,
        "cash_base_currency": record.cash_base_currency,
        "cash_amount": _decimal_or_none_str(record.cash_amount),
        "market_snapshot_id": record.market_snapshot_id,
        "market_last_price": _decimal_or_none_str(record.market_last_price),
        "market_freshness_status": record.market_freshness_status,
        "market_provider_code": record.market_provider_code,
        "market_provider_as_of": (
            record.market_provider_as_of.isoformat()
            if record.market_provider_as_of
            else None
        ),
        "fx_pair": record.fx_pair,
        "fx_rate": _decimal_or_none_str(record.fx_rate),
        "fx_freshness_status": record.fx_freshness_status,
        "forecast_id": record.forecast_id,
        "forecast_model_code": record.forecast_model_code,
        "forecast_model_version": record.forecast_model_version,
        "forecast_horizon_days": record.forecast_horizon_days,
        "forecast_p10_price": _decimal_or_none_str(record.forecast_p10_price),
        "forecast_p50_price": _decimal_or_none_str(record.forecast_p50_price),
        "forecast_p90_price": _decimal_or_none_str(record.forecast_p90_price),
        "forecast_prob_gain": _decimal_or_none_str(record.forecast_prob_gain),
        "forecast_prob_loss": _decimal_or_none_str(record.forecast_prob_loss),
        "forecast_expected_return_pct": _decimal_or_none_str(record.forecast_expected_return_pct),
        "forecast_expected_volatility_annual": _decimal_or_none_str(
            record.forecast_expected_volatility_annual
        ),
        "forecast_downside_risk_score": _decimal_or_none_str(record.forecast_downside_risk_score),
        "forecast_confidence_score": _decimal_or_none_str(record.forecast_confidence_score),
        "suggestion_id": record.suggestion_id,
        "suggestion_model_code": record.suggestion_model_code,
        "suggestion_action_label": record.suggestion_action_label,
        "suggestion_action_label_nl": record.suggestion_action_label_nl,
        "suggestion_confidence_label": record.suggestion_confidence_label,
        "suggestion_confidence_label_nl": record.suggestion_confidence_label_nl,
        "suggestion_status": record.suggestion_status,
        "has_position": record.has_position,
        "gate_outcomes": list(record.gate_outcomes_json or ()),
        "evidence_links": list(record.evidence_links_json or ()),
        "audit_links": list(record.audit_links_json or ()),
        "rationale_nl": record.rationale_nl,
        "explanation_nl": record.explanation_nl,
        "status": record.status,
        "blocking_reason": record.blocking_reason,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
    }
