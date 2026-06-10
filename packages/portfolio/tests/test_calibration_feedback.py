"""Tests for V1.2 §C — empirical calibration feedback.

The forecast bands are scaled by an empirical factor derived from the
calibration diary's rolling p10-p90 coverage. Default behaviour (no
scaling) is preserved unchanged.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.baseline_forecast import (
    BAND_SCALE_MAX,
    BAND_SCALE_MIN,
    DEFAULT_BAND_SCALE_FACTOR,
    DEFAULT_CALIBRATION_TARGET_COVERAGE,
    Z_10,
    Z_90,
    HistoricalBar,
    _empirical_band_scale_factor,
    _inverse_standard_normal_cdf,
    compute_baseline_forecast,
)

# ---- Inverse standard normal CDF (Beasley-Springer-Moro) ------------------


@pytest.mark.parametrize(
    "p, expected_z",
    [
        # Well-known reference values from any standard-normal table.
        (0.5, 0.0),
        (0.975, 1.95996398),
        (0.025, -1.95996398),
        (0.9, 1.28155157),
        (0.1, -1.28155157),
        (0.84134474606854, 1.0),  # ≈ Φ(1.0)
        (0.99, 2.32634787),
    ],
)
def test_inverse_normal_matches_standard_table(p: float, expected_z: float) -> None:
    assert _inverse_standard_normal_cdf(p) == pytest.approx(expected_z, abs=5e-6)


def test_inverse_normal_rejects_boundary_and_out_of_range_inputs() -> None:
    for p in (0.0, 1.0, -0.1, 1.1, 2.0):
        with pytest.raises(ValueError):
            _inverse_standard_normal_cdf(p)


# ---- Empirical band scaling factor ----------------------------------------


def test_perfectly_calibrated_returns_unit_scale() -> None:
    """When observed coverage matches the target, scale = 1.0 exactly."""

    assert _empirical_band_scale_factor(observed_coverage=0.80) == pytest.approx(1.0, abs=1e-10)


def test_under_coverage_returns_widening_scale_greater_than_one() -> None:
    """Observed = 65% (bands too narrow): scale ≈ z(0.90)/z(0.825) ≈ 1.37."""

    scale = _empirical_band_scale_factor(observed_coverage=0.65)
    assert scale > 1.0
    # Hand-computed: z(0.90)=1.2816, z(0.825)≈0.9346 → 1.371.
    z_target = _inverse_standard_normal_cdf(0.90)
    z_observed = _inverse_standard_normal_cdf((1 + 0.65) / 2)
    expected = z_target / z_observed
    assert scale == pytest.approx(expected, abs=1e-6)


def test_over_coverage_returns_narrowing_scale_less_than_one() -> None:
    """Observed = 92% (bands too wide): scale ≈ z(0.90)/z(0.96) ≈ 0.73."""

    scale = _empirical_band_scale_factor(observed_coverage=0.92)
    assert scale < 1.0
    z_target = _inverse_standard_normal_cdf(0.90)
    z_observed = _inverse_standard_normal_cdf((1 + 0.92) / 2)
    expected = z_target / z_observed
    assert scale == pytest.approx(expected, abs=1e-6)


def test_extreme_under_coverage_is_clamped_to_max() -> None:
    """Pathological case (observed = 5% inside the 80% band) — clamp
    saves σ from blowing up to ~5x."""

    scale = _empirical_band_scale_factor(observed_coverage=0.05)
    assert scale == BAND_SCALE_MAX


def test_extreme_over_coverage_is_clamped_to_min() -> None:
    """Pathological case (observed = 99% inside the 80% band) — clamp
    saves σ from collapsing the band to zero."""

    scale = _empirical_band_scale_factor(observed_coverage=0.99)
    assert scale == BAND_SCALE_MIN


def test_degenerate_zero_and_one_coverages_return_unit_scale() -> None:
    """Φ⁻¹ is undefined / infinite at the endpoints; the helper must
    not crash — it returns 1.0 (no scaling) so the caller's sample-
    size check is the only safety net needed at degenerate inputs."""

    assert _empirical_band_scale_factor(observed_coverage=0.0) == 1.0
    assert _empirical_band_scale_factor(observed_coverage=1.0) == 1.0


def test_custom_target_coverage_changes_scale_direction() -> None:
    """If the operator wants 90% bands instead of 80%, and observed
    coverage is 80%, the scale must be > 1 (widen)."""

    scale = _empirical_band_scale_factor(
        observed_coverage=0.80, target_coverage=0.90
    )
    assert scale > 1.0


def test_target_coverage_validation() -> None:
    for bad in (0.0, 1.0, -0.1, 1.1):
        with pytest.raises(ValueError):
            _empirical_band_scale_factor(
                observed_coverage=0.80, target_coverage=bad
            )


# ---- Integration: compute_baseline_forecast band scaling ------------------


def _series(prices: list[float]) -> list[HistoricalBar]:
    today = date(2026, 1, 1)
    return [
        HistoricalBar(
            bar_date=today - timedelta(days=len(prices) - i),
            close_price=Decimal(str(p)),
        )
        for i, p in enumerate(prices)
    ]


def _build_geometric_series(
    n: int, drift_daily: float, sigma_daily: float, seed: int
) -> list[float]:
    rng = random.Random(seed)
    prices = [100.0]
    for _ in range(n - 1):
        r = rng.gauss(drift_daily, sigma_daily)
        prices.append(prices[-1] * math.exp(r))
    return prices


def test_default_scale_factor_preserves_v1_behaviour() -> None:
    """band_scale_factor=1.0 must produce a forecast byte-identical
    to the legacy call without the param."""

    prices = _build_geometric_series(
        252, drift_daily=0.0005, sigma_daily=0.012, seed=1
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    legacy = compute_baseline_forecast(bars=bars, current_price=current)
    explicit = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=DEFAULT_BAND_SCALE_FACTOR
    )
    assert legacy.p10_price == explicit.p10_price
    assert legacy.p50_price == explicit.p50_price
    assert legacy.p90_price == explicit.p90_price
    assert legacy.expected_return_pct == explicit.expected_return_pct


def test_scale_factor_above_one_widens_band() -> None:
    prices = _build_geometric_series(
        252, drift_daily=0.0, sigma_daily=0.012, seed=2
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    unscaled = compute_baseline_forecast(bars=bars, current_price=current)
    widened = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=1.4
    )
    unscaled_width = float(unscaled.p90_price - unscaled.p10_price)
    widened_width = float(widened.p90_price - widened.p10_price)
    assert widened_width > unscaled_width


def test_scale_factor_below_one_narrows_band() -> None:
    prices = _build_geometric_series(
        252, drift_daily=0.0, sigma_daily=0.012, seed=3
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    unscaled = compute_baseline_forecast(bars=bars, current_price=current)
    narrowed = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=0.7
    )
    unscaled_width = float(unscaled.p90_price - unscaled.p10_price)
    narrowed_width = float(narrowed.p90_price - narrowed.p10_price)
    assert narrowed_width < unscaled_width


def test_scaled_band_p50_unchanged_only_width_moves() -> None:
    """The median (p50) is driven by drift_log, which the band scale
    doesn't touch. Only p10 and p90 should change."""

    prices = _build_geometric_series(
        252, drift_daily=0.0008, sigma_daily=0.012, seed=4
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    unscaled = compute_baseline_forecast(bars=bars, current_price=current)
    widened = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=1.5
    )
    assert widened.p50_price == unscaled.p50_price
    assert widened.expected_return_pct == unscaled.expected_return_pct
    assert widened.p10_price < unscaled.p10_price
    assert widened.p90_price > unscaled.p90_price


