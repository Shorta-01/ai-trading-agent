"""Tests for PDF export endpoints + auto-archive (V1.2 §BC)."""

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
    db_path = str(tmp_path / "pdf.sqlite")
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
                "('0078_sell_signal_cards')"
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


def test_belasting_pdf_returns_valid_pdf_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get(
        "/belasting/jaaroverzicht.pdf?year=2026"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    # Een geldige PDF begint met "%PDF-".
    assert response.content.startswith(b"%PDF-")


def test_belasting_pdf_attachment_filename(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get(
        "/belasting/jaaroverzicht.pdf?year=2026"
    )
    assert "belasting-2026.pdf" in response.headers["content-disposition"]


def test_belasting_pdf_works_without_storage() -> None:
    _disable_storage()
    response = TestClient(app).get("/belasting/jaaroverzicht.pdf?year=2026")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_belasting_pdf_rejects_invalid_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get(
        "/belasting/jaaroverzicht.pdf?year=1500"
    )
    assert response.status_code == 400


def test_maandrapport_pdf_returns_valid_pdf(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get(
        "/rapporten/maand.pdf?year=2026&month=6"
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert "maandrapport-2026-06.pdf" in response.headers["content-disposition"]


def test_maandrapport_pdf_rejects_invalid_month(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get(
        "/rapporten/maand.pdf?year=2026&month=13"
    )
    assert response.status_code == 400


# ---- Archive endpoints --------------------------------------------


def test_archive_list_empty_when_no_storage() -> None:
    _disable_storage()
    body = TestClient(app).get("/rapporten/archief").json()
    assert body["items"] == []


def test_archive_list_empty_when_no_entries(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/rapporten/archief").json()
    assert body["items"] == []


def test_archive_generate_creates_pdf(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.post(
        "/rapporten/archief/generate", json={"year": 2026, "month": 5}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted"] is True
    assert body["pdf_size_bytes"] > 100  # plausible PDF size


def test_archive_get_returns_pdf_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    client.post(
        "/rapporten/archief/generate", json={"year": 2026, "month": 5}
    )
    response = client.get("/rapporten/archief/2026/5")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_archive_get_404_when_no_entry(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).get("/rapporten/archief/2026/3")
    assert response.status_code == 404


def test_archive_generate_is_idempotent_per_month(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Twee genereer-calls voor dezelfde (year, month) → één entry."""

    client = _client(_seed_db(tmp_path))
    client.post(
        "/rapporten/archief/generate", json={"year": 2026, "month": 5}
    )
    client.post(
        "/rapporten/archief/generate", json={"year": 2026, "month": 5}
    )
    listed = client.get("/rapporten/archief").json()
    assert len(listed["items"]) == 1


def test_archive_list_shows_multiple_months(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    for month in (4, 5, 6):
        client.post(
            "/rapporten/archief/generate",
            json={"year": 2026, "month": month},
        )
    listed = client.get("/rapporten/archief").json()
    assert len(listed["items"]) == 3
    # Newest first.
    assert listed["items"][0]["month"] == 6


def test_archive_generate_rejects_invalid_month(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = _client(_seed_db(tmp_path)).post(
        "/rapporten/archief/generate", json={"year": 2026, "month": 13}
    )
    assert response.status_code == 400
