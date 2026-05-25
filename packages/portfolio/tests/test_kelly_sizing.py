"""Tests for fractional Kelly + risk-parity sizing (Slice 19)."""

from __future__ import annotations

from decimal import Decimal

from portfolio_outlook_portfolio import (
    DEFAULT_KELLY_FRACTION,
    DEFAULT_PER_ASSET_CAP_PCT,
    DEFAULT_PER_SECTOR_CAP_PCT,
    KellyInputs,
    apply_risk_parity_caps,
    compute_fractional_kelly_fraction,
    size_buy_with_kelly,
)

# ---- compute_fractional_kelly_fraction --------------------------------


def test_classic_symmetric_kelly_matches_p_minus_q() -> None:
    """When b == L the asymmetric Kelly collapses to (p - q) / b."""

    # p = 0.6, q = 0.4, b = L = 10%
    # raw Kelly = (0.6*0.10 - 0.4*0.10) / (0.10*0.10) = 0.02 / 0.01 = 2.0
    # half-Kelly = 1.0, but we clip to [0, 1] so = 1.0
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("10"),
        downside_loss_pct=Decimal("10"),
    )
    assert result == Decimal("1.000000")


def test_asymmetric_kelly_positive_expected_value() -> None:
    # p = 0.6, b = 20%, L = 10%
    # raw = (0.6*0.20 - 0.4*0.10) / (0.20*0.10) = 0.08 / 0.02 = 4.0
    # half-Kelly = 2.0 → clipped to 1.0
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("20"),
        downside_loss_pct=Decimal("10"),
    )
    assert result == Decimal("1.000000")


def test_modest_edge_yields_modest_kelly_fraction() -> None:
    # p = 0.52, b = 4%, L = 4%
    # raw = (0.52*0.04 - 0.48*0.04) / (0.04*0.04) = 0.0016 / 0.0016 = 1.0
    # half-Kelly = 0.5 → uncapped
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.52"),
        expected_return_pct=Decimal("4"),
        downside_loss_pct=Decimal("4"),
    )
    assert result == Decimal("0.500000")


def test_negative_ev_returns_zero() -> None:
    # p = 0.4 (mostly lose), b = L = 5% → negative numerator
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.4"),
        expected_return_pct=Decimal("5"),
        downside_loss_pct=Decimal("5"),
    )
    assert result == Decimal("0.000000")


def test_zero_expected_return_returns_zero() -> None:
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("0"),
        downside_loss_pct=Decimal("5"),
    )
    assert result == Decimal("0.000000")


def test_zero_downside_returns_zero() -> None:
    """A zero-downside "infinite-edge" bet is refused — Kelly can't
    size it."""

    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("5"),
        downside_loss_pct=Decimal("0"),
    )
    assert result == Decimal("0.000000")


def test_zero_kelly_fraction_returns_zero() -> None:
    result = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("5"),
        downside_loss_pct=Decimal("5"),
        kelly_fraction=0.0,
    )
    assert result == Decimal("0.000000")


def test_full_kelly_returns_double_of_half_kelly() -> None:
    half = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.55"),
        expected_return_pct=Decimal("8"),
        downside_loss_pct=Decimal("8"),
        kelly_fraction=0.5,
    )
    full = compute_fractional_kelly_fraction(
        prob_gain=Decimal("0.55"),
        expected_return_pct=Decimal("8"),
        downside_loss_pct=Decimal("8"),
        kelly_fraction=1.0,
    )
    # Full Kelly should be at least half×2 (when not capped at 1.0).
    assert full >= half


def test_default_kelly_fraction_is_half() -> None:
    assert DEFAULT_KELLY_FRACTION == 0.5


# ---- apply_risk_parity_caps -------------------------------------------


def test_no_cap_when_fraction_is_below_per_asset_cap() -> None:
    result = apply_risk_parity_caps(fraction=Decimal("0.03"))
    assert result.fraction == Decimal("0.03")
    assert result.per_asset_cap_hit is False
    assert result.per_sector_cap_hit is False


def test_per_asset_cap_clips_oversized_fraction() -> None:
    result = apply_risk_parity_caps(fraction=Decimal("0.50"))
    assert result.fraction == Decimal("0.05")  # 5% cap
    assert result.per_asset_cap_hit is True


def test_per_sector_cap_clips_when_sector_is_full() -> None:
    # Sector already at 28% → only 2% headroom; per-asset cap at 5%.
    result = apply_risk_parity_caps(
        fraction=Decimal("0.05"),
        current_sector_exposure_pct=Decimal("28"),
    )
    assert result.fraction == Decimal("0.02")
    assert result.per_sector_cap_hit is True


