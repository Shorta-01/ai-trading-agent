"""Tests for the macro-snapshot endpoint (V1.2 §AV)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

_BASE_TS = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    """Don't let one test leak storage URL state into the next —
    shared global ``api_settings.storage`` would otherwise convince
    later unrelated tests they have a database when they don't."""

    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "macro.sqlite")
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
                "('0077_monthly_report_archive')"
            )
        )
    engine.dispose()
    return db_url


def _insert_verdict(
    db_url: str,
    *,
    verdict_id: str,
    macro_details: dict | None,
    decision: str = "suggest",
    generated_at: datetime = _BASE_TS,
    account_ref: str = "default",
) -> None:
    engine = create_engine(db_url, future=True)
    details = {"macro": macro_details}
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orchestrator_scoring_verdicts ("
                "verdict_id, ibkr_account_ref, symbol, ibkr_conid, "
                "forecast_id, generated_at, decision, blocking_reason, "
                "details_json, summary_nl) VALUES ("
                ":vid, :acc, :sym, 1, :fid, :gen, :dec, NULL, "
                ":dj, 'nl')"
            ),
            {
                "vid": verdict_id,
                "acc": account_ref,
                "sym": f"SYM-{verdict_id}",
                "fid": f"fc-{verdict_id}",
                "gen": generated_at.isoformat(),
                "dec": decision,
                "dj": json.dumps(details),
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


def test_returns_onbekend_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/markets/macro-snapshot").json()
    assert body["state"] == "onbekend"
    assert body["severity"] == "info"
    assert body["sample_size"] == 0


def test_returns_onbekend_when_no_verdicts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/markets/macro-snapshot").json()
    assert body["state"] == "onbekend"


def test_returns_rustig_when_favorable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _insert_verdict(
        db,
        verdict_id="v1",
        macro_details={
            "favorable": True,
            "blocking_reason": None,
            "vix_level": "14.5",
            "ma_short_day": "5100",
            "ma_long_day": "5050",
        },
    )
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "rustig"
    assert body["severity"] == "info"
    assert body["vix_level"] == 14.5
    assert body["headline_nl"].lower().startswith("markt-regime rustig")


def test_returns_verhoogd_when_vix_warning(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _insert_verdict(
        db,
        verdict_id="v1",
        macro_details={
            "favorable": False,
            "blocking_reason": "vix_too_high",
            "vix_level": "28.0",
            "ma_short_day": "5100",
            "ma_long_day": "5050",
        },
    )
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "verhoogd"
    assert body["severity"] == "warning"
    assert "VIX 28" in body["headline_nl"]


def test_returns_stress_when_vix_and_ma_both_unfavorable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _insert_verdict(
        db,
        verdict_id="v1",
        macro_details={
            "favorable": False,
            "blocking_reason": "bear_trend",
            "vix_level": "32.0",
            "ma_short_day": "4900",
            "ma_long_day": "5200",
        },
    )
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "stress"
    assert body["severity"] == "critical"
    assert "VIX 32" in body["headline_nl"]
    assert "S&P" in body["headline_nl"]


def test_returns_verhoogd_when_only_ma_bear_trend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _insert_verdict(
        db,
        verdict_id="v1",
        macro_details={
            "favorable": False,
            "blocking_reason": "bear_trend",
            "vix_level": "18.0",
            "ma_short_day": "4900",
            "ma_long_day": "5200",
        },
    )
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "verhoogd"
    assert "S&P-trend negatief" in body["headline_nl"]


def test_picks_latest_batch_only(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Yesterday's run should not pollute the snapshot."""

    db = _seed_db(tmp_path)
    yesterday = _BASE_TS - timedelta(days=1)
    _insert_verdict(
        db,
        verdict_id="old",
        macro_details={
            "favorable": False,
            "vix_level": "35.0",
            "ma_short_day": "4500",
            "ma_long_day": "5200",
        },
        generated_at=yesterday,
    )
    _insert_verdict(
        db,
        verdict_id="new",
        macro_details={
            "favorable": True,
            "vix_level": "14.0",
            "ma_short_day": "5100",
            "ma_long_day": "5050",
        },
    )
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "rustig"


def test_handles_missing_macro_blob(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Old verdicts predating the macro field should not crash."""

    db = _seed_db(tmp_path)
    _insert_verdict(db, verdict_id="v1", macro_details=None)
    body = _client(db).get("/markets/macro-snapshot").json()
    assert body["state"] == "onbekend"
