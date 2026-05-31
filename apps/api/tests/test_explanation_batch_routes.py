"""Endpoint tests for ``POST /explanations/morning-batch``.

The route reads today's persisted Decision Packages for held positions
and pre-computes a Claude explanation for each one so the operator
opens the dashboard to ready-to-show paraphrases. The tests exercise
the empty-state cascade + a happy path that asserts the counts land in
the response.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
)
from fastapi.testclient import TestClient
from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api import explanation_batch_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ai_explanation_enabled = False
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_explanation_provider_code = "stub"
    api_settings.ai_explanation_max_output_chars = 2000
    api_settings.ai_explanation_morning_batch_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _package(
    *,
    decision_package_id: str = "dp-1",
    content_hash: str = "hash-aapl-1",
    symbol: str = "AAPL",
    conid: str = "265598",
) -> AssetDecisionPackageRecord:
    return AssetDecisionPackageRecord(
        decision_package_id=decision_package_id,
        content_hash=content_hash,
        ibkr_conid=conid,
        symbol=symbol,
        currency="USD",
        risk_profile="Gebalanceerd",
        generated_at=_NOW,
        valid_until=_NOW,
        position_snapshot_id=None,
        position_quantity=Decimal("10"),
        position_average_cost=Decimal("150"),
        cash_snapshot_id=None,
        cash_base_currency="USD",
        cash_amount=Decimal("5000"),
        market_snapshot_id=None,
        market_last_price=Decimal("180"),
        market_freshness_status="fresh",
        market_provider_code="eodhd",
        market_provider_as_of=_NOW,
        fx_pair=None,
        fx_rate=None,
        fx_freshness_status=None,
        forecast_id="fc-1",
        forecast_model_code="baseline_gbm",
        forecast_model_version="v1",
        forecast_horizon_days=21,
        forecast_p10_price=Decimal("170"),
        forecast_p50_price=Decimal("182"),
        forecast_p90_price=Decimal("194"),
        forecast_prob_gain=Decimal("0.62"),
        forecast_prob_loss=Decimal("0.38"),
        forecast_expected_return_pct=Decimal("1.5"),
        forecast_expected_volatility_annual=Decimal("0.22"),
        forecast_downside_risk_score=Decimal("6.0"),
        forecast_confidence_score=Decimal("0.85"),
        suggestion_id="sug-1",
        suggestion_model_code="baseline_label_translator",
        suggestion_action_label="Houden",
        suggestion_action_label_nl="Houden",
        suggestion_confidence_label="Hoog",
        suggestion_confidence_label_nl="Hoog",
        suggestion_status="ready",
        has_position=True,
        gate_outcomes_json=None,
        evidence_links_json=None,
        audit_links_json=None,
        rationale_nl="Houden vanwege lichte stijging.",
        explanation_nl="Decision Package voor AAPL.",
        status="ready",
        blocking_reason=None,
        research_evidence_count=0,
        research_credibility_summary="no_research",
        research_freshness_status="no_research",
        research_blocking_reason=None,
        research_snippet_nl="Geen onderzoek gekoppeld aan dit asset.",
    )


def _sync_run(sync_run_id: str = "sync-1") -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id=sync_run_id,
        started_at=_NOW,
        completed_at=_NOW,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="completed",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=1,
        cash_values_count=0,
        open_orders_count=0,
        executions_count=0,
        status_nl="Klaar",
        next_step_nl=None,
        help_nl=None,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _position(conid: str = "265598") -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos-{conid}",
        sync_run_id="sync-1",
        account_ref=None,
        conid=conid,
        symbol="AAPL",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        quantity=Decimal("10"),
        average_cost=Decimal("150"),
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id="DU1234567",
    )


def _install_fake_storage(
    monkeypatch,
    *,
    latest_run: IbkrSyncRunRecord | None,
    positions: list[IbkrPositionSnapshotRecord],
    decision_packages: list[AssetDecisionPackageRecord],
) -> list:
    saved_explanations: list = []

    class _FakeConn:
        def commit(self) -> None:
            return None

    class _Checked:
        connection = _FakeConn()
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Checked()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return latest_run

        def list_ibkr_position_snapshots(self, _sync_run_id):
            return positions

    class _FakePackageRepo:
        def list_latest_asset_decision_packages_by_conids(self, _conids):
            return type("_R", (), {"records": tuple(decision_packages)})()

    class _FakeExplanationRepo:
        def save_decision_package_explanation(self, record):
            saved_explanations.append(record)

        def save_explanation_evidence_ledger_entry(self, _record):
            pass

    class _FakeResearchRepo:
        def list_research_sources_for_asset(self, _symbol):
            return ()

    monkeypatch.setattr(
        explanation_batch_routes, "StorageConnectionProvider", _FakeStorageProvider
    )
    monkeypatch.setattr(
        explanation_batch_routes,
        "build_database_connection_settings",
        lambda _u: object(),
    )
    monkeypatch.setattr(
        explanation_batch_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
    )
    monkeypatch.setattr(
        explanation_batch_routes,
        "SqlAlchemyAssetDecisionPackageRepository",
        lambda *a, **k: _FakePackageRepo(),
    )
    monkeypatch.setattr(
        explanation_batch_routes,
        "SqlAlchemyDecisionPackageExplanationRepository",
        lambda *a, **k: _FakeExplanationRepo(),
    )
    monkeypatch.setattr(
        explanation_batch_routes,
        "SqlAlchemyResearchSourceArchiveRepository",
        lambda *a, **k: _FakeResearchRepo(),
    )
    return saved_explanations


def test_returns_disabled_when_flag_off() -> None:
    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "disabled"
    assert "uitgeschakeld" in body["status_nl"].lower()
    assert body["package_count"] == 0
    assert body["generated_count"] == 0
    assert body["safe_for_orders"] is False


def test_returns_not_configured_when_storage_disabled() -> None:
    api_settings.ai_explanation_morning_batch_enabled = True
    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert body["status"] == "not_configured"


def test_returns_no_ibkr_sync_run_when_none_exists(monkeypatch) -> None:
    api_settings.ai_explanation_morning_batch_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _install_fake_storage(
        monkeypatch, latest_run=None, positions=[], decision_packages=[]
    )

    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert body["status"] == "no_ibkr_sync_run"


def test_returns_no_held_positions_when_none(monkeypatch) -> None:
    api_settings.ai_explanation_morning_batch_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _install_fake_storage(
        monkeypatch,
        latest_run=_sync_run(),
        positions=[],
        decision_packages=[],
    )

    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert body["status"] == "no_held_positions"


def test_returns_no_decision_packages_when_held_but_no_dps(monkeypatch) -> None:
    api_settings.ai_explanation_morning_batch_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _install_fake_storage(
        monkeypatch,
        latest_run=_sync_run(),
        positions=[_position()],
        decision_packages=[],
    )

    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert body["status"] == "no_decision_packages"


def test_happy_path_generates_one_explanation_per_held_package(monkeypatch) -> None:
    api_settings.ai_explanation_morning_batch_enabled = True
    api_settings.ai_explanation_enabled = True
    api_settings.ai_explanation_provider_code = "stub"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    saved = _install_fake_storage(
        monkeypatch,
        latest_run=_sync_run(),
        positions=[_position()],
        decision_packages=[_package()],
    )

    r = client.post("/explanations/morning-batch")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "ok"
    assert body["package_count"] == 1
    assert body["generated_count"] == 1
    assert body["blocked_count"] == 0
    assert body["skipped_count"] == 0
    assert body["blocking_reasons"] == []
    assert body["safe_for_orders"] is False
    assert len(saved) == 1
    assert saved[0].decision_package_id == "dp-1"
    assert LOCKED_RISK_DISCLAIMER_NL in saved[0].explanation_nl
