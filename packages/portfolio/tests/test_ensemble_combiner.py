"""Tests for the deterministic ensemble combiner (Slice 15)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    ENSEMBLE_MODEL_CODE,
    PREDICTOR_STATUS_BLOCKED,
    PREDICTOR_STATUS_READY,
    GbmPredictor,
    HistoricalBar,
    MeanReversionPredictor,
    MomentumPredictor,
    PredictionDistribution,
    PredictorInputs,
    compute_ensemble_forecast,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def _flat_prediction(
    *,
    model_code: str,
    expected_return_pct: str,
    direction: str = DIRECTION_FLAT,
    p10: str = "95",
    p50: str = "100",
    p90: str = "105",
    prob_gain: str = "0.5",
    confidence: str = "0.7",
    status: str = PREDICTOR_STATUS_READY,
    blocking_reason: str | None = None,
) -> PredictionDistribution:
    return PredictionDistribution(
        model_code=model_code,
        model_version="v1",
        horizon_trading_days=21,
        current_price=Decimal("100"),
        p10_price=Decimal(p10),
        p50_price=Decimal(p50),
        p90_price=Decimal(p90),
        prob_gain=Decimal(prob_gain),
        prob_loss=Decimal("1") - Decimal(prob_gain),
        expected_return_pct=Decimal(expected_return_pct),
        direction=direction,
        confidence_score=Decimal(confidence),
        status=status,
        blocking_reason=blocking_reason,
        explanation_nl="test",
    )


class _StaticPredictor:
    def __init__(self, prediction: PredictionDistribution) -> None:
        self._prediction = prediction

    @property
    def model_code(self) -> str:
        return self._prediction.model_code

    @property
    def model_version(self) -> str:
        return self._prediction.model_version

    def predict(self, _inputs: PredictorInputs) -> PredictionDistribution:
        return self._prediction


_BASIC_INPUTS = PredictorInputs(
    historical_bars=(),
    current_price=Decimal("100"),
    horizon_trading_days=21,
)


# ---- edge cases ----------------------------------------------------------


def test_empty_predictor_list_yields_blocked_ensemble() -> None:
    result = compute_ensemble_forecast([], _BASIC_INPUTS)
    assert result.forecast.status == PREDICTOR_STATUS_BLOCKED
    assert result.forecast.blocking_reason == "no_predictors"
    assert result.contributions == ()


def test_all_blocked_predictors_yield_blocked_ensemble() -> None:
    blocked = _flat_prediction(
        model_code="a",
        expected_return_pct="0",
        status=PREDICTOR_STATUS_BLOCKED,
        blocking_reason="insufficient_history",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(blocked), _StaticPredictor(blocked)], _BASIC_INPUTS
    )
    assert result.forecast.status == PREDICTOR_STATUS_BLOCKED
    assert result.forecast.blocking_reason == "all_predictors_blocked"
    assert "a" in result.blocked_model_codes
    assert result.contributions == ()


def test_blocked_predictor_is_excluded_but_logged() -> None:
    ready = _flat_prediction(
        model_code="ready",
        expected_return_pct="3",
        direction=DIRECTION_SLIGHT_UP,
        prob_gain="0.6",
    )
    blocked = _flat_prediction(
        model_code="blocked",
        expected_return_pct="0",
        status=PREDICTOR_STATUS_BLOCKED,
        blocking_reason="insufficient_history",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(ready), _StaticPredictor(blocked)], _BASIC_INPUTS
    )
    assert result.forecast.status == PREDICTOR_STATUS_READY
    assert "blocked" in result.blocked_model_codes
    assert len(result.contributions) == 1
    assert result.contributions[0].model_code == "ready"


# ---- weighting -----------------------------------------------------------


def test_default_equal_weight_averages_two_ready_predictors() -> None:
    a = _flat_prediction(
        model_code="a",
        expected_return_pct="4",
        direction=DIRECTION_SLIGHT_UP,
        prob_gain="0.6",
    )
    b = _flat_prediction(
        model_code="b",
        expected_return_pct="2",
        direction=DIRECTION_SLIGHT_UP,
        prob_gain="0.55",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)], _BASIC_INPUTS
    )
    assert result.forecast.expected_return_pct == Decimal("3.000000")
    assert result.forecast.prob_gain == Decimal("0.575000")
    assert result.forecast.direction == DIRECTION_SLIGHT_UP
    # Equal weights → normalised 0.5 each.
    assert all(c.weight_normalised == Decimal("0.5") for c in result.contributions)


def test_custom_weights_are_applied_and_normalised() -> None:
    a = _flat_prediction(
        model_code="a", expected_return_pct="6", direction=DIRECTION_SLIGHT_UP
    )
    b = _flat_prediction(
        model_code="b", expected_return_pct="2", direction=DIRECTION_SLIGHT_UP
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)],
        _BASIC_INPUTS,
        weights={"a": Decimal("3"), "b": Decimal("1")},
    )
    # Weighted average: (6*3 + 2*1) / 4 = 5
    assert result.forecast.expected_return_pct == Decimal("5.000000")
    weights = {c.model_code: c.weight_normalised for c in result.contributions}
    assert weights["a"] == Decimal("0.75")
    assert weights["b"] == Decimal("0.25")


def test_missing_weight_entry_defaults_to_1() -> None:
    a = _flat_prediction(model_code="a", expected_return_pct="4", direction=DIRECTION_SLIGHT_UP)
    b = _flat_prediction(model_code="b", expected_return_pct="2", direction=DIRECTION_SLIGHT_UP)
    # Only a has a weight specified; b defaults to 1.0.
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)],
        _BASIC_INPUTS,
        weights={"a": Decimal("1")},
    )
    weights = {c.model_code: c.weight_normalised for c in result.contributions}
    assert weights["a"] == Decimal("0.5")
    assert weights["b"] == Decimal("0.5")


def test_zero_weight_falls_back_to_1() -> None:
    a = _flat_prediction(model_code="a", expected_return_pct="4", direction=DIRECTION_SLIGHT_UP)
    result = compute_ensemble_forecast(
        [_StaticPredictor(a)],
        _BASIC_INPUTS,
        weights={"a": Decimal("0")},
    )
    assert result.forecast.expected_return_pct == Decimal("4.000000")


# ---- direction + agreement ----------------------------------------------


def test_agreement_factor_full_when_all_predictors_agree() -> None:
    pred = _flat_prediction(
        model_code="x",
        expected_return_pct="5",
        direction=DIRECTION_SLIGHT_UP,
        confidence="0.6",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(pred), _StaticPredictor(pred), _StaticPredictor(pred)],
        _BASIC_INPUTS,
    )
    # Agreement factor 1.0 → combined confidence = base confidence 0.6.
    assert result.forecast.confidence_score == Decimal("0.600000")


def test_agreement_factor_dampens_confidence_on_split_directions() -> None:
    up = _flat_prediction(
        model_code="up",
        expected_return_pct="6",
        direction=DIRECTION_SLIGHT_UP,
        confidence="0.8",
    )
    down = _flat_prediction(
        model_code="down",
        expected_return_pct="-6",
        direction=DIRECTION_SLIGHT_DOWN,
        confidence="0.8",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(up), _StaticPredictor(down)], _BASIC_INPUTS
    )
    # Base confidence 0.8 × agreement 0.4 = 0.32
    assert result.forecast.confidence_score == Decimal("0.320000")


def test_direction_label_derives_from_combined_expected_return() -> None:
    up = _flat_prediction(model_code="a", expected_return_pct="12", direction=DIRECTION_STRONG_UP)
    down = _flat_prediction(
        model_code="b",
        expected_return_pct="-6",
        direction=DIRECTION_SLIGHT_DOWN,
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(up), _StaticPredictor(down)], _BASIC_INPUTS
    )
    # Combined return = 3 → slight_up
    assert result.forecast.direction == DIRECTION_SLIGHT_UP


# ---- integration with real predictors -----------------------------------


def test_real_predictors_combine_on_an_uptrending_series() -> None:
    closes = [100.0 * math.exp(0.001 * i) * (1 + 0.0005 * math.sin(i)) for i in range(280)]
    inputs = PredictorInputs(
        historical_bars=_bars(closes),
        current_price=Decimal(str(closes[-1])),
        horizon_trading_days=21,
    )
    result = compute_ensemble_forecast(
        [GbmPredictor(), MomentumPredictor(), MeanReversionPredictor()], inputs
    )
    assert result.forecast.status == PREDICTOR_STATUS_READY
    assert result.forecast.model_code == ENSEMBLE_MODEL_CODE
    assert len(result.contributions) >= 1
    # The contributions all have valid normalised weights summing to ~1.0
    # (Decimal-division can leave a sub-femto residue).
    total = sum(c.weight_normalised for c in result.contributions)
    assert abs(total - Decimal("1.0")) < Decimal("0.0000000001")


def test_combiner_is_deterministic_for_same_inputs() -> None:
    pred = _flat_prediction(model_code="a", expected_return_pct="3", direction=DIRECTION_SLIGHT_UP)
    a = compute_ensemble_forecast([_StaticPredictor(pred)], _BASIC_INPUTS)
    b = compute_ensemble_forecast([_StaticPredictor(pred)], _BASIC_INPUTS)
    assert a == b


def test_real_predictors_block_when_history_is_too_short() -> None:
    short = [100.0] * 50
    inputs = PredictorInputs(
        historical_bars=_bars(short),
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    result = compute_ensemble_forecast(
        [GbmPredictor(), MomentumPredictor(), MeanReversionPredictor()], inputs
    )
    # All three predictors block on insufficient history.
    assert result.forecast.status == PREDICTOR_STATUS_BLOCKED
    assert result.forecast.blocking_reason == "all_predictors_blocked"
    assert BLOCKING_REASON_INSUFFICIENT_HISTORY not in (
        result.forecast.blocking_reason or ""
    )  # The ensemble has its own reason; the per-predictor reason is in blocked_codes.
    assert len(result.blocked_model_codes) == 3


def test_explanation_lists_contributing_predictors() -> None:
    a = _flat_prediction(model_code="a", expected_return_pct="3", direction=DIRECTION_SLIGHT_UP)
    b = _flat_prediction(model_code="b", expected_return_pct="2", direction=DIRECTION_SLIGHT_UP)
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)], _BASIC_INPUTS
    )
    text = result.forecast.explanation_nl
    assert "a" in text and "b" in text
    assert "agreement" in text.lower()


def test_p10_p50_p90_are_weighted_averages() -> None:
    a = _flat_prediction(
        model_code="a",
        expected_return_pct="0",
        direction=DIRECTION_FLAT,
        p10="90",
        p50="100",
        p90="110",
    )
    b = _flat_prediction(
        model_code="b",
        expected_return_pct="0",
        direction=DIRECTION_FLAT,
        p10="80",
        p50="100",
        p90="120",
    )
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)], _BASIC_INPUTS
    )
    assert result.forecast.p10_price == Decimal("85.000000")
    assert result.forecast.p50_price == Decimal("100.000000")
    assert result.forecast.p90_price == Decimal("115.000000")


def test_strong_down_direction_propagates_through_combiner() -> None:
    a = _flat_prediction(model_code="a", expected_return_pct="-15", direction=DIRECTION_STRONG_DOWN)
    b = _flat_prediction(model_code="b", expected_return_pct="-12", direction=DIRECTION_STRONG_DOWN)
    result = compute_ensemble_forecast(
        [_StaticPredictor(a), _StaticPredictor(b)], _BASIC_INPUTS
    )
    assert result.forecast.direction == DIRECTION_STRONG_DOWN
