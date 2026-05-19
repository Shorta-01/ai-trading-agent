from ai_trading_agent_storage import MigrationReadinessReport, MigrationReadinessStatus

from portfolio_outlook_worker.config import StorageSettings
from portfolio_outlook_worker.storage_readiness import build_worker_storage_readiness


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


def test_worker_storage_readiness_disabled_no_engine() -> None:
    called = False

    def fake_engine_factory(_: str) -> FakeEngine:
        nonlocal called
        called = True
        return FakeEngine()

    response = build_worker_storage_readiness(
        StorageSettings(enabled=False),
        engine_factory=fake_engine_factory,
    )

    assert called is False
    assert response.configured is False
    assert response.connected is False
    assert response.safe_to_write is False
    assert response.status_nl == "Niet geconfigureerd"
    assert response.writes_status_nl == "Writes geblokkeerd"


def test_worker_storage_readiness_enabled_missing_url_no_engine() -> None:
    called = False

    def fake_engine_factory(_: str) -> FakeEngine:
        nonlocal called
        called = True
        return FakeEngine()

    response = build_worker_storage_readiness(
        StorageSettings(enabled=True, database_url=None),
        engine_factory=fake_engine_factory,
    )

    assert called is False
    assert response.configured is False
    assert response.connected is False
    assert response.safe_to_write is False
    assert response.status_nl == "Geblokkeerd"
    assert response.message_nl == "Database-url ontbreekt. Niet verbonden."


def test_worker_storage_readiness_success_connection_lifecycle() -> None:
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

    response = build_worker_storage_readiness(
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
        engine_factory=fake_engine_factory,
        readiness_checker=fake_readiness_checker,
    )

    assert len(created) == 1
    assert len(checker_connections) == 1
    assert checker_connections[0] is created[0].connection
    assert created[0].connection.closed is True
    assert created[0].disposed is True
    assert response.configured is True
    assert response.connected is True
    assert response.safe_to_write is True
    assert "postgresql://" not in str(response.model_dump())


def test_worker_storage_readiness_connection_failure() -> None:
    created: list[FakeEngine] = []

    def fake_engine_factory(_: str) -> FakeEngine:
        engine = FakeEngine(should_fail_connect=True)
        created.append(engine)
        return engine

    response = build_worker_storage_readiness(
        StorageSettings(enabled=True, database_url="postgresql://user:pass@db/app"),
        engine_factory=fake_engine_factory,
    )

    assert len(created) == 1
    assert created[0].disposed is True
    assert response.connected is False
    assert response.safe_to_write is False
    assert response.status_nl == "Geblokkeerd"
    assert response.message_nl == "Database niet bereikbaar"
    assert "user:pass" not in str(response.model_dump())
