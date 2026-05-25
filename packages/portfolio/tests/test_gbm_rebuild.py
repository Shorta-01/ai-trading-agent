"""Tests for the V1.1 Slice 27 GBM rebuild knobs.

The defaults preserve V1 behaviour exactly (verified by the
existing `test_baseline_forecast.py` + `test_predictor_protocol.py`).
This file covers only the opt-in rebuild paths.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.baseline_forecast import (
    DEFAULT_REGIME_SHIFT_THRESHOLD_PCT,
    HistoricalBar,
    compute_baseline_forecast,
)
from portfolio_outlook_portfolio.gbm_predictor import GbmPredictor
from portfolio_outlook_portfolio.predictor_protocol import (
    STATUS_READY,
    PredictorInputs,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def _two_regime_closes(
    *,
    n_before: int,
    n_after: int,
    drift_before: float,
    drift_after: float,
    seed_price: float = 100.0,
) -> list[float]:
    closes = [seed_price]
    for _ in range(n_before):
        closes.append(closes[-1] * math.exp(drift_before))
    for _ in range(n_after):
        closes.append(closes[-1] * math.exp(drift_after))
    return closes


# ---- drift_window_days ----------------------------------------------------


def test_drift_window_caps_drift_to_recent_segment() -> None:
    """A series with a 1-year up-trend followed by a recent
    1-year down-trend should produce a *more negative* drift when
    we cap the window to the recent year compared to the full
    2-year history."""

    closes = _two_regime_closes(
        n_before=252,
        n_after=252,
        drift_before=0.002,  # strong up
        drift_after=-0.002,  # strong down
    )
    bars = _bars(closes)

    full_history = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    recent_only = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        drift_window_days=252,
    )
    # With a 50/50 up+down split the full-history drift is ~zero;
    # the recent-window version sees only the down-trend.
    assert recent_only.expected_return_pct < full_history.expected_return_pct


def test_drift_window_explanation_mentions_the_cap() -> None:
    closes = [100.0 + 0.05 * i for i in range(400)]
    bars = _bars(closes)
    forecast = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        drift_window_days=252,
    )
    assert "252" in forecast.explanation_nl


def test_drift_window_no_op_when_history_shorter_than_window() -> None:
    """If the bar series is shorter than the cap, behaviour is
    identical to no cap."""

    closes = [100.0 + 0.05 * i for i in range(120)]
    bars = _bars(closes)
    capped = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        drift_window_days=252,
    )
    uncapped = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    assert capped.expected_return_pct == uncapped.expected_return_pct


# ---- regime_shift_enabled -------------------------------------------------


def test_regime_shift_inactive_when_divergence_below_threshold() -> None:
    """A steady up-trend has near-identical short and long drifts —
    the regime-shift blend should not fire."""

    closes = [100.0 * math.exp(0.0002 * i) for i in range(400)]
    bars = _bars(closes)
    f = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        regime_shift_enabled=True,
        regime_shift_threshold_pct=5.0,
    )
    assert "Regime-shift detector inactief" in f.explanation_nl


def test_regime_shift_active_blends_when_divergence_above_threshold() -> None:
    """A long up-trend followed by a sharp recent down-trend should
    trigger the 50/50 blend; the explanation must surface it."""

    closes = _two_regime_closes(
        n_before=300,
        n_after=60,
        drift_before=0.003,  # strong up
        drift_after=-0.003,  # strong down
    )
    bars = _bars(closes)
    f = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        regime_shift_enabled=True,
        regime_shift_threshold_pct=DEFAULT_REGIME_SHIFT_THRESHOLD_PCT,
    )
    assert "Regime-shift blend actief" in f.explanation_nl
    assert f.status == "ready"


def test_regime_shift_default_off_preserves_v1_behaviour() -> None:
    """Without the rebuild flags GBM still produces the exact V1
    drift — useful sanity check against accidental regressions."""

    closes = [100.0 * math.exp(0.0001 * i) for i in range(300)]
    bars = _bars(closes)
    baseline = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    explicit_default = compute_baseline_forecast(
        bars=bars,
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
        regime_shift_enabled=False,
        drift_window_days=None,
    )
    assert baseline.expected_return_pct == explicit_default.expected_return_pct


# ---- garch_enabled (defer marker) -----------------------------------------


def test_garch_enabled_raises_not_implemented_in_slice_27() -> None:
    closes = [100.0 + 0.1 * i for i in range(300)]
    with pytest.raises(NotImplementedError, match="garch_enabled"):
        compute_baseline_forecast(
            bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
            garch_enabled=True,
        )


# ---- GbmPredictor threads the knobs through ------------------------------


def test_gbm_predictor_accepts_rebuild_kwargs_and_passes_them_through() -> None:
    closes = _two_regime_closes(
        n_before=200, n_after=80, drift_before=0.003, drift_after=-0.003
    )
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    rebuilt = GbmPredictor(
        drift_window_days=252,
        regime_shift_enabled=True,
        regime_shift_threshold_pct=3.0,
    ).predict(inputs)
    v1 = GbmPredictor().predict(inputs)
    # Both ready, both have the same model_code — the difference is
    # only in the projected return.
    assert rebuilt.status == STATUS_READY
    assert v1.status == STATUS_READY
    assert rebuilt.model_code == v1.model_code
    # With a recent down-trend, the rebuilt path should project a
    # less-positive (or more-negative) return than the V1 baseline.
    assert rebuilt.expected_return_pct < v1.expected_return_pct


def test_gbm_predictor_garch_enabled_raises() -> None:
    closes = [100.0 + 0.1 * i for i in range(300)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    with pytest.raises(NotImplementedError):
        GbmPredictor(garch_enabled=True).predict(inputs)
