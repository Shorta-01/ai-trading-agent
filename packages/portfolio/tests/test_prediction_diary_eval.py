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


# ---- #5 — live Brier history from diary outcomes ------------------------


def _diary_entry(
    *,
    entry_id: str,
    forecast_id: str | None,
    outcome_1m: str | None,
):  # type: ignore[no-untyped-def]
    """Minimal diary entry stub for the Brier-aggregation function."""

    from datetime import UTC, datetime
    from decimal import Decimal as _D

    from ai_trading_agent_storage import PredictionDiaryEntryRecord

    return PredictionDiaryEntryRecord(
        entry_id=entry_id,
        suggestion_id=f"sug_{entry_id}",
        forecast_id=forecast_id,
        ibkr_conid="100",
        symbol="ASML",
        currency="EUR",
        issued_at=datetime(2026, 5, 1, tzinfo=UTC),
        issued_action_label="Kopen",
        issued_action_label_nl="Kopen",
        issued_confidence_label="Hoog",
        issued_horizon_days=30,
        issued_price=_D("100"),
        issued_p10_price=_D("90"),
        issued_p50_price=_D("105"),
        issued_p90_price=_D("120"),
        issued_prob_gain=_D("0.8"),
        issued_prob_loss=_D("0.2"),
        user_decision=None,
        realized_price_1d=None,
        realized_price_1w=None,
        realized_price_1m=None,
        realized_return_pct_1d=None,
        realized_return_pct_1w=None,
        realized_return_pct_1m=None,
        outcome_label_1d=None,
        outcome_label_1w=None,
        outcome_label_1m=outcome_1m,
        outcome_explanation_nl="test",
        last_evaluated_at=datetime(2026, 5, 30, tzinfo=UTC),
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 30, tzinfo=UTC),
    )


def test_compute_live_brier_returns_empty_dict_with_no_entries() -> None:
    from portfolio_outlook_portfolio.prediction_diary_eval import (
        compute_live_brier_history_from_diary,
    )

    assert compute_live_brier_history_from_diary(
        diary_entries=(), forecast_model_by_id={}
    ) == {}


def test_compute_live_brier_averages_per_predictor() -> None:
    """Two predictors, three entries each: GBM (right, right, wrong)
    avg = (0 + 0 + 1)/3 ≈ 0.333; QVM (right, inconclusive, wrong)
    avg = (0 + 0.5 + 1)/3 = 0.5. Lower = better, so GBM gets more
    weight in the inverse-Brier ensemble."""

    from portfolio_outlook_portfolio.prediction_diary_eval import (
        compute_live_brier_history_from_diary,
    )

    entries = [
        _diary_entry(entry_id="a", forecast_id="f1", outcome_1m="right"),
        _diary_entry(entry_id="b", forecast_id="f2", outcome_1m="right"),
        _diary_entry(entry_id="c", forecast_id="f3", outcome_1m="wrong"),
        _diary_entry(entry_id="d", forecast_id="f4", outcome_1m="right"),
        _diary_entry(entry_id="e", forecast_id="f5", outcome_1m="inconclusive"),
        _diary_entry(entry_id="f", forecast_id="f6", outcome_1m="wrong"),
    ]
    model_map = {
        "f1": "baseline_gbm",
        "f2": "baseline_gbm",
        "f3": "baseline_gbm",
        "f4": "qvm",
        "f5": "qvm",
        "f6": "qvm",
    }
    history = compute_live_brier_history_from_diary(
        diary_entries=entries, forecast_model_by_id=model_map
    )
    assert "baseline_gbm" in history
    assert "qvm" in history
    # 1/3 ≈ 0.333333
    assert abs(history["baseline_gbm"] - Decimal("0.333333")) < Decimal("0.000005")
    # 1.5/3 = 0.5
    assert history["qvm"] == Decimal("0.500000")


def test_compute_live_brier_skips_no_data_and_unmapped_entries() -> None:
    """no_data outcomes contribute no signal; entries whose forecast_id
    isn't in the model map are silently dropped (the lookup table is
    the source of truth)."""

    from portfolio_outlook_portfolio.prediction_diary_eval import (
        compute_live_brier_history_from_diary,
    )

    entries = [
        _diary_entry(entry_id="a", forecast_id="f1", outcome_1m="right"),
        _diary_entry(entry_id="b", forecast_id="f2", outcome_1m="no_data"),
        _diary_entry(entry_id="c", forecast_id="f3", outcome_1m="wrong"),  # unmapped
        _diary_entry(entry_id="d", forecast_id=None, outcome_1m="right"),  # no forecast_id
    ]
    model_map = {"f1": "baseline_gbm", "f2": "baseline_gbm"}
    history = compute_live_brier_history_from_diary(
        diary_entries=entries, forecast_model_by_id=model_map
    )
    # Only the "right" entry for f1 was counted; no_data skipped.
    assert history == {"baseline_gbm": Decimal("0.000000")}


def test_compute_live_brier_honors_horizon_key() -> None:
    """The function defaults to the 1m horizon but lets the caller
    pick 1d or 1w when they prefer faster feedback."""

    from datetime import UTC, datetime
    from decimal import Decimal as _D

    from ai_trading_agent_storage import PredictionDiaryEntryRecord

    from portfolio_outlook_portfolio.prediction_diary_eval import (
        compute_live_brier_history_from_diary,
    )

    entry = PredictionDiaryEntryRecord(
        entry_id="e",
        suggestion_id="s",
        forecast_id="f1",
        ibkr_conid="100",
        symbol="ASML",
        currency="EUR",
        issued_at=datetime(2026, 5, 1, tzinfo=UTC),
        issued_action_label="Kopen",
        issued_action_label_nl="Kopen",
        issued_confidence_label="Hoog",
        issued_horizon_days=30,
        issued_price=_D("100"),
        issued_p10_price=_D("90"),
        issued_p50_price=_D("105"),
        issued_p90_price=_D("120"),
        issued_prob_gain=_D("0.8"),
        issued_prob_loss=_D("0.2"),
        user_decision=None,
        realized_price_1d=None,
        realized_price_1w=None,
        realized_price_1m=None,
        realized_return_pct_1d=None,
        realized_return_pct_1w=None,
        realized_return_pct_1m=None,
        outcome_label_1d="right",
        outcome_label_1w="wrong",
        outcome_label_1m=None,
        outcome_explanation_nl="test",
        last_evaluated_at=datetime(2026, 5, 30, tzinfo=UTC),
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 30, tzinfo=UTC),
    )
    via_1d = compute_live_brier_history_from_diary(
        diary_entries=(entry,),
        forecast_model_by_id={"f1": "baseline_gbm"},
        horizon_key="outcome_label_1d",
    )
    via_1w = compute_live_brier_history_from_diary(
        diary_entries=(entry,),
        forecast_model_by_id={"f1": "baseline_gbm"},
        horizon_key="outcome_label_1w",
    )
    assert via_1d == {"baseline_gbm": Decimal("0.000000")}  # right = 0
    assert via_1w == {"baseline_gbm": Decimal("1.000000")}  # wrong = 1
