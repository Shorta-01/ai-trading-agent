"""Tests for the suggestion sync orchestrator.

The translator math itself is exhaustively tested in
``packages/portfolio/tests/test_baseline_label_translator.py``. Here we focus
on the orchestrator's job: pair forecasts to held/cold positions, persist each
result, classify failures, return the right summary fields.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetForecastRecord,
    AssetSuggestionRecord,
    IbkrPositionSnapshotRecord,
)

from portfolio_outlook_api.suggestion_sync import (
    serialize_suggestion_for_response,
    sync_suggestions,
)

_NOW = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)


def _forecast(
    *,
    conid: str,
    symbol: str,
    direction: str,
    confidence: str = "0.85",
    status: str = "ready",
    blocking_reason: str | None = None,
) -> AssetForecastRecord:
    return AssetForecastRecord(
        forecast_id=f"forecast_{conid}",
        ibkr_conid=conid,
        symbol=symbol,
        currency="USD",
        model_code="baseline_gbm",
        model_version="v1.0.0",
        horizon_days=21,
        generated_at=_NOW,
        valid_until=_NOW,
        data_points_used=120,
        history_first_bar_date=date(2025, 1, 1),
        history_last_bar_date=date(2025, 5, 23),
        current_price=Decimal("100"),
        expected_return_pct=Decimal("0.5"),
        p10_price=Decimal("90"),
        p50_price=Decimal("100"),
        p90_price=Decimal("110"),
        prob_gain=Decimal("0.55"),
        prob_loss=Decimal("0.45"),
        prob_loss_gt_5pct=Decimal("0.2"),
        prob_loss_gt_10pct=Decimal("0.05"),
        prob_gain_gt_5pct=Decimal("0.25"),
        prob_gain_gt_10pct=Decimal("0.08"),
        expected_volatility_annual=Decimal("0.22"),
        downside_risk_score=Decimal("10"),
        confidence_score=Decimal(confidence),
        direction_label=direction,
        direction_label_nl="test",
        explanation_nl="test",
        status=status,
        blocking_reason=blocking_reason,
    )


def _position(conid: str, symbol: str) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos_{conid}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU12345",
        conid=conid,
        symbol=symbol,
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        quantity=Decimal("10"),
        average_cost=Decimal("90"),
        received_at=_NOW,
        stored_at=_NOW,
    )


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[AssetSuggestionRecord] = []

    def save_asset_suggestion(self, record: AssetSuggestionRecord) -> object:
        self.saved.append(record)
        return None


class RaisingRepo:
    def save_asset_suggestion(self, record: AssetSuggestionRecord) -> object:
        raise RuntimeError("simulated persistence failure")


def test_held_strong_down_high_confidence_persists_verkopen() -> None:
    repo = FakeRepo()

    report = sync_suggestions(
        forecasts=[_forecast(conid="1", symbol="AAPL", direction="strong_down", confidence="0.85")],
        positions=[_position("1", "AAPL")],
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.suggestion_persisted == 1
    assert report.held_positions == 1
    assert report.cold_start_positions == 0
    assert len(repo.saved) == 1
    record = repo.saved[0]
    assert record.action_label == "Verkopen"
    assert record.has_position is True
    assert record.confidence_label == "Hoog"
    assert record.safe_for_action_drafts is False
    assert record.safe_for_orders is False


def test_cold_start_strong_up_high_confidence_groei_persists_kopen() -> None:
    repo = FakeRepo()

    report = sync_suggestions(
        forecasts=[_forecast(conid="2", symbol="MSFT", direction="strong_up", confidence="0.90")],
        positions=[],  # not held
        risk_profile="Groei",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.suggestion_persisted == 1
    assert report.held_positions == 0
    assert report.cold_start_positions == 1
    assert repo.saved[0].action_label == "Kopen"


def test_blocked_forecast_persists_geblokkeerd_with_blocking_reason() -> None:
    repo = FakeRepo()

    report = sync_suggestions(
        forecasts=[
            _forecast(
                conid="3",
                symbol="GOOG",
                direction="blocked",
                status="blocked",
                blocking_reason="insufficient_history",
            )
        ],
        positions=[_position("3", "GOOG")],
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    assert report.suggestion_persisted == 1
    record = repo.saved[0]
    assert record.action_label == "Geblokkeerd"
    assert record.status == "blocked"
    assert record.blocking_reason == "insufficient_history"


def test_persistence_failure_is_classified_as_failed() -> None:
    report = sync_suggestions(
        forecasts=[_forecast(conid="1", symbol="AAPL", direction="neutral")],
        positions=[_position("1", "AAPL")],
        risk_profile="Gebalanceerd",
        repo=RaisingRepo(),
        valid_minutes=1440,
    )

    assert report.suggestion_persisted == 0
    assert report.suggestion_failed == 1
    assert any(f["reason"] == "persistence_error" for f in report.failures)


def test_serializer_renders_decimal_as_string_and_strips_safety_flags() -> None:
    repo = FakeRepo()
    sync_suggestions(
        forecasts=[_forecast(conid="1", symbol="AAPL", direction="neutral", confidence="0.85")],
        positions=[_position("1", "AAPL")],
        risk_profile="Gebalanceerd",
        repo=repo,
        valid_minutes=1440,
    )

    rendered = serialize_suggestion_for_response(repo.saved[0])

    assert isinstance(rendered["confidence_score"], str)
    assert rendered["safe_for_action_drafts"] is False
    assert rendered["safe_for_orders"] is False
    assert rendered["safe_for_broker_submission"] is False
    assert isinstance(rendered["drivers"], list)


def test_report_summary_status_when_no_forecasts() -> None:
    report = sync_suggestions(
        forecasts=[],
        positions=[],
        risk_profile="Gebalanceerd",
        repo=FakeRepo(),
        valid_minutes=1440,
    )

    assert report.suggestion_persisted == 0
    assert report.status_nl == "Geen voorspellingen beschikbaar"
