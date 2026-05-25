"""Task 130 — historical bootstrap math tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from ai_trading_agent_storage import BootstrapInsufficientHistoryError

from portfolio_outlook_worker.forecasting.historical_bootstrap import (
    DEFAULT_HORIZON_DAYS,
    MIN_CLOSES_FOR_FORECAST,
    compute_historical_bootstrap_forecast,
)


def _flat_closes(*, count: int, price: Decimal = Decimal("100")) -> list[Decimal]:
    return [price] * count


def _monotonic_increase(*, count: int, daily_step_pct: Decimal = Decimal("0.001")) -> list[Decimal]:
    closes: list[Decimal] = [Decimal("100")]
    for _ in range(count - 1):
        closes.append(closes[-1] * (Decimal("1") + daily_step_pct))
    return closes


def _monotonic_decrease(*, count: int, daily_step_pct: Decimal = Decimal("0.001")) -> list[Decimal]:
    closes: list[Decimal] = [Decimal("100")]
    for _ in range(count - 1):
        closes.append(closes[-1] * (Decimal("1") - daily_step_pct))
    return closes


# ---- input validation --------------------------------------------


def test_rejects_short_history_with_typed_error() -> None:
    with pytest.raises(BootstrapInsufficientHistoryError):
        compute_historical_bootstrap_forecast(
            daily_closes=_flat_closes(count=100), rng_seed=42
        )


def test_rejects_negative_close() -> None:
    closes = _flat_closes(count=252)
    closes[10] = Decimal("-1")
    with pytest.raises(ValueError, match="non-negative"):
        compute_historical_bootstrap_forecast(
            daily_closes=closes, rng_seed=42
        )


def test_rejects_non_positive_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_days"):
        compute_historical_bootstrap_forecast(
            daily_closes=_flat_closes(count=252),
            horizon_days=0,
            rng_seed=42,
        )


def test_rejects_non_positive_num_resamples() -> None:
    with pytest.raises(ValueError, match="num_resamples"):
        compute_historical_bootstrap_forecast(
            daily_closes=_flat_closes(count=252),
            num_resamples=0,
            rng_seed=42,
        )


# ---- structural invariants ---------------------------------------


def test_quantile_ordering_p10_le_p50_le_p90() -> None:
    closes = _monotonic_increase(count=252)
    result = compute_historical_bootstrap_forecast(
        daily_closes=closes, rng_seed=42, num_resamples=2000
    )
    assert result.p10_log_return <= result.p50_log_return
    assert result.p50_log_return <= result.p90_log_return


def test_probabilities_within_unit_interval() -> None:
    result = compute_historical_bootstrap_forecast(
        daily_closes=_monotonic_increase(count=252),
        rng_seed=42,
        num_resamples=2000,
    )
    assert Decimal("0") <= result.prob_positive <= Decimal("1")
    assert Decimal("0") <= result.prob_loss_gt_5pct <= Decimal("1")


def test_history_close_count_reported_correctly() -> None:
    closes = _flat_closes(count=252)
    result = compute_historical_bootstrap_forecast(
        daily_closes=closes, rng_seed=42, num_resamples=500
    )
    assert result.history_closes_count == 252


def test_horizon_days_reported_correctly() -> None:
    result = compute_historical_bootstrap_forecast(
        daily_closes=_monotonic_increase(count=252),
        horizon_days=DEFAULT_HORIZON_DAYS,
        rng_seed=42,
        num_resamples=500,
    )
    assert result.horizon_days == DEFAULT_HORIZON_DAYS


# ---- edge-case directionality ------------------------------------


def test_flat_prices_produce_quantiles_near_zero() -> None:
    """A flat price series → returns are all zero → bootstrap is 0."""

    result = compute_historical_bootstrap_forecast(
        daily_closes=_flat_closes(count=252),
        rng_seed=42,
        num_resamples=2000,
    )
    # Every quantile is exactly 0 since all daily returns are 0.
    assert abs(result.p10_log_return) <= Decimal("0.0000000001")
    assert abs(result.p50_log_return) <= Decimal("0.0000000001")
    assert abs(result.p90_log_return) <= Decimal("0.0000000001")


def test_monotonic_increase_produces_positive_median() -> None:
    result = compute_historical_bootstrap_forecast(
        daily_closes=_monotonic_increase(count=252),
        rng_seed=42,
        num_resamples=2000,
    )
    assert result.p50_log_return > Decimal("0")
    assert result.prob_positive > Decimal("0.5")


def test_monotonic_decrease_produces_negative_median() -> None:
    result = compute_historical_bootstrap_forecast(
        daily_closes=_monotonic_decrease(count=252),
        rng_seed=42,
        num_resamples=2000,
    )
    assert result.p50_log_return < Decimal("0")
    assert result.prob_positive < Decimal("0.5")


def test_seeded_rng_produces_reproducible_output() -> None:
    closes = _monotonic_increase(count=252)
    a = compute_historical_bootstrap_forecast(
        daily_closes=closes, rng_seed=7, num_resamples=500
    )
    b = compute_historical_bootstrap_forecast(
        daily_closes=closes, rng_seed=7, num_resamples=500
    )
    assert a == b


def test_decimal_precision_preserved_in_output() -> None:
    closes = _flat_closes(count=252, price=Decimal("640.123456"))
    result = compute_historical_bootstrap_forecast(
        daily_closes=closes, rng_seed=42, num_resamples=500
    )
    # Quantize precision: 10 decimals for returns, 6 for probabilities,
    # 8 for volatility.
    assert isinstance(result.p10_log_return, Decimal)
    assert isinstance(result.prob_positive, Decimal)
    assert isinstance(result.expected_volatility_annualized, Decimal)
    # Flat series → vol is 0.
    assert result.expected_volatility_annualized == Decimal("0E-8")


def test_min_closes_threshold_is_200() -> None:
    """Exactly MIN_CLOSES_FOR_FORECAST should work."""

    result = compute_historical_bootstrap_forecast(
        daily_closes=_flat_closes(count=MIN_CLOSES_FOR_FORECAST),
        rng_seed=42,
        num_resamples=200,
    )
    assert result.history_closes_count == MIN_CLOSES_FOR_FORECAST
