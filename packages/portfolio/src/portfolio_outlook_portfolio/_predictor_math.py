"""Shared numpy-backed math primitives for the V1.1 predictors.

V1.1 §22.1 lock relaxes the heavy-dep boundary inside
`packages/portfolio`. This module centralises the log-return,
rolling-statistic, and normal-distribution primitives every
predictor needs. Callers stay pure-Python at the dataclass
boundary; numpy / pandas arrays never leak past the predictor.

Functions here are deterministic given the same inputs; no
randomness, no I/O, no datetime.now().
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import numpy as np
from scipy import stats

from .baseline_forecast import HistoricalBar


def bar_closes_array(bars: Sequence[HistoricalBar]) -> np.ndarray:
    """Return the close prices as a float64 numpy array.

    Returns an empty array when ``bars`` is empty. Decimal closes are
    cast to float — predictor math runs in float; Decimal stays at
    the dataclass boundary where money precision matters.
    """

    if not bars:
        return np.empty(0, dtype=np.float64)
    return np.asarray([float(bar.close_price) for bar in bars], dtype=np.float64)


def log_returns(prices: np.ndarray) -> np.ndarray:
    """Vectorised log-returns. Non-positive prices break the chain at
    the offending step; the rest of the series stays connected.

    Implementation: ``log(prices[1:] / prices[:-1])`` with non-positive
    guards. Returns an empty array when ``prices.size < 2`` or all
    consecutive pairs have a non-positive endpoint.
    """

    if prices.size < 2:
        return np.empty(0, dtype=np.float64)
    valid_mask = (prices[:-1] > 0) & (prices[1:] > 0)
    if not valid_mask.any():
        return np.empty(0, dtype=np.float64)
    valid_prev = prices[:-1][valid_mask]
    valid_curr = prices[1:][valid_mask]
    out: np.ndarray = np.log(valid_curr / valid_prev)
    return out


def sample_mean(values: np.ndarray) -> float:
    """Plain arithmetic mean. ``0.0`` for empty input."""

    if values.size == 0:
        return 0.0
    return float(values.mean())


def sample_stdev(values: np.ndarray) -> float:
    """Bessel-corrected sample standard deviation. ``0.0`` when there
    are fewer than two observations (matches the pre-V1.1 helper)."""

    if values.size < 2:
        return 0.0
    return float(values.std(ddof=1))


def population_stdev(values: np.ndarray) -> float:
    """Population standard deviation (ddof=0). Used by the Bollinger /
    Hurst paths that historically used the population SD."""

    if values.size == 0:
        return 0.0
    return float(values.std(ddof=0))


def normal_cdf(z: float) -> float:
    """Standard-normal CDF backed by scipy.stats."""

    return float(stats.norm.cdf(z))


# Quantile constants reused across predictors (z_α for α ∈ {0.1, 0.5, 0.9}).
Z_10: float = float(stats.norm.ppf(0.10))
Z_50: float = 0.0
Z_90: float = float(stats.norm.ppf(0.90))


def decimal_from_float(value: float, places: int = 6) -> Decimal:
    """Deterministic Decimal coercion for the float → Decimal boundary."""

    quant = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quant)


def clipped_probability(value: float) -> Decimal:
    """Coerce a float to a six-decimal probability in [0, 1]."""

    return decimal_from_float(max(0.0, min(1.0, value)), 6)


__all__ = [
    "Z_10",
    "Z_50",
    "Z_90",
    "bar_closes_array",
    "clipped_probability",
    "decimal_from_float",
    "log_returns",
    "normal_cdf",
    "population_stdev",
    "sample_mean",
    "sample_stdev",
]
