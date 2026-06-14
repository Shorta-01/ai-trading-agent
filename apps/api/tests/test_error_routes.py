"""Tests for the central error-log API (GET/report/resolve/delete)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage import (
    CreateSystemEventRequest,
    MigrationReadinessReport,
    MigrationReadinessStatus,
    SqlAlchemySystemEventRepository,
)
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0074_runtime_config_software_pause",
        database_revision_id="0074_runtime_config_software_pause",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _event(event_id: str, *, severity: str, status: str) -> CreateSystemEventRequest:
    return CreateSystemEventRequest(
        system_event_id=event_id,
        created_at=datetime.now(UTC),
        severity=severity,
        category="runtime_error",
        source_service="api",
        source_component="route",
        event_code="unhandled_exception",
        title_nl="Fout",
        message_nl="Er ging iets mis.",
        help_nl="Bekijk de details.",
        technical_summary="ValueError: boom",
        redacted_details_json={"path": "/x"},
        stack_trace_redacted="Traceback ... ValueError: boom",
        related_entity_type=None,
        related_entity_id=None,
        blocks_suggestions=False,
        blocks_writes=False,
        blocks_ai_explanation=False,
        status=status,
        explanation_nl="seed",
    )


def _seed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite+pysqlite:///{tmp_path / 'errors.sqlite'}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0074_runtime_config_software_pause')"
            )
        )
        repo = SqlAlchemySystemEventRepository(conn, _report())
        repo.create_event(_event("err-open", severity="error", status="open"))
        repo.create_event(_event("warn-open", severity="warning", status="open"))
        repo.create_event(_event("err-done", severity="error", status="resolved"))


def test_list_errors_returns_only_open_error_severity_with_detail(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    resp = client.get("/errors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["open_count"] == 1
    assert [e["system_event_id"] for e in body["errors"]] == ["err-open"]
    item = body["errors"][0]
    # Full technical detail is exposed for copy-to-Claude-Code.
    assert item["technical_summary"] == "ValueError: boom"
    assert "Traceback" in item["stack_trace_redacted"]
    assert item["redacted_details_json"] == {"path": "/x"}


def test_report_frontend_error_creates_web_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    resp = client.post(
        "/errors/report",
        json={"message": "TypeError: x is undefined", "component": "ErrorPanel"},
    )
    assert resp.status_code == 201
    assert resp.json()["system_event_id"]
    # Now two open errors (seeded + reported).
    assert client.get("/errors").json()["open_count"] == 2


def test_resolve_error_drops_from_open(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    assert client.post("/errors/err-open/resolve").status_code == 200
    assert client.get("/errors").json()["open_count"] == 0


def test_resolve_missing_returns_404(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    assert client.post("/errors/nope/resolve").status_code == 404


def test_delete_error_removes_and_404_when_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    assert client.delete("/errors/err-open").status_code == 200
    assert client.get("/errors").json()["open_count"] == 0
    # Second delete: already gone.
    assert client.delete("/errors/err-open").status_code == 404


def test_record_error_event_persists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from portfolio_outlook_api.error_routes import record_error_event

    _seed(tmp_path)
    record_error_event(
        source_service="api",
        source_component="/action-draft",
        event_code="unhandled_exception",
        message="ValueError: boom",
        technical_summary="ValueError: boom",
        stack_trace="Traceback ... ValueError: boom",
    )
    body = client.get("/errors").json()
    # Seeded err-open + the auto-recorded one.
    assert body["open_count"] == 2
    assert any(e["event_code"] == "unhandled_exception" for e in body["errors"])


def test_record_error_event_noop_when_storage_disabled() -> None:
    from portfolio_outlook_api.error_routes import record_error_event

    _reset()  # storage disabled
    # Must not raise even though there is nowhere to persist.
    record_error_event(
        source_service="api",
        source_component="/x",
        event_code="unhandled_exception",
        message="boom",
    )


def test_unhandled_exception_handler_records_and_returns_500(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import asyncio

    from fastapi import Request

    from portfolio_outlook_api.error_routes import unhandled_exception_handler

    _seed(tmp_path)
    request = Request(
        {"type": "http", "path": "/boom", "method": "GET", "headers": []}
    )
    response = asyncio.run(
        unhandled_exception_handler(request, ValueError("kaboom"))
    )
    assert response.status_code == 500
    body = client.get("/errors").json()
    assert body["open_count"] == 2
    assert any(e["event_code"] == "unhandled_exception" for e in body["errors"])
