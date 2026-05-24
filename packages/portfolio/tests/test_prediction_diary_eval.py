"""Tests for the deterministic Prediction Diary outcome evaluator."""

from __future__ import annotations

from decimal import Decimal

from portfolio_outlook_portfolio.prediction_diary_eval import (
    OUTCOME_EARLY,
    OUTCOME_INCONCLUSIVE,
    OUTCOME_NO_DATA,
    OUTCOME_RIGHT,
    OUTCOME_WRONG,
    evaluate_diary_outcomes,
)


def _eval(realized_1d: str | None, realized_1w: str | None, realized_1m: str | None,
          *, prob_gain: str = "0.6"):
    return evaluate_diary_outcomes(
        issued_price=Decimal("100"),
        issued_p10_price=Decimal("90"),
        issued_p50_price=Decimal("105"),
        issued_p90_price=Decimal("115"),
        issued_prob_gain=Decimal(prob_gain),
        realized_price_1d=Decimal(realized_1d) if realized_1d else None,
        realized_price_1w=Decimal(realized_1w) if realized_1w else None,
        realized_price_1m=Decimal(realized_1m) if realized_1m else None,
    )


def test_no_data_when_realized_price_missing() -> None:
    result = _eval(None, None, None)
    assert result.horizon_1d.outcome_label == OUTCOME_NO_DATA
    assert result.horizon_1w.outcome_label == OUTCOME_NO_DATA
    assert result.horizon_1m.outcome_label == OUTCOME_NO_DATA
    assert result.horizon_1d.realized_price is None


def test_right_when_direction_matches_and_realised_outside_band() -> None:
    # Forecast prob_gain=0.6 (up), realised +25% → right
    result = _eval(realized_1d="125", realized_1w=None, realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_RIGHT
    assert result.horizon_1d.realized_return_pct == Decimal("25")


def test_wrong_when_direction_mismatched() -> None:
    # Forecast prob_gain=0.6 (up), realised -25% → wrong
    result = _eval(realized_1d="75", realized_1w=None, realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_WRONG


def test_inconclusive_when_inside_tolerance_band() -> None:
    # Realised return < 0.25% → inconclusive regardless of direction
    result = _eval(realized_1d="100.10", realized_1w=None, realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_INCONCLUSIVE


def test_inconclusive_when_inside_forecast_band_with_matching_direction() -> None:
    # Direction up, realised 102 (between p10=90 and p90=115, below p50=105)
    # Above the inconclusive tolerance (~2%) but still inside the forecast band
    # AND below p50 → ``early``
    result = _eval(realized_1d="102", realized_1w=None, realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_EARLY


def test_right_when_direction_matches_above_p90_band() -> None:
    # Realised above p90 → above the forecast band entirely → right
    result = _eval(realized_1d="125", realized_1w=None, realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_RIGHT


def test_per_horizon_independence() -> None:
    result = _eval(realized_1d="100.10", realized_1w="125", realized_1m=None)
    assert result.horizon_1d.outcome_label == OUTCOME_INCONCLUSIVE
    assert result.horizon_1w.outcome_label == OUTCOME_RIGHT
    assert result.horizon_1m.outcome_label == OUTCOME_NO_DATA


def test_explanation_mentions_each_horizon_outcome() -> None:
    result = _eval(realized_1d="125", realized_1w="75", realized_1m=None)
    assert "1d=right" in result.explanation_nl
    assert "1w=wrong" in result.explanation_nl
    assert "1m=no_data" in result.explanation_nl


def test_down_forecast_with_realised_below_p50_is_right() -> None:
    # prob_gain=0.3 → forecast is down; p50=105. realised=90 is below p50 in
    # the down direction → right.
    result = _eval(realized_1d="90", realized_1w=None, realized_1m=None, prob_gain="0.3")
    assert result.horizon_1d.outcome_label == OUTCOME_RIGHT


def test_down_forecast_with_realised_far_below_band_is_right() -> None:
    result = _eval(realized_1d="50", realized_1w=None, realized_1m=None, prob_gain="0.3")
    assert result.horizon_1d.outcome_label == OUTCOME_RIGHT


def test_down_forecast_with_realised_up_is_wrong() -> None:
    result = _eval(realized_1d="130", realized_1w=None, realized_1m=None, prob_gain="0.3")
    assert result.horizon_1d.outcome_label == OUTCOME_WRONG


def test_zero_or_negative_issued_price_returns_zero_pct() -> None:
    from portfolio_outlook_portfolio.prediction_diary_eval import (
        evaluate_diary_outcomes as _eval_fn,
    )

    result = _eval_fn(
        issued_price=Decimal("0"),
        issued_p10_price=Decimal("0"),
        issued_p50_price=Decimal("0"),
        issued_p90_price=Decimal("0"),
        issued_prob_gain=Decimal("0.5"),
        realized_price_1d=Decimal("100"),
        realized_price_1w=None,
        realized_price_1m=None,
    )
    assert result.horizon_1d.realized_return_pct == Decimal("0")
