"""Tests for the orchestrator verdicts API endpoints (V1.2 §AD)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

_BASE_TS = datetime(2026, 6, 12, 9, 0, tzinfo=UTC)


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "verdicts.sqlite")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0072_earnings_events')"
            )
        )
    engine.dispose()
    return db_url


def _insert_verdict(
    db_url: str,
    *,
    verdict_id: str,
    symbol: str = "AAPL",
    decision: str = "suggest",
    blocking_reason: str | None = None,
    generated_at: datetime = _BASE_TS,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orchestrator_scoring_verdicts ("
                "verdict_id, ibkr_account_ref, symbol, ibkr_conid, "
                "forecast_id, generated_at, decision, blocking_reason, "
                "details_json, summary_nl) VALUES ("
                ":vid, 'default', :sym, 1, :fid, :gen, :dec, :br, "
                ":dj, :nl)"
            ),
            {
                "vid": verdict_id,
                "sym": symbol,
                "fid": f"fc-{symbol}",
                "gen": generated_at.isoformat(),
                "dec": decision,
                "br": blocking_reason,
                "dj": json.dumps({"macro": {"favorable": True}}),
                "nl": f"Test summary {symbol}",
            },
        )
    engine.dispose()


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


# ---- summary endpoint ------------------------------------------------


def test_summary_returns_empty_when_storage_disabled() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.get("/orchestrator-verdicts/today")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["by_decision"] == {}
    assert body["latest_generated_at"] is None


def test_summary_returns_empty_with_no_verdicts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts/today")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_summary_counts_by_decision(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_verdict(db_url, verdict_id="v1", symbol="AAPL", decision="suggest")
    _insert_verdict(db_url, verdict_id="v2", symbol="MSFT", decision="suggest")
    _insert_verdict(
        db_url,
        verdict_id="v3",
        symbol="TINY",
        decision="skip_risk_universe",
        blocking_reason="below_min_market_cap",
    )
    _insert_verdict(
        db_url,
        verdict_id="v4",
        symbol="EARN",
        decision="skip_earnings_window",
        blocking_reason="earnings_within_block_window",
    )
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts/today")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["by_decision"]["suggest"] == 2
    assert body["by_decision"]["skip_risk_universe"] == 1
    assert body["by_decision"]["skip_earnings_window"] == 1
    assert body["latest_generated_at"] is not None


def test_summary_filters_to_latest_batch(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Only the most-recent burst counts — yesterday's run shouldn't
    pollute today's summary."""

    db_url = _seed_db(tmp_path)
    yesterday = _BASE_TS - timedelta(days=1)
    _insert_verdict(
        db_url, verdict_id="old", symbol="OLD", decision="suggest",
        generated_at=yesterday,
    )
    _insert_verdict(
        db_url, verdict_id="new", symbol="NEW", decision="suggest"
    )
    client = _client(db_url)
    body = client.get("/orchestrator-verdicts/today").json()
    assert body["total"] == 1
    assert body["by_decision"]["suggest"] == 1


# ---- list endpoint ---------------------------------------------------


def test_list_returns_empty_when_storage_disabled() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.get("/orchestrator-verdicts")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert "Orchestrator" in body["title_nl"]


def test_list_returns_recent_verdicts_newest_first(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_verdict(
        db_url, verdict_id="v1", symbol="AAPL", decision="suggest",
        generated_at=_BASE_TS,
    )
    _insert_verdict(
        db_url, verdict_id="v2", symbol="MSFT", decision="suggest",
        generated_at=_BASE_TS + timedelta(hours=1),
    )
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["symbol"] == "MSFT"  # newest first
    assert items[1]["symbol"] == "AAPL"


def test_list_response_carries_summary_and_details(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_verdict(db_url, verdict_id="v1", symbol="AAPL")
    client = _client(db_url)
    items = client.get("/orchestrator-verdicts").json()["items"]
    assert items[0]["summary_nl"] == "Test summary AAPL"
    assert items[0]["details_json"]["macro"] == {"favorable": True}


def test_list_respects_limit_param(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    for i in range(15):
        _insert_verdict(
            db_url, verdict_id=f"v{i}", symbol=f"T{i:02d}",
            generated_at=_BASE_TS + timedelta(minutes=i),
        )
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts?limit=5")
    items = response.json()["items"]
    assert len(items) == 5


def test_list_rejects_non_positive_limit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts?limit=0")
    assert response.status_code == 400


def test_list_caps_limit_at_500(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    # Request 9999, expect cap to 500 (no crash).
    client = _client(db_url)
    response = client.get("/orchestrator-verdicts?limit=9999")
    assert response.status_code == 200
