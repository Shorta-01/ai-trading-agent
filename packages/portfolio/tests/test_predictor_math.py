"""Tests for the V1.1 shared numpy-backed math primitives."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

import numpy as np

from portfolio_outlook_portfolio._predictor_math import (
    Z_10,
    Z_50,
    Z_90,
    bar_closes_array,
    clipped_probability,
    decimal_from_float,
    log_returns,
    normal_cdf,
    population_stdev,
    sample_mean,
    sample_stdev,
)
from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar


def _bar(d: int, close: str) -> HistoricalBar:
    return HistoricalBar(bar_date=date(2026, 1, d), close_price=Decimal(close))


def test_bar_closes_array_returns_float_array() -> None:
    bars = [_bar(1, "100"), _bar(2, "101.5"), _bar(3, "99.25")]
    arr = bar_closes_array(bars)
    assert arr.dtype == np.float64
    assert arr.tolist() == [100.0, 101.5, 99.25]


def test_bar_closes_array_empty_input() -> None:
    arr = bar_closes_array([])
    assert arr.size == 0
    assert arr.dtype == np.float64


def test_log_returns_matches_explicit_loop() -> None:
    prices = np.array([100.0, 110.0, 99.0, 121.0], dtype=np.float64)
    expected = np.array(
        [math.log(110 / 100), math.log(99 / 110), math.log(121 / 99)]
    )
    assert np.allclose(log_returns(prices), expected)


def test_log_returns_skips_non_positive_endpoints() -> None:
    prices = np.array([100.0, 0.0, 50.0, 60.0], dtype=np.float64)
    # The first two pairs (100→0 and 0→50) drop; only 50→60 survives.
    out = log_returns(prices)
    assert out.size == 1
    assert math.isclose(out[0], math.log(60 / 50))


def test_log_returns_too_short_input_returns_empty() -> None:
    assert log_returns(np.array([100.0])).size == 0
    assert log_returns(np.array([])).size == 0


def test_sample_mean_and_stdev_match_numpy_definitions() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert math.isclose(sample_mean(values), 3.0)
    # Sample SD (ddof=1) for 1..5 is √(10/4) = √2.5 ≈ 1.58113883
    assert math.isclose(sample_stdev(values), math.sqrt(2.5))


def test_sample_stdev_returns_zero_for_single_value() -> None:
    assert sample_stdev(np.array([42.0])) == 0.0


def test_population_stdev_differs_from_sample() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    # Population SD (ddof=0) = √(10/5) = √2
    assert math.isclose(population_stdev(values), math.sqrt(2.0))


def test_normal_cdf_known_values() -> None:
    assert math.isclose(normal_cdf(0.0), 0.5, abs_tol=1e-9)
    # Symmetric: cdf(z) + cdf(-z) == 1
    assert math.isclose(normal_cdf(1.0) + normal_cdf(-1.0), 1.0, abs_tol=1e-9)
    # cdf(1.96) ≈ 0.975
    assert math.isclose(normal_cdf(1.96), 0.975, abs_tol=1e-3)


def test_z_quantile_constants() -> None:
    # Z_10 ≈ -1.2816; Z_50 = 0; Z_90 ≈ 1.2816 (symmetric).
    assert math.isclose(Z_10, -Z_90, abs_tol=1e-9)
    assert Z_50 == 0.0
    assert -1.29 < Z_10 < -1.27


def test_decimal_from_float_six_places() -> None:
    d = decimal_from_float(0.123456789, places=6)
    assert d == Decimal("0.123457")


def test_clipped_probability_bounds() -> None:
    assert clipped_probability(-0.5) == Decimal("0.000000")
    assert clipped_probability(1.5) == Decimal("1.000000")
    assert clipped_probability(0.42) == Decimal("0.420000")
