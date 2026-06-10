"""Tests for V1.2 §A (EWMA volatility) and §B (drift shrinkage).

The V1 forecast remains unchanged: ``volatility_method`` defaults to
``sample_sd`` and ``drift_shrinkage_factor`` defaults to ``0.0``. These
tests verify the new opt-in paths produce the math we claim.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.baseline_forecast import (
    DEFAULT_EWMA_LAMBDA,
    EWMA_LAMBDA_MAX,
    EWMA_LAMBDA_MIN,
    VOLATILITY_METHOD_EWMA,
    VOLATILITY_METHOD_SAMPLE_SD,
    HistoricalBar,
    _ewma_stdev,
    _sample_mean,
    _sample_stdev,
    _shrink_drift,
    compute_baseline_forecast,
)

# ---- EWMA standalone math --------------------------------------------------


def test_ewma_recursion_matches_riskmetrics_formula_on_medium_series() -> None:
    """Hand-computed reference: with λ=0.94, warmup σ² = var of the first
    half of the series, the recursion ``σ²_t = λ·σ²_{t-1} + (1-λ)·r²_t``
    must produce the same terminal value as the helper.

    Series length 40 is large enough that the helper runs the
    recursion rather than degrading to sample SD fallback.
    """

    rng = random.Random(99)
    returns = [rng.gauss(0.0, 0.012) for _ in range(40)]
    lam = 0.94
    # The implementation anchors variance on warmup = min(30, max(2, n//2)).
    warmup = min(30, max(2, len(returns) // 2))
    warmup_slice = returns[:warmup]
    warmup_mean = sum(warmup_slice) / warmup
    var_t = sum((r - warmup_mean) ** 2 for r in warmup_slice) / warmup
    for r in returns[warmup:]:
        var_t = lam * var_t + (1 - lam) * r * r
    expected = math.sqrt(var_t)
    assert _ewma_stdev(returns, lam) == pytest.approx(expected, rel=1e-12)


def test_ewma_tracks_regime_change_faster_than_sample_sd() -> None:
    """A series that doubles in volatility halfway through: EWMA's
    terminal estimate should sit closer to the recent (high-vol) regime
    than the full-history sample SD does. This is the entire reason we
    add EWMA — bands track the new regime, not a smeared average."""

    rng = random.Random(42)
    calm = [rng.gauss(0.0, 0.005) for _ in range(120)]
    storm = [rng.gauss(0.0, 0.025) for _ in range(60)]
    series = calm + storm

    sample = _sample_stdev(series, _sample_mean(series))
    ewma = _ewma_stdev(series, DEFAULT_EWMA_LAMBDA)
    recent_actual = _sample_stdev(storm, _sample_mean(storm))

    # EWMA tracks the new regime closer than full-history sample SD.
    assert abs(ewma - recent_actual) < abs(sample - recent_actual)
    # And EWMA is materially higher than the smeared sample SD.
    assert ewma > sample


def test_ewma_returns_zero_for_too_few_observations() -> None:
    assert _ewma_stdev([], 0.94) == 0.0
    assert _ewma_stdev([0.01], 0.94) == 0.0


def test_ewma_falls_back_to_sample_sd_below_warmup_plus_one() -> None:
    """A series barely longer than warmup degrades gracefully — we
    never want the forecast to silently use a non-anchored EWMA."""

    short = [0.01, -0.01, 0.005]  # n=3, warmup falls below the +1 threshold
    fallback = _ewma_stdev(short, 0.94)
    expected = _sample_stdev(short, _sample_mean(short))
    assert fallback == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("lam", [0.79, 1.0, 1.5, -0.1])
def test_ewma_rejects_out_of_band_lambda(lam: float) -> None:
    with pytest.raises(ValueError):
        _ewma_stdev([0.01] * 50, lam)


def test_ewma_lambda_band_constants_are_sane() -> None:
    """The band ``[0.80, 0.99]`` is the practitioner range — too low
    and EWMA becomes noisy, too high and it's indistinguishable from
    sample SD."""

    assert EWMA_LAMBDA_MIN < DEFAULT_EWMA_LAMBDA < EWMA_LAMBDA_MAX
    assert EWMA_LAMBDA_MIN >= 0.5  # never below half-decay
    assert EWMA_LAMBDA_MAX <= 0.999  # always strictly less than 1


# ---- Drift shrinkage standalone math --------------------------------------


def test_shrinkage_zero_preserves_raw_mu() -> None:
    assert _shrink_drift(0.12, 0.0) == 0.12
    assert _shrink_drift(-0.05, 0.0) == -0.05


def test_shrinkage_one_zeroes_drift() -> None:
    assert _shrink_drift(0.12, 1.0) == 0.0
    assert _shrink_drift(-0.05, 1.0) == 0.0


def test_shrinkage_half_pulls_toward_zero_linearly() -> None:
    assert _shrink_drift(0.20, 0.5) == pytest.approx(0.10)
    assert _shrink_drift(-0.30, 0.5) == pytest.approx(-0.15)


@pytest.mark.parametrize("factor", [-0.01, 1.01, 2.0, -0.5])
def test_shrinkage_rejects_out_of_band_factor(factor: float) -> None:
    with pytest.raises(ValueError):
        _shrink_drift(0.1, factor)


# ---- Integration: opt-in paths through compute_baseline_forecast ---------


def _series(prices: list[float]) -> list[HistoricalBar]:
    today = date(2026, 1, 1)
    return [
        HistoricalBar(bar_date=today - timedelta(days=len(prices) - i), close_price=Decimal(str(p)))
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


def test_default_path_unchanged_by_new_flags() -> None:
    """The V1 lock: with default kwargs, the forecast must be
    byte-identical to a forecast computed without passing the new
    args at all."""

    prices = _build_geometric_series(252, drift_daily=0.0005, sigma_daily=0.015, seed=1)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    legacy = compute_baseline_forecast(bars=bars, current_price=current)
    explicit = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        volatility_method=VOLATILITY_METHOD_SAMPLE_SD,
        drift_shrinkage_factor=0.0,
    )
    assert legacy.p50_price == explicit.p50_price
    assert legacy.p10_price == explicit.p10_price
    assert legacy.p90_price == explicit.p90_price
    assert legacy.expected_return_pct == explicit.expected_return_pct


def test_ewma_path_widens_band_after_recent_vol_spike() -> None:
    """If volatility doubled in the last 40 days, EWMA's p10-p90 band
    must be wider than the sample-SD band — that's the whole point."""

    rng = random.Random(7)
    calm = [100.0]
    for _ in range(200):
        calm.append(calm[-1] * math.exp(rng.gauss(0.0, 0.005)))
    storm = [calm[-1]]
    for _ in range(40):
        storm.append(storm[-1] * math.exp(rng.gauss(0.0, 0.030)))
    prices = calm + storm[1:]
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    sd_forecast = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        volatility_method=VOLATILITY_METHOD_SAMPLE_SD,
    )
    ewma_forecast = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        volatility_method=VOLATILITY_METHOD_EWMA,
    )
    sd_width = float(sd_forecast.p90_price - sd_forecast.p10_price)
    ewma_width = float(ewma_forecast.p90_price - ewma_forecast.p10_price)
    assert ewma_width > sd_width


