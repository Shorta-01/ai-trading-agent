"""Tests for /pauze endpoints (V1.2 §AY)."""

from __future__ import annotations

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "pauze.sqlite")
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


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


# ---- GET /pauze -----------------------------------------------------


def test_status_returns_draaiend_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/pauze").json()
    assert body["paused"] is False
    assert body["paused_at"] is None


def test_status_returns_draaiend_when_no_config_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    body = _client(db).get("/pauze").json()
    assert body["paused"] is False
    assert "draait" in body["summary_nl"].lower()


# ---- POST /pauze ----------------------------------------------------


def test_pauze_sets_paused_true_with_timestamp(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    client = _client(db)
    body = client.post("/pauze").json()
    assert body["paused"] is True
    assert body["paused_at"] is not None
    assert "gepauzeerd" in body["summary_nl"].lower()


def test_pauze_persists_across_requests(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    client = _client(db)
    client.post("/pauze")
    body = client.get("/pauze").json()
    assert body["paused"] is True


def test_pauze_is_idempotent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Pauzeren wanneer al gepauzeerd refresht het timestamp, geen error."""

    db = _seed_db(tmp_path)
    client = _client(db)
    first = client.post("/pauze").json()
    second = client.post("/pauze").json()
    assert first["paused"] is True
    assert second["paused"] is True


# ---- POST /pauze/hervat --------------------------------------------


def test_hervat_clears_paused_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    client = _client(db)
    client.post("/pauze")
    body = client.post("/pauze/hervat").json()
    assert body["paused"] is False
    assert body["paused_at"] is None


def test_hervat_is_idempotent_when_already_running(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    client = _client(db)
    body = client.post("/pauze/hervat").json()
    assert body["paused"] is False


# ---- is_software_paused helper -------------------------------------


def test_is_software_paused_returns_false_when_storage_disabled() -> None:
    from portfolio_outlook_api.pauze_routes import is_software_paused

    _disable_storage()
    assert is_software_paused() is False


def test_is_software_paused_reflects_post_pauze(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from portfolio_outlook_api.pauze_routes import is_software_paused

    db = _seed_db(tmp_path)
    client = _client(db)
    assert is_software_paused() is False
    client.post("/pauze")
    assert is_software_paused() is True
    client.post("/pauze/hervat")
    assert is_software_paused() is False


# ---- Morning-chain skip -------------------------------------------


def test_orchestrator_scoring_leg_skips_when_paused(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """De morning-chain leg moet "skipped" returnen wanneer software
    op pauze staat — verifieert de doctrine §11 wiring."""

    from portfolio_outlook_api.morning_chain import LEG_STATUS_SKIPPED
    from portfolio_outlook_api.orchestrator_scoring_leg import (
        build_real_orchestrator_scoring_leg,
    )

    db = _seed_db(tmp_path)
    client = _client(db)
    # Storage on + scoring enabled — without pauze the leg would
    # proceed (no forecasts in DB → "geen forecasts beschikbaar"
    # succeeded). After pauze it should return SKIPPED instead.
    api_settings.orchestrator_scoring_enabled = True
    try:
        client.post("/pauze")
        leg = build_real_orchestrator_scoring_leg(api_settings)
        outcome = leg()
        assert outcome.status == LEG_STATUS_SKIPPED
        assert "gepauzeerd" in outcome.detail_nl
    finally:
        api_settings.orchestrator_scoring_enabled = False
        client.post("/pauze/hervat")
