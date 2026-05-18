from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def test_setup_status() -> None:
    res = client.get('/portfolio/setup/status')
    assert res.status_code == 200
    body = res.json()
    assert body['setup_status'] == 'not_configured'
    assert body['configured'] is False


def test_setup_defaults() -> None:
    res = client.get('/portfolio/setup/defaults')
    assert res.status_code == 200
    body = res.json()
    assert body['default_base_currency'] == 'eur'
    assert body['default_starting_cash'] == '10000'


def test_setup_preview_valid() -> None:
    payload = {
        'base_currency': 'eur',
        'starting_cash': '10000',
        'portfolio_name': 'Mijn paper portefeuille',
        'user_confirmed_paper_only': True,
        'user_confirmed_no_real_money': True,
        'user_confirmed_no_broker_order': True,
    }
    res = client.post('/portfolio/setup/preview', json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body['setup_status'] == 'preview_ready'
    assert body['persisted'] is False
    assert 'preview_not_saved' in body['warning_reasons']
