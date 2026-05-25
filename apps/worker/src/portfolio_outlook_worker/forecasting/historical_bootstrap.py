"""Task 130: 252-day historical-bootstrap probabilistic forecast.

Pure function. The locked algorithm:

1. Take the last ``history_window_days`` daily closes (default 252).
2. Compute daily log-returns.
3. Slide ``horizon_days``-long overlapping windows of log-returns.
4. Bootstrap ``num_resamples`` (default 10 000) cumulative
   ``horizon_days`` log-returns using ``block_size``-day block
   resampling (default 5).
5. Return p10/p50/p90 + probabilities + annualized volatility.

Doctrine boundary: numpy float64 inside the bootstrap (we're
computing distribution summary stats, not money). Decimal at
every output where money is later derived.

Reproducibility: a seeded ``numpy.random.default_rng`` is used so
golden tests pin the output to the fourth decimal place.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from ai_trading_agent_storage import BootstrapInsufficientHistoryError

DEFAULT_HORIZON_DAYS = 20
DEFAULT_NUM_RESAMPLES = 10_000
DEFAULT_BLOCK_SIZE = 5
DEFAULT_HISTORY_WINDOW_DAYS = 252
MIN_CLOSES_FOR_FORECAST = 200
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BootstrapForecastResult:
    """Pure-Python summary of the bootstrap distribution."""

    history_closes_count: int
    horizon_days: int
    p10_log_return: Decimal
    p50_log_return: Decimal
    p90_log_return: Decimal
    prob_positive: Decimal
    prob_loss_gt_5pct: Decimal
    expected_volatility_annualized: Decimal


def compute_historical_bootstrap_forecast(
    *,
    daily_closes: list[Decimal],
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    num_resamples: int = DEFAULT_NUM_RESAMPLES,
    block_size: int = DEFAULT_BLOCK_SIZE,
    rng_seed: int | None = None,
) -> BootstrapForecastResult:
    """Compute the locked p10/p50/p90 + probabilities + volatility.

    Args:
        daily_closes: sorted-ascending list of Decimal closes.
            At least ``MIN_CLOSES_FOR_FORECAST`` rows required.
        horizon_days: locked at 20 trading days for V1.1.0.
        num_resamples: locked at 10 000 for V1.1.0.
        block_size: locked at 5 trading days for V1.1.0.
        rng_seed: optional seed for the numpy Generator so golden
            tests are deterministic. ``None`` uses the OS RNG.

    Raises:
        BootstrapInsufficientHistoryError: < 200 daily closes.
        ValueError: any negative close, horizon ≤ 0, block_size ≤ 0,
            or num_resamples ≤ 0.
    """

    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if num_resamples <= 0:
        raise ValueError("num_resamples must be positive")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if len(daily_closes) < MIN_CLOSES_FOR_FORECAST:
        raise BootstrapInsufficientHistoryError(
            f"need ≥{MIN_CLOSES_FOR_FORECAST} closes, "
            f"got {len(daily_closes)}"
        )
    if any(close < 0 for close in daily_closes):
        raise ValueError("daily_closes must all be non-negative")

    closes_arr = np.array([float(c) for c in daily_closes], dtype=np.float64)
    # Daily log-returns: r_t = ln(c_t / c_{t-1})
    log_returns = np.diff(np.log(closes_arr))
    if log_returns.size < horizon_days:
        raise BootstrapInsufficientHistoryError(
            f"need ≥{horizon_days} daily returns, got {log_returns.size}"
        )

    rng = np.random.default_rng(rng_seed)

    # Block-bootstrap horizon_days cumulative log-returns.
    # Pick blocks of ``block_size`` consecutive daily returns. Sum
    # blocks to assemble a horizon-length resampled return path; the
    # last block may be truncated so total length equals horizon_days.
    num_blocks_per_resample = math.ceil(horizon_days / block_size)
    max_block_start = log_returns.size - block_size
    if max_block_start <= 0:
        # Edge case: history exactly equals block_size; fall back to
        # single-day bootstrap.
        block_size = 1
        num_blocks_per_resample = horizon_days
        max_block_start = log_returns.size - 1

    resampled_cumulative = np.zeros(num_resamples, dtype=np.float64)
    for i in range(num_resamples):
        path = np.empty(horizon_days, dtype=np.float64)
        filled = 0
        for _ in range(num_blocks_per_resample):
            start = int(rng.integers(0, max_block_start + 1))
            remaining = horizon_days - filled
            take = min(block_size, remaining)
            path[filled : filled + take] = log_returns[start : start + take]
            filled += take
            if filled >= horizon_days:
                break
        resampled_cumulative[i] = path.sum()

    p10 = float(np.quantile(resampled_cumulative, 0.10))
    p50 = float(np.quantile(resampled_cumulative, 0.50))
    p90 = float(np.quantile(resampled_cumulative, 0.90))
    prob_pos = float(np.mean(resampled_cumulative > 0.0))
    prob_loss_gt_5 = float(np.mean(resampled_cumulative < math.log(1.0 - 0.05)))

    daily_std = float(np.std(log_returns, ddof=1))
    annualized_vol = daily_std * math.sqrt(TRADING_DAYS_PER_YEAR)

    return BootstrapForecastResult(
        history_closes_count=len(daily_closes),
        horizon_days=horizon_days,
        p10_log_return=Decimal(repr(p10)).quantize(Decimal("0.0000000001")),
        p50_log_return=Decimal(repr(p50)).quantize(Decimal("0.0000000001")),
        p90_log_return=Decimal(repr(p90)).quantize(Decimal("0.0000000001")),
        prob_positive=Decimal(repr(prob_pos)).quantize(Decimal("0.000001")),
        prob_loss_gt_5pct=Decimal(repr(prob_loss_gt_5)).quantize(
            Decimal("0.000001")
        ),
        expected_volatility_annualized=Decimal(repr(annualized_vol)).quantize(
            Decimal("0.00000001")
        ),
    )


__all__ = [
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_NUM_RESAMPLES",
    "DEFAULT_BLOCK_SIZE",
    "DEFAULT_HISTORY_WINDOW_DAYS",
    "MIN_CLOSES_FOR_FORECAST",
    "BootstrapForecastResult",
    "compute_historical_bootstrap_forecast",
]
