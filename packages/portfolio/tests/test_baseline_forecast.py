"""Tests for the baseline GBM forecast engine.

The forecaster is deterministic, so every test pins exact expectations rather
than approximations. Where a float ↔ Decimal conversion is involved we still
compare against tight numerical neighbourhoods (``≤ 1e-3``) so legitimate
rounding differences don't flake.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio.baseline_forecast import (
    DEFAULT_TRADING_DAYS_PER_YEAR,
    MINIMUM_BARS_REQUIRED,
    BaselineForecast,
    HistoricalBar,
    compute_baseline_forecast,
)


def _bars_from_closes(closes: list[float], start: date = date(2025, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(repr(c)))
        for i, c in enumerate(closes)
    ]


def _constant_growth_closes(initial: float, daily_return: float, n: int) -> list[float]:
    """Generate a series of closes with a constant daily simple return.
    For ``daily_return = 0.001`` that means each bar = previous × 1.001."""

    result = [initial]
    for _ in range(1, n):
        result.append(result[-1] * (1.0 + daily_return))
    return result


def _flat_closes(value: float, n: int) -> list[float]:
    return [value] * n


def _realistic_closes(
    *,
    initial: float,
    annual_drift: float,
    annual_sigma: float,
    n_bars: int,
    trading_days_per_year: int = 252,
) -> list[float]:
    """Deterministic synthetic series with the requested annualised moments.

    Uses a five-element cycle of fixed log returns. The cycle's mean and
    sample standard deviation match the requested drift and volatility, so
    the forecaster's recovered parameters are predictable enough for the
    test to make directional assertions without flaking on rounding.
    """

    mu_daily = annual_drift / trading_days_per_year
    sigma_daily = annual_sigma / math.sqrt(trading_days_per_year)
    # Five fixed offsets, mean 0, sample-σ = 1 (multiplied by sigma_daily).
    offsets = (1.4142, -1.4142, 0.7071, -0.7071, 0.0)
    if abs(sum(offsets)) > 1e-9:
        raise AssertionError("offsets must sum to zero")
    closes = [initial]
    for i in range(1, n_bars):
        log_return = mu_daily + sigma_daily * offsets[(i - 1) % 5]
        closes.append(closes[-1] * math.exp(log_return))
    return closes


def test_insufficient_history_returns_blocked_with_reason() -> None:
    bars = _bars_from_closes(_constant_growth_closes(100.0, 0.001, 5))

    result = compute_baseline_forecast(bars=bars, current_price=Decimal("100"))

    assert isinstance(result, BaselineForecast)
    assert result.status == "blocked"
    assert result.blocking_reason == "insufficient_history"
    assert result.direction_label == "blocked"
    assert result.confidence_score == Decimal("0.000000")


def test_invalid_current_price_returns_blocked() -> None:
    bars = _bars_from_closes(_constant_growth_closes(100.0, 0.001, MINIMUM_BARS_REQUIRED + 10))

    result = compute_baseline_forecast(bars=bars, current_price=Decimal("0"))

    assert result.status == "blocked"
    assert result.blocking_reason == "invalid_current_price"


def test_invalid_horizon_returns_blocked() -> None:
    bars = _bars_from_closes(_constant_growth_closes(100.0, 0.001, MINIMUM_BARS_REQUIRED + 10))

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal("100"), horizon_trading_days=0
    )

    assert result.status == "blocked"
    assert result.blocking_reason == "invalid_horizon"


def test_flat_history_blocks_with_zero_volatility_reason() -> None:
    bars = _bars_from_closes(_flat_closes(100.0, MINIMUM_BARS_REQUIRED + 20))

    result = compute_baseline_forecast(bars=bars, current_price=Decimal("100"))

    assert result.status == "blocked"
    assert result.blocking_reason == "zero_volatility"
    assert result.expected_volatility_annual == Decimal("0.000000")


def test_invalid_bar_price_blocks() -> None:
    closes = _constant_growth_closes(100.0, 0.001, MINIMUM_BARS_REQUIRED + 10)
    closes[5] = 0.0  # invalid mid-series
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(bars=bars, current_price=Decimal("100"))

    assert result.status == "blocked"
    assert result.blocking_reason == "invalid_bar_price"


def test_baseline_against_realistic_positive_drift_series() -> None:
    """Realistic 10% annual drift with 20% annual σ — gives roughly a 55–65%
    probability of gain over a one-month horizon, which is what a sensible
    GBM baseline should report."""

    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.10,
        annual_sigma=0.20,
        n_bars=MINIMUM_BARS_REQUIRED + 60,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    assert result.status == "ready"
    assert result.blocking_reason is None
    assert result.horizon_days == 21
    # Positive drift but vol still dominates over 21 days → gain probability
    # should be modestly above 0.5 but well below 0.9.
    assert Decimal("0.5") < result.prob_gain < Decimal("0.9")
    assert result.prob_loss + result.prob_gain == Decimal("1.000000") or abs(
        float(result.prob_loss) + float(result.prob_gain) - 1.0
    ) < 1e-3
    # Quantiles ordered: p10 < p50 < p90.
    assert result.p10_price < result.p50_price < result.p90_price
    # With realistic σ, p10 should also sit below current price.
    assert result.p10_price < result.current_price
    # Expected one-month return is positive and modest.
    assert Decimal("0") < result.expected_return_pct < Decimal("5")
    assert result.direction_label in {"slight_up", "neutral"}
    assert result.confidence_score > Decimal("0.4")
    # Recovered annual vol should be close to the requested 20%.
    assert Decimal("0.10") < result.expected_volatility_annual < Decimal("0.30")


def test_baseline_assigns_higher_loss_probability_for_falling_series() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=-0.10,
        annual_sigma=0.20,
        n_bars=MINIMUM_BARS_REQUIRED + 60,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    assert result.status == "ready"
    assert result.prob_loss > Decimal("0.55")
    assert result.expected_return_pct < Decimal("0")
    assert result.direction_label in {"slight_down", "neutral"}


def test_probabilities_sum_to_one_within_rounding() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.18,
        n_bars=MINIMUM_BARS_REQUIRED + 80,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    total = float(result.prob_gain) + float(result.prob_loss)
    assert abs(total - 1.0) < 1e-3


def test_threshold_probabilities_are_monotone() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.02,
        annual_sigma=0.20,
        n_bars=MINIMUM_BARS_REQUIRED + 80,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    # P(loss > 10%) <= P(loss > 5%) <= P(loss)
    assert result.prob_loss_gt_10pct <= result.prob_loss_gt_5pct <= result.prob_loss
    # P(gain > 10%) <= P(gain > 5%) <= P(gain)
    assert result.prob_gain_gt_10pct <= result.prob_gain_gt_5pct <= result.prob_gain


def test_history_window_metadata_is_recorded() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.15,
        n_bars=MINIMUM_BARS_REQUIRED + 30,
    )
    bars = _bars_from_closes(closes, start=date(2025, 1, 6))

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    assert result.status == "ready"
    assert result.history_first_bar_date == date(2025, 1, 6)
    assert result.history_last_bar_date == bars[-1].bar_date
    assert result.data_points_used == len(closes) - 1  # log returns count


def test_p10_p50_p90_relationship_to_current_price_with_positive_drift() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.08,
        annual_sigma=0.18,
        n_bars=MINIMUM_BARS_REQUIRED + 30,
    )
    bars = _bars_from_closes(closes)
    current = Decimal(repr(closes[-1]))

    result = compute_baseline_forecast(
        bars=bars, current_price=current, horizon_trading_days=21
    )

    assert result.status == "ready"
    # With realistic positive drift the median should be above current price.
    assert result.p50_price > current
    # And p10 still sits below current (left tail risk).
    assert result.p10_price < current
    # Downside risk = percentage drawdown to p10.
    expected_downside = (float(current) - float(result.p10_price)) / float(current) * 100.0
    assert math.isclose(
        float(result.downside_risk_score), expected_downside, abs_tol=1e-3
    )


def test_confidence_caps_at_one_year_sample_size() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.18,
        n_bars=DEFAULT_TRADING_DAYS_PER_YEAR + 200,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    assert result.status == "ready"
    assert result.confidence_score == Decimal("0.950000")


def test_explanation_is_dutch_and_mentions_horizon() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.18,
        n_bars=MINIMUM_BARS_REQUIRED + 30,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    assert "Baseline GBM" in result.explanation_nl
    assert "horizon 21 handelsdagen" in result.explanation_nl
    assert "Geen suggesties" in result.explanation_nl


def test_decimal_precision_is_preserved_in_outputs() -> None:
    closes = _realistic_closes(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.18,
        n_bars=MINIMUM_BARS_REQUIRED + 40,
    )
    bars = _bars_from_closes(closes)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal(repr(closes[-1])), horizon_trading_days=21
    )

    for value in (
        result.p10_price,
        result.p50_price,
        result.p90_price,
        result.expected_return_pct,
        result.expected_volatility_annual,
        result.downside_risk_score,
        result.confidence_score,
        result.prob_gain,
        result.prob_loss,
    ):
        assert isinstance(value, Decimal)


# ---- #2 risk-adjusted (Sharpe) direction labels --------------------------


def test_direction_label_falls_back_to_absolute_thresholds_without_volatility() -> None:
    """Legacy callers (tests with no volatility input) keep the V1
    ±2% / ±10% behavior so existing assertions don't break."""

    from portfolio_outlook_portfolio.baseline_forecast import _direction_label

    assert _direction_label(15.0) == ("strong_up", "Sterke stijging verwacht")
    assert _direction_label(5.0) == ("slight_up", "Lichte stijging verwacht")
    assert _direction_label(0.0) == ("neutral", "Geen duidelijke richting")
    assert _direction_label(-5.0) == ("slight_down", "Lichte daling verwacht")
    assert _direction_label(-15.0) == ("strong_down", "Duidelijke daling verwacht")


