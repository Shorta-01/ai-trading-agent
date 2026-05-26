"""Task 133 — Decimal preservation through the Action Draft composer.

No ``float`` anywhere in the composition path. Notional + limit price +
fx rate + audit hash all stay in :class:`decimal.Decimal` through to
the persisted ``ActionDraftEntry``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    FxRateRecord,
    GateOutcome,
    IbkrAccountCashSnapshotRecord,
)
from portfolio_outlook_worker.action_draft.composer import (
    compose_action_draft_from_decision_package,
    compose_action_draft_user_supplied,
)

_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


def _package() -> DecisionPackageEntry:
    return DecisionPackageEntry(
        decision_package_id="dp-1",
        forecast_run_id="fcst-1",
        composed_at=_BASE_TS,
        valid_until=_BASE_TS + timedelta(days=28),
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="USD",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("123.45678900"),
        current_price_eur=Decimal("113.58024388"),
        as_of_market_data_ts=_BASE_TS,
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("108.769000"),
        p50_price_eur=Decimal("113.929000"),
        p90_price_eur=Decimal("123.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        forecast_confidence_level="Hoog",
        suggested_action_label="Kopen",
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


def _cash(amount: Decimal) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=amount,
        available_funds=amount,
        buying_power=amount,
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


def test_all_money_fields_are_decimal_through_composer() -> None:
    pkg = _package()
    fx = FxRateRecord(
        base_currency="USD",
        quote_currency="EUR",
        as_of_date=date(2026, 5, 26),
        rate=Decimal("0.92000000"),
        ingested_ts=_BASE_TS,
        provider="eodhd",
    )
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=_cash(Decimal("10000")),
        ibkr_position_snapshot=None,
        fx_rate=fx,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("10000"),
    )
    for field_name in (
        "quantity",
        "limit_price_local",
        "notional_local",
        "notional_eur",
        "fx_rate_at_creation",
        "usable_cash_eur_at_creation",
    ):
        assert isinstance(
            getattr(draft, field_name), Decimal
        ), f"{field_name} must be Decimal, got {type(getattr(draft, field_name)).__name__}"


def test_user_supplied_composer_preserves_user_quantity() -> None:
    cash = _cash(Decimal("10000"))
    draft = compose_action_draft_user_supplied(
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=Decimal("7"),
        limit_price_local=Decimal("638.72000000"),
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
    )
    # The user-supplied composer does NOT apply sizing rules — it
    # echoes the inputs (after Decimal-quantizing notional).
    assert draft.quantity == Decimal("7")
    assert draft.limit_price_local == Decimal("638.72000000")
    assert draft.notional_local == Decimal("4471.04000000")
    assert draft.notional_eur == Decimal("4471.04000000")


def test_audit_trail_hash_is_deterministic_modulo_id() -> None:
    pkg = _package()
    fx = FxRateRecord(
        base_currency="USD",
        quote_currency="EUR",
        as_of_date=date(2026, 5, 26),
        rate=Decimal("0.92"),
        ingested_ts=_BASE_TS,
        provider="eodhd",
    )
    cash = _cash(Decimal("10000"))
    draft_a = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=fx,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("10000"),
        created_at=_BASE_TS,
    )
    draft_b = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=fx,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("10000"),
        created_at=_BASE_TS,
    )
    # Different draft ids → different hashes (which is the spec: each
    # draft is uniquely identified even if otherwise identical).
    assert draft_a.action_draft_id != draft_b.action_draft_id
    assert draft_a.audit_trail_hash != draft_b.audit_trail_hash
    # But everything else is identical.
    assert draft_a.quantity == draft_b.quantity
    assert draft_a.limit_price_local == draft_b.limit_price_local
    assert draft_a.fx_rate_at_creation == draft_b.fx_rate_at_creation