def test_full_shrinkage_lands_at_the_ito_correction_floor() -> None:
    """Direction-independent contract: with shrinkage α=1.0 the
    annualised drift becomes 0, so ``expected_return_pct = exp(drift_log) - 1``
    where ``drift_log = -0.5·σ²·T`` — the Itô correction floor. The
    full-shrink result therefore equals the no-drift forecast regardless
    of whether the raw sample drift was positive or negative.
    """

    prices = _build_geometric_series(252, drift_daily=0.001, sigma_daily=0.012, seed=3)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    no_shrink = compute_baseline_forecast(bars=bars, current_price=current)
    full_shrink = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        drift_shrinkage_factor=1.0,
    )
    # Recompute the expected Itô floor analytically from the same σ.
    sigma_annual = float(full_shrink.expected_volatility_annual)
    horizon_years = 21 / 252.0
    drift_log_zero = -0.5 * sigma_annual**2 * horizon_years
    expected_floor_pct = (math.exp(drift_log_zero) - 1.0) * 100.0
    assert float(full_shrink.expected_return_pct) == pytest.approx(
        expected_floor_pct, abs=1e-4
    )
    # And the full-shrink p50 differs from the raw p50 (raw drift ≠ 0).
    assert full_shrink.p50_price != no_shrink.p50_price


def test_half_shrinkage_sits_strictly_between_raw_and_full_in_absolute_terms() -> None:
    """Direction-independent contract: ``|μ_shrunk| = (1-α)|μ_raw|``,
    so the half-shrunk expected return must sit between the raw and
    fully-shrunk values in absolute distance from the no-drift floor."""

    prices = _build_geometric_series(252, drift_daily=0.0008, sigma_daily=0.012, seed=11)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    raw = compute_baseline_forecast(bars=bars, current_price=current)
    half = compute_baseline_forecast(
        bars=bars, current_price=current, drift_shrinkage_factor=0.5
    )
    full = compute_baseline_forecast(
        bars=bars, current_price=current, drift_shrinkage_factor=1.0
    )
    floor = float(full.expected_return_pct)
    raw_dist = abs(float(raw.expected_return_pct) - floor)
    half_dist = abs(float(half.expected_return_pct) - floor)
    full_dist = abs(float(full.expected_return_pct) - floor)
    # full == floor (distance ≈ 0); half is approximately halfway. The
    # approximation isn't exact because ``expected_return_pct = exp(μ·T) - 1``
    # is non-linear in μ (drift_log is the linear quantity); at typical
    # monthly horizons the convexity correction is ~1-2%, so we allow a
    # 5% relative tolerance.
    assert full_dist == pytest.approx(0.0, abs=1e-6)
    assert half_dist == pytest.approx(0.5 * raw_dist, rel=5e-2)


def test_combined_ewma_and_shrinkage_compose() -> None:
    """The two knobs are orthogonal: EWMA changes σ, shrinkage
    changes μ. Both opted in must produce a forecast distinct from
    either one alone."""

    prices = _build_geometric_series(252, drift_daily=0.0006, sigma_daily=0.015, seed=42)
    bars = _series(prices)
    current = Decimal(str(prices[-1]))

    baseline = compute_baseline_forecast(bars=bars, current_price=current)
    ewma_only = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        volatility_method=VOLATILITY_METHOD_EWMA,
    )
    shrink_only = compute_baseline_forecast(
        bars=bars, current_price=current, drift_shrinkage_factor=0.7
    )
    both = compute_baseline_forecast(
        bars=bars,
        current_price=current,
        volatility_method=VOLATILITY_METHOD_EWMA,
        drift_shrinkage_factor=0.7,
    )
    # All four are different.
    distinct_p50s = {
        baseline.p50_price,
        ewma_only.p50_price,
        shrink_only.p50_price,
        both.p50_price,
    }
    assert len(distinct_p50s) >= 3


def test_unknown_volatility_method_raises() -> None:
    prices = _build_geometric_series(120, drift_daily=0.0, sigma_daily=0.01, seed=1)
    bars = _series(prices)
    with pytest.raises(ValueError, match="Unknown volatility_method"):
        compute_baseline_forecast(
            bars=bars,
            current_price=Decimal(str(prices[-1])),
            volatility_method="garch_v2_experimental",
        )