def test_scaled_band_widens_proportional_in_log_space() -> None:
    """The contract: ``ln(p90/p50) = scale · σ_annual · sqrt(T) · Z_90``.
    A scale of 1.5 must produce exactly 1.5x the log-width."""

    prices = _build_geometric_series(
        252, drift_daily=0.0, sigma_daily=0.015, seed=5
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    unscaled = compute_baseline_forecast(bars=bars, current_price=current)
    scale = 1.5
    widened = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=scale
    )
    unscaled_log_halfwidth = math.log(float(unscaled.p90_price) / float(unscaled.p50_price))
    widened_log_halfwidth = math.log(float(widened.p90_price) / float(widened.p50_price))
    assert widened_log_halfwidth == pytest.approx(scale * unscaled_log_halfwidth, rel=1e-6)


def test_out_of_range_scale_factor_raises() -> None:
    prices = _build_geometric_series(120, drift_daily=0.0, sigma_daily=0.01, seed=6)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))
    for bad in (BAND_SCALE_MIN - 0.01, BAND_SCALE_MAX + 0.01, 0.0, 10.0):
        with pytest.raises(ValueError):
            compute_baseline_forecast(
                bars=bars, current_price=current, band_scale_factor=bad
            )


def test_ito_correction_uses_unscaled_sigma() -> None:
    """The drift_log carries ``-0.5·σ²·T``. Band scaling must NOT enter
    this term — otherwise a widened band would also shift the median,
    double-counting the calibration adjustment. The p50 invariance
    test covers this implicitly; this test makes the contract
    explicit."""

    prices = _build_geometric_series(
        252, drift_daily=0.0, sigma_daily=0.020, seed=7
    )
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    a = compute_baseline_forecast(bars=bars, current_price=current, band_scale_factor=1.0)
    b = compute_baseline_forecast(bars=bars, current_price=current, band_scale_factor=2.0)
    # Same drift_log, same σ_annual → identical p50 and expected_return_pct.
    assert a.p50_price == b.p50_price
    assert a.expected_return_pct == b.expected_return_pct
    assert a.expected_volatility_annual == b.expected_volatility_annual


