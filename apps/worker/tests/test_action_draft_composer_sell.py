"""Task 133 — Action Draft composer SELL-side tests.

Locked rules (Task 133 product lock §4):

* Verminderen → quantity = floor(0.25 × held_quantity).
* Verkopen   → quantity = held_quantity (full exit).
* No position → NoPositionToSellError.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    GateOutcome,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
)
from portfolio_outlook_worker.action_draft.composer import (
    NoPositionToSellError,
    compose_action_draft_from_decision_package,
)

_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


def _package(
    *,
    label: str,
    held_quantity: Decimal | None,
    current_price_local: Decimal = Decimal("640.00000000"),
) -> DecisionPackageEntry:
    user_holds = held_quantity is not None and held_quantity > 0
    return DecisionPackageEntry(
        decision_package_id="dp-1",
        forecast_run_id="fcst-1",
        composed_at=_BASE_TS,
        valid_until=_BASE_TS + timedelta(days=28),
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=user_holds,
        held_quantity=held_quantity if user_holds else None,
        held_avg_cost_local=Decimal("500.00") if user_holds else None,
        current_price_local=current_price_local,
        current_price_eur=current_price_local,
        as_of_market_data_ts=_BASE_TS - timedelta(hours=12),
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("608.769000"),
        p50_price_eur=Decimal("652.929000"),
        p90_price_eur=Decimal("693.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        forecast_confidence_level="Hoog",
        suggested_action_label=label,
        block_reason=None,
        gate_outcomes=(GateOutcome(gate_name="forecast_valid", passed=True, reason_nl=""),),
        evidence_references=(
            EvidenceReference(
                source_id="snap-1",
                source_type="market_data_snapshot",
                claim_summary="snap",
            ),
        ),
        deterministic_dutch_explanation="explanation",
        audit_trail_hash="dp-hash",
        previous_package_hash=None,
        safe_for_action_drafts=False,
        safe_for_orders=False,
    )


def _cash() -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=Decimal("0"),
        available_funds=Decimal("0"),
        buying_power=Decimal("0"),
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


def _position(quantity: Decimal) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id="pos-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        security_type="STK",
        currency="EUR",
        exchange="AEB",
        primary_exchange="AEB",
        quantity=quantity,
        average_cost=Decimal("500.00"),
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


def test_verminderen_sells_25_percent_of_position() -> None:
    pkg = _package(label="Verminderen", held_quantity=Decimal("100"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=_cash(),
        ibkr_position_snapshot=_position(Decimal("100")),
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
    )
    assert draft.side == "SELL"
    assert draft.quantity == Decimal("25")
    # SELL limit price = close × (1 + 0.002) = 640 × 1.002 = 641.28.
    assert draft.limit_price_local == Decimal("641.28000000")
    assert draft.held_quantity_at_creation == Decimal("100")


def test_verminderen_rounds_down_floor() -> None:
    pkg = _package(label="Verminderen", held_quantity=Decimal("11"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=_cash(),
        ibkr_position_snapshot=_position(Decimal("11")),
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
    )
    # 0.25 × 11 = 2.75 → floor = 2.
    assert draft.quantity == Decimal("2")


def test_verkopen_full_exit() -> None:
    pkg = _package(label="Verkopen", held_quantity=Decimal("100"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=_cash(),
        ibkr_position_snapshot=_position(Decimal("100")),
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
    )
    assert draft.side == "SELL"
    assert draft.quantity == Decimal("100")


def test_no_position_raises() -> None:
    pkg = _package(label="Verkopen", held_quantity=None)
    with pytest.raises(NoPositionToSellError):
        compose_action_draft_from_decision_package(
            decision_package=pkg,
            ibkr_cash_snapshot=_cash(),
            ibkr_position_snapshot=None,
            fx_rate=None,
            user_buffer_eur=Decimal("0"),
        )
