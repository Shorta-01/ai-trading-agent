"""Tests for the predictor protocol + GBM + momentum predictors (Slice 14)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    GBM_MODEL_CODE,
    MOMENTUM_MIN_BARS,
    MOMENTUM_MODEL_CODE,
    PREDICTOR_STATUS_BLOCKED,
    PREDICTOR_STATUS_READY,
    GbmPredictor,
    HistoricalBar,
    MomentumPredictor,
    PredictionDistribution,
    PredictorInputs,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


# ---- PredictionDistribution invariants --------------------------------


def test_distribution_rejects_blank_model_code() -> None:
    with pytest.raises(ValueError, match="model_code"):
        PredictionDistribution(
            model_code="",
            model_version="v1",
            horizon_trading_days=21,
            current_price=Decimal("100"),
            p10_price=Decimal("95"),
            p50_price=Decimal("100"),
            p90_price=Decimal("105"),
            prob_gain=Decimal("0.5"),
            prob_loss=Decimal("0.5"),
            expected_return_pct=Decimal("0"),
            direction=DIRECTION_FLAT,
            confidence_score=Decimal("0.5"),
            status=PREDICTOR_STATUS_READY,
        )


def test_distribution_rejects_non_positive_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_trading_days"):
        PredictionDistribution(
            model_code="m",
            model_version="v1",
            horizon_trading_days=0,
            current_price=Decimal("100"),
            p10_price=Decimal("95"),
            p50_price=Decimal("100"),
            p90_price=Decimal("105"),
            prob_gain=Decimal("0.5"),
            prob_loss=Decimal("0.5"),
            expected_return_pct=Decimal("0"),
            direction=DIRECTION_FLAT,
            confidence_score=Decimal("0.5"),
            status=PREDICTOR_STATUS_READY,
        )


def test_distribution_rejects_unknown_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        PredictionDistribution(
            model_code="m",
            model_version="v1",
            horizon_trading_days=21,
            current_price=Decimal("100"),
            p10_price=Decimal("95"),
            p50_price=Decimal("100"),
            p90_price=Decimal("105"),
            prob_gain=Decimal("0.5"),
            prob_loss=Decimal("0.5"),
            expected_return_pct=Decimal("0"),
            direction="moonshot",
            confidence_score=Decimal("0.5"),
            status=PREDICTOR_STATUS_READY,
        )


def test_distribution_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="status"):
        PredictionDistribution(
            model_code="m",
            model_version="v1",
            horizon_trading_days=21,
            current_price=Decimal("100"),
            p10_price=Decimal("95"),
            p50_price=Decimal("100"),
            p90_price=Decimal("105"),
            prob_gain=Decimal("0.5"),
            prob_loss=Decimal("0.5"),
            expected_return_pct=Decimal("0"),
            direction=DIRECTION_FLAT,
            confidence_score=Decimal("0.5"),
            status="thinking",
        )


# ---- GBM wrapper ------------------------------------------------------


def test_gbm_predictor_implements_protocol_and_returns_ready_on_clean_series() -> None:
    # A gently rising series with realistic noise.
    closes = [100.0 + i * 0.1 + math.sin(i / 7) for i in range(260)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    result = GbmPredictor().predict(inputs)
    assert result.model_code == GBM_MODEL_CODE
    assert result.status == PREDICTOR_STATUS_READY
    assert result.direction in {
        DIRECTION_STRONG_UP,
        DIRECTION_SLIGHT_UP,
        DIRECTION_FLAT,
        DIRECTION_SLIGHT_DOWN,
        DIRECTION_STRONG_DOWN,
    }
    assert result.p10_price < result.p50_price < result.p90_price


def test_gbm_predictor_returns_blocked_on_short_history() -> None:
    result = GbmPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * 10),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == "insufficient_history"
    # Even when blocked the direction is a locked label, not "blocked".
    assert result.direction == DIRECTION_FLAT


def test_gbm_predictor_returns_blocked_on_zero_price() -> None:
    result = GbmPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * 260),
            current_price=Decimal("0"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == "invalid_current_price"


# ---- Momentum predictor ------------------------------------------------


def test_momentum_predictor_blocks_when_history_is_too_short() -> None:
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * 50),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INSUFFICIENT_HISTORY


def test_momentum_predictor_blocks_when_horizon_is_invalid() -> None:
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * MOMENTUM_MIN_BARS),
            current_price=Decimal("100"),
            horizon_trading_days=0,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_HORIZON


def test_momentum_predictor_blocks_when_current_price_is_zero() -> None:
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars([100.0 + 0.5 * i for i in range(MOMENTUM_MIN_BARS)]),
            current_price=Decimal("0"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_CURRENT_PRICE


def test_momentum_predictor_blocks_on_dead_flat_recent_history() -> None:
    # 1 year of trend, then 6 perfectly flat months → zero recent
    # volatility → can't build a distribution.
    closes = [100.0 + 0.1 * i for i in range(150)] + [115.0] * 130
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal("115"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_FLAT_HISTORY


def test_momentum_predictor_signals_upside_on_persistent_uptrend() -> None:
    """A clear 12-month uptrend must produce a positive expected return
    and a prob_gain > 50%. At a 60-day horizon a max-momentum signal
    compounds enough to clear the ``slight_up`` direction threshold."""

    closes = [100.0 * math.exp(0.002 * i) * (1 + 0.001 * math.sin(i)) for i in range(280)]
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.direction in {DIRECTION_STRONG_UP, DIRECTION_SLIGHT_UP}
    assert result.expected_return_pct > 0
    assert result.prob_gain > Decimal("0.5")


def test_momentum_predictor_signals_downside_on_persistent_downtrend() -> None:
    closes = [100.0 * math.exp(-0.002 * i) * (1 + 0.001 * math.cos(i)) for i in range(280)]
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.direction in {DIRECTION_STRONG_DOWN, DIRECTION_SLIGHT_DOWN}
    assert result.expected_return_pct < 0
    assert result.prob_loss > Decimal("0.5")


def test_momentum_predictor_short_horizon_signal_can_still_be_flat() -> None:
    """The direction is *conservative by design*: even a max-momentum
    signal over a short horizon (21 days) may project below the
    ``slight_up`` threshold. The expected return must still be
    positive, prob_gain must still be > 50%."""

    closes = [100.0 * math.exp(0.002 * i) for i in range(280)]
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct > 0
    assert result.prob_gain > Decimal("0.5")


def test_momentum_predictor_returns_flat_or_near_flat_on_noisy_sideways_series() -> None:
    # No drift, just noise around 100.
    closes = [100.0 + 0.5 * math.sin(i / 3) for i in range(280)]
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    # On a sideways series the predicted drift should be small.
    assert abs(result.expected_return_pct) < Decimal("3.0")


def test_momentum_and_gbm_outputs_are_drop_in_interchangeable() -> None:
    """Both predictors must return the same dataclass shape so the
    ensemble combiner can treat them identically. We just need both
    results to be a ``PredictionDistribution`` with the same field
    set."""

    closes = [100.0 + 0.1 * i for i in range(280)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    gbm_result = GbmPredictor().predict(inputs)
    mom_result = MomentumPredictor().predict(inputs)
    assert type(gbm_result) is type(mom_result)
    assert gbm_result.model_code != mom_result.model_code
    # Same field set:
    assert set(vars(gbm_result).keys()) == set(vars(mom_result).keys())


def test_momentum_is_deterministic() -> None:
    closes = [100.0 + 0.05 * i for i in range(280)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    a = MomentumPredictor().predict(inputs)
    b = MomentumPredictor().predict(inputs)
    assert a == b


def test_momentum_explanation_mentions_score_and_horizon() -> None:
    closes = [100.0 + 0.1 * i for i in range(280)]
    result = MomentumPredictor().predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal(str(closes[-1])),
            horizon_trading_days=21,
        )
    )
    assert "composite score" in result.explanation_nl.lower()
    assert "21" in result.explanation_nl


def test_predictors_expose_their_model_identity() -> None:
    gbm = GbmPredictor()
    mom = MomentumPredictor()
    assert gbm.model_code == GBM_MODEL_CODE
    assert mom.model_code == MOMENTUM_MODEL_CODE
    assert gbm.model_version
    assert mom.model_version


# ---- V1.1 Slice 24: PredictorResearchProtocol + BacktestWindowScore ----


def test_backtest_window_score_is_a_value_object() -> None:
    from portfolio_outlook_portfolio.predictor_protocol import BacktestWindowScore

    score = BacktestWindowScore(
        model_code="momentum_v1",
        model_version="v1.0.0",
        window_days=90,
        bars_used=120,
        brier_score=0.18,
        hit_rate=0.56,
        sharpe_ratio=1.23,
        explanation_nl="walk-forward 90d Momentum",
    )
    assert score.model_code == "momentum_v1"
    assert score.window_days == 90
    assert score.brier_score == 0.18
    # Frozen dataclass: assignment raises FrozenInstanceError.
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        score.brier_score = 0.5  # type: ignore[misc]


def test_backtest_window_score_supports_none_metrics() -> None:
    from portfolio_outlook_portfolio.predictor_protocol import BacktestWindowScore

    score = BacktestWindowScore(
        model_code="momentum_v1",
        model_version="v1.0.0",
        window_days=90,
        bars_used=0,
        brier_score=None,
        hit_rate=None,
        sharpe_ratio=None,
    )
    assert score.brier_score is None
    assert score.hit_rate is None
    assert score.sharpe_ratio is None


def test_predictor_research_protocol_is_structural() -> None:
    """PredictorResearchProtocol is a Protocol; any object exposing
    `model_code`, `model_version`, `predict(...)`, and
    `backtest_window_score(...)` satisfies it. Slice 25 (backtesting
    framework) wires the real implementations; this test only proves
    the protocol shape."""

    from portfolio_outlook_portfolio.predictor_protocol import (
        BacktestWindowScore,
        PredictorResearchProtocol,
    )

    class _FakeResearchPredictor:
        @property
        def model_code(self) -> str:
            return "fake_research_v1"

        @property
        def model_version(self) -> str:
            return "v0.0.1"

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            raise NotImplementedError

        def backtest_window_score(
            self, inputs, *, window_days: int
        ) -> BacktestWindowScore:  # type: ignore[no-untyped-def]
            return BacktestWindowScore(
                model_code=self.model_code,
                model_version=self.model_version,
                window_days=window_days,
                bars_used=0,
                brier_score=None,
                hit_rate=None,
                sharpe_ratio=None,
                explanation_nl="stub",
            )

    fake: PredictorResearchProtocol = _FakeResearchPredictor()
    inputs = PredictorInputs(
        historical_bars=[],
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    score = fake.backtest_window_score(inputs, window_days=90)
    assert isinstance(score, BacktestWindowScore)
    assert score.window_days == 90
