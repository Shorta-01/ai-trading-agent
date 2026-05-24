"""Tests for the deterministic mean-reversion predictor (Slice 15)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    MEAN_REVERSION_MIN_BARS,
    MEAN_REVERSION_MODEL_CODE,
    PREDICTOR_STATUS_BLOCKED,
    PREDICTOR_STATUS_READY,
    HistoricalBar,
    MeanReversionPredictor,
    PredictorInputs,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def test_blocks_on_short_history() -> None:
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * 50),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INSUFFICIENT_HISTORY


def test_blocks_on_invalid_horizon() -> None:
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0 + 0.1 * i for i in range(MEAN_REVERSION_MIN_BARS)]),
            current_price=Decimal("100"),
            horizon_trading_days=0,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_HORIZON


def test_blocks_on_invalid_current_price() -> None:
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0 + 0.1 * i for i in range(MEAN_REVERSION_MIN_BARS)]),
            current_price=Decimal("0"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_CURRENT_PRICE


def test_blocks_on_dead_flat_recent_history() -> None:
    closes = [100.0 + 0.05 * i for i in range(50)] + [105.0] * MEAN_REVERSION_MIN_BARS
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal("105"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_FLAT_HISTORY


def test_predicts_downside_when_price_is_far_above_sma_in_mean_reverting_series() -> None:
    """Build a noisy series oscillating around 100, then end with a
    sharp 1-bar spike. The 20-day SMA is still near 100, so the
    predictor should pull the price back down."""

    base = [100.0 + 5.0 * math.sin(i / 10) + 1.5 * math.cos(i / 3) for i in range(199)]
    closes = base + [120.0]
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal("120"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct < 0


def test_predicts_upside_when_price_is_far_below_sma_in_mean_reverting_series() -> None:
    base = [100.0 + 5.0 * math.sin(i / 10) + 1.5 * math.cos(i / 3) for i in range(199)]
    closes = base + [80.0]
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal("80"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct > 0


def test_signal_dampens_on_trending_series() -> None:
    """On a clear uptrend the Hurst exponent should be > 0.5, so the
    pull factor collapses toward zero. Even if RSI / Bollinger flag
    overbought, the predicted return must stay modest."""

    closes = [100.0 * math.exp(0.003 * i) for i in range(MEAN_REVERSION_MIN_BARS + 60)]
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    # The pull factor multiplies by the Hurst confidence which is near
    # zero for a trending series, so the predicted move shouldn't be
    # large in magnitude.
    assert abs(result.expected_return_pct) < Decimal("5.0")


def test_signal_is_flat_when_price_is_at_sma() -> None:
    closes = [100.0 + math.sin(i / 7) * 1.5 for i in range(200)]
    # Last bar is right around the 20-day mean (≈100).
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert abs(result.expected_return_pct) < Decimal("2.0")
    assert result.direction == DIRECTION_FLAT


def test_predictor_is_deterministic() -> None:
    closes = [100.0 + math.sin(i / 5) * 2 for i in range(200)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    a = MeanReversionPredictor().predict(inputs)
    b = MeanReversionPredictor().predict(inputs)
    assert a == b


def test_explanation_mentions_rsi_bollinger_hurst_pull() -> None:
    closes = [100.0 + math.sin(i / 5) * 4 for i in range(200)]
    result = MeanReversionPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    text = result.explanation_nl.lower()
    assert "rsi" in text
    assert "bollinger" in text
    assert "hurst" in text
    assert "pull" in text


def test_predictor_identity() -> None:
    pred = MeanReversionPredictor()
    assert pred.model_code == MEAN_REVERSION_MODEL_CODE
    assert pred.model_version
