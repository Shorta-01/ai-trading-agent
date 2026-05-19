from contextlib import contextmanager
from decimal import Decimal

from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    StorageConnectionNotReadyError,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _valid_payload() -> dict[str, object]:
    return {
        'base_currency': 'eur',
        'starting_cash': '10000',
        'portfolio_name': 'Mijn paper portefeuille',
        'user_confirmed_paper_only': True,
        'user_confirmed_no_real_money': True,
        'user_confirmed_no_broker_order': True,
    }


def test_setup_status() -> None:
    res = client.get('/portfolio/setup/status')
    assert res.status_code == 200
    body = res.json()
    assert body['setup_status'] == 'not_configured'


def test_setup_defaults() -> None:
    res = client.get('/portfolio/setup/defaults')
    assert res.status_code == 200
    assert res.json()['default_starting_cash'] == '10000'


def test_setup_preview_storage_disabled(monkeypatch) -> None:
    monkeypatch.setattr(status_routes.settings, 'storage', StorageSettings(enabled=False))
    res = client.post('/portfolio/setup/preview', json=_valid_payload())
    assert res.status_code == 409
    assert 'Opslag staat uit' in res.json()['detail']


def test_setup_preview_storage_enabled_missing_url(monkeypatch) -> None:
    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url=None),
    )
    res = client.post('/portfolio/setup/preview', json=_valid_payload())
    assert res.status_code == 409
    assert 'Database-url ontbreekt' in res.json()['detail']


def test_setup_preview_storage_not_ready(monkeypatch) -> None:
    class FakeProvider:
        def __init__(self, _: object) -> None:
            pass

        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            raise StorageConnectionNotReadyError('not ready')
            yield

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='postgresql://x/y'),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.paper_setup_persistence.StorageConnectionProvider',
        FakeProvider,
    )

    res = client.post('/portfolio/setup/preview', json=_valid_payload())
    assert res.status_code == 409
    assert 'Writes zijn geblokkeerd' in res.json()['detail']


def test_setup_preview_storage_ready_persists(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, _: object) -> None:
            captured['provider_created'] = True

        @contextmanager
        def checked_connection(self, *, require_writable: bool):
            captured['require_writable'] = require_writable
            captured['connection_opened'] = True
            class Conn:
                pass
            readiness = MigrationReadinessReport(
                status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
                database_connected=True,
                migrations_checked_against_database=True,
                offline_inventory_valid=True,
                latest_expected_revision_id='0006',
                database_revision_id='0006',
                persistence_allowed=True,
                blocks_runtime_writes=False,
                explanation_nl='Klaar',
            )
            try:
                yield type('Checked', (), {'connection': Conn(), 'readiness': readiness})()
            finally:
                captured['connection_closed'] = True

    class FakeRepo:
        def __init__(self, connection: object, readiness_report: MigrationReadinessReport) -> None:
            captured['repo_connection'] = connection
            captured['repo_readiness'] = readiness_report

        def create_setup(self, request):
            captured['request_cash_type'] = type(request.starting_cash_amount)
            captured['request_cash_value'] = request.starting_cash_amount
            return type('WriteResult', (), {'accepted': True})()

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='postgresql://x/y'),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.paper_setup_persistence.StorageConnectionProvider',
        FakeProvider,
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.paper_setup_persistence.SqlAlchemyPaperPortfolioSetupRepository',
        FakeRepo,
    )

    res = client.post('/portfolio/setup/preview', json=_valid_payload())
    assert res.status_code == 200
    body = res.json()
    assert body['persisted'] is True
    assert captured['provider_created'] is True
    assert captured['require_writable'] is True
    assert isinstance(captured['repo_readiness'], MigrationReadinessReport)
    assert captured['request_cash_type'] is Decimal
    assert captured['request_cash_value'] == Decimal('10000')
    assert captured['connection_closed'] is True
    assert 'postgresql://' not in str(body)


def test_setup_preview_rejects_invalid_cash_before_storage(monkeypatch) -> None:
    called = {'provider': False}

    class FakeProvider:
        def __init__(self, _: object) -> None:
            called['provider'] = True

    monkeypatch.setattr(
        status_routes.settings,
        'storage',
        StorageSettings(enabled=True, database_url='postgresql://x/y'),
    )
    monkeypatch.setattr(
        'portfolio_outlook_api.paper_setup_persistence.StorageConnectionProvider',
        FakeProvider,
    )

    payload = _valid_payload()
    payload['starting_cash'] = 'geen-getal'
    res = client.post('/portfolio/setup/preview', json=payload)
    assert res.status_code == 400
    assert called['provider'] is False
