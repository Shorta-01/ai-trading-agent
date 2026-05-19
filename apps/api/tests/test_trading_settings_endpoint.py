from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def test_trading_settings_endpoint_returns_read_only_defaults() -> None:
    response = client.get('/settings/trading')

    assert response.status_code == 200
    body = response.json()

    assert body['title_nl'] == 'Trading instellingen'
    assert 'mag onderzoeken' in body['message_nl']
    assert body['safety_summary_nl'] == (
        'Toegestane beleggingen zijn harde veiligheidsregels. '
        'Mijn strategie bepaalt alleen voorkeur en rangschikking.'
    )

    allowed_universe = body['allowed_universe']
    assert allowed_universe['allow_etfs'] is True
    assert allowed_universe['allow_stocks'] is True
    assert allowed_universe['allow_currencies_watch_only'] is False
    assert allowed_universe['blocked_asset_types'] == [
        'options',
        'futures',
        'leverage',
        'short_selling',
        'crypto',
        'penny_stocks',
        'cfds',
        'complex_derivatives',
    ]

    user_strategy = body['user_strategy']
    assert user_strategy['portfolio_goal'] == 'balanced_growth_risk'
    assert user_strategy['risk_level'] == 'medium'
    assert user_strategy['max_position_pct'] == '10'
    assert user_strategy['min_cash_reserve_pct'] == '5'

    assert body['always_blocked_asset_types'] == allowed_universe['blocked_asset_types']

    help_text_keys = {item['key'] for item in body['help_texts']}
    assert {'allow_etfs', 'allow_stocks', 'allow_currencies_watch_only'}.issubset(help_text_keys)
    assert {'max_position_pct', 'min_cash_reserve_pct', 'currency_preference'}.issubset(help_text_keys)
