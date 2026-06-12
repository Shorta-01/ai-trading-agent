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


def test_p_hit_above_50pct_when_median_equals_target() -> None:
    # If median forecast == target, P(S_T >= target) should be 50%
    # (it's the median of a continuous distribution).
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("104.73"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,  # 6 months
        target_price=Decimal("104.73"),
    )
    assert p is not None
    assert Decimal("49.50") <= p <= Decimal("50.50")


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


def test_p_hit_low_when_median_well_below_target() -> None:
    # Median forecast below target → P should be low.
    p = probability_of_target_hit(
        current_price=Decimal("100"),
        median_forecast_price=Decimal("95"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
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
