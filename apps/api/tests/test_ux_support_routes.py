"""Endpoint tests for V1.1 Slice 33 UX-support routes.

The Next.js panels read from these three new endpoints; this file
covers the API-side contract end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    ClaudeAiBudgetUsageRecord,
    PredictorBacktestRunRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.claude_ai_budget_monthly_eur = Decimal("50")


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _record(
    *,
    run_id: str = "bt-1",
    model_code: str = "baseline_gbm",
    asset_symbol: str = "AAPL",
    status: str = "succeeded",
) -> PredictorBacktestRunRecord:
    started = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)
    return PredictorBacktestRunRecord(
        run_id=run_id,
        model_code=model_code,
        model_version="v1.0.0",
        asset_symbol=asset_symbol,
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


@dataclass
class _FakeDecisionPackage:
    decision_package_id: str
    ibkr_conid: str
    generated_at: datetime
    status: str
    content_hash: str
    ensemble_prob_gain: Decimal | None = None
    ensemble_direction: str | None = None


def _fake_storage(
    monkeypatch,
    *,
    bt_records: tuple[PredictorBacktestRunRecord, ...] = (),
    budget_total_eur: Decimal = Decimal("0"),
    dp_records: tuple[_FakeDecisionPackage, ...] = (),
) -> None:
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
        def list_recent_backtest_runs(
            self, *, model_code=None, asset_symbol=None, limit=25
        ):
            class _R:
                records = tuple(bt_records)

            return _R()

    class _FakeBudgetRepo:
        saved: list[ClaudeAiBudgetUsageRecord] = []

        def monthly_total_eur(self, _month):
            return budget_total_eur

        def save_usage(self, _record):
            pass

    class _FakeDpRepo:
        def list_latest_asset_decision_packages_by_conids(self, _conids):
            class _R:
                records = tuple(dp_records)

            return _R()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyPredictorBacktestRunRepository",
        lambda *_a, **_k: _FakeBacktestRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyClaudeAiBudgetUsageRepository",
        lambda *_a, **_k: _FakeBudgetRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetDecisionPackageRepository",
        lambda *_a, **_k: _FakeDpRepo(),
    )


# ---- GET /predictor/backtest/history -----------------------------------


def test_backtest_history_not_configured_without_storage() -> None:
    r = client.get("/predictor/backtest/history")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []
    assert body["safe_for_orders"] is False


def test_backtest_history_returns_recent_rows(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(
        monkeypatch,
        bt_records=(
            _record(run_id="bt-a"),
            _record(run_id="bt-b", status="skipped"),
        ),
    )
    r = client.get("/predictor/backtest/history?limit=5")
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["items"]) == 2
    assert body["items"][0]["run_id"] == "bt-a"
    assert body["items"][1]["status"] == "skipped"


def test_backtest_history_caps_limit_at_100(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, bt_records=(_record(run_id="bt-z"),))
    # limit > 100 should be clamped silently.
    r = client.get("/predictor/backtest/history?limit=500")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---- GET /claude/budget/status -----------------------------------------


def test_claude_budget_status_not_configured_without_storage() -> None:
    r = client.get("/claude/budget/status")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["monthly_cap_eur"] == "50"
    assert body["budget_month"] is None
    assert body["exceeded"] is False
    assert body["safe_for_orders"] is False


def test_claude_budget_status_returns_running_total(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, budget_total_eur=Decimal("12.50"))
    r = client.get("/claude/budget/status")
    body = r.json()
    assert body["status"] == "ok"
    assert body["budget_month"] is not None
    assert Decimal(body["monthly_total_eur"]) == Decimal("12.50")
    assert Decimal(body["remaining_eur"]) == Decimal("37.50")
    assert body["exceeded"] is False


def test_claude_budget_status_flags_exceeded_when_over_cap(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, budget_total_eur=Decimal("60.00"))
    r = client.get("/claude/budget/status")
    body = r.json()
    assert body["status"] == "ok"
    assert body["exceeded"] is True


# ---- GET /decision-packages/{conid}/diff ------------------------------


def test_decision_package_diff_not_configured_without_storage() -> None:
    r = client.get("/decision-packages/265598/diff")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["newer"] is None
    assert body["safe_for_orders"] is False


def test_decision_package_diff_not_found_when_no_packages(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, dp_records=())
    r = client.get("/decision-packages/265598/diff")
    body = r.json()
    assert body["status"] == "not_found"
    assert body["changes"] == []


def test_decision_package_diff_only_one_package_returns_marker(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    pkg = _FakeDecisionPackage(
        decision_package_id="dp-1",
        ibkr_conid="265598",
        generated_at=datetime(2026, 6, 17, 7, 0, tzinfo=UTC),
        status="ready",
        content_hash="hash-1",
        ensemble_prob_gain=Decimal("0.62"),
        ensemble_direction="slight_up",
    )
    _fake_storage(monkeypatch, dp_records=(pkg,))
    r = client.get("/decision-packages/265598/diff")
    body = r.json()
    assert body["status"] == "only_one_package"
    assert body["newer"]["decision_package_id"] == "dp-1"
    assert body["older"] is None
    assert body["changes"] == []


def test_decision_package_diff_reports_changed_fields(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    older = _FakeDecisionPackage(
        decision_package_id="dp-old",
        ibkr_conid="265598",
        generated_at=datetime(2026, 6, 16, 7, 0, tzinfo=UTC),
        status="ready",
        content_hash="hash-old",
        ensemble_prob_gain=Decimal("0.50"),
        ensemble_direction="flat",
    )
    newer = _FakeDecisionPackage(
        decision_package_id="dp-new",
        ibkr_conid="265598",
        generated_at=datetime(2026, 6, 17, 7, 0, tzinfo=UTC),
        status="ready",
        content_hash="hash-new",
        ensemble_prob_gain=Decimal("0.62"),
        ensemble_direction="slight_up",
    )
    _fake_storage(monkeypatch, dp_records=(older, newer))
    r = client.get("/decision-packages/265598/diff")
    body = r.json()
    assert body["status"] == "ok"
    assert body["newer"]["decision_package_id"] == "dp-new"
    assert body["older"]["decision_package_id"] == "dp-old"
    changed_fields = {c["field"] for c in body["changes"]}
    assert "content_hash" in changed_fields
    assert "ensemble_prob_gain" in changed_fields
    assert "ensemble_direction" in changed_fields
