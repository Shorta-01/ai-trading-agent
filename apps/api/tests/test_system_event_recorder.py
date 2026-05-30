from contextlib import contextmanager
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    StorageConnectionError,
    StorageConnectionNotReadyError,
)

from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.system_event_recorder import (
    ApiSystemEventInput,
    record_api_system_event,
)


class _FakeConn:
    """Fake connection exposing the no-op ``commit()`` the recorder calls."""

    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _payload() -> ApiSystemEventInput:
    return ApiSystemEventInput(
        severity='warning',
        category='storage',
        source_component='api.storage.status',
        event_code='storage_blocked',
        title_nl='Opslag geblokkeerd',
        message_nl='Schrijven is tijdelijk geblokkeerd.',
        help_nl='Controleer migratie-readiness en probeer later opnieuw.',
    )


def _readiness() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id='0007',
        database_revision_id='0007',
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl='Klaar voor writes',
    )


def test_record_event_storage_disabled() -> None:
    called = {'provider': False, 'repo': False}

    def fake_provider_factory(_: object):
        called['provider'] = True
        return object()

    def fake_repo_factory(_: object, __: object):
        called['repo'] = True
        return object()

    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(enabled=False),
        connection_provider_factory=fake_provider_factory,
        repository_factory=fake_repo_factory,
    )

    assert result.recorded is False
    assert result.blocked is True
    assert 'opslag staat uit' in result.message_nl
    assert called['provider'] is False
    assert called['repo'] is False


def test_record_event_storage_enabled_missing_database_url() -> None:
    called = {'provider': False, 'repo': False}

    def fake_provider_factory(_: object):
        called['provider'] = True
        return object()

    def fake_repo_factory(_: object, __: object):
        called['repo'] = True
        return object()

    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(enabled=True, database_url='   '),
        connection_provider_factory=fake_provider_factory,
        repository_factory=fake_repo_factory,
    )

    assert result.recorded is False
    assert result.blocked is True
    assert 'database-url ontbreekt' in result.message_nl
    assert called['provider'] is False
    assert called['repo'] is False


def test_record_event_readiness_not_safe() -> None:
    called = {'repo': False}

    class FakeProvider:
        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            assert require_writable is True
            raise StorageConnectionNotReadyError('not ready')
            yield

    def fake_repo_factory(_: object, __: object):
        called['repo'] = True
        return object()

    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(enabled=True, database_url='postgresql://x/y'),
        connection_provider_factory=lambda _: FakeProvider(),
        repository_factory=fake_repo_factory,
    )

    assert result.recorded is False
    assert result.blocked is True
    assert 'writes geblokkeerd' in result.message_nl
    assert called['repo'] is False


def test_record_event_success() -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            captured['require_writable'] = require_writable
            checked = type('Checked', (), {'connection': _FakeConn(), 'readiness': _readiness()})()
            yield checked

    class FakeRepository:
        def __init__(self, connection: object, readiness_report: MigrationReadinessReport) -> None:
            captured['repo_connection'] = connection
            captured['repo_readiness'] = readiness_report

        def create_event(self, request):
            captured['request'] = request
            return type('WriteResult', (), {'accepted': True})()

    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(enabled=True, database_url='postgresql://x/y'),
        connection_provider_factory=lambda _: FakeProvider(),
        repository_factory=FakeRepository,
        now_provider=lambda: now,
        id_provider=lambda: 'system-event-123',
    )

    assert result.recorded is True
    assert result.system_event_id == 'system-event-123'
    assert captured['require_writable'] is True
    assert isinstance(captured['repo_readiness'], MigrationReadinessReport)
    request = captured['request']
    assert request.system_event_id == 'system-event-123'
    assert request.source_service == 'api'
    assert request.status == 'open'
    assert request.created_at == now


def test_record_event_generic_storage_failure_is_safe() -> None:
    class FakeProvider:
        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            raise StorageConnectionError('failed postgresql://user:pass@host/db?api_key=abc')
            yield

    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(enabled=True, database_url='postgresql://u:p@h/d'),
        connection_provider_factory=lambda _: FakeProvider(),
    )

    assert result.recorded is False
    assert 'veilige foutafhandeling' in result.message_nl
    assert 'postgresql://' not in result.message_nl
    assert 'api_key' not in result.message_nl


def test_record_event_redacted_details_pass_through() -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            yield type('Checked', (), {'connection': _FakeConn(), 'readiness': _readiness()})()

    class FakeRepository:
        def __init__(self, _: object, __: MigrationReadinessReport) -> None:
            pass

        def create_event(self, request):
            captured['request'] = request
            return type('WriteResult', (), {'accepted': True})()

    payload = ApiSystemEventInput(
        severity='error',
        category='storage',
        source_component='api.storage.write',
        event_code='write_failed',
        title_nl='Write mislukt',
        message_nl='Opslagactie mislukt.',
        help_nl='Controleer logboek.',
        redacted_details_json={'dsn': 'postgresql://***:***@db/app', 'api_key': '***REDACTED***'},
    )

    result = record_api_system_event(
        payload=payload,
        storage_settings=StorageSettings(enabled=True, database_url='postgresql://x/y'),
        connection_provider_factory=lambda _: FakeProvider(),
        repository_factory=FakeRepository,
    )

    assert result.recorded is True
    request = captured['request']
    assert request.redacted_details_json == payload.redacted_details_json
    assert 'super-secret-password' not in result.message_nl
    assert 'sk-live-123' not in result.message_nl


def test_record_event_persists_to_real_db(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Regression: the recorder must COMMIT so the event survives the
    connection closing (it previously did not, silently losing the row)."""

    from ai_trading_agent_storage import SqlAlchemySystemEventRepository
    from ai_trading_agent_storage.metadata import metadata
    from sqlalchemy import create_engine, text

    db_url = f"sqlite+pysqlite:///{tmp_path / 'events.sqlite'}"
    with create_engine(db_url).begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0057_runtime_config_order_policy')"
            )
        )

    result = record_api_system_event(
        payload=_payload(),
        storage_settings=StorageSettings(
            enabled=True, database_url=db_url, writes_enabled=True
        ),
        id_provider=lambda: "system-event-persist-1",
    )
    assert result.recorded is True

    # Fresh connection -> proves the row was committed, not rolled back.
    with create_engine(db_url).connect() as conn:
        repo = SqlAlchemySystemEventRepository(conn, _readiness())
        found = repo.get_by_id("system-event-persist-1")
    assert found.found is True
    assert found.record is not None
    assert found.record.event_code == "storage_blocked"
