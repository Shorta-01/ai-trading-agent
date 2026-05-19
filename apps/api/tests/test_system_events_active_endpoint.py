from datetime import UTC, datetime

from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    StorageConnectionError,
    SystemEventRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.system_event_reader import list_active_system_events


def _readiness() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0007",
        database_revision_id="0007",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="Migraties klaar.",
    )


def test_active_events_storage_disabled_no_provider(monkeypatch) -> None:
    called = False

    def factory(_):
        nonlocal called
        called = True
        raise AssertionError("provider should not be created")

    monkeypatch.setattr(status_routes.settings, "storage", StorageSettings(enabled=False))
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.list_active_system_events",
        lambda storage: list_active_system_events(storage, connection_provider_factory=factory),
    )
    client = TestClient(app)
    response = client.get('/system/events/active')
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["active_count"] == 0
    assert "opslag staat uit" in data["message_nl"].lower()
    assert called is False


def test_active_events_storage_enabled_missing_url_no_provider(monkeypatch) -> None:
    called = False

    def factory(_):
        nonlocal called
        called = True
        raise AssertionError("provider should not be created")

    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url=None),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.list_active_system_events",
        lambda storage: list_active_system_events(storage, connection_provider_factory=factory),
    )

    client = TestClient(app)
    response = client.get('/system/events/active')
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["active_count"] == 0
    assert "database-url ontbreekt" in data["message_nl"].lower()
    assert called is False


def test_active_events_loaded_read_only_connection(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, _settings) -> None:
            captured["provider_created"] = True

        def checked_connection(self, *, require_writable: bool):
            captured["require_writable"] = require_writable

            class _Ctx:
                def __enter__(self_inner):
                    checked = type(
                        "Checked", (), {"connection": object(), "readiness": _readiness()}
                    )()
                    return checked

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

    class FakeRepository:
        def __init__(self, connection, readiness) -> None:
            captured["repository_connection"] = connection
            captured["repository_readiness"] = readiness

        def list_open_events(self):
            captured["list_open_events_called"] = True
            return type(
                "Result",
                (),
                {
                    "records": (
                        SystemEventRecord(
                            system_event_id="evt-1",
                            created_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
                            severity="error",
                            category="storage",
                            source_service="api",
                            source_component="status",
                            event_code="STORAGE_BLOCKED",
                            title_nl="Opslag geblokkeerd",
                            message_nl="Opslag is niet beschikbaar.",
                            help_nl="Controleer databaseverbinding.",
                            technical_summary="safe",
                            redacted_details_json={"safe": "value"},
                            stack_trace_redacted="trace",
                            related_entity_type=None,
                            related_entity_id=None,
                            blocks_suggestions=True,
                            blocks_writes=True,
                            blocks_ai_explanation=False,
                            status="open",
                            resolved_at=None,
                            archived_at=None,
                            copied_for_codex_at=None,
                            explanation_nl="Uitleg",
                        ),
                    )
                },
            )()

    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.list_active_system_events",
        lambda storage: list_active_system_events(
            storage,
            connection_provider_factory=FakeProvider,
            repository_factory=FakeRepository,
        ),
    )

    client = TestClient(app)
    response = client.get('/system/events/active')
    assert response.status_code == 200
    data = response.json()
    assert captured["provider_created"] is True
    assert captured["require_writable"] is False
    assert captured["list_open_events_called"] is True
    assert data["available"] is True
    assert data["events_loaded"] is True
    assert data["active_count"] == 1
    assert data["events"][0]["system_event_id"] == "evt-1"
    assert "database_url" not in str(data)
    assert "user:pass" not in str(data)
    assert "redacted_details_json" not in data["events"][0]
    assert "stack_trace_redacted" not in data["events"][0]


def test_active_events_connection_failure_returns_safe_response(monkeypatch) -> None:
    class FailingProvider:
        def __init__(self, _settings) -> None:
            pass

        def checked_connection(self, *, require_writable: bool):
            raise StorageConnectionError("postgresql://user:pass@db/app")

    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.status_routes.list_active_system_events",
        lambda storage: list_active_system_events(
            storage,
            connection_provider_factory=FailingProvider,
        ),
    )

    client = TestClient(app)
    response = client.get('/system/events/active')
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["active_count"] == 0
    assert "veilige foutafhandeling" in data["message_nl"].lower()
    assert "postgresql://" not in str(data)
    assert "user:pass" not in str(data)
