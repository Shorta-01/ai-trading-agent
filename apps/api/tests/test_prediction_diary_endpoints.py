"""Endpoint tests for /prediction-diary routes (Slice 8)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetForecastRecord,
    AssetSuggestionRecord,
    IbkrSyncRunRecord,
    MarketDataBarRecord,
    PredictionDiaryEntryRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)
_ISSUED_AT = datetime(2025, 4, 20, 12, 0, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.prediction_diary_sync_enabled = False
    api_settings.prediction_diary_inconclusive_tolerance_pct = "0.25"


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _sync_run() -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id="run-1",
        started_at=_NOW - timedelta(minutes=1),
        completed_at=_NOW,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="ok",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=1,
        cash_values_count=1,
        open_orders_count=0,
        executions_count=0,
        status_nl="ok",
        next_step_nl=None,
        help_nl="ok",
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=_NOW,
    )


def _suggestion() -> AssetSuggestionRecord:
    return AssetSuggestionRecord(
        suggestion_id="sug-1",
        ibkr_conid="265598",
        symbol="AAPL",
        currency="USD",
        forecast_id="fc-1",
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
        drivers_json=None,
        blockers_json=None,
        status="ready",
        blocking_reason=None,
    )


def _forecast() -> AssetForecastRecord:
    return AssetForecastRecord(
        forecast_id="fc-1",
        ibkr_conid="265598",
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
        current_price=Decimal("100"),
        expected_return_pct=Decimal("5.0"),
        p10_price=Decimal("95"),
        p50_price=Decimal("105"),
        p90_price=Decimal("115"),
        prob_gain=Decimal("0.6"),
        prob_loss=Decimal("0.4"),
        prob_loss_gt_5pct=Decimal("0.2"),
        prob_loss_gt_10pct=Decimal("0.1"),
        prob_gain_gt_5pct=Decimal("0.4"),
        prob_gain_gt_10pct=Decimal("0.2"),
        expected_volatility_annual=Decimal("0.25"),
        downside_risk_score=Decimal("0.30"),
        confidence_score=Decimal("0.7"),
        direction_label="up",
        direction_label_nl="omhoog",
        explanation_nl="ok",
        status="ready",
        blocking_reason=None,
    )


def _bar(bar_date: date, close_price: str) -> MarketDataBarRecord:
    return MarketDataBarRecord(
        bar_id=f"bar-{bar_date}",
        ibkr_conid="265598",
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
        explanation_nl="ok",
    )


def _entry() -> PredictionDiaryEntryRecord:
    return PredictionDiaryEntryRecord(
        entry_id="diary-1",
        suggestion_id="sug-1",
        forecast_id="fc-1",
        ibkr_conid="265598",
        symbol="AAPL",
        currency="USD",
        issued_at=_ISSUED_AT,
        issued_action_label="Kopen",
        issued_action_label_nl="Kopen",
        issued_confidence_label="Hoog",
        issued_horizon_days=21,
        issued_price=Decimal("100"),
        issued_p10_price=Decimal("95"),
        issued_p50_price=Decimal("105"),
        issued_p90_price=Decimal("115"),
        issued_prob_gain=Decimal("0.6"),
        issued_prob_loss=Decimal("0.4"),
        user_decision=None,
        realized_price_1d=Decimal("106"),
        realized_price_1w=Decimal("108"),
        realized_price_1m=Decimal("112"),
        realized_return_pct_1d=Decimal("6.0"),
        realized_return_pct_1w=Decimal("8.0"),
        realized_return_pct_1m=Decimal("12.0"),
        outcome_label_1d="right",
        outcome_label_1w="right",
        outcome_label_1m="right",
        outcome_explanation_nl="ok",
        last_evaluated_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _fake_storage(
    monkeypatch,
    *,
    sync_run=None,
    positions=None,
    suggestions=None,
    forecasts=None,
    bars=None,
    entries=None,
):
    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return sync_run

        def list_ibkr_position_snapshots(self, _run_id: str):
            return list(positions or [])

    class _FakeSuggestionRepo:
        def list_latest_asset_suggestions_by_conids(self, _conids):
            return type("_R", (), {"records": tuple(suggestions or [])})()

    class _FakeForecastRepo:
        def list_latest_asset_forecasts_by_conids(self, _conids):
            return type("_R", (), {"records": tuple(forecasts or [])})()

    class _FakeBarRepo:
        def list_market_data_bars_by_conid(self, _conid: str):
            return type("_R", (), {"records": tuple(bars or [])})()

    saved_entries: list = []

    class _FakeDiaryRepo:
        def upsert_prediction_diary_entry(self, record):
            saved_entries.append(record)

        def list_prediction_diary_entries(self):
            return type("_R", (), {"records": tuple(entries or [])})()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: _FakeSuggestionRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetForecastRepository",
        lambda *a, **k: _FakeForecastRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataBarRepository",
        lambda *a, **k: _FakeBarRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyPredictionDiaryRepository",
        lambda *a, **k: _FakeDiaryRepo(),
    )
    return saved_entries


# ---- POST /prediction-diary/evaluate -----------------------------------


def test_evaluate_blocked_when_sync_disabled() -> None:
    r = client.post("/prediction-diary/evaluate")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "prediction_diary_sync_disabled"
    assert body["safe_for_self_learning"] is False
    assert body["safe_for_model_retraining"] is False


def test_evaluate_blocked_when_storage_not_writable() -> None:
    api_settings.prediction_diary_sync_enabled = True
    r = client.post("/prediction-diary/evaluate")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_evaluate_blocked_when_no_positions(monkeypatch) -> None:
    api_settings.prediction_diary_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(monkeypatch, sync_run=None, positions=[])

    r = client.post("/prediction-diary/evaluate")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_positions"


def test_evaluate_happy_path_persists_entries(monkeypatch) -> None:
    api_settings.prediction_diary_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    class _Pos:
        conid = "265598"

    saved = _fake_storage(
        monkeypatch,
        sync_run=_sync_run(),
        positions=[_Pos()],
        suggestions=[_suggestion()],
        forecasts=[_forecast()],
        bars=[
            _bar(date(2025, 4, 21), "106"),
            _bar(date(2025, 4, 27), "108"),
            _bar(date(2025, 5, 20), "112"),
        ],
    )

    r = client.post("/prediction-diary/evaluate")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "completed"
    assert body["suggestion_total"] == 1
    assert body["entries_persisted"] == 1
    assert body["safe_for_self_learning"] is False
    assert body["safe_for_model_retraining"] is False
    assert len(saved) == 1


# ---- GET /prediction-diary --------------------------------------------


def test_read_diary_returns_not_configured_without_storage() -> None:
    r = client.get("/prediction-diary")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []
    assert body["safe_for_self_learning"] is False
    assert body["safe_for_model_retraining"] is False


def test_read_diary_returns_entries_when_storage_available(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, entries=[_entry()])

    r = client.get("/prediction-diary")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["suggestion_id"] == "sug-1"
    assert item["outcome_label_1d"] == "right"
    assert item["safe_for_self_learning"] is False
