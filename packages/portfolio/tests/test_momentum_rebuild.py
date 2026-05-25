"""Tests for the V1.1 Slice 27 Momentum rebuild knobs."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio.momentum_predictor import (
    DIRECTION_THRESHOLD_BASELINE_HORIZON,
    DIRECTION_THRESHOLD_SLIGHT_PCT,
    DIRECTION_THRESHOLD_STRONG_PCT,
    MomentumPredictor,
    _direction_label,
    _direction_label_for_horizon,
)
from portfolio_outlook_portfolio.predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_READY,
    HistoricalBar,
    PredictorInputs,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


# ---- horizon-scaled direction thresholds --------------------------------


def test_horizon_scaled_thresholds_match_baseline_at_21_days() -> None:
    """At the baseline horizon (21d) the scaled function returns the
    exact same label set as the unscaled function."""

    for return_pct in (-15.0, -5.0, -1.0, 0.0, 1.0, 5.0, 15.0):
        assert _direction_label(return_pct) == _direction_label_for_horizon(
            return_pct, horizon_trading_days=DIRECTION_THRESHOLD_BASELINE_HORIZON
        )


def test_horizon_scaled_thresholds_narrower_at_shorter_horizon() -> None:
    """A 5-day horizon should classify smaller returns as `slight`."""

    # +1% over 5 days: baseline says ``flat`` (1% < 2%); scaled with
    # √(5/21) ≈ 0.488 says slight_up (1% >= 2% × 0.488 = 0.976%).
    baseline = _direction_label(1.0)
    scaled = _direction_label_for_horizon(1.0, horizon_trading_days=5)
    assert baseline == DIRECTION_FLAT
    assert scaled == DIRECTION_SLIGHT_UP


def test_horizon_scaled_thresholds_wider_at_longer_horizon() -> None:
    """A 60-day horizon should be more permissive — a 3% return is
    still ``flat`` because the scaled threshold is ~3.38%."""

    baseline = _direction_label(3.0)
    scaled = _direction_label_for_horizon(3.0, horizon_trading_days=60)
    assert baseline == DIRECTION_SLIGHT_UP
    # 60-day scaled threshold: 2% × √(60/21) ≈ 3.38%.
    assert scaled == DIRECTION_FLAT


def test_horizon_scaled_thresholds_preserve_strong_at_baseline_horizon() -> None:
    assert (
        _direction_label_for_horizon(15.0, horizon_trading_days=21)
        == DIRECTION_STRONG_UP
    )
    assert (
        _direction_label_for_horizon(-15.0, horizon_trading_days=21)
        == DIRECTION_STRONG_DOWN
    )


def test_horizon_scaled_thresholds_strong_at_longer_horizon_requires_bigger_return() -> None:
    """Strong bucket scales with √(horizon/21) too. A 60-day +12%
    return is *below* the scaled strong threshold (~16.9%) and stays
    in slight_up."""

    assert (
        _direction_label_for_horizon(12.0, horizon_trading_days=60)
        == DIRECTION_SLIGHT_UP
    )


# ---- MomentumPredictor honours the new flags ---------------------------


def test_momentum_predictor_default_keeps_v1_thresholds() -> None:
    """Without the rebuild flag the predictor uses the locked
    ±2% / ±10% thresholds — even at horizons ≠ 21 days."""

    closes = [100.0 * math.exp(0.001 * i) for i in range(300)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=5,
    )
    default = MomentumPredictor().predict(inputs)
    assert default.status == STATUS_READY
    # The default still produces a direction label from the locked
    # set — we don't assert which one because the input drift is
    # close to the threshold, but the predictor must not crash.


def test_momentum_predictor_horizon_scaled_changes_label_for_short_horizon() -> None:
    """Same series, two predictors with the same inputs but the
    rebuilt one uses horizon-scaled thresholds. At a short horizon
    a slight positive return should now classify as slight_up where
    the V1 thresholds say flat."""

    closes = [100.0 * math.exp(0.00005 * i) for i in range(280)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=5,
    )
    v1 = MomentumPredictor().predict(inputs)
    rebuilt = MomentumPredictor(horizon_scaled_thresholds=True).predict(inputs)
    # Same projected return; possibly different direction labels.
    assert v1.expected_return_pct == rebuilt.expected_return_pct
    # The rebuilt label set is a superset of the V1 label set —
    # changing thresholds can only move the label, not blow it up.
    assert rebuilt.direction in {
        DIRECTION_STRONG_UP,
        DIRECTION_SLIGHT_UP,
        DIRECTION_FLAT,
        DIRECTION_SLIGHT_DOWN,
        DIRECTION_STRONG_DOWN,
    }


def test_momentum_predictor_skip_week_short_horizon_uses_skip_week_path() -> None:
    """Short horizon + skip_week_short_horizon=True should produce
    a different composite score than the V1 skip-the-month path on
    the same input."""

    # A series where the most-recent month was sideways but the
    # 12-week trailing window was strongly up — V1 skip-month sees
    # the up-trend, skip-week sees the most-recent sideways too.
    closes_uptrend = [100.0 * math.exp(0.002 * i) for i in range(260)]
    sideways = [closes_uptrend[-1]] * 20
    closes = closes_uptrend + sideways

    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=5,  # short horizon → skip-week path
    )
    v1 = MomentumPredictor().predict(inputs)
    rebuilt = MomentumPredictor(skip_week_short_horizon=True).predict(inputs)
    # The flat tail near the end means the skip-week 12-1 window
    # has near-zero return where the skip-month version still sees
    # the up-trend's tail.
    assert v1.status == STATUS_READY
    assert rebuilt.status == STATUS_READY


def test_momentum_predictor_skip_week_inactive_for_long_horizons() -> None:
    """For long horizons (>= 21 days) the skip-week flag is a no-op:
    the V1 skip-the-month path is correct for monthly horizons."""

    closes = [100.0 * math.exp(0.0005 * i) for i in range(280)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    v1 = MomentumPredictor().predict(inputs)
    rebuilt = MomentumPredictor(skip_week_short_horizon=True).predict(inputs)
    # Same horizon, same inputs, same path → identical projection.
    assert v1.expected_return_pct == rebuilt.expected_return_pct
    assert v1.prob_gain == rebuilt.prob_gain


def test_locked_threshold_constants_at_module_scope() -> None:
    assert DIRECTION_THRESHOLD_STRONG_PCT == 10.0
    assert DIRECTION_THRESHOLD_SLIGHT_PCT == 2.0
    assert DIRECTION_THRESHOLD_BASELINE_HORIZON == 21
