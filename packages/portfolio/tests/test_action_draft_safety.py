"""Tests for action-draft sizing, Orderimpact and dry-run safety checks."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.action_draft_safety import (
    DEFAULT_BUY_VALUE_EUR,
    DraftSourceContext,
    compute_orderimpact,
    derive_action_draft_sizing,
    run_dry_run_safety_checks,
)


def _context(
    *,
    action_label: str = "Kopen",
    held_quantity: str = "0",
    market_price: str | None = "180.00",
    market_freshness: str | None = "fresh",
    cash: str | None = "10000",
    cash_currency: str = "USD",
    currency: str = "USD",
    primary_exchange: str | None = "NASDAQ",
    account_mode: str = "paper",
    expected_account_mode: str = "paper",
    fx_required: bool = False,
    fx_freshness: str | None = None,
    total_portfolio_value: str | None = "10000",
    base_currency: str | None = "USD",
) -> DraftSourceContext:
    return DraftSourceContext(
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        ibkr_conid="265598",
        symbol="AAPL",
        currency=currency,
        exchange="SMART",
        primary_exchange=primary_exchange,
        account_mode=account_mode,
        expected_account_mode=expected_account_mode,
        action_label=action_label,
        action_label_nl=action_label,
        rationale_nl="test",
        current_position_quantity=Decimal(held_quantity),
        current_position_average_cost=None,
        current_market_last_price=Decimal(market_price) if market_price is not None else None,
        current_market_freshness_status=market_freshness,
        cash_amount=Decimal(cash) if cash is not None else None,
        cash_currency=cash_currency,
        fx_required=fx_required,
        fx_freshness_status=fx_freshness,
        total_portfolio_value=Decimal(total_portfolio_value) if total_portfolio_value else None,
        base_currency=base_currency,
    )


# ---- Sizing --------------------------------------------------------------


def test_kopen_floors_capital_div_price_to_whole_shares() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Kopen", market_price="180.00"),
        default_buy_value_in_quote_currency=DEFAULT_BUY_VALUE_EUR,
    )
    assert sizing.action_side == "BUY"
    assert sizing.quantity == Decimal("5")  # floor(1000 / 180)
    assert sizing.limit_price == Decimal("180.000000")
    assert sizing.status == "ready"


def test_kopen_blocked_when_limit_price_exceeds_capital() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Kopen", market_price="50000.00"),
        default_buy_value_in_quote_currency=Decimal("1000"),
    )
    assert sizing.status == "blocked"
    assert sizing.blocking_reason == "buy_value_too_small_for_one_share"


def test_kopen_blocked_when_market_price_missing() -> None:
    sizing = derive_action_draft_sizing(_context(market_price=None))
    assert sizing.status == "blocked"
    assert sizing.blocking_reason == "missing_market_price"


def test_langzaam_bijkopen_uses_top_up_pct_of_held_quantity() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Langzaam bijkopen", held_quantity="40"),
        top_up_pct=Decimal("0.25"),
    )
    assert sizing.action_side == "BUY"
    assert sizing.quantity == Decimal("10")  # floor(40 * 0.25)


def test_langzaam_bijkopen_falls_back_to_default_buy_when_no_held_quantity() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Langzaam bijkopen", held_quantity="0", market_price="100"),
        default_buy_value_in_quote_currency=Decimal("500"),
    )
    assert sizing.quantity == Decimal("5")


def test_verminderen_uses_reduce_pct_of_held() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Verminderen", held_quantity="40"),
        reduce_pct=Decimal("0.25"),
    )
    assert sizing.action_side == "SELL"
    assert sizing.quantity == Decimal("10")


def test_verkopen_sells_all_held_shares() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Verkopen", held_quantity="37")
    )
    assert sizing.action_side == "SELL"
    assert sizing.quantity == Decimal("37")


def test_sell_branch_blocked_when_no_held_quantity() -> None:
    sizing = derive_action_draft_sizing(
        _context(action_label="Verkopen", held_quantity="0")
    )
    assert sizing.status == "blocked"
    assert sizing.blocking_reason == "no_held_position_to_sell"


@pytest.mark.parametrize(
    "label",
    ["Houden", "Bekijken", "Geen actie", "Vermijden", "Cash houden", "Geblokkeerd"],
)
def test_non_actionable_labels_block(label: str) -> None:
    sizing = derive_action_draft_sizing(_context(action_label=label))
    assert sizing.status == "blocked"
    assert sizing.blocking_reason == "not_actionable_label"


# ---- Orderimpact ---------------------------------------------------------


def test_orderimpact_buy_decreases_cash_and_increases_position() -> None:
    context = _context(action_label="Kopen", held_quantity="0", market_price="100", cash="1000")
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)

    assert impact.estimated_order_value == Decimal("500.000000")  # 5 * 100
    assert impact.estimated_cash_before == Decimal("1000.000000")
    assert impact.estimated_cash_after == Decimal("500.000000")
    assert impact.estimated_position_quantity_before == Decimal("0")
    assert impact.estimated_position_quantity_after == Decimal("5")
    assert impact.estimated_position_value_after == Decimal("500.000000")
    assert impact.estimated_portfolio_weight_after_pct is not None
    # Belgian TOB default: standard_stock 0.35% on 500 = 1.75
    assert impact.estimated_belgian_tob == Decimal("1.75")
    assert impact.belgian_tob_security_class == "standard_stock"


def test_orderimpact_uses_explicit_security_class_when_provided() -> None:
    from portfolio_outlook_portfolio import TobSecurityClass

    context = _context(
        action_label="Kopen", held_quantity="0", market_price="100", cash="10000"
    )
    sizing = derive_action_draft_sizing(
        context, default_buy_value_in_quote_currency=Decimal("1000")
    )
    impact = compute_orderimpact(
        context,
        sizing,
        belgian_tob_security_class=TobSecurityClass.ACCUMULATING_ETF,
    )
    # 10 * 100 = 1000 → 1000 * 1.32% = 13.20
    assert impact.estimated_belgian_tob == Decimal("13.20")
    assert impact.belgian_tob_security_class == "accumulating_etf"


def test_orderimpact_sell_increases_cash_and_decreases_position() -> None:
    context = _context(
        action_label="Verkopen", held_quantity="10", market_price="200", cash="100"
    )
    sizing = derive_action_draft_sizing(context)
    impact = compute_orderimpact(context, sizing)

    assert sizing.action_side == "SELL"
    assert sizing.quantity == Decimal("10")
    assert impact.estimated_cash_before == Decimal("100.000000")
    assert impact.estimated_cash_after == Decimal("2100.000000")  # 100 + 10*200
    assert impact.estimated_position_quantity_after == Decimal("0")


def test_orderimpact_omits_cash_when_currencies_differ_and_fx_required() -> None:
    context = _context(
        action_label="Kopen",
        held_quantity="0",
        market_price="100",
        cash="1000",
        cash_currency="EUR",  # different from order currency
        currency="USD",
        fx_required=True,
    )
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)

    assert impact.estimated_cash_before is None
    assert impact.estimated_cash_after is None
    assert impact.estimated_order_value == Decimal("500.000000")


# ---- Dry-run -------------------------------------------------------------


def test_dry_run_passes_for_a_clean_buy() -> None:
    context = _context(
        action_label="Kopen",
        held_quantity="0",
        market_price="100",
        market_freshness="fresh",
        cash="10000",
    )
    sizing = derive_action_draft_sizing(
        context, default_buy_value_in_quote_currency=Decimal("500")
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert result.status == "passed"
    assert result.failures == ()


def test_dry_run_no_longer_blocks_on_account_mode_mismatch() -> None:
    """V1 §21.1 relock: account-mode is reported, not gated.

    A paper-vs-live difference between the connected IBKR account and
    the operator's expected_account_mode is informational; it must not
    fail dry-run anymore. The remaining safety surface is per-draft
    manual approval + the broker's own account selection.
    """

    context = _context(
        account_mode="paper",
        expected_account_mode="real",
        market_freshness="fresh",
    )
    sizing = derive_action_draft_sizing(
        context, default_buy_value_in_quote_currency=Decimal("500")
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "account_mode_mismatch" not in result.failures


def test_dry_run_still_flags_missing_account_mode() -> None:
    """Missing-mode (empty string) still fails dry-run — the connected
    IBKR session must always report a mode."""

    context = _context(
        account_mode="", expected_account_mode="paper", market_freshness="fresh"
    )
    sizing = derive_action_draft_sizing(
        context, default_buy_value_in_quote_currency=Decimal("500")
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "missing_account_mode" in result.failures


def test_dry_run_flags_unsupported_exchange() -> None:
    context = _context(primary_exchange="OTC")
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "unsupported_exchange" in result.failures


def test_dry_run_flags_stale_market_data() -> None:
    context = _context(market_freshness="stale")
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "market_data_not_fresh" in result.failures


def test_dry_run_flags_stale_fx_when_required() -> None:
    context = _context(fx_required=True, fx_freshness="stale", cash_currency="EUR", currency="USD")
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "fx_not_fresh" in result.failures


def test_dry_run_flags_buy_exceeds_usable_cash() -> None:
    # Available cash 100; order value 500 → should flag.
    context = _context(action_label="Kopen", market_price="100", cash="100")
    sizing = derive_action_draft_sizing(context, default_buy_value_in_quote_currency=Decimal("500"))
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "buy_value_exceeds_usable_cash" in result.failures


def test_dry_run_flags_sell_quantity_exceeds_held_when_input_inconsistent() -> None:
    # We can't easily build a SELL that exceeds held through the regular
    # sizing helper, so we tamper with the sizing result the way an editor
    # eventually will.
    from portfolio_outlook_portfolio.action_draft_safety import DraftSizing

    context = _context(action_label="Verkopen", held_quantity="5", market_price="100")
    sizing = DraftSizing(
        action_side="SELL",
        quantity=Decimal("10"),  # exceeds held=5
        limit_price=Decimal("100"),
        status="ready",
        blocking_reason=None,
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "sell_quantity_exceeds_held" in result.failures


def test_dry_run_short_circuits_on_blocked_sizing() -> None:
    context = _context(action_label="Houden")
    sizing = derive_action_draft_sizing(context)
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert result.status == "failed"
    assert result.failures == ("not_actionable_label",)


# ---- Kelly BUY path (Slice 19) ----------------------------------------


def _kelly_context(
    *,
    market_price: str = "100.00",
    cash: str = "100000",
    total_portfolio_value: str = "100000",
    prob_gain: str | None = "0.6",
    expected_return_pct: str | None = "10",
    downside_loss_pct: str | None = "5",
    current_sector_exposure_pct: str | None = None,
) -> DraftSourceContext:
    return DraftSourceContext(
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        ibkr_conid="265598",
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        account_mode="paper",
        expected_account_mode="paper",
        action_label="Kopen",
        action_label_nl="Kopen",
        rationale_nl="test",
        current_position_quantity=Decimal("0"),
        current_position_average_cost=None,
        current_market_last_price=Decimal(market_price),
        current_market_freshness_status="fresh",
        cash_amount=Decimal(cash),
        cash_currency="USD",
        fx_required=False,
        fx_freshness_status=None,
        total_portfolio_value=Decimal(total_portfolio_value),
        base_currency="USD",
        ensemble_prob_gain=Decimal(prob_gain) if prob_gain is not None else None,
        ensemble_expected_return_pct=(
            Decimal(expected_return_pct) if expected_return_pct is not None else None
        ),
        ensemble_downside_loss_pct=(
            Decimal(downside_loss_pct) if downside_loss_pct is not None else None
        ),
        current_sector_exposure_pct=(
            Decimal(current_sector_exposure_pct)
            if current_sector_exposure_pct is not None
            else None
        ),
        current_portfolio_position_count=None,
    )


def test_kopen_uses_kelly_when_ensemble_inputs_present() -> None:
    sizing = derive_action_draft_sizing(_kelly_context())
    # p=0.6, b=10%, L=5% → Kelly raw = 7.0 → capped at 1.0 (per_asset_cap)
    # then per_asset_cap brings it to 0.05 → 0.05 × 100,000 = 5,000
    # → 5,000 / 100 = 50 shares.
    assert sizing.action_side == "BUY"
    assert sizing.quantity == Decimal("50")


def test_kopen_falls_back_to_default_when_ensemble_missing() -> None:
    sizing = derive_action_draft_sizing(
        _kelly_context(prob_gain=None),
        default_buy_value_in_quote_currency=Decimal("1000"),
    )
    # 1000 / 100 = 10 shares (legacy default-buy-value path).
    assert sizing.quantity == Decimal("10")


def test_kopen_kelly_is_zero_on_negative_ev() -> None:
    sizing = derive_action_draft_sizing(
        _kelly_context(prob_gain="0.30", expected_return_pct="3", downside_loss_pct="10"),
    )
    # Negative EV → fraction 0 → 0 shares → blocked.
    assert sizing.status == "blocked"
    assert sizing.blocking_reason == "buy_value_too_small_for_one_share"
    assert sizing.quantity == Decimal("0")


def test_kopen_kelly_capped_when_cash_smaller_than_kelly_target() -> None:
    # Portfolio = 100,000 but cash only 2,000 → 0.05 × 100k = 5,000
    # > 2,000 cash; so capital = min(5000, 2000) = 2000 → 2000/100 = 20 shares.
    sizing = derive_action_draft_sizing(
        _kelly_context(cash="2000"),
    )
    assert sizing.quantity == Decimal("20")


def test_kopen_sector_cap_reduces_quantity() -> None:
    # Sector already at 28% → only 2% sector headroom; per-asset cap 5%.
    sizing = derive_action_draft_sizing(
        _kelly_context(current_sector_exposure_pct="28"),
    )
    # 0.02 × 100,000 = 2,000 / 100 = 20 shares.
    assert sizing.quantity == Decimal("20")


def test_kopen_falls_back_when_portfolio_value_missing() -> None:
    sizing = derive_action_draft_sizing(
        _kelly_context(total_portfolio_value="0"),
        default_buy_value_in_quote_currency=Decimal("1000"),
    )
    assert sizing.quantity == Decimal("10")  # legacy default-buy-value


def test_kopen_falls_back_when_cash_missing() -> None:
    sizing = derive_action_draft_sizing(
        _kelly_context(cash="0"),
        default_buy_value_in_quote_currency=Decimal("500"),
    )
    # Cash missing → Kelly skipped → legacy default-buy-value (500/100 = 5).
    assert sizing.quantity == Decimal("5")


# ---- Per-order-type dry-run (Slice 20 / §21.3 vocabulary) -----------------


def _ready_sizing(**overrides: object):  # type: ignore[no-untyped-def]
    from portfolio_outlook_portfolio.action_draft_safety import DraftSizing

    fields: dict[str, object] = dict(
        action_side="BUY",
        quantity=Decimal("10"),
        limit_price=Decimal("100"),
        status="ready",
        blocking_reason=None,
        order_type="LMT",
    )
    fields.update(overrides)
    return DraftSizing(**fields)  # type: ignore[arg-type]


def test_dry_run_unsupported_order_type_is_reported() -> None:
    context = _context(action_label="Kopen", market_price="100", cash="100000")
    sizing = _ready_sizing(order_type="MOC")
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "unsupported_order_type" in result.failures


def test_dry_run_mkt_buy_passes_without_extras() -> None:
    context = _context(action_label="Kopen", market_price="100", cash="100000")
    # MKT has no limit_price requirement; we set it to 0 to demonstrate.
    sizing = _ready_sizing(order_type="MKT", limit_price=Decimal("0"))
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    # The cash-vs-order check uses limit_price=0 so order_value=0 → no cash
    # failure. The dry-run should pass for the MKT path.
    assert "invalid_limit_price" not in result.failures
    assert result.status == "passed"


def test_dry_run_stp_requires_stop_price() -> None:
    context = _context(action_label="Verminderen", held_quantity="50", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL", order_type="STP", stop_price=None
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "stp_missing_stop_price" in result.failures


def test_dry_run_stp_lmt_requires_stop_and_limit() -> None:
    context = _context(action_label="Verminderen", held_quantity="50", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL",
        order_type="STP_LMT",
        stop_price=None,  # missing
        limit_price=Decimal("100"),
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "stp_lmt_missing_stop_or_limit" in result.failures


def test_dry_run_trail_requires_one_of_amount_or_percent() -> None:
    context = _context(action_label="Verminderen", held_quantity="50", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL",
        order_type="TRAIL",
        trail_amount=None,
        trail_percent=None,
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "trail_missing_trail_value" in result.failures


def test_dry_run_trail_rejects_both_amount_and_percent() -> None:
    context = _context(action_label="Verminderen", held_quantity="50", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL",
        order_type="TRAIL",
        trail_amount=Decimal("1"),
        trail_percent=Decimal("1"),
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "trail_amount_and_percent_set" in result.failures


def test_dry_run_trail_lmt_requires_limit_price() -> None:
    context = _context(action_label="Verminderen", held_quantity="50", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL",
        order_type="TRAIL_LMT",
        trail_amount=Decimal("1"),
        limit_price=Decimal("0"),  # missing
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "trail_lmt_missing_limit_price" in result.failures
    assert "invalid_limit_price" in result.failures


def test_dry_run_bracket_buy_needs_tp_above_and_sl_below_limit() -> None:
    context = _context(action_label="Kopen", market_price="100", cash="100000")
    sizing = _ready_sizing(
        action_side="BUY",
        order_type="BRACKET",
        limit_price=Decimal("100"),
        bracket_take_profit_limit_price=Decimal("95"),  # below limit
        bracket_stop_loss_price=Decimal("105"),  # above limit
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "bracket_take_profit_below_limit" in result.failures
    assert "bracket_stop_loss_above_limit" in result.failures


def test_dry_run_bracket_sell_requires_inverted_ordering() -> None:
    context = _context(action_label="Verkopen", held_quantity="20", market_price="100")
    sizing = _ready_sizing(
        action_side="SELL",
        order_type="BRACKET",
        limit_price=Decimal("100"),
        # SELL bracket needs tp < limit < sl; this one is wrong.
        bracket_take_profit_limit_price=Decimal("110"),
        bracket_stop_loss_price=Decimal("90"),
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "bracket_inverted_for_sell" in result.failures


def test_dry_run_bracket_missing_tp_and_sl() -> None:
    context = _context(action_label="Kopen", market_price="100", cash="100000")
    sizing = _ready_sizing(
        action_side="BUY",
        order_type="BRACKET",
        limit_price=Decimal("100"),
        bracket_take_profit_limit_price=None,
        bracket_stop_loss_price=None,
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert "bracket_missing_take_profit" in result.failures
    assert "bracket_missing_stop_loss" in result.failures


def test_dry_run_bracket_buy_passes_when_ordering_is_correct() -> None:
    context = _context(action_label="Kopen", market_price="100", cash="100000")
    sizing = _ready_sizing(
        action_side="BUY",
        order_type="BRACKET",
        limit_price=Decimal("100"),
        bracket_take_profit_limit_price=Decimal("110"),
        bracket_stop_loss_price=Decimal("90"),
    )
    impact = compute_orderimpact(context, sizing)
    result = run_dry_run_safety_checks(context, sizing, impact)
    assert result.status == "passed"
    assert result.failures == ()
