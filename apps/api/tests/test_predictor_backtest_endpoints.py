"""Endpoint tests for the V1.1 predictor backtest routes."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import PredictorBacktestRunRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.predictor_backtest_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _record(
    *,
    run_id: str = "bt-1",
    model_code: str = "baseline_gbm",
    status: str = "succeeded",
) -> PredictorBacktestRunRecord:
    started = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)
    return PredictorBacktestRunRecord(
        run_id=run_id,
        model_code=model_code,
        model_version="v1.0.0",
        asset_symbol="AAPL",
        started_at=started,
        finished_at=started,
        status=status,
        window_days=252,
        bars_used=252,
        brier_score=Decimal("0.187200") if status == "succeeded" else None,
        hit_rate=Decimal("0.563000") if status == "succeeded" else None,
        sharpe_ratio=Decimal("1.230000") if status == "succeeded" else None,
        blocking_reason=None,
        explanation_nl="ok",
    )


def _fake_writable_storage(monkeypatch, *, list_result=None, run_outcome=None) -> None:
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

        def checked_connection(self, *_, require_writable=False, **__):
            return _Ctx()

    class _FakeBacktestRepo:
        def save_backtest_run(self, _record):
            pass

        def update_backtest_run(self, _record):
            pass

        def list_recent_backtest_runs(
            self, *, model_code=None, asset_symbol=None, limit=25
        ):
            class _R:
                records = tuple(list_result or ())

            return _R()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyPredictorBacktestRunRepository",
        lambda *a, **k: _FakeBacktestRepo(),
    )
    class _FakeBarRepo:
        def list_market_data_bars_by_conid(self, *_a, **_k):
            class _Result:
                records = ()

            return _Result()

    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataBarRepository",
        lambda *_a, **_k: _FakeBarRepo(),
    )

    if run_outcome is not None:
        from portfolio_outlook_api import predictor_backtest_orchestrator as orch

        def _fake_run(**kwargs):
            return run_outcome

        monkeypatch.setattr(orch, "run_backtest_for_symbol", _fake_run)


# ---- POST /predictor/backtest/run ---------------------------------------


def test_run_route_blocked_when_disabled() -> None:
    r = client.post("/predictor/backtest/run", json={"model_code": "baseline_gbm"})
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "predictor_backtest_disabled"
    assert body["safe_for_orders"] is False


def test_run_route_blocked_when_missing_input() -> None:
    api_settings.predictor_backtest_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    r = client.post("/predictor/backtest/run", json={})
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "missing_input"


def test_run_route_blocked_when_storage_not_writable() -> None:
    api_settings.predictor_backtest_enabled = True
    r = client.post(
        "/predictor/backtest/run",
        json={
            "model_code": "baseline_gbm",
            "asset_symbol": "AAPL",
            "ibkr_conid": "265598",
        },
    )
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_run_route_returns_persisted_audit_row(monkeypatch) -> None:
    api_settings.predictor_backtest_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    # Stub the orchestrator's run_backtest_for_symbol via monkeypatching
    # the symbol the route imports lazily. The route does `from
    # portfolio_outlook_api.predictor_backtest_orchestrator import ...`
    # so we patch the function on that module.
    from portfolio_outlook_api import predictor_backtest_orchestrator as orch
    from portfolio_outlook_api.predictor_backtest_orchestrator import (
        BacktestOrchestratorResult,
    )

    fake_record = _record(run_id="bt-fake-1")
    monkeypatch.setattr(
        orch,
        "run_backtest_for_symbol",
        lambda **_: BacktestOrchestratorResult(
            record=fake_record, status_nl="ok", help_nl="ok"
        ),
    )
    _fake_writable_storage(monkeypatch)

    r = client.post(
        "/predictor/backtest/run",
        json={
            "model_code": "baseline_gbm",
            "asset_symbol": "AAPL",
            "ibkr_conid": "265598",
            "window_days": 252,
            "horizon_trading_days": 21,
            "step_days": 5,
        },
    )
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "succeeded"
    assert body["item"]["run_id"] == "bt-fake-1"
    assert body["safe_for_orders"] is False


# ---- GET /predictor/backtest/latest -------------------------------------


def test_latest_route_returns_not_configured_without_storage() -> None:
    r = client.get("/predictor/backtest/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []


def test_latest_route_returns_leaderboard_when_storage_present(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    _fake_writable_storage(
        monkeypatch,
        list_result=(_record(run_id="bt-a"), _record(run_id="bt-b", status="skipped")),
    )

    r = client.get("/predictor/backtest/latest?limit=10")
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["items"]) == 2
    assert body["items"][0]["run_id"] == "bt-a"
    assert body["items"][1]["status"] == "skipped"
    assert body["safe_for_orders"] is False


# ---- V1.1 Slice 26: GET /predictor/leaderboard --------------------------


def test_leaderboard_returns_not_configured_without_storage() -> None:
    r = client.get("/predictor/leaderboard")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []
    assert body["auto_weights"] == {}
    assert body["safe_for_orders"] is False


def test_leaderboard_aggregates_latest_per_model_and_computes_auto_weights(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    # Three predictors with varying Brier — auto-weights should be
    # ordered (gbm best → highest, momentum worst → lowest within clip).
    gbm = _record(run_id="bt-gbm", model_code="baseline_gbm")
    mom = _record(run_id="bt-mom", model_code="momentum_v1")
    # Override brier_score for the spread.
    from dataclasses import replace

    gbm = replace(gbm, brier_score=Decimal("0.10"))
    mom = replace(mom, brier_score=Decimal("0.40"))
    mr = replace(
        _record(run_id="bt-mr", model_code="mean_reversion_v1"),
        brier_score=Decimal("0.25"),
    )

    _fake_writable_storage(monkeypatch, list_result=(gbm, mom, mr))

    r = client.get("/predictor/leaderboard")
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["items"]) == 3
    assert body["safe_for_orders"] is False
    # Auto-weights surfaced for each model_code; sum to ~1.
    weights = body["auto_weights"]
    assert set(weights) == {"baseline_gbm", "momentum_v1", "mean_reversion_v1"}
    total = sum(Decimal(w) for w in weights.values())
    assert abs(total - Decimal("1")) <= Decimal("0.0001")
    # gbm (best Brier) outweighs momentum (worst Brier).
    assert Decimal(weights["baseline_gbm"]) > Decimal(weights["momentum_v1"])


def test_leaderboard_filters_by_asset_symbol(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    _fake_writable_storage(monkeypatch, list_result=(_record(run_id="bt-a"),))

    r = client.get("/predictor/leaderboard?asset_symbol=AAPL")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
