"""Task 133 — Action Draft composer BUY-side tests.

Locked sizing rules from product lock §4:

* Hoog × Kopen → target = min(8% × portfolio_total_eur, available_funds_eur).
* Gemiddeld × Kopen → target = min(4% × portfolio_total_eur, available_funds_eur).
* Insufficient cash → InsufficientCashError (with the locked Dutch message).
* Partial cash → pre-fills the max affordable quantity (no error).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    FxRateRecord,
    GateOutcome,
    IbkrAccountCashSnapshotRecord,
)

from portfolio_outlook_worker.action_draft.composer import (
    InsufficientCashError,
    compose_action_draft_from_decision_package,
)

_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


def _package(
    *,
    confidence: str = "Hoog",
    label: str = "Kopen",
    current_price_local: Decimal = Decimal("640.00000000"),
    currency: str = "EUR",
) -> DecisionPackageEntry:
    return DecisionPackageEntry(
        decision_package_id="dp-1",
        forecast_run_id="fcst-1",
        composed_at=_BASE_TS,
        valid_until=_BASE_TS + timedelta(days=28),
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local=currency,
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
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
        forecast_confidence_level=confidence,
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


def _cash(available_funds: Decimal | None = None) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=available_funds,
        available_funds=available_funds,
        buying_power=available_funds,
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


# ---- Hoog × Kopen -----------------------------------------------------


def test_hoog_kopen_sizes_to_8pct_of_portfolio() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    cash = _cash(Decimal("50000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("50000"),
    )
    # 8% of 50_000 = 4000 EUR target. Limit = 640 × 0.998 = 638.72.
    # 4000 / 1 / 638.72 = 6.26... → floor = 6.
    assert draft.side == "BUY"
    assert draft.quantity == Decimal("6")
    assert draft.limit_price_local == Decimal("638.72000000")
    assert draft.status == "proposed"
    assert draft.usable_cash_eur_at_creation == Decimal("50000")


def test_gemiddeld_kopen_sizes_to_4pct_of_portfolio() -> None:
    pkg = _package(confidence="Gemiddeld", label="Kopen")
    cash = _cash(Decimal("50000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("50000"),
    )
    # 4% of 50_000 = 2000 EUR. 2000 / 638.72 = 3.13... → floor = 3.
    assert draft.quantity == Decimal("3")


# ---- partial-cash falls back to max affordable -----------------------


def test_partial_cash_prefills_max_affordable() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    # Portfolio is 50k (so 8% target = 4000 EUR), but only 1500 EUR cash.
    cash = _cash(Decimal("1500"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("50000"),
    )
    # min(4000, 1500) = 1500. 1500 / 638.72 = 2.34... → floor = 2.
    assert draft.quantity == Decimal("2")


# ---- insufficient cash raises -----------------------------------------


def test_insufficient_cash_raises_dutch_message() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    cash = _cash(Decimal("100"))  # less than one share at €638
    with pytest.raises(InsufficientCashError) as exc:
        compose_action_draft_from_decision_package(
            decision_package=pkg,
            ibkr_cash_snapshot=cash,
            ibkr_position_snapshot=None,
            fx_rate=None,
            user_buffer_eur=Decimal("0"),
            portfolio_total_eur=Decimal("100"),
        )
    assert "Onvoldoende cash" in str(exc.value)


# ---- user_buffer reduces usable cash ----------------------------------


def test_user_buffer_reduces_usable_cash() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    cash = _cash(Decimal("50000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("1000"),
        portfolio_total_eur=Decimal("50000"),
    )
    assert draft.usable_cash_eur_at_creation == Decimal("49000")
    # 8% × 50_000 = 4000 still beats 49_000, so target = 4000 → still 6 shares.
    assert draft.quantity == Decimal("6")


def test_user_buffer_caps_usable_cash_below_percentage_target() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    # Portfolio is 100_000 (so 8% = 8_000 EUR target), but a hefty
    # 5_000 EUR buffer leaves only 4_000 EUR usable. The buffer wins
    # over the percentage cap.
    cash = _cash(Decimal("9000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("5000"),
        portfolio_total_eur=Decimal("100000"),
    )
    # available = 9000, buffer = 5000 → usable = 4000.
    # 8% × 100_000 = 8000 → target = min(8000, 4000) = 4000 EUR.
    # 4000 / 638.72 = 6.26... → floor = 6.
    assert draft.usable_cash_eur_at_creation == Decimal("4000")
    assert draft.quantity == Decimal("6")


def test_approved_drafts_notional_reduces_usable_cash() -> None:
    pkg = _package(confidence="Hoog", label="Kopen")
    cash = _cash(Decimal("50000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("50000"),
        approved_drafts_notional_eur=Decimal("48000"),
    )
    # usable_cash = 50_000 - 48_000 - 0 = 2_000.
    # 8% × 50_000 = 4000. target = min(4000, 2000) = 2000.
    # 2000 / 638.72 = 3.13 → floor = 3.
    assert draft.usable_cash_eur_at_creation == Decimal("2000")
    assert draft.quantity == Decimal("3")


# ---- limit price -----------------------------------------------------


def test_buy_limit_price_is_2bps_below_close() -> None:
    pkg = _package(current_price_local=Decimal("100.00000000"))
    cash = _cash(Decimal("10000"))
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=None,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("10000"),
    )
    assert draft.limit_price_local == Decimal("99.80000000")


# ---- non-EUR currency uses FX rate -----------------------------------


def test_non_eur_uses_fx_rate_for_sizing() -> None:
    pkg = _package(currency="USD", current_price_local=Decimal("200.00000000"))
    cash = _cash(Decimal("10000"))  # 10_000 EUR available
    fx = FxRateRecord(
        base_currency="USD",
        quote_currency="EUR",
        as_of_date=date(2026, 5, 26),
        rate=Decimal("0.92"),  # 1 USD = 0.92 EUR
        ingested_ts=_BASE_TS,
        provider="eodhd",
    )
    draft = compose_action_draft_from_decision_package(
        decision_package=pkg,
        ibkr_cash_snapshot=cash,
        ibkr_position_snapshot=None,
        fx_rate=fx,
        user_buffer_eur=Decimal("0"),
        portfolio_total_eur=Decimal("10000"),
    )
    # 8% × 10_000 EUR = 800 EUR target.
    # 800 EUR / 0.92 = 869.5652 USD target in local.
    # limit_price = 200 × 0.998 = 199.60.
    # 869.5652 / 199.60 = 4.35... → floor = 4.
    assert draft.side == "BUY"
    assert draft.quantity == Decimal("4")
    assert draft.fx_rate_at_creation == Decimal("0.92")
