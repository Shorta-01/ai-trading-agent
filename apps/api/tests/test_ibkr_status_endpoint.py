from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def test_ibkr_status_endpoint_placeholder() -> None:
    response = client.get("/broker/ibkr/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["provider"] == "ibkr"
    assert payload["configured"] is False
    assert payload["connection_status"] == "not_connected"
    assert payload["account_mode_status"] == "unknown"
    assert payload["expected_environment"] == "paper"
    assert payload["account_id_hint_present"] is False
    assert payload["gateway_url_configured"] is False
    assert payload["status_check_enabled"] is False
    assert payload["can_submit_orders"] is False
    assert payload["blocks_orders"] is True
    assert payload["status_nl"] == "Niet gekoppeld"
    assert "nog geen IBKR API-calls" in payload["message_nl"]
    assert "paper-only" in payload["help_nl"]


def test_ibkr_status_endpoint_exposes_no_secrets() -> None:
    payload = client.get("/broker/ibkr/status").json()
    serialized = str(payload).lower()

    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "database_url" not in serialized
    assert "postgres" not in serialized