def test_direction_label_sharpe_penalises_volatile_assets() -> None:
    """A 10% expected return on a 5%-vol utility is a strong signal;
    the same 10% on a 60%-vol small-cap is noise. The V1 absolute
    thresholds called both 'strong_up'; the Sharpe path distinguishes."""

    from portfolio_outlook_portfolio.baseline_forecast import _direction_label

    # Low-vol utility — Sharpe ~ 10 / (5 * sqrt(30/252)*100/100) ≈ very high.
    low_vol = _direction_label(10.0, vol_annual=0.05, horizon_days=30)
    assert low_vol[0] == "strong_up"

    # High-vol small-cap — Sharpe ~ 10 / (60 * sqrt(30/252)) ≈ 0.48 → slight_up.
    high_vol = _direction_label(10.0, vol_annual=0.60, horizon_days=30)
    assert high_vol[0] == "slight_up"


def test_direction_label_sharpe_thresholds_at_buckets() -> None:
    """Lock the Sharpe bucket boundaries (1.0 strong, 0.3 slight) so
    re-tuning shows up in code review rather than silently shifting
    the system's recommendations."""

    from portfolio_outlook_portfolio.baseline_forecast import _direction_label

    # Construct inputs so the Sharpe lands at a known value.
    # vol_h_pct = vol_annual * 100 * sqrt(horizon_days/252).
    # With vol_annual=0.10, horizon=63 (~quarter): vol_h_pct = 10 * 0.5 = 5.
    # Then a 5%-expected-return → Sharpe = 1.0 → strong_up boundary.
    assert _direction_label(5.0, vol_annual=0.10, horizon_days=63)[0] == "strong_up"
    # And 1.5%-expected-return → Sharpe = 0.3 → slight_up boundary.
    assert (
        _direction_label(1.5, vol_annual=0.10, horizon_days=63)[0] == "slight_up"
    )
    # Below the slight boundary → neutral.
    assert (
        _direction_label(1.0, vol_annual=0.10, horizon_days=63)[0] == "neutral"
    )


def test_direction_label_sharpe_handles_zero_volatility_gracefully() -> None:
    """A zero-vol degenerate input should fall back to absolute
    thresholds rather than divide-by-zero."""

    from portfolio_outlook_portfolio.baseline_forecast import _direction_label

    assert _direction_label(15.0, vol_annual=0.0, horizon_days=30)[0] == "strong_up"
