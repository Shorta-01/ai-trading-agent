"""Tests for the V1.1 walk-forward backtester."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import HistoricalBar, PredictorInputs
from portfolio_outlook_portfolio.belgian_tax import TobSecurityClass
from portfolio_outlook_portfolio.gbm_predictor import GbmPredictor
from portfolio_outlook_portfolio.mean_reversion_predictor import (
    MeanReversionPredictor,
)
from portfolio_outlook_portfolio.momentum_predictor import MomentumPredictor
from portfolio_outlook_portfolio.predictor_backtester import (
    BacktestCostModel,
    aggregate_window_score,
    backtest_window_score_for_predictor,
    cost_model_for,
    new_backtest_run_id,
    run_predictor_backtest,
    walk_forward_backtest,
    walk_forward_score,
)
from portfolio_outlook_portfolio.predictor_protocol import (
    DIRECTION_FLAT,
    STATUS_BLOCKED,
    STATUS_READY,
    BacktestWindowScore,
    PredictionDistribution,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


# ---- input validation ----------------------------------------------------


def test_walk_forward_rejects_non_positive_window_days() -> None:
    with pytest.raises(ValueError, match="window_days"):
        walk_forward_backtest(GbmPredictor(), _bars([100.0] * 300), window_days=0)


def test_walk_forward_rejects_non_positive_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_trading_days"):
        walk_forward_backtest(
            GbmPredictor(), _bars([100.0] * 300), horizon_trading_days=0
        )


def test_walk_forward_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="step_days"):
        walk_forward_backtest(GbmPredictor(), _bars([100.0] * 300), step_days=0)


def test_walk_forward_returns_empty_when_bars_too_few() -> None:
    # Need >= window + horizon + 1 bars; here we have 30 vs default
    # 252 + 21 + 1.
    out = walk_forward_backtest(GbmPredictor(), _bars([100.0] * 30))
    assert out == ()


# ---- no-look-ahead invariant --------------------------------------------


def test_walk_forward_has_no_lookahead_per_fold() -> None:
    """Critical invariant: at each fold the predictor must only see
    bars[start:end], never beyond. We assert this by giving the
    predictor a spy that records the historical-bar-count it sees;
    the count must equal `window_days` for every fold."""

    seen_counts: list[int] = []

    class _SpyPredictor:
        model_code = "spy_v1"
        model_version = "v1.0.0"

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            seen_counts.append(len(inputs.historical_bars))
            return PredictionDistribution(
                model_code=self.model_code,
                model_version=self.model_version,
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                p10_price=inputs.current_price,
                p50_price=inputs.current_price,
                p90_price=inputs.current_price,
                prob_gain=Decimal("0.5"),
                prob_loss=Decimal("0.5"),
                expected_return_pct=Decimal("0"),
                direction=DIRECTION_FLAT,
                confidence_score=Decimal("0.5"),
                status=STATUS_READY,
            )

    bars = _bars([100.0 + 0.01 * i for i in range(400)])
    out = walk_forward_backtest(
        _SpyPredictor(), bars, window_days=200, horizon_trading_days=21, step_days=10
    )
    assert len(out) > 0
    # Every fold saw exactly 200 bars (no look-ahead).
    assert all(count == 200 for count in seen_counts)


def test_walk_forward_skips_blocked_predictions() -> None:
    """A predictor that always blocks yields zero folds — but no
    exception, no crash."""

    class _AlwaysBlock:
        model_code = "block_v1"
        model_version = "v1.0.0"

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            return PredictionDistribution(
                model_code=self.model_code,
                model_version=self.model_version,
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                p10_price=inputs.current_price,
                p50_price=inputs.current_price,
                p90_price=inputs.current_price,
                prob_gain=Decimal("0.5"),
                prob_loss=Decimal("0.5"),
                expected_return_pct=Decimal("0"),
                direction=DIRECTION_FLAT,
                confidence_score=Decimal("0"),
                status=STATUS_BLOCKED,
                blocking_reason="test",
            )

    out = walk_forward_backtest(
        _AlwaysBlock(),
        _bars([100.0 + 0.01 * i for i in range(400)]),
        window_days=200,
    )
    assert out == ()


def test_walk_forward_catches_predictor_exceptions() -> None:
    """A predictor that raises mid-batch is silently skipped per
    fold; the harness never crashes the whole run."""

    class _Boom:
        model_code = "boom_v1"
        model_version = "v1.0.0"

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            raise RuntimeError("kaboom")

    out = walk_forward_backtest(
        _Boom(),
        _bars([100.0 + 0.01 * i for i in range(400)]),
        window_days=200,
    )
    assert out == ()


# ---- aggregation --------------------------------------------------------


def test_aggregate_returns_none_metrics_with_too_few_folds() -> None:
    score = aggregate_window_score(
        predictor=GbmPredictor(),
        outcomes=(),
        window_days=200,
    )
    assert score.brier_score is None
    assert score.hit_rate is None
    assert score.sharpe_ratio is None
    assert score.bars_used == 0


def test_walk_forward_score_on_clean_uptrend_produces_reasonable_metrics() -> None:
    """End-to-end on a deterministic up-trending series: GBM should
    produce a finite Brier + hit-rate, and the hit-rate should beat
    random (≥ 0.5) because the realised direction is consistently up."""

    closes = [100.0 * math.exp(0.001 * i) for i in range(500)]
    score = walk_forward_score(
        GbmPredictor(),
        _bars(closes),
        window_days=250,
        horizon_trading_days=21,
        step_days=10,
    )
    assert score.brier_score is not None
    assert 0.0 <= score.brier_score <= 1.0
    assert score.hit_rate is not None
    assert score.hit_rate >= 0.5
    assert score.bars_used == 250


def test_walk_forward_score_explanation_mentions_predictor_code() -> None:
    closes = [100.0 + 0.05 * i for i in range(500)]
    score = walk_forward_score(
        GbmPredictor(),
        _bars(closes),
        window_days=250,
        horizon_trading_days=21,
        step_days=20,
    )
    assert "baseline_gbm" in score.explanation_nl


# ---- per-predictor research helper --------------------------------------


def test_backtest_window_score_for_predictor_returns_score() -> None:
    closes = [100.0 * math.exp(0.0005 * i) for i in range(500)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    score = backtest_window_score_for_predictor(
        GbmPredictor(), inputs, window_days=250
    )
    assert isinstance(score, BacktestWindowScore)
    assert score.model_code == "baseline_gbm"
    assert score.window_days == 250


def test_backtest_window_score_for_predictor_blocks_on_invalid_horizon() -> None:
    inputs = PredictorInputs(
        historical_bars=_bars([100.0] * 100),
        current_price=Decimal("100"),
        horizon_trading_days=0,
    )
    score = backtest_window_score_for_predictor(
        GbmPredictor(), inputs, window_days=50
    )
    assert score.brier_score is None
    assert score.hit_rate is None


# ---- run_predictor_backtest persistence shape ---------------------------


def test_run_predictor_backtest_marks_succeeded_when_metrics_exist() -> None:
    closes = [100.0 + 0.1 * i for i in range(500)]
    outputs = run_predictor_backtest(
        GbmPredictor(),
        _bars(closes),
        window_days=250,
        horizon_trading_days=21,
        step_days=10,
    )
    assert outputs.status == "succeeded"
    assert outputs.blocking_reason is None
    assert outputs.score.brier_score is not None


def test_run_predictor_backtest_marks_skipped_when_insufficient_folds() -> None:
    # Bars just below the (window + horizon + 1) minimum.
    closes = [100.0] * 30
    outputs = run_predictor_backtest(
        GbmPredictor(),
        _bars(closes),
        window_days=200,
        horizon_trading_days=21,
        step_days=10,
    )
    assert outputs.status == "skipped"
    assert outputs.blocking_reason == "insufficient_folds"


# ---- new_backtest_run_id ------------------------------------------------


def test_new_backtest_run_id_prefix() -> None:
    rid = new_backtest_run_id()
    assert rid.startswith("bt_")
    assert len(rid) > 5
    # Two consecutive calls yield distinct ids.
    assert new_backtest_run_id() != new_backtest_run_id()


# ---- PredictorResearchProtocol wired on each predictor ------------------


def test_each_predictor_implements_backtest_window_score() -> None:
    closes = [100.0 + 0.05 * i for i in range(500)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    for predictor in (
        GbmPredictor(),
        MomentumPredictor(),
        MeanReversionPredictor(),
    ):
        score = predictor.backtest_window_score(inputs, window_days=250)
        assert isinstance(score, BacktestWindowScore)
        assert score.window_days == 250
        assert score.model_code == predictor.model_code


# ---- transaction costs (predictor-lifecycle.md §1) ----------------------


def test_cost_model_round_trip_doubles_per_leg() -> None:
    model = BacktestCostModel(
        tob_rate_pct=0.35, commission_bps_per_fill=5.0, half_spread_bps=20.0
    )
    # 2 * (0.35 + 0.05 + 0.20) = 1.20
    assert model.round_trip_cost_pct() == pytest.approx(1.20)


def test_cost_model_for_liquid_etf_uses_5bps_half_spread() -> None:
    model = cost_model_for(
        security_class=TobSecurityClass.DISTRIBUTING_ETF, liquid=True
    )
    assert model.tob_rate_pct == pytest.approx(0.35)  # TOB_RATE_STANDARD
    assert model.half_spread_bps == pytest.approx(5.0)
    # 2 * (0.35 + 0.05 + 0.05) = 0.90
    assert model.round_trip_cost_pct() == pytest.approx(0.90)


def test_walk_forward_deducts_round_trip_costs() -> None:
    closes = [100.0 * math.exp(0.001 * i) for i in range(500)]
    outcomes = walk_forward_backtest(
        GbmPredictor(), _bars(closes), window_days=250, step_days=10
    )
    assert outcomes
    expected_cost = cost_model_for().round_trip_cost_pct()  # default stock model
    for fold in outcomes:
        assert fold.round_trip_cost_pct == pytest.approx(expected_cost)
        assert fold.realised_net_return_pct == pytest.approx(
            fold.realised_return_pct - expected_cost
        )
        assert fold.realised_net_return_pct < fold.realised_return_pct


def test_zero_cost_model_leaves_net_equal_gross() -> None:
    closes = [100.0 * math.exp(0.001 * i) for i in range(500)]
    zero = BacktestCostModel(
        tob_rate_pct=0.0, commission_bps_per_fill=0.0, half_spread_bps=0.0
    )
    outcomes = walk_forward_backtest(
        GbmPredictor(), _bars(closes), window_days=250, step_days=10, cost_model=zero
    )
    assert outcomes
    for fold in outcomes:
        assert fold.round_trip_cost_pct == pytest.approx(0.0)
        assert fold.realised_net_return_pct == pytest.approx(fold.realised_return_pct)


def test_costs_lower_net_sharpe_on_a_profitable_uptrend() -> None:
    closes = [100.0 * math.exp(0.001 * i) for i in range(500)]
    bars = _bars(closes)
    zero = BacktestCostModel(
        tob_rate_pct=0.0, commission_bps_per_fill=0.0, half_spread_bps=0.0
    )
    gross = aggregate_window_score(
        predictor=GbmPredictor(),
        outcomes=walk_forward_backtest(
            GbmPredictor(), bars, window_days=250, step_days=10, cost_model=zero
        ),
        window_days=250,
    )
    net = aggregate_window_score(
        predictor=GbmPredictor(),
        outcomes=walk_forward_backtest(
            GbmPredictor(), bars, window_days=250, step_days=10
        ),
        window_days=250,
    )
    assert gross.sharpe_ratio is not None
    assert net.sharpe_ratio is not None
    # Costs shift the mean return down without changing dispersion → lower Sharpe.
    assert net.sharpe_ratio < gross.sharpe_ratio
    # Brier is cost-independent (gross direction).
    assert net.brier_score == pytest.approx(gross.brier_score)
