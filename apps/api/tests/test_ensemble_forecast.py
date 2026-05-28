"""Tests for the ensemble forecast adapter + wiring."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from ai_trading_agent_storage import PredictorBacktestRunRecord
from portfolio_outlook_portfolio import (
    GbmPredictor,
    HistoricalBar,
    PredictorInputs,
    UniverseFundamentals,
    compute_baseline_forecast,
    compute_ensemble_forecast,
)
from portfolio_outlook_portfolio.baseline_forecast import _direction_label

from portfolio_outlook_api.ensemble_forecast import (
    ENSEMBLE_FORECAST_MODEL_CODE,
    adapt_ensemble_to_forecast_record,
    build_ensemble_predictors,
    derive_lognormal_metrics,
    ensemble_direction_label,
    latest_brier_by_model_code,
    run_ensemble_forecast,
)

_H = 20


def _synthetic_bars(n: int = 260) -> list[HistoricalBar]:
    start = date(2025, 1, 1)
    px = 100.0
    bars: list[HistoricalBar] = []
    for i in range(n):
        px *= math.exp(0.0004 + 0.01 * math.sin(i / 9.0))
        close = Decimal(repr(round(px, 6)))
        bars.append(
            HistoricalBar(bar_date=start + timedelta(days=i), close_price=close)
        )
    return bars


def _position():
    return SimpleNamespace(conid="265598", symbol="AAPL", currency="USD")


def _close(a: Decimal, b: Decimal, tol: float = 2e-3) -> bool:
    return abs(float(a) - float(b)) <= tol


# ---- label parity (guards against drift from the GBM vocabulary) -------


def test_direction_label_matches_baseline_across_grid() -> None:
    for pct in (-25.0, -10.0, -9.99, -2.0, -1.99, 0.0, 1.99, 2.0, 9.99, 10.0, 25.0):
        assert ensemble_direction_label(pct) == _direction_label(pct)


# ---- derive_lognormal_metrics matches the GBM oracle -------------------


def test_derived_metrics_match_single_gbm_ensemble() -> None:
    bars = _synthetic_bars()
    current = bars[-1].close_price
    base = compute_baseline_forecast(
        bars=bars, current_price=current, horizon_trading_days=_H
    )
    inputs = PredictorInputs(
        historical_bars=bars, current_price=current, horizon_trading_days=_H
    )
    ensemble = compute_ensemble_forecast([GbmPredictor()], inputs)
    f = ensemble.forecast
    assert f.status == "ready"
    # Quantiles pass straight through.
    assert f.p10_price == base.p10_price
    assert f.p50_price == base.p50_price
    assert f.p90_price == base.p90_price

    m = derive_lognormal_metrics(
        current_price=current,
        p10_price=f.p10_price,
        p50_price=f.p50_price,
        p90_price=f.p90_price,
        horizon_trading_days=_H,
    )
    assert _close(m.prob_loss, base.prob_loss)
    assert _close(m.prob_gain, base.prob_gain)
    assert _close(m.prob_loss_gt_5pct, base.prob_loss_gt_5pct)
    assert _close(m.prob_loss_gt_10pct, base.prob_loss_gt_10pct)
    assert _close(m.prob_gain_gt_5pct, base.prob_gain_gt_5pct)
    assert _close(m.prob_gain_gt_10pct, base.prob_gain_gt_10pct)
    assert _close(m.expected_volatility_annual, base.expected_volatility_annual, 5e-3)
    assert _close(m.downside_risk_score, base.downside_risk_score, 5e-3)


# ---- build_ensemble_predictors -----------------------------------------


def test_build_predictors_excludes_qvm_without_universe() -> None:
    predictors = build_ensemble_predictors(target_symbol="AAPL")
    codes = [p.model_code for p in predictors]
    assert len(predictors) == 3
    assert "baseline_gbm" in codes
    assert "momentum_v1" in codes
    assert "mean_reversion_v1" in codes


def test_build_predictors_includes_qvm_with_universe() -> None:
    predictors = build_ensemble_predictors(
        target_symbol="AAPL", qvm_universe=UniverseFundamentals(entries=())
    )
    assert len(predictors) == 4
    assert any(p.model_code == "qvm_factor_v1" for p in predictors)


# ---- adapt_ensemble_to_forecast_record ---------------------------------


def test_adapt_ready_produces_ensemble_record() -> None:
    bars = _synthetic_bars()
    current = bars[-1].close_price
    ensemble = run_ensemble_forecast(
        bars=bars,
        current_price=current,
        target_symbol="AAPL",
        sector=None,
        horizon_trading_days=_H,
    )
    now = datetime(2026, 5, 28, tzinfo=UTC)
    record = adapt_ensemble_to_forecast_record(
        position=_position(),
        ensemble=ensemble,
        current_price=current,
        bars=bars,
        horizon_trading_days=_H,
        generated_at=now,
        valid_until=now + timedelta(hours=1),
    )
    assert record.status == "ready"
    assert record.model_code == ENSEMBLE_FORECAST_MODEL_CODE
    assert record.symbol == "AAPL"
    assert record.p50_price == ensemble.forecast.p50_price
    assert Decimal("0") <= record.prob_gain <= Decimal("1")
    assert record.data_points_used == len(bars)


# ---- weighting ----------------------------------------------------------


def test_equal_weight_default_splits_evenly() -> None:
    bars = _synthetic_bars()
    current = bars[-1].close_price
    ensemble = run_ensemble_forecast(
        bars=bars,
        current_price=current,
        target_symbol="AAPL",
        sector=None,
        horizon_trading_days=_H,
    )
    weights = {c.model_code: c.weight_normalised for c in ensemble.contributions}
    assert len(weights) == 3
    for w in weights.values():
        assert abs(float(w) - 1 / 3) < 0.02


def test_auto_weighting_favours_lower_brier_predictor() -> None:
    bars = _synthetic_bars()
    current = bars[-1].close_price
    brier = {
        "baseline_gbm": Decimal("0.10"),  # best (lowest Brier)
        "momentum_v1": Decimal("0.25"),
        "mean_reversion_v1": Decimal("0.25"),
    }
    ensemble = run_ensemble_forecast(
        bars=bars,
        current_price=current,
        target_symbol="AAPL",
        sector=None,
        horizon_trading_days=_H,
        weight_strategy="auto",
        brier_history=brier,
    )
    weights = {c.model_code: c.weight_normalised for c in ensemble.contributions}
    assert len(weights) == 3
    # The best predictor gets the most weight; the 10%/40% bounds hold.
    assert weights["baseline_gbm"] > weights["momentum_v1"]
    assert weights["baseline_gbm"] > weights["mean_reversion_v1"]
    for w in weights.values():
        assert Decimal("0.10") <= w <= Decimal("0.40")
    assert abs(float(sum(weights.values())) - 1.0) < 1e-6


def _backtest_run(model_code: str, status: str, brier: str | None) -> PredictorBacktestRunRecord:
    return PredictorBacktestRunRecord(
        run_id=f"bt_{model_code}_{status}",
        model_code=model_code,
        model_version="v1.0.0",
        asset_symbol="AAPL",
        started_at=datetime(2026, 5, 28, tzinfo=UTC),
        finished_at=datetime(2026, 5, 28, tzinfo=UTC),
        status=status,
        window_days=252,
        bars_used=300,
        brier_score=Decimal(brier) if brier is not None else None,
        hit_rate=None,
        sharpe_ratio=None,
        blocking_reason=None,
        explanation_nl=None,
    )


def test_latest_brier_by_model_code_picks_newest_succeeded() -> None:
    # Records arrive most-recent-first. gbm: newest succeeded wins over older.
    # momentum: newest run is skipped → no history. mean_reversion: succeeded.
    records = [
        _backtest_run("baseline_gbm", "succeeded", "0.12"),
        _backtest_run("baseline_gbm", "succeeded", "0.30"),  # older, ignored
        _backtest_run("momentum_v1", "skipped", None),  # newest skipped → drop
        _backtest_run("momentum_v1", "succeeded", "0.20"),  # older, blocked by skip
        _backtest_run("mean_reversion_v1", "succeeded", "0.18"),
    ]
    brier = latest_brier_by_model_code(records)
    assert brier == {
        "baseline_gbm": Decimal("0.12"),
        "mean_reversion_v1": Decimal("0.18"),
    }


def test_adapt_blocked_ensemble_produces_blocked_record() -> None:
    bars = _synthetic_bars(5)  # too short → every predictor blocks
    current = bars[-1].close_price
    ensemble = run_ensemble_forecast(
        bars=bars,
        current_price=current,
        target_symbol="AAPL",
        sector=None,
        horizon_trading_days=_H,
    )
    assert ensemble.forecast.status != "ready"
    now = datetime(2026, 5, 28, tzinfo=UTC)
    record = adapt_ensemble_to_forecast_record(
        position=_position(),
        ensemble=ensemble,
        current_price=current,
        bars=bars,
        horizon_trading_days=_H,
        generated_at=now,
        valid_until=now + timedelta(hours=1),
    )
    assert record.status == "blocked"
    assert record.blocking_reason
    assert record.p50_price == current
