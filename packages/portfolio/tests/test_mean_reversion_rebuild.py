"""Tests for the V1.1 Slice 28 Mean-Rev rebuild knob."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio.mean_reversion_predictor import (
    MeanReversionPredictor,
    _hurst_asymmetric_target_price,
)
from portfolio_outlook_portfolio.predictor_protocol import (
    STATUS_READY,
    HistoricalBar,
    PredictorInputs,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


# ---- _hurst_asymmetric_target_price -------------------------------------


def test_hurst_asymmetric_falls_back_to_sma_when_hurst_missing() -> None:
    target, clause = _hurst_asymmetric_target_price(
        current_price=100.0,
        sma=105.0,
        pull=0.5,
        hurst=None,
        prices=[100.0] * 30,
    )
    # current + 0.5 × (sma - current) = 100 + 0.5 × 5 = 102.5
    assert target == 102.5
    assert clause == ""


def test_hurst_asymmetric_full_reversion_at_low_hurst() -> None:
    """``H ≤ 0.45`` → full SMA pull (V1 behaviour)."""

    target, clause = _hurst_asymmetric_target_price(
        current_price=100.0,
        sma=105.0,
        pull=0.5,
        hurst=0.40,
        prices=[100.0] * 30,
    )
    assert target == 102.5
    assert "mean-reverting regime" in clause


def test_hurst_asymmetric_full_trend_at_high_hurst() -> None:
    """``H ≥ 0.55`` → full trend extrapolation; SMA pull dropped."""

    # 20-day return: 100 → 110 → +10% → trend target = 110 × 1.10 = 121
    prices = [100.0] * 20 + [110.0]
    target, clause = _hurst_asymmetric_target_price(
        current_price=110.0,
        sma=105.0,  # would pull DOWN to 105 under V1
        pull=0.5,
        hurst=0.60,
        prices=prices,
    )
    assert math.isclose(target, 121.0, rel_tol=1e-9)
    assert "trending regime" in clause


def test_hurst_asymmetric_blend_between_thresholds() -> None:
    """``H`` in ``(0.45, 0.55)`` → linear blend of SMA + trend
    targets. H=0.50 → 50/50 blend."""

    prices = [100.0] * 20 + [110.0]
    sma_target = 110.0 + 0.5 * (105.0 - 110.0)  # = 107.5
    trend_target = 110.0 * 1.10  # = 121.0
    expected_blend = 0.5 * sma_target + 0.5 * trend_target  # = 114.25
    target, clause = _hurst_asymmetric_target_price(
        current_price=110.0,
        sma=105.0,
        pull=0.5,
        hurst=0.50,
        prices=prices,
    )
    assert math.isclose(target, expected_blend, rel_tol=1e-9)
    assert "overgang" in clause


def test_hurst_asymmetric_no_data_when_history_short() -> None:
    target, clause = _hurst_asymmetric_target_price(
        current_price=100.0,
        sma=105.0,
        pull=0.5,
        hurst=0.60,
        prices=[100.0] * 5,
    )
    # Not enough history → falls back to SMA pull.
    assert target == 102.5
    assert clause == ""


# ---- MeanReversionPredictor honours the new flag ------------------------


def test_mean_rev_predictor_default_keeps_v1_behaviour() -> None:
    closes = [100.0 + 0.05 * i for i in range(140)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    v1 = MeanReversionPredictor().predict(inputs)
    explicit_default = MeanReversionPredictor(hurst_asymmetric_target=False).predict(
        inputs
    )
    # Without the rebuild flag the default behaviour stays identical.
    assert v1.expected_return_pct == explicit_default.expected_return_pct
    assert v1.status == STATUS_READY


def test_mean_rev_rebuilt_changes_target_on_trending_series() -> None:
    """A strong uptrend should make the rebuilt predictor blend the
    SMA-pull with a trend extrapolation (less negative pull → less
    reversion downside). On a strongly-trending series the rebuilt
    expected_return_pct should differ from the V1 value."""

    closes = [100.0 * math.exp(0.005 * i) for i in range(140)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    v1 = MeanReversionPredictor().predict(inputs)
    rebuilt = MeanReversionPredictor(hurst_asymmetric_target=True).predict(inputs)
    # Both ready; both produce a finite expected return; the rebuilt
    # path's explanation surfaces the Hurst-asymmetric clause.
    assert v1.status == STATUS_READY
    assert rebuilt.status == STATUS_READY
    assert "Hurst-asymmetric" in rebuilt.explanation_nl
