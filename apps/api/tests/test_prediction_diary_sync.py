"""Tests for the prediction diary orchestrator (Slice 8)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetForecastRecord,
    AssetSuggestionRecord,
    MarketDataBarRecord,
    PredictionDiaryEntryRecord,
)

from portfolio_outlook_api.prediction_diary_sync import (
    PredictionDiaryReport,
    evaluate_prediction_diary,
    serialize_prediction_diary_entry_for_response,
)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)
_ISSUED_AT = datetime(2025, 4, 20, 12, 0, tzinfo=UTC)


def _suggestion(
    *,
    suggestion_id: str = "sug-1",
    forecast_id: str | None = "fc-1",
    ibkr_conid: str = "265598",
    symbol: str = "AAPL",
) -> AssetSuggestionRecord:
    return AssetSuggestionRecord(
        suggestion_id=suggestion_id,
        ibkr_conid=ibkr_conid,
        symbol=symbol,
        currency="USD",
        forecast_id=forecast_id,
        model_code="rule_v1",
        model_version="2025-05",
        generated_at=_ISSUED_AT,
        valid_until=_ISSUED_AT + timedelta(days=2),
        risk_profile="Gebalanceerd",
        has_position=False,
        action_label="Kopen",
        action_label_nl="Kopen",
        confidence_label="Hoog",
        confidence_label_nl="Hoog",
        confidence_score=Decimal("0.75"),
        rationale_nl="rationale",
        drivers_json=("driver-1",),
        blockers_json=None,
        status="ready",
        blocking_reason=None,
    )


def _forecast(
    *,
    forecast_id: str = "fc-1",
    ibkr_conid: str = "265598",
    current_price: str = "100",
    p10: str = "95",
    p50: str = "105",
    p90: str = "115",
    prob_gain: str = "0.6",
    prob_loss: str = "0.4",
) -> AssetForecastRecord:
    return AssetForecastRecord(
        forecast_id=forecast_id,
        ibkr_conid=ibkr_conid,
        symbol="AAPL",
        currency="USD",
        model_code="lognormal_gbm_v1",
        model_version="0.1.0",
        horizon_days=21,
        generated_at=_ISSUED_AT,
        valid_until=_ISSUED_AT + timedelta(days=1),
        data_points_used=180,
        history_first_bar_date=date(2024, 10, 1),
        history_last_bar_date=date(2025, 4, 19),
        current_price=Decimal(current_price),
        expected_return_pct=Decimal("5.0"),
        p10_price=Decimal(p10),
        p50_price=Decimal(p50),
        p90_price=Decimal(p90),
        prob_gain=Decimal(prob_gain),
        prob_loss=Decimal(prob_loss),
        prob_loss_gt_5pct=Decimal("0.2"),
        prob_loss_gt_10pct=Decimal("0.1"),
        prob_gain_gt_5pct=Decimal("0.4"),
        prob_gain_gt_10pct=Decimal("0.2"),
        expected_volatility_annual=Decimal("0.25"),
        downside_risk_score=Decimal("0.30"),
        confidence_score=Decimal("0.7"),
        direction_label="up",
        direction_label_nl="omhoog",
        explanation_nl="explanation",
        status="ready",
        blocking_reason=None,
    )


def _bar(
    *,
    ibkr_conid: str,
    bar_date: date,
    close_price: str,
    bar_id_suffix: str = "",
) -> MarketDataBarRecord:
    return MarketDataBarRecord(
        bar_id=f"bar-{ibkr_conid}-{bar_date}-{bar_id_suffix}",
        ibkr_conid=ibkr_conid,
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        provider_code="eodhd",
        bar_date=bar_date,
        interval_code="1d",
        open_price=Decimal(close_price),
        high_price=Decimal(close_price),
        low_price=Decimal(close_price),
        close_price=Decimal(close_price),
        adjusted_close_price=Decimal(close_price),
        volume=Decimal("1000000"),
        provider_as_of=datetime.combine(bar_date, datetime.min.time(), tzinfo=UTC),
        received_at=_NOW,
        stored_at=_NOW,
        source_type="eod",
        explanation_nl="EOD-bar",
    )


class FakeDiaryRepo:
    def __init__(self, raise_on_upsert: bool = False) -> None:
        self.saved: list[PredictionDiaryEntryRecord] = []
        self._raise = raise_on_upsert

    def upsert_prediction_diary_entry(
        self, record: PredictionDiaryEntryRecord
    ) -> object:
        if self._raise:
            raise RuntimeError("fake-db-error")
        self.saved.append(record)
        return None


def test_happy_path_persists_entry_with_outcomes() -> None:
    suggestion = _suggestion()
    forecast = _forecast()
    bars = [
        _bar(ibkr_conid="265598", bar_date=date(2025, 4, 21), close_price="106"),
        _bar(ibkr_conid="265598", bar_date=date(2025, 4, 27), close_price="108"),
        _bar(ibkr_conid="265598", bar_date=date(2025, 5, 20), close_price="112"),
    ]
    repo = FakeDiaryRepo()

    report = evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={"fc-1": forecast},
        bars=bars,
        repo=repo,
    )

    assert isinstance(report, PredictionDiaryReport)
    assert report.entries_persisted == 1
    assert report.entries_failed == 0
    assert report.entries_skipped_no_forecast == 0
    assert len(repo.saved) == 1
    entry = repo.saved[0]
    assert entry.suggestion_id == "sug-1"
    assert entry.forecast_id == "fc-1"
    assert entry.realized_price_1d == Decimal("106")
    assert entry.realized_price_1w == Decimal("108")
    assert entry.realized_price_1m == Decimal("112")
    assert entry.outcome_label_1d is not None
    assert entry.outcome_label_1w is not None
    assert entry.outcome_label_1m is not None


def test_suggestion_without_forecast_id_is_skipped() -> None:
    suggestion = _suggestion(forecast_id=None)
    repo = FakeDiaryRepo()

    report = evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={},
        bars=[],
        repo=repo,
    )

    assert report.entries_persisted == 0
    assert report.entries_skipped_no_forecast == 1
    assert report.failures[0]["reason"] == "no_linked_forecast"


def test_missing_forecast_in_map_is_skipped() -> None:
    suggestion = _suggestion(forecast_id="missing")
    repo = FakeDiaryRepo()

    report = evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={},
        bars=[],
        repo=repo,
    )

    assert report.entries_persisted == 0
    assert report.entries_skipped_no_forecast == 1
    assert report.failures[0]["reason"] == "forecast_not_found"


def test_persistence_error_is_classified_as_failed() -> None:
    suggestion = _suggestion()
    forecast = _forecast()
    repo = FakeDiaryRepo(raise_on_upsert=True)

    report = evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={"fc-1": forecast},
        bars=[],
        repo=repo,
    )

    assert report.entries_persisted == 0
    assert report.entries_failed == 1
    assert report.failures[0]["reason"] == "persistence_error"
    assert "fake-db-error" in report.failures[0]["detail"]


def test_bars_lookback_walks_past_weekends() -> None:
    suggestion = _suggestion()
    forecast = _forecast()
    # Issued 2025-04-20 (a Sunday). 1d target = 2025-04-21 (Mon). 1w target
    # = 2025-04-27 (Sun). Provide only a Friday 2025-04-25 bar so the 1w
    # walker has to step back 2 days.
    bars = [
        _bar(ibkr_conid="265598", bar_date=date(2025, 4, 21), close_price="106"),
        _bar(ibkr_conid="265598", bar_date=date(2025, 4, 25), close_price="109"),
    ]
    repo = FakeDiaryRepo()

    evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={"fc-1": forecast},
        bars=bars,
        repo=repo,
    )

    assert repo.saved[0].realized_price_1d == Decimal("106")
    assert repo.saved[0].realized_price_1w == Decimal("109")
    assert repo.saved[0].realized_price_1m is None


def test_no_bars_yields_no_data_outcomes() -> None:
    suggestion = _suggestion()
    forecast = _forecast()
    repo = FakeDiaryRepo()

    evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={"fc-1": forecast},
        bars=[],
        repo=repo,
    )

    entry = repo.saved[0]
    assert entry.realized_price_1d is None
    assert entry.realized_price_1w is None
    assert entry.realized_price_1m is None
    assert entry.outcome_label_1d == "no_data"
    assert entry.outcome_label_1w == "no_data"
    assert entry.outcome_label_1m == "no_data"


def test_empty_suggestions_returns_zero_report() -> None:
    repo = FakeDiaryRepo()

    report = evaluate_prediction_diary(
        suggestions=[],
        forecasts_by_id={},
        bars=[],
        repo=repo,
    )

    assert report.suggestion_total == 0
    assert report.entries_persisted == 0
    assert report.status_nl.startswith("Geen suggesties")


def test_serialize_entry_for_response_returns_strings_for_decimals() -> None:
    suggestion = _suggestion()
    forecast = _forecast()
    bars = [
        _bar(ibkr_conid="265598", bar_date=date(2025, 4, 21), close_price="106"),
    ]
    repo = FakeDiaryRepo()
    evaluate_prediction_diary(
        suggestions=[suggestion],
        forecasts_by_id={"fc-1": forecast},
        bars=bars,
        repo=repo,
    )

    payload = serialize_prediction_diary_entry_for_response(repo.saved[0])

    assert payload["suggestion_id"] == "sug-1"
    assert payload["forecast_id"] == "fc-1"
    assert payload["issued_price"] == "100"
    assert payload["realized_price_1d"] == "106"
    # Only one bar at issued+1d → 1m horizon target is > 7 days past it
    assert payload["realized_price_1m"] is None
    assert payload["safe_for_self_learning"] is False
    assert payload["safe_for_model_retraining"] is False
