from fastapi.testclient import TestClient

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
    assert body['configured'] is False
    assert body['persisted'] is False
    assert 'title_nl' in body
    assert 'help_nl' in body


def test_setup_defaults() -> None:
    res = client.get('/portfolio/setup/defaults')
    assert res.status_code == 200
    body = res.json()
    assert body['default_base_currency'] == 'eur'
    assert body['default_starting_cash'] == '10000'


def test_setup_preview_valid() -> None:
    res = client.post('/portfolio/setup/preview', json=_valid_payload())
    assert res.status_code == 200
    body = res.json()
    assert body['setup_status'] == 'preview_ready'
    assert body['persisted'] is False
    assert 'preview_not_saved' in body['warning_reasons']
    assert body['positions'] == []
    assert body['orders'] == []
    assert body['title_nl']
    assert body['help_nl']
    assert 'secret' not in body


def test_setup_preview_rejects_missing_confirmation() -> None:
    payload = _valid_payload()
    payload['user_confirmed_no_broker_order'] = False
    res = client.post('/portfolio/setup/preview', json=payload)
    assert res.status_code == 400


def test_setup_preview_rejects_invalid_cash() -> None:
    payload = _valid_payload()
    payload['starting_cash'] = 'geen-getal'
    res = client.post('/portfolio/setup/preview', json=payload)
    assert res.status_code == 400


def test_setup_preview_rejects_non_eur_currency() -> None:
    payload = _valid_payload()
    payload['base_currency'] = 'usd'
    res = client.post('/portfolio/setup/preview', json=payload)
    assert res.status_code == 400
