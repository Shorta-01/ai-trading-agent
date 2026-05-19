from ai_trading_agent_storage import MigrationReadinessReport, MigrationReadinessStatus
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeEngine:
    def __init__(self, should_fail_connect: bool = False) -> None:
        self.should_fail_connect = should_fail_connect
        self.disposed = False
        self.connection = FakeConnection()

    def connect(self) -> FakeConnection:
        if self.should_fail_connect:
            raise ValueError("boom")
        return self.connection

    def dispose(self) -> None:
        self.disposed = True


def test_online_storage_status_disabled_no_engine(monkeypatch) -> None:
    monkeypatch.setattr(status_routes.settings, "storage", StorageSettings(enabled=False))
    client = TestClient(app)
    response = client.get('/storage/status/online')
    assert response.status_code == 200
    data = response.json()
    assert data['configured'] is False
    assert data['connected'] is False
    assert data['safe_to_write'] is False
    assert data['status_nl'] == 'Niet geconfigureerd'
    assert data['writes_status_nl'] == 'Writes geblokkeerd'


def test_online_storage_status_enabled_missing_url_no_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url=None),
    )
    client = TestClient(app)
    response = client.get('/storage/status/online')
    assert response.status_code == 200
    data = response.json()
    assert data['configured'] is False
    assert data['connected'] is False
    assert data['safe_to_write'] is False
    assert data['message_nl'].startswith('Database-url ontbreekt')


def test_online_storage_status_success_connection_lifecycle(monkeypatch) -> None:
    created: list[FakeEngine] = []
    checker_connections: list[FakeConnection] = []

    def fake_engine_factory(_: str) -> FakeEngine:
        engine = FakeEngine()
        created.append(engine)
        return engine

    def fake_readiness_checker(connection: FakeConnection) -> MigrationReadinessReport:
        checker_connections.append(connection)
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
            database_connected=True,
            migrations_checked_against_database=True,
            offline_inventory_valid=True,
            latest_expected_revision_id="0006",
            database_revision_id="0006",
            persistence_allowed=True,
            blocks_runtime_writes=False,
            explanation_nl="Migraties klaar.",
        )

    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.online_storage_status.create_engine",
        fake_engine_factory,
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.online_storage_status.check_online_migration_readiness",
        fake_readiness_checker,
    )

    client = TestClient(app)
    response = client.get('/storage/status/online')
    assert response.status_code == 200
    data = response.json()

    assert len(created) == 1
    assert len(checker_connections) == 1
    assert checker_connections[0] is created[0].connection
    assert created[0].connection.closed is True
    assert created[0].disposed is True
    assert data['configured'] is True
    assert data['connected'] is True
    assert data['safe_to_write'] is True
    assert 'postgresql://' not in str(data)


def test_online_storage_status_connection_failure(monkeypatch) -> None:
    def fake_engine_factory(_: str) -> FakeEngine:
        return FakeEngine(should_fail_connect=True)

    monkeypatch.setattr(
        status_routes.settings,
        "storage",
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
    )
    monkeypatch.setattr(
        "portfolio_outlook_api.online_storage_status.create_engine",
        fake_engine_factory,
    )

    client = TestClient(app)
    response = client.get('/storage/status/online')
    assert response.status_code == 200
    data = response.json()
    assert data['connected'] is False
    assert data['safe_to_write'] is False
    assert data['status_nl'] == 'Geblokkeerd'
    assert data['message_nl'] == 'Database niet bereikbaar'
    assert 'user:pass' not in str(data)
