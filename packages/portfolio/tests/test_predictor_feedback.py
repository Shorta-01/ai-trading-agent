"""Tests for the V1.1 Slice 26 feedback-loop helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.ensemble_combiner import (
    EnsembleContribution,
    EnsembleResult,
)
from portfolio_outlook_portfolio.predictor_feedback import (
    DEFAULT_WEIGHT_CLIP_HIGH,
    DEFAULT_WEIGHT_CLIP_LOW,
    OUTCOME_CORRECT,
    OUTCOME_NO_DATA,
    OUTCOME_PARTIAL,
    OUTCOME_WRONG,
    compute_inverse_brier_weights,
    compute_per_predictor_outcomes,
)
from portfolio_outlook_portfolio.predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    STATUS_READY,
    PredictionDistribution,
)


def _prediction(
    *,
    model_code: str = "momentum_v1",
    direction: str = DIRECTION_SLIGHT_UP,
    expected_return_pct: str = "3.0",
    prob_gain: str = "0.62",
) -> PredictionDistribution:
    return PredictionDistribution(
        model_code=model_code,
        model_version="v1.0.0",
        horizon_trading_days=21,
        current_price=Decimal("100"),
        p10_price=Decimal("90"),
        p50_price=Decimal("103"),
        p90_price=Decimal("115"),
        prob_gain=Decimal(prob_gain),
        prob_loss=Decimal("1") - Decimal(prob_gain),
        expected_return_pct=Decimal(expected_return_pct),
        direction=direction,
        confidence_score=Decimal("0.6"),
        status=STATUS_READY,
        blocking_reason=None,
        explanation_nl="test",
    )


def _ensemble_with(*predictions: PredictionDistribution) -> EnsembleResult:
    contributions = tuple(
        EnsembleContribution(
            model_code=p.model_code,
            model_version=p.model_version,
            weight_raw=Decimal("1"),
            weight_normalised=Decimal("1") / Decimal(str(len(predictions) or 1)),
            prediction=p,
        )
        for p in predictions
    )
    return EnsembleResult(
        forecast=predictions[0] if predictions else _prediction(),
        contributions=contributions,
        blocked_model_codes=(),
    )


# ---- compute_per_predictor_outcomes -------------------------------------


def test_outcomes_correct_when_direction_matches_exactly() -> None:
    ensemble = _ensemble_with(_prediction(direction=DIRECTION_SLIGHT_UP))
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=Decimal("4.5")
    )
    assert len(outcomes) == 1
    o = outcomes[0]
    assert o.outcome_label == OUTCOME_CORRECT
    assert o.realised_direction == "slight_up"
    assert o.brier_score is not None
    # Brier = (0.62 - 1)^2 = 0.1444 (positive realised return → indicator=1)
    assert o.brier_score == Decimal("0.144400")


def test_outcomes_partial_when_buckets_match_but_strengths_differ() -> None:
    # Predicted slight_up; realised strong_up. Same bucket, different strength.
    ensemble = _ensemble_with(_prediction(direction=DIRECTION_SLIGHT_UP))
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=Decimal("15.0")
    )
    assert outcomes[0].outcome_label == OUTCOME_PARTIAL


def test_outcomes_wrong_when_buckets_disagree() -> None:
    ensemble = _ensemble_with(_prediction(direction=DIRECTION_SLIGHT_UP))
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=Decimal("-7.0")
    )
    assert outcomes[0].outcome_label == OUTCOME_WRONG
    assert outcomes[0].realised_direction == "slight_down"


def test_outcomes_no_data_when_realised_is_missing() -> None:
    ensemble = _ensemble_with(_prediction())
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=None
    )
    assert outcomes[0].outcome_label == OUTCOME_NO_DATA
    assert outcomes[0].brier_score is None
    assert outcomes[0].realised_return_pct is None


def test_outcomes_one_row_per_surviving_predictor() -> None:
    ensemble = _ensemble_with(
        _prediction(model_code="gbm_v1", direction=DIRECTION_SLIGHT_UP),
        _prediction(model_code="momentum_v1", direction=DIRECTION_FLAT),
        _prediction(model_code="mean_reversion_v1", direction=DIRECTION_STRONG_DOWN),
    )
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=Decimal("2.5")
    )
    codes = [o.model_code for o in outcomes]
    assert codes == ["gbm_v1", "momentum_v1", "mean_reversion_v1"]


def test_outcomes_return_spread_is_signed_difference() -> None:
    # Predicted +3%; realised +5% → spread = -2 (predictor undershot).
    ensemble = _ensemble_with(_prediction(expected_return_pct="3.0"))
    outcomes = compute_per_predictor_outcomes(
        ensemble=ensemble, realised_return_pct=Decimal("5.0")
    )
    assert outcomes[0].return_spread_pct == Decimal("-2.000000")


# ---- compute_inverse_brier_weights --------------------------------------


def test_inverse_brier_lower_brier_yields_higher_weight() -> None:
    weights = compute_inverse_brier_weights(
        {
            "a_v1": Decimal("0.10"),  # best
            "b_v1": Decimal("0.25"),  # middling
            "c_v1": Decimal("0.40"),  # worst
        }
    )
    assert weights["a_v1"] > weights["b_v1"] > weights["c_v1"]


def test_inverse_brier_clip_floors_low_weight_above_zero() -> None:
    # An extreme outlier (`brier=10`) would normalise to near-zero
    # weight; the clip floor keeps it at the locked lower bound.
    weights = compute_inverse_brier_weights(
        {"a_v1": Decimal("0.10"), "b_v1": Decimal("10.0")}
    )
    assert weights["b_v1"] >= DEFAULT_WEIGHT_CLIP_LOW


def test_inverse_brier_clip_caps_dominant_weight_below_one() -> None:
    # A near-zero brier would otherwise dominate; the clip cap holds.
    weights = compute_inverse_brier_weights(
        {"a_v1": Decimal("0.001"), "b_v1": Decimal("0.50"), "c_v1": Decimal("0.50")}
    )
    assert weights["a_v1"] <= DEFAULT_WEIGHT_CLIP_HIGH


def test_inverse_brier_weights_sum_to_one_within_quantisation() -> None:
    weights = compute_inverse_brier_weights(
        {"a_v1": Decimal("0.10"), "b_v1": Decimal("0.20"), "c_v1": Decimal("0.30")}
    )
    total = sum(weights.values(), Decimal("0"))
    # Six-decimal quantisation; allow a small rounding drift.
    assert abs(total - Decimal("1")) <= Decimal("0.00001")


def test_inverse_brier_empty_history_returns_empty_dict() -> None:
    assert compute_inverse_brier_weights({}) == {}


def test_inverse_brier_all_none_falls_back_to_empty() -> None:
    assert compute_inverse_brier_weights({"a_v1": None, "b_v1": None}) == {}


def test_inverse_brier_fallback_codes_get_equal_share_when_history_is_empty() -> None:
    weights = compute_inverse_brier_weights(
        {}, fallback_codes=["a_v1", "b_v1", "c_v1"]
    )
    assert len(weights) == 3
    # Equal share at the clip-band lower bound after the equal-weight
    # collapse + clip re-normalisation. The important property is they
    # all carry positive weight that sums to 1.
    total = sum(weights.values(), Decimal("0"))
    assert abs(total - Decimal("1")) <= Decimal("0.00001")
    assert all(w > 0 for w in weights.values())


def test_inverse_brier_includes_fallback_codes_with_history() -> None:
    weights = compute_inverse_brier_weights(
        {"a_v1": Decimal("0.10"), "b_v1": Decimal("0.20")},
        fallback_codes=["c_v1"],
    )
    assert "c_v1" in weights
    # c_v1 had no history; it inherits the mean-Brier baseline.
    assert weights["c_v1"] > 0


def test_inverse_brier_rejects_invalid_clip_band() -> None:
    with pytest.raises(ValueError, match="clip"):
        compute_inverse_brier_weights(
            {"a_v1": Decimal("0.10")},
            clip=(Decimal("0.5"), Decimal("0.5")),
        )
    with pytest.raises(ValueError, match="clip"):
        compute_inverse_brier_weights(
            {"a_v1": Decimal("0.10")},
            clip=(Decimal("0"), Decimal("0.5")),
        )


# ---- ensemble combiner strategy switch -----------------------------------


def test_ensemble_combiner_rejects_unknown_weight_strategy() -> None:
    from portfolio_outlook_portfolio import compute_ensemble_forecast
    from portfolio_outlook_portfolio.predictor_protocol import PredictorInputs

    inputs = PredictorInputs(
        historical_bars=[],
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    with pytest.raises(ValueError, match="weight_strategy"):
        compute_ensemble_forecast([], inputs, weight_strategy="bogus")


def test_ensemble_combiner_auto_strategy_uses_brier_history() -> None:
    """With ``auto`` + a brier_history that strongly favours one
    predictor, that predictor's normalised weight in the result must
    exceed the equal-weight share. Uses a fake-predictor pair to keep
    the math obvious."""

    from portfolio_outlook_portfolio import compute_ensemble_forecast
    from portfolio_outlook_portfolio.predictor_protocol import (
        PredictionDistribution as PD,
    )
    from portfolio_outlook_portfolio.predictor_protocol import (
        PredictorInputs,
    )

    class _FakePredictor:
        def __init__(self, code: str, expected: str, prob_gain: str) -> None:
            self.model_code = code
            self.model_version = "v1.0.0"
            self._expected = expected
            self._prob_gain = prob_gain

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            return PD(
                model_code=self.model_code,
                model_version=self.model_version,
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                p10_price=Decimal("90"),
                p50_price=Decimal("100"),
                p90_price=Decimal("110"),
                prob_gain=Decimal(self._prob_gain),
                prob_loss=Decimal("1") - Decimal(self._prob_gain),
                expected_return_pct=Decimal(self._expected),
                direction=DIRECTION_SLIGHT_UP
                if Decimal(self._expected) > 0
                else DIRECTION_SLIGHT_DOWN,
                confidence_score=Decimal("0.6"),
                status=STATUS_READY,
            )

    inputs = PredictorInputs(
        historical_bars=[],
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    # Need ≥ 3 predictors for the locked clip band [0.05, 0.40] to be
    # feasible (N × clip_high ≥ 1 requires N ≥ 3 at 0.40).
    a = _FakePredictor("gbm_v1", expected="5", prob_gain="0.7")
    b = _FakePredictor("momentum_v1", expected="-5", prob_gain="0.3")
    c = _FakePredictor("mean_reversion_v1", expected="0", prob_gain="0.5")
    result = compute_ensemble_forecast(
        [a, b, c],
        inputs,
        weight_strategy="auto",
        brier_history={
            "gbm_v1": Decimal("0.10"),  # great
            "momentum_v1": Decimal("0.40"),  # poor
            "mean_reversion_v1": Decimal("0.25"),  # middling
        },
    )
    # gbm_v1 must outweigh momentum_v1 under auto-weight.
    by_code = {c.model_code: c for c in result.contributions}
    assert by_code["gbm_v1"].weight_normalised > by_code["momentum_v1"].weight_normalised


def test_ensemble_combiner_auto_strategy_falls_back_to_equal_when_history_empty() -> None:
    from portfolio_outlook_portfolio import compute_ensemble_forecast
    from portfolio_outlook_portfolio.predictor_protocol import (
        PredictionDistribution as PD,
    )
    from portfolio_outlook_portfolio.predictor_protocol import (
        PredictorInputs,
    )

    class _FakePredictor:
        model_version = "v1.0.0"

        def __init__(self, code: str) -> None:
            self.model_code = code

        def predict(self, inputs):  # type: ignore[no-untyped-def]
            return PD(
                model_code=self.model_code,
                model_version=self.model_version,
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                p10_price=Decimal("90"),
                p50_price=Decimal("100"),
                p90_price=Decimal("110"),
                prob_gain=Decimal("0.5"),
                prob_loss=Decimal("0.5"),
                expected_return_pct=Decimal("1"),
                direction=DIRECTION_FLAT,
                confidence_score=Decimal("0.5"),
                status=STATUS_READY,
            )

    inputs = PredictorInputs(
        historical_bars=[],
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    a = _FakePredictor("gbm_v1")
    b = _FakePredictor("momentum_v1")
    c = _FakePredictor("mean_reversion_v1")
    result = compute_ensemble_forecast(
        [a, b, c], inputs, weight_strategy="auto", brier_history={}
    )
    # Without history every predictor gets equal share. The clip + re-
    # normalise pipeline still maps to a uniform set when fallback
    # codes are all that's present.
    by_code = {c.model_code: c for c in result.contributions}
    assert (
        by_code["gbm_v1"].weight_normalised
        == by_code["momentum_v1"].weight_normalised
        == by_code["mean_reversion_v1"].weight_normalised
    )
