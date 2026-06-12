"""Tests for the profit-harvest cycle math (V1.2 §F)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    TobSecurityClass,
    compute_take_profit_sell_price,
    conviction_weighted_position_size_eur,
    gross_pct_for_net_target_pct,
)

# ---- gross_pct_for_net_target_pct -------------------------------------


def test_standard_stock_4pct_net_needs_roughly_4_73_pct_gross() -> None:
    # Derivation: 1.04 * 1.0035 / 0.9965 = 1.04733... → +4.73%.
    gross = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert gross == Decimal("4.73")


def test_distributing_etf_matches_standard_stock_rate() -> None:
    gross_stock = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    gross_etf = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.DISTRIBUTING_ETF,
    )
    assert gross_stock == gross_etf


def test_accumulating_etf_requires_much_higher_gross() -> None:
    # 1.04 * 1.0132 / 0.9868 = 1.06782... → +6.78%. The TOB on
    # accumulating funds is ~3.8x the standard rate.
    gross = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.ACCUMULATING_ETF,
    )
    assert gross == Decimal("6.78")


def test_bond_needs_only_slight_uplift() -> None:
    # 1.04 * 1.0012 / 0.9988 = 1.04250... → +4.25%.
    gross = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.BOND,
    )
    assert gross == Decimal("4.25")


def test_zero_target_returns_zero_gross() -> None:
    # Even at zero net target the gross is *slightly* above zero due
    # to the round-trip TOB cost. 1.0 * 1.0035 / 0.9965 = 1.00702.
    gross = gross_pct_for_net_target_pct(
        target_net_pct=Decimal("0"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert gross == Decimal("0.70")


def test_negative_target_rejected() -> None:
    with pytest.raises(ValueError):
        gross_pct_for_net_target_pct(
            target_net_pct=Decimal("-1"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


def test_float_target_rejected() -> None:
    with pytest.raises(TypeError):
        gross_pct_for_net_target_pct(
            target_net_pct=4.0,  # type: ignore[arg-type]
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


# ---- compute_take_profit_sell_price -----------------------------------


def test_take_profit_price_uses_gross_uplift() -> None:
    # Entry 100, +4% net target on standard stock → ~104.73.
    price = compute_take_profit_sell_price(
        entry_price=Decimal("100"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert price == Decimal("104.7300")


def test_take_profit_price_quantises_to_four_decimals() -> None:
    price = compute_take_profit_sell_price(
        entry_price=Decimal("47.81"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    # 47.81 * 1.0473 = 50.0714... → 50.0714
    assert price == Decimal("50.0714")


def test_zero_or_negative_entry_rejected() -> None:
    with pytest.raises(ValueError):
        compute_take_profit_sell_price(
            entry_price=Decimal("0"),
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )
    with pytest.raises(ValueError):
        compute_take_profit_sell_price(
            entry_price=Decimal("-10"),
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


def test_float_entry_rejected() -> None:
    with pytest.raises(TypeError):
        compute_take_profit_sell_price(
            entry_price=100.0,  # type: ignore[arg-type]
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
        )


# ---- conviction_weighted_position_size_eur ----------------------------


def test_at_floor_confidence_returns_minimum_position() -> None:
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("70"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("25000")


def test_at_full_confidence_returns_maximum_position() -> None:
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("100"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("100000")


def test_below_floor_returns_zero() -> None:
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("65"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("0")


def test_midpoint_confidence_is_linear() -> None:
    # 85% is exactly halfway between 70 (floor) and 100; expect midpoint
    # between min and max = €62 500.
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("85"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("62500")


def test_quarter_progress_is_linear() -> None:
    # 77.5 = floor + 25% of span; expect min + 25% of (max - min).
    # 25000 + 0.25 * 75000 = 43750.
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("77.5"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("43750")


def test_floor_at_100_degenerate_case() -> None:
    # Floor at 100% means the only acceptable level is exactly 100;
    # we treat that as 'max position' for an accepted trade.
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("100"),
        confidence_floor_pct=Decimal("100"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    assert size == Decimal("100000")


def test_rounded_to_whole_eur() -> None:
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("73"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
    )
    # 25000 + (3/30) * 75000 = 32500 — already whole.
    assert size == Decimal("32500")
    # Awkward bounds: pick numbers that produce a non-whole euro.
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("71"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("25001"),
        max_position_eur=Decimal("100000"),
    )
    # 25001 + (1/30) * 74999 = 25001 + 2499.966... = 27500.966... → 27501.
    assert size == Decimal("27501")


def test_invalid_bounds_rejected() -> None:
    with pytest.raises(ValueError):
        conviction_weighted_position_size_eur(
            confidence_pct=Decimal("70"),
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("0"),
            max_position_eur=Decimal("100000"),
        )
    with pytest.raises(ValueError):
        conviction_weighted_position_size_eur(
            confidence_pct=Decimal("70"),
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("100000"),
            max_position_eur=Decimal("50000"),
        )


def test_invalid_confidence_rejected() -> None:
    with pytest.raises(ValueError):
        conviction_weighted_position_size_eur(
            confidence_pct=Decimal("-1"),
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("25000"),
            max_position_eur=Decimal("100000"),
        )
    with pytest.raises(ValueError):
        conviction_weighted_position_size_eur(
            confidence_pct=Decimal("101"),
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("25000"),
            max_position_eur=Decimal("100000"),
        )
    with pytest.raises(ValueError):
        conviction_weighted_position_size_eur(
            confidence_pct=Decimal("70"),
            confidence_floor_pct=Decimal("-1"),
            min_position_eur=Decimal("25000"),
            max_position_eur=Decimal("100000"),
        )


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        conviction_weighted_position_size_eur(
            confidence_pct=70.0,  # type: ignore[arg-type]
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("25000"),
            max_position_eur=Decimal("100000"),
        )
