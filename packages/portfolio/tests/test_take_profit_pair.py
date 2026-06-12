"""Tests for the take-profit order pair builder (V1.2 §J)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_INVALID_NET_TARGET,
    BLOCKING_REASON_INVALID_POSITION_EUR,
    BLOCKING_REASON_INVALID_PRICE,
    BLOCKING_REASON_POSITION_TOO_SMALL,
    ENTRY_TIF,
    TAKE_PROFIT_TIF,
    TobSecurityClass,
    build_take_profit_pair,
)

# ---- happy path ------------------------------------------------------


def test_standard_stock_pair_built_with_correct_take_profit_price() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.allowed
    assert result.pair is not None
    pair = result.pair
    assert pair.ticker == "AAPL"
    assert pair.take_profit_sell_price == Decimal("104.7300")
    assert pair.required_gross_pct == Decimal("4.73")
    assert pair.entry_tif == ENTRY_TIF
    assert pair.take_profit_tif == TAKE_PROFIT_TIF


def test_qty_floors_to_avoid_exceeding_position_cap() -> None:
    # €25 000 / (100 * 1.0035) = 249.12... → floor to 249.
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.pair is not None
    assert result.pair.qty == 249
    # Actual outlay must not exceed the intended cap.
    assert result.pair.actual_outlay_eur <= Decimal("25000")


def test_expected_net_profit_roughly_equals_target_pct_of_outlay() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("100000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.pair is not None
    pair = result.pair
    # Expected net profit should be very close to 4 % of actual outlay.
    pct = (
        pair.expected_net_profit_eur
        / pair.actual_outlay_eur
        * Decimal("100")
    )
    assert Decimal("3.95") < pct < Decimal("4.05")


def test_accumulating_etf_needs_higher_gross_uplift() -> None:
    result = build_take_profit_pair(
        ticker="IWDA",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.ACCUMULATING_ETF,
    )
    assert result.pair is not None
    assert result.pair.required_gross_pct == Decimal("6.78")
    assert result.pair.take_profit_sell_price == Decimal("106.7800")


def test_ticker_normalised_to_upper() -> None:
    result = build_take_profit_pair(
        ticker="  aapl  ",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.pair is not None
    assert result.pair.ticker == "AAPL"


# ---- refusal paths ---------------------------------------------------


def test_position_too_small_blocked() -> None:
    # €50 budget at €100 per share = can't even buy one.
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("50"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_POSITION_TOO_SMALL
    assert result.pair is None


def test_zero_entry_price_blocked() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("0"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_PRICE


def test_negative_entry_price_blocked() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("-10"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_PRICE


def test_zero_position_eur_blocked() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("0"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_POSITION_EUR


def test_zero_target_blocked() -> None:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("0"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_NET_TARGET


# ---- input type guards -----------------------------------------------


def test_empty_ticker_rejected() -> None:
    with pytest.raises(ValueError):
        build_take_profit_pair(
            ticker="",
            entry_lmt_price=Decimal("100"),
            intended_position_eur=Decimal("25000"),
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        build_take_profit_pair(
            ticker="AAPL",
            entry_lmt_price=100.0,  # type: ignore[arg-type]
            intended_position_eur=Decimal("25000"),
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )
    with pytest.raises(TypeError):
        build_take_profit_pair(
            ticker="AAPL",
            entry_lmt_price=Decimal("100"),
            intended_position_eur=25000.0,  # type: ignore[arg-type]
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )
    with pytest.raises(TypeError):
        build_take_profit_pair(
            ticker="AAPL",
            entry_lmt_price=Decimal("100"),
            intended_position_eur=Decimal("25000"),
            target_net_pct=4.0,  # type: ignore[arg-type]
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


# ---- doctrinal invariants --------------------------------------------


def test_take_profit_above_entry_for_any_positive_target() -> None:
    # Sanity: take-profit must always be strictly above entry, on
    # every security class, for any non-zero target.
    for klass in TobSecurityClass:
        result = build_take_profit_pair(
            ticker="X",
            entry_lmt_price=Decimal("100"),
            intended_position_eur=Decimal("100000"),
            target_net_pct=Decimal("4"),
            security_class=klass,
        )
        assert result.pair is not None
        assert result.pair.take_profit_sell_price > Decimal("100")


def test_actual_outlay_never_exceeds_intended_position() -> None:
    # Doctrine: under-fill is safe, over-fill breaks the position cap.
    for entry, intended in (
        (Decimal("47.81"), Decimal("25000")),
        (Decimal("321.12"), Decimal("100000")),
        (Decimal("1.23"), Decimal("50000")),
    ):
        result = build_take_profit_pair(
            ticker="X",
            entry_lmt_price=entry,
            intended_position_eur=intended,
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )
        assert result.pair is not None
        assert result.pair.actual_outlay_eur <= intended


def test_expected_net_profit_positive_when_pair_allowed() -> None:
    # If the pair is built at all, the target is positive and the
    # math must produce a positive expected profit.
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.pair is not None
    assert result.pair.expected_net_profit_eur > Decimal("0")
