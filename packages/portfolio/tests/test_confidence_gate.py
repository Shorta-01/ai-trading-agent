"""Tests for the confidence gate (V1.2 §H)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_BELOW_CONFIDENCE,
    BLOCKING_REASON_INVALID_FORECAST,
    CONFIDENCE_GATE_BLOCKING_REASON_ZERO_VOLATILITY,
    TobSecurityClass,
    evaluate_confidence_gate,
    probability_of_target_hit,
)

# ---- probability_of_target_hit ---------------------------------------


def test_p_hit_well_above_50pct_when_median_equals_target() -> None:
    # Running-max upgrade (V1.2 §P): when median == target the
    # terminal-only probability is 50 %, but the running-max picks up
    # additional probability from paths that touched the target then
    # came back down by horizon end. With 20 % annual vol over 6
    # months that reflection mass pushes P > 75 %.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("104.73"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,  # 6 months
        target_price=Decimal("104.73"),
    )
    assert p is not None
    assert Decimal("75") <= p <= Decimal("90")


def test_p_hit_high_when_median_well_above_target() -> None:
    # Median forecast way above target → P should be high.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("120"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_price=Decimal("104.73"),
    )
    assert p is not None
    assert p > Decimal("80")


def test_p_hit_low_when_median_well_below_target_and_low_vol() -> None:
    # Running-max upgrade (V1.2 §P): even when the median is below
    # target, the running-max can still be substantial if vol is
    # high (the price can excurse up to target then retreat). To
    # produce a *low* running-max we need both: median clearly below
    # target AND low vol.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("90"),
        annual_volatility_pct=Decimal("5"),  # low vol
        horizon_days=63,  # 3 months
        target_price=Decimal("104.73"),
    )
    assert p is not None
    assert p < Decimal("30")


def test_p_hit_rises_with_volatility() -> None:
    # When the median is below the target, higher vol increases the
    # tail probability of touching the target.
    low_vol = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("100"),
        annual_volatility_pct=Decimal("10"),
        horizon_days=126,
        target_price=Decimal("110"),
    )
    high_vol = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("100"),
        annual_volatility_pct=Decimal("40"),
        horizon_days=126,
        target_price=Decimal("110"),
    )
    assert low_vol is not None and high_vol is not None
    assert high_vol > low_vol


def test_p_hit_rises_with_horizon() -> None:
    # Longer horizon → wider distribution → more chance the target
    # is reached.
    short = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("100"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=21,  # 1 month
        target_price=Decimal("110"),
    )
    long = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("100"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=252,  # 12 months
        target_price=Decimal("110"),
    )
    assert short is not None and long is not None
    assert long > short


def test_target_at_or_below_current_returns_100() -> None:
    # The take-profit LMT would trigger on entry → 100 %.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("110"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_price=Decimal("100"),
    )
    assert p == Decimal("100.00")
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("110"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_price=Decimal("95"),
    )
    assert p == Decimal("100.00")


def test_running_max_strictly_greater_than_terminal_only() -> None:
    # Sanity: the running-max probability for any K > S_0 must be
    # at least the terminal-price probability. With median ≈ S_0
    # and target slightly above current, the gap is dramatic.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("100"),  # flat median
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_price=Decimal("105"),
    )
    assert p is not None
    # Terminal-only probability with median == current and target
    # 5 % above would be roughly Φ(ln(100/105) / σ_horizon) ≈ Φ(-0.35)
    # ≈ 36 %. Running-max is ~70 %+ — the reflection nearly doubles
    # the chance.
    assert p > Decimal("65")


def test_p_hit_capped_at_100_on_extreme_inputs() -> None:
    # Median well above target with high vol: probability must cap
    # at 100, never overflow.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("200"),
        annual_volatility_pct=Decimal("80"),
        horizon_days=252,
        target_price=Decimal("105"),
    )
    assert p is not None
    assert p <= Decimal("100.00")


def test_p_hit_returns_none_on_invalid_inputs() -> None:
    assert (
        probability_of_target_hit(
            current_price=Decimal("0"),
            median_forecast_price=Decimal("100"),
            annual_volatility_pct=Decimal("20"),
            horizon_days=126,
            target_price=Decimal("104"),
        )
        is None
    )
    assert (
        probability_of_target_hit(
            current_price=Decimal("100"),
            median_forecast_price=Decimal("100"),
            annual_volatility_pct=Decimal("0"),
            horizon_days=126,
            target_price=Decimal("104"),
        )
        is None
    )
    assert (
        probability_of_target_hit(
            current_price=Decimal("100"),
            median_forecast_price=Decimal("100"),
            annual_volatility_pct=Decimal("20"),
            horizon_days=0,
            target_price=Decimal("104"),
        )
        is None
    )


# ---- evaluate_confidence_gate ----------------------------------------


def test_passes_when_p_hit_above_threshold() -> None:
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("115"),  # well above the 4.73 % target
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert result.allowed
    assert result.blocking_reason is None
    assert result.required_gross_pct == Decimal("4.73")
    assert result.target_price == Decimal("104.7300")
    assert result.p_target_hit_pct >= Decimal("70")


def test_blocks_when_p_hit_below_threshold() -> None:
    # Median right at current → barely any room above the target.
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("99"),
        annual_volatility_pct=Decimal("15"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_BELOW_CONFIDENCE
    # Diagnostics still populated.
    assert result.required_gross_pct == Decimal("4.73")
    assert result.target_price == Decimal("104.7300")
    assert result.p_target_hit_pct < Decimal("70")


def test_threshold_at_50_pct_lets_marginal_candidate_through() -> None:
    # Median ≈ target → P ≈ 50 %. With a 50 % threshold this should
    # squeak past.
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("104.73"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("49"),
    )
    assert result.allowed


def test_blocks_on_zero_volatility() -> None:
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("110"),
        annual_volatility_pct=Decimal("0"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert not result.allowed
    assert result.blocking_reason == CONFIDENCE_GATE_BLOCKING_REASON_ZERO_VOLATILITY
    # Target was still computed for the UI.
    assert result.target_price == Decimal("104.7300")


def test_blocks_on_invalid_current_price() -> None:
    result = evaluate_confidence_gate(
        current_price=Decimal("0"),
        median_forecast_price=Decimal("110"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_FORECAST


def test_blocks_on_invalid_median_price() -> None:
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("0"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_FORECAST


def test_blocks_on_zero_horizon() -> None:
    result = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("110"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=0,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("70"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_INVALID_FORECAST


def test_accumulating_etf_target_higher_than_standard() -> None:
    # Same forecast, different security class → accumulating ETF
    # needs a higher gross uplift (1.32 % TOB instead of 0.35 %).
    standard = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("108"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        confidence_threshold_pct=Decimal("60"),
    )
    accumulating = evaluate_confidence_gate(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("108"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.ACCUMULATING_ETF,
        confidence_threshold_pct=Decimal("60"),
    )
    assert standard.required_gross_pct == Decimal("4.73")
    assert accumulating.required_gross_pct == Decimal("6.78")
    # Higher target → lower probability of hit.
    assert accumulating.p_target_hit_pct < standard.p_target_hit_pct


def test_float_inputs_rejected() -> None:
    with pytest.raises(TypeError):
        evaluate_confidence_gate(
            current_price=100.0,  # type: ignore[arg-type]
            median_forecast_price=Decimal("110"),
            annual_volatility_pct=Decimal("20"),
            horizon_days=126,
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
            confidence_threshold_pct=Decimal("70"),
        )
    with pytest.raises(TypeError):
        evaluate_confidence_gate(
            current_price=Decimal("100"),
            median_forecast_price=Decimal("110"),
            annual_volatility_pct=Decimal("20"),
            horizon_days=126.0,  # type: ignore[arg-type]
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
            confidence_threshold_pct=Decimal("70"),
        )


def test_bool_horizon_rejected() -> None:
    # Python treats bool as int, but a True/False horizon is a clear
    # caller bug — guard explicitly.
    with pytest.raises(TypeError):
        evaluate_confidence_gate(
            current_price=Decimal("100"),
            median_forecast_price=Decimal("110"),
            annual_volatility_pct=Decimal("20"),
            horizon_days=True,  # type: ignore[arg-type]
            target_net_pct=Decimal("4"),
            security_class=TobSecurityClass.STANDARD_STOCK,
            confidence_threshold_pct=Decimal("70"),
        )
