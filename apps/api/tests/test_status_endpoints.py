from collections.abc import Iterable

from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)
FORBIDDEN_SECRET_FIELDS = {
    "api_key",
    "password",
    "secret_value",
    "token_value",
    "access_token",
    "refresh_token",
}


def _iter_keys(payload: object) -> Iterable[str]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from _iter_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_keys(item)


def _assert_no_secret_keys(payload: dict[str, object]) -> None:
    found = set(_iter_keys(payload))
    assert FORBIDDEN_SECRET_FIELDS.isdisjoint(found)


def test_system_status_summary() -> None:
    response = client.get("/system/status")
    assert response.status_code == 200
    body = response.json()

    assert body["project_name"] == "AI-Trading-Agent"
    assert body["paper_only"] is True
    assert body["can_create_new_suggestions"] is False

    service_cards = body["services"]
    keys = {card["key"] for card in service_cards}
    assert "api" in keys
    assert "ibkr_paper" in keys
    assert "openai" in keys

    for card in service_cards:
        assert card["label_nl"]
        assert card["help_nl"]

    openai_card = next(card for card in service_cards if card["key"] == "openai")
    assert openai_card["status_nl"] != "Verbonden"

    _assert_no_secret_keys(body)


def test_settings_summary() -> None:
    response = client.get("/settings/summary")
    assert response.status_code == 200
    body = response.json()

    assert body["ibkr"]["status_nl"] == "Niet ingesteld"
    assert body["openai"]["status_nl"] == "Niet ingesteld"
    assert body["ibkr"]["paper_account_required"] is True
    assert body["ibkr"]["live_order_transmission_allowed"] is False
    assert body["openai"]["api_key_configured"] is False

    for section in (body["ibkr"], body["openai"]):
        for field in section["fields_needed_later"]:
            assert field["label_nl"]
            assert field["help_nl"]

    _assert_no_secret_keys(body)


def test_ai_usage_summary() -> None:
    response = client.get("/usage/ai/summary")
    assert response.status_code == 200
    body = response.json()

    assert body["usage_available"] is False
    assert body["estimated_cost_usd"] is None
    assert body["estimated_cost_eur"] is None
    assert body["actual_cost_usd"] is None
    assert "Nog geen OpenAI-koppeling actief" in body["source_nl"]
    assert body["input_tokens"] is None
    assert body["output_tokens"] is None

    _assert_no_secret_keys(body)


def test_integrations_summary() -> None:
    response = client.get("/integrations/summary")
    assert response.status_code == 200
    body = response.json()

    cards = {card["key"]: card for card in body["cards"]}
    assert cards["ibkr"]["configured"] is False
    assert cards["ibkr"]["connected"] is False
    assert cards["openai"]["configured"] is False
    assert cards["openai"]["connected"] is False
    assert cards["openai"]["blocks_related_jobs"] is True
    assert cards["scheduler"]["status_nl"] == "Nog niet actief"
    assert cards["worker"]["status_nl"] == "Nog niet actief"

    _assert_no_secret_keys(body)


def test_dutch_labels_summary() -> None:
    response = client.get("/ui/dutch-labels")
    assert response.status_code == 200
    labels = response.json()["labels"]

    assert labels["system_status"] == "Systeemstatus"
    assert labels["settings"] == "Instellingen"
    assert labels["not_configured"] == "Niet ingesteld"
    assert labels["blocked"] == "Geblokkeerd"