# ---- End-to-end calibration loop semantics --------------------------------


def test_under_calibrated_diary_widens_next_forecast_band() -> None:
    """The 'closes the loop' test: simulate a calibration diary that
    showed 60% coverage (bands historically too narrow). Apply the
    derived scale factor to the next forecast. The result must be a
    wider p10-p90 band than the unscaled forecast — and the width
    should match the empirical-z math exactly."""

    observed = 0.60
    scale = _empirical_band_scale_factor(observed_coverage=observed)
    assert scale > 1.0

    prices = _build_geometric_series(252, drift_daily=0.0, sigma_daily=0.014, seed=8)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    raw = compute_baseline_forecast(bars=bars, current_price=current)
    feedback = compute_baseline_forecast(
        bars=bars, current_price=current, band_scale_factor=scale
    )
    # Empirical band check: log half-width must scale by exactly `scale`.
    raw_lhw = math.log(float(raw.p90_price) / float(raw.p50_price))
    fb_lhw = math.log(float(feedback.p90_price) / float(feedback.p50_price))
    assert fb_lhw == pytest.approx(scale * raw_lhw, rel=1e-6)


def test_target_coverage_constant_is_eighty_percent() -> None:
    """The 80% target matches the standard Z_10/Z_90 (±1.2816) band.
    If anyone changes it, they must change the Z constants too."""

    assert DEFAULT_CALIBRATION_TARGET_COVERAGE == 0.80
    # The Z constants must agree with the target — 80% two-sided
    # interval ⇔ Z = Φ⁻¹(0.90).
    assert abs(_inverse_standard_normal_cdf(0.90) - Z_90) < 1e-8
    assert abs(-_inverse_standard_normal_cdf(0.90) - Z_10) < 1e-8
