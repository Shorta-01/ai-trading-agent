"""Endpoint tests for the AI explanation routes (Slice 10)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetDecisionPackageRecord,
    DecisionPackageExplanationRecord,
)
from fastapi.testclient import TestClient
from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api import status_routes
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


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _package(decision_package_id: str = "dp-1") -> AssetDecisionPackageRecord:
    return AssetDecisionPackageRecord(
        decision_package_id=decision_package_id,
        content_hash="hash-aapl-1",
        ibkr_conid="265598",
        symbol="AAPL",
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


def _explanation(decision_package_id: str = "dp-1") -> DecisionPackageExplanationRecord:
    return DecisionPackageExplanationRecord(
        explanation_id="exp-1",
        decision_package_id=decision_package_id,
        decision_package_content_hash="hash-aapl-1",
        ibkr_conid="265598",
        symbol="AAPL",
        model_provider_code="stub",
        model_name="deterministic_paraphrase",
        model_version="v1",
        input_evidence_hash="input-hash",
        output_text_hash="output-hash",
        explanation_nl=f"Test uitleg. {LOCKED_RISK_DISCLAIMER_NL}",
        risk_disclaimer_nl=LOCKED_RISK_DISCLAIMER_NL,
        status="generated",
        blocking_reason=None,
        hallucinated_numbers_json=None,
        generated_at=_NOW,
        created_at=_NOW,
    )


def _fake_storage(
    monkeypatch,
    *,
    packages=None,
    explanation_latest=None,
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

    class _FakePackageRepo:
        def list_latest_asset_decision_packages_by_conids(self, _conids):
            return type("_R", (), {"records": tuple(packages or [])})()

        def get_latest_asset_decision_package_by_conid(self, _conid):
            for p in packages or []:
                return type("_R", (), {"found": True, "record": p})()
            return type("_R", (), {"found": False, "record": None})()

    saved_explanations: list = []

    class _FakeExplanationRepo:
        def save_decision_package_explanation(self, record):
            saved_explanations.append(record)

        def save_explanation_evidence_ledger_entry(self, record):
            pass

        def get_latest_explanation_for_package(self, _decision_package_id):
            if explanation_latest is not None:
                return type(
                    "_R", (), {"found": True, "record": explanation_latest}
                )()
            if saved_explanations:
                return type(
                    "_R", (), {"found": True, "record": saved_explanations[-1]}
                )()
            return type("_R", (), {"found": False, "record": None})()

    class _FakeResearchRepo:
        def list_research_sources_for_asset(self, _symbol):
            return ()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetDecisionPackageRepository",
        lambda *a, **k: _FakePackageRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyDecisionPackageExplanationRepository",
        lambda *a, **k: _FakeExplanationRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyResearchSourceArchiveRepository",
        lambda *a, **k: _FakeResearchRepo(),
    )
    return saved_explanations


def test_run_explanation_blocked_when_ai_disabled() -> None:
    r = client.post("/decision-packages/dp-1/explanation")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "ai_explanation_disabled"
    assert body["safe_for_self_learning"] is False


def test_run_explanation_blocked_when_storage_not_writable() -> None:
    api_settings.ai_explanation_enabled = True
    r = client.post("/decision-packages/dp-1/explanation")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_run_explanation_404_when_package_missing(monkeypatch) -> None:
    api_settings.ai_explanation_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(monkeypatch, packages=[])

    r = client.post("/decision-packages/dp-missing/explanation")
    assert r.status_code == 404


def test_run_explanation_happy_path_with_stub_provider(monkeypatch) -> None:
    api_settings.ai_explanation_enabled = True
    api_settings.ai_explanation_provider_code = "stub"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    saved = _fake_storage(monkeypatch, packages=[_package()])

    r = client.post("/decision-packages/dp-1/explanation")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "generated"
    assert body["explanation_id"] is not None
    assert body["blocking_reason"] is None
    assert body["hallucinated_numbers"] == []
    assert body["safe_for_self_learning"] is False
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False
    assert body["explanation"] is not None
    assert body["explanation"]["risk_disclaimer_nl"] == LOCKED_RISK_DISCLAIMER_NL
    assert len(saved) == 1


def test_read_explanation_returns_not_configured_without_storage() -> None:
    r = client.get("/decision-packages/dp-1/explanation")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"


def test_read_explanation_returns_latest_record(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, explanation_latest=_explanation())

    r = client.get("/decision-packages/dp-1/explanation")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["item"]["explanation_id"] == "exp-1"
    assert body["item"]["status"] == "generated"
    assert body["item"]["safe_for_orders"] is False


def test_read_explanation_returns_not_found_when_missing(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch)

    r = client.get("/decision-packages/dp-1/explanation")
    body = r.json()
    assert body["status"] == "not_found"