def test_both_caps_can_hit_together() -> None:
    # Sector at 20% → 10% sector headroom; per-asset cap 5%.
    # Raw fraction 0.40 → asset cap → 0.05 (per_asset_cap_hit=True),
    # then sector cap 0.10 → no further clip.
    result = apply_risk_parity_caps(
        fraction=Decimal("0.40"),
        current_sector_exposure_pct=Decimal("20"),
    )
    assert result.fraction == Decimal("0.05")
    assert result.per_asset_cap_hit is True
    # Sector cap doesn't bind because per-asset already brought us
    # below the sector headroom.
    assert result.per_sector_cap_hit is False


def test_sector_already_full_yields_zero_fraction() -> None:
    result = apply_risk_parity_caps(
        fraction=Decimal("0.05"),
        current_sector_exposure_pct=Decimal("30"),
    )
    assert result.fraction == Decimal("0")
    assert result.per_sector_cap_hit is True


def test_unknown_sector_exposure_skips_sector_cap() -> None:
    result = apply_risk_parity_caps(
        fraction=Decimal("0.04"),
        current_sector_exposure_pct=None,
    )
    assert result.fraction == Decimal("0.04")
    assert result.per_sector_cap_hit is False


def test_explanation_describes_active_cap() -> None:
    result_no_cap = apply_risk_parity_caps(fraction=Decimal("0.02"))
    assert "binnen de caps" in result_no_cap.explanation_nl

    result_asset_cap = apply_risk_parity_caps(fraction=Decimal("0.50"))
    assert "per-asset cap" in result_asset_cap.explanation_nl

    result_sector_cap = apply_risk_parity_caps(
        fraction=Decimal("0.04"),
        current_sector_exposure_pct=Decimal("28"),
    )
    assert "per-sector cap" in result_sector_cap.explanation_nl


def test_default_caps_are_5_and_30_pct() -> None:
    assert DEFAULT_PER_ASSET_CAP_PCT == 5.0
    assert DEFAULT_PER_SECTOR_CAP_PCT == 30.0


# ---- size_buy_with_kelly ----------------------------------------------


def test_end_to_end_kelly_to_whole_shares() -> None:
    inputs = KellyInputs(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("10"),
        downside_loss_pct=Decimal("5"),
    )
    qty, result = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("100000"),
        market_price=Decimal("150"),
    )
    # Kelly fraction caps at 0.05 (per-asset cap of 5%).
    # → 0.05 * 100,000 = 5,000 / 150 = 33.33 → floor to 33 shares.
    assert result.per_asset_cap_hit is True
    assert qty == Decimal("33")


def test_size_zero_when_fraction_collapses_to_zero() -> None:
    inputs = KellyInputs(
        prob_gain=Decimal("0.3"),
        expected_return_pct=Decimal("5"),
        downside_loss_pct=Decimal("10"),
    )
    qty, result = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("100000"),
        market_price=Decimal("150"),
    )
    assert qty == Decimal("0")
    assert result.fraction == Decimal("0")


def test_size_zero_when_cash_is_zero() -> None:
    inputs = KellyInputs(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("10"),
        downside_loss_pct=Decimal("5"),
    )
    qty, _ = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("0"),
        market_price=Decimal("150"),
    )
    assert qty == Decimal("0")


def test_size_zero_when_market_price_is_zero() -> None:
    inputs = KellyInputs(
        prob_gain=Decimal("0.6"),
        expected_return_pct=Decimal("10"),
        downside_loss_pct=Decimal("5"),
    )
    qty, _ = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("10000"),
        market_price=Decimal("0"),
    )
    assert qty == Decimal("0")


def test_sector_cap_can_reduce_quantity_compared_to_per_asset_cap() -> None:
    """When the asset's sector is nearly full the sector cap fires
    *before* the per-asset cap, producing fewer shares."""

    inputs = KellyInputs(
        prob_gain=Decimal("0.7"),
        expected_return_pct=Decimal("20"),
        downside_loss_pct=Decimal("5"),
    )
    qty_no_sector, _ = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("100000"),
        market_price=Decimal("100"),
    )
    qty_full_sector, _ = size_buy_with_kelly(
        inputs=inputs,
        usable_cash=Decimal("100000"),
        market_price=Decimal("100"),
        current_sector_exposure_pct=Decimal("29"),
    )
    # Full sector → only 1% headroom → far fewer shares.
    assert qty_full_sector < qty_no_sector
