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


# V1.2 §AO — stepped confidence-tier sizing.
# Tiers are RELATIVE to ``max_position_eur``:
#   ≥90% → 100% of max
#   80-90% → 60% of max
#   70-80% → 30% of max
# Caller is expected to pass max = portfolio × 0.50 so the
# operator-doctrine percentages (50/30/15 of portfolio) land
# correctly.


def test_confidence_90_or_above_returns_max_position() -> None:
    # ≥90% tier → 100% of cap (50% of €50k portfolio).
    for conf in (Decimal("90"), Decimal("95"), Decimal("100")):
        size = conviction_weighted_position_size_eur(
            confidence_pct=conf,
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("5000"),
            max_position_eur=Decimal("25000"),
        )
        assert size == Decimal("25000"), f"failed at conf={conf}"


def test_confidence_80_to_90_returns_60pct_of_max() -> None:
    # 80-90% tier → 60% of cap. 60% × €25k = €15k (= 30% of €50k portfolio).
    for conf in (Decimal("80"), Decimal("85"), Decimal("89.99")):
        size = conviction_weighted_position_size_eur(
            confidence_pct=conf,
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("5000"),
            max_position_eur=Decimal("25000"),
        )
        assert size == Decimal("15000"), f"failed at conf={conf}"


def test_confidence_70_to_80_returns_30pct_of_max() -> None:
    # 70-80% tier → 30% of cap. 30% × €25k = €7.5k (= 15% of €50k portfolio).
    for conf in (Decimal("70"), Decimal("75"), Decimal("79.99")):
        size = conviction_weighted_position_size_eur(
            confidence_pct=conf,
            confidence_floor_pct=Decimal("70"),
            min_position_eur=Decimal("5000"),
            max_position_eur=Decimal("25000"),
        )
        assert size == Decimal("7500"), f"failed at conf={conf}"


def test_below_floor_returns_zero() -> None:
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("65"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("25000"),
    )
    assert size == Decimal("0")


def test_tier_size_is_floored_at_min_position() -> None:
    # 70-80% tier at €5k cap → 30% × €5k = €1500 → floored at min_position
    # of €5000. The doctrine treats €5k as the TOB-efficiency floor.
    size = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("75"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("5000"),
    )
    assert size == Decimal("5000")


def test_tier_boundaries_are_inclusive_at_lower_bound() -> None:
    # Exactly 90.00% → top tier.
    size_at_90 = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("90"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("25000"),
    )
    # Just below 90 → middle tier (60% × €25k = €15k).
    size_at_89_99 = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("89.99"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("25000"),
    )
    assert size_at_90 == Decimal("25000")
    assert size_at_89_99 == Decimal("15000")
    # Same boundary check at 80.
    size_at_80 = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("80"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("25000"),
    )
    size_at_79_99 = conviction_weighted_position_size_eur(
        confidence_pct=Decimal("79.99"),
        confidence_floor_pct=Decimal("70"),
        min_position_eur=Decimal("5000"),
        max_position_eur=Decimal("25000"),
    )
    assert size_at_80 == Decimal("15000")
    assert size_at_79_99 == Decimal("7500")


def test_operator_doctrine_at_50k_portfolio() -> None:
    """CLAUDE.md §3 doctrine: on €50k trading-portfolio with
    max_position_pct=50%, expect the locked tier sizes."""

    portfolio_eur = Decimal("50000")
    max_position_eur = portfolio_eur * Decimal("0.50")  # €25k cap
    floor = Decimal("70")
    min_eur = Decimal("5000")

    assert conviction_weighted_position_size_eur(
        confidence_pct=Decimal("92"),
        confidence_floor_pct=floor,
        min_position_eur=min_eur,
        max_position_eur=max_position_eur,
    ) == Decimal("25000")  # 50% of portfolio
    assert conviction_weighted_position_size_eur(
        confidence_pct=Decimal("85"),
        confidence_floor_pct=floor,
        min_position_eur=min_eur,
        max_position_eur=max_position_eur,
    ) == Decimal("15000")  # 30% of portfolio
    assert conviction_weighted_position_size_eur(
        confidence_pct=Decimal("75"),
        confidence_floor_pct=floor,
        min_position_eur=min_eur,
        max_position_eur=max_position_eur,
    ) == Decimal("7500")  # 15% of portfolio


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
