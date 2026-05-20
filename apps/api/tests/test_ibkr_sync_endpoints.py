from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.main import app

client = TestClient(app)

def setup_function() -> None:
    ibkr_sync.STORE.runs.clear()
    ibkr_sync.STORE.positions.clear()
    ibkr_sync.STORE.cash.clear()


def test_ibkr_sync_status_not_configured() -> None:
    body = client.get('/ibkr/sync/status').json()
    assert body['configured'] is False


def test_ibkr_sync_run_returns_failed_when_not_configured() -> None:
    body = client.post('/ibkr/sync/run').json()
    assert body['status'] == 'failed'


def test_ibkr_snapshot_endpoints_empty_without_sync_data() -> None:
    assert client.get('/ibkr/portfolio/positions').json()['items'] == []
    assert client.get('/ibkr/account/cash').json()['items'] == []
