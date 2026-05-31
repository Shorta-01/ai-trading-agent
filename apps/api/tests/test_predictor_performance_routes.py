"""Endpoint tests for ``GET /predictors/performance``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    PredictionDiaryPredictorContributionRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import predictor_performance_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _contribution(
    *,
    model_code: str,
    created_at: datetime,
    brier_score: Decimal | None,
    return_spread_pct: Decimal | None = None,
    realised_return_pct: Decimal | None = None,
    realised_direction: str | None = "up",
    contribution_id: str | None = None,
) -> PredictionDiaryPredictorContributionRecord:
    return PredictionDiaryPredictorContributionRecord(
        contribution_id=contribution_id
        or f"contrib-{model_code}-{int(created_at.timestamp())}",
        diary_entry_id="diary-1",
        model_code=model_code,
        model_version="v1",
        predicted_return_pct=Decimal("1.5"),
        predicted_prob_gain=Decimal("0.6"),
        predicted_direction="up",
        realised_return_pct=realised_return_pct,
        realised_direction=realised_direction,
        outcome_label="hit" if brier_score is not None else None,
        brier_score=brier_score,
        return_spread_pct=return_spread_pct,
        explanation_nl=None,
        created_at=created_at,
    )


def _install_fake_storage(
    monkeypatch,
    *,
    records: list[PredictionDiaryPredictorContributionRecord],
) -> None:
    class _Checked:
        connection = object()
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

    class _FakeRepo:
        def list_recent_contributions(self, *, limit: int):
            return type("_R", (), {"records": tuple(records[:limit])})()

    monkeypatch.setattr(
        predictor_performance_routes,
        "StorageConnectionProvider",
        _FakeStorageProvider,
    )
    monkeypatch.setattr(
        predictor_performance_routes,
        "build_database_connection_settings",
        lambda _u: object(),
    )
    monkeypatch.setattr(
        predictor_performance_routes,
        "SqlAlchemyPredictionDiaryPredictorContributionRepository",
        lambda *a, **k: _FakeRepo(),
    )


def test_returns_not_configured_when_storage_disabled() -> None:
    r = client.get("/predictors/performance")
    body = r.json()
    assert body["status"] == "not_configured"
    assert body["predictors"] == []


def test_returns_no_data_when_no_contributions(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _install_fake_storage(monkeypatch, records=[])
    body = client.get("/predictors/performance").json()
    assert body["status"] == "no_data"
    assert body["predictors"] == []


def test_aggregates_groups_by_model_code_with_means(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    now = datetime.now(UTC)
    records = [
        # GBM: lower mean Brier (better)
        _contribution(
            model_code="GBM",
            created_at=now - timedelta(days=5),
            brier_score=Decimal("0.20"),
            return_spread_pct=Decimal("1.0"),
            realised_return_pct=Decimal("3.0"),
            contribution_id="c1",
        ),
        _contribution(
            model_code="GBM",
            created_at=now - timedelta(days=10),
            brier_score=Decimal("0.22"),
            return_spread_pct=Decimal("0.8"),
            realised_return_pct=Decimal("2.5"),
            contribution_id="c2",
        ),
        # Momentum: higher mean Brier (worse)
        _contribution(
            model_code="Momentum",
            created_at=now - timedelta(days=3),
            brier_score=Decimal("0.30"),
            return_spread_pct=Decimal("0.5"),
            realised_return_pct=Decimal("1.0"),
            contribution_id="c3",
        ),
    ]
    _install_fake_storage(monkeypatch, records=records)
    body = client.get("/predictors/performance?lookback_days=30").json()
    assert body["status"] == "ok"
    assert body["total_contributions_considered"] == 3
    assert body["best_model_code"] == "GBM"

    by_code = {p["model_code"]: p for p in body["predictors"]}
    assert by_code["GBM"]["sample_count"] == 2
    assert by_code["GBM"]["realised_sample_count"] == 2
    # (0.20 + 0.22) / 2 = 0.21
    assert by_code["GBM"]["mean_brier_score"] == "0.2100"
    assert by_code["Momentum"]["sample_count"] == 1


def test_excludes_contributions_older_than_lookback(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    now = datetime.now(UTC)
    records = [
        _contribution(
            model_code="GBM",
            created_at=now - timedelta(days=100),  # outside 30d window
            brier_score=Decimal("0.10"),
        ),
        _contribution(
            model_code="GBM",
            created_at=now - timedelta(days=5),
            brier_score=Decimal("0.20"),
        ),
    ]
    _install_fake_storage(monkeypatch, records=records)
    body = client.get("/predictors/performance?lookback_days=30").json()
    assert body["total_contributions_considered"] == 1
    assert body["predictors"][0]["sample_count"] == 1


def test_predictors_without_brier_score_sort_after_those_with(monkeypatch) -> None:
    """An active-but-no-data-yet predictor (realised outcomes not in)
    should still be listed so the operator sees it's there — but after
    those that have a real verdict."""

    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    now = datetime.now(UTC)
    records = [
        # GBM with realised data — should win sort
        _contribution(
            model_code="GBM",
            created_at=now - timedelta(days=5),
            brier_score=Decimal("0.30"),
            realised_return_pct=Decimal("2.0"),
        ),
        # NewPredictor with no Brier (no realised outcome yet)
        _contribution(
            model_code="NewPredictor",
            created_at=now - timedelta(days=2),
            brier_score=None,
            realised_return_pct=None,
            realised_direction=None,
        ),
    ]
    _install_fake_storage(monkeypatch, records=records)
    body = client.get("/predictors/performance").json()
    assert body["best_model_code"] == "GBM"
    assert body["predictors"][0]["model_code"] == "GBM"
    assert body["predictors"][1]["model_code"] == "NewPredictor"
    assert body["predictors"][1]["mean_brier_score"] is None


def test_lookback_days_param_is_clamped() -> None:
    r = client.get("/predictors/performance?lookback_days=0")
    assert r.status_code == 422
    r = client.get("/predictors/performance?lookback_days=9999")
    assert r.status_code == 422
