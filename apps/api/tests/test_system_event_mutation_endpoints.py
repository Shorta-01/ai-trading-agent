from contextlib import contextmanager

from ai_trading_agent_storage import StorageConnectionNotReadyError
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app

client = TestClient(app)


class _FakeConn:
    """Fake connection exposing the no-op ``commit()`` the mutation calls."""

    def commit(self) -> None:
        return None


def test_resolve_storage_disabled_no_provider(monkeypatch) -> None:
    called = {'provider': False}

    class FakeProvider:
        def __init__(self, _settings) -> None:
            called['provider'] = True

    monkeypatch.setattr(status_routes.settings, 'storage', StorageSettings(enabled=False))
    monkeypatch.setattr(
        'portfolio_outlook_api.system_event_mutations.StorageConnectionProvider',
        FakeProvider,
    )

    res = client.post('/system/events/evt-1/resolve', json={'reason_nl': 'klaar'})
    assert res.status_code == 409
    assert 'Opslag staat uit' in res.json()['detail']
    assert called['provider'] is False


def test_archive_missing_database_url_no_provider(monkeypatch) -> None:
    called = {'provider': False}

    class FakeProvider:
        def __init__(self, _settings) -> None:
            called['provider'] = True

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='  '),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.system_event_mutations.StorageConnectionProvider',
        FakeProvider,
    )

    res = client.post('/system/events/evt-1/archive', json={})
    assert res.status_code == 409
    assert 'Database-url ontbreekt' in res.json()['detail']
    assert called['provider'] is False


def test_resolve_not_ready_blocks_write(monkeypatch) -> None:
    class FakeProvider:
        def __init__(self, _settings) -> None:
            pass

        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            assert require_writable is True
            raise StorageConnectionNotReadyError('not ready')
            yield

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='postgresql://x/y'),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.system_event_mutations.StorageConnectionProvider',
        FakeProvider,
    )

    res = client.post('/system/events/evt-1/resolve', json={})
    assert res.status_code == 409
    assert 'Writes zijn geblokkeerd' in res.json()['detail']


def test_mutation_success_and_not_found(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, _settings) -> None:
            captured['provider'] = True

        def checked_connection(self, *, require_writable: bool):
            captured['require_writable'] = require_writable

            class _Ctx:
                def __enter__(self_inner):
                    return type('Checked', (), {'connection': _FakeConn(), 'readiness': object()})()

                def __exit__(self_inner, exc_type, exc, tb):
                    captured['closed'] = True
                    return False

            return _Ctx()

    class FakeRepo:
        def __init__(self, connection, readiness) -> None:
            captured['repo_connection'] = connection
            captured['repo_readiness'] = readiness

        def mark_resolved(self, system_event_id: str, *, reason_nl: str | None = None):
            captured['resolved_id'] = system_event_id
            captured['resolved_reason'] = reason_nl
            return type('WriteResult', (), {'accepted': True})()

        def mark_archived(self, system_event_id: str, *, reason_nl: str | None = None):
            captured['archived_id'] = system_event_id
            return type('WriteResult', (), {'accepted': False})()

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='postgresql://user:pass@db/app'),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.system_event_mutations.StorageConnectionProvider',
        FakeProvider,
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.system_event_mutations.SqlAlchemySystemEventRepository',
        FakeRepo,
    )

    ok = client.post('/system/events/evt-ok/resolve', json={'reason_nl': 'Handmatig opgelost'})
    assert ok.status_code == 200
    assert ok.json()['updated'] is True
    assert captured['require_writable'] is True
    assert captured['resolved_id'] == 'evt-ok'
    assert captured['resolved_reason'] == 'Handmatig opgelost'

    missing = client.post('/system/events/evt-missing/archive', json={})
    assert missing.status_code == 404
    assert 'niet gevonden' in missing.json()['detail'].lower()
