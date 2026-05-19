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

    def fake_engine_factory(_: str) -> FakeEngine:
        engine = FakeEngine()
        created.append(engine)
        return engine

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

    assert len(created) == 1
    assert created[0].connection.closed is True
    assert created[0].disposed is True
    assert data['configured'] is True
    assert data['connected'] in {True, False}
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
