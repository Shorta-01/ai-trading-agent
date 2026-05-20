from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_contracts
from portfolio_outlook_api.config import settings
from portfolio_outlook_api.ibkr_contracts import (
    IbkrContractCandidate,
    IbkrContractSearchAdapter,
    IbkrContractValidationResult,
)
from portfolio_outlook_api.main import app

client = TestClient(app)


class FakeContractAdapter(IbkrContractSearchAdapter):
    def search_contracts(self, query: str, *, search_name: bool = False):
        if query == "none":
            return []
        return [
            IbkrContractCandidate(
                candidate_id="cand-1",
                ibkr_conid="265598",
                symbol="AAPL",
                company_name="Apple Inc",
                asset_class="STK",
                exchange="SMART",
                primary_exchange="NASDAQ",
                currency="USD",
                description="NASDAQ listing",
                restricted=False,
                raw_secdef_summary={"conid": "265598"},
                source="ibkr_secdef_search",
                searched_query=query,
                searched_at="2026-05-20T00:00:00Z",
                validation_status="unvalidated",
            )
        ]

    def fetch_contract_details(self, conid: str, *, security_type: str | None = None):
        if conid != "265598":
            return IbkrContractValidationResult(
                validation_id="val-not-found",
                asset_id=None,
                watchlist_item_id=None,
                ibkr_conid=conid,
                symbol="",
                security_type=security_type,
                exchange=None,
                primary_exchange=None,
                currency=None,
                validation_status="not_found",
                validation_message="Niet gevonden.",
                validated_at="2026-05-20T00:00:00Z",
                source="ibkr_secdef_info",
                raw_contract_reference=None,
            )
        return IbkrContractValidationResult(
            validation_id="val-1",
            asset_id=None,
            watchlist_item_id=None,
            ibkr_conid="265598",
            symbol="AAPL",
            security_type=security_type or "STK",
            exchange="SMART",
            primary_exchange="NASDAQ",
            currency="USD",
            validation_status="valid",
            validation_message="Gevalideerd.",
            validated_at="2026-05-20T00:00:00Z",
            source="ibkr_secdef_info",
            raw_contract_reference={"conid": "265598"},
        )


def test_contract_search_short_query_safe_response() -> None:
    body = client.get("/ibkr/contracts/search?query=A").json()
    assert body["status"] == "invalid_query"
    assert body["items"] == []


def test_contract_search_not_configured_returns_empty() -> None:
    body = client.get("/ibkr/contracts/search?query=apple").json()
    assert body["status"] == "not_configured"
    assert body["items"] == []


def test_contract_search_and_validate_from_fake_adapter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ibkr_enabled", True)
    monkeypatch.setattr(settings, "ibkr_gateway_url", "https://example")
    monkeypatch.setattr(settings, "ibkr_account_id_hint", "DU123")
    monkeypatch.setattr(ibkr_contracts, "DEFAULT_ADAPTER", FakeContractAdapter())

    search = client.get("/ibkr/contracts/search?query=apple&name=true").json()
    assert search["status"] == "ok"
    assert search["items"][0]["ibkr_conid"] == "265598"

    details = client.get("/ibkr/contracts/265598/details?security_type=STK").json()
    assert details["status"] == "ok"
    assert details["validation"]["validation_status"] == "valid"


def test_contract_validate_unknown_conid_safe_not_found(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ibkr_enabled", True)
    monkeypatch.setattr(settings, "ibkr_gateway_url", "https://example")
    monkeypatch.setattr(settings, "ibkr_account_id_hint", "DU123")
    monkeypatch.setattr(ibkr_contracts, "DEFAULT_ADAPTER", FakeContractAdapter())

    body = client.post(
        "/ibkr/contracts/validate",
        json={"ibkr_conid": "999999", "security_type": "STK"},
    ).json()
    assert body["status"] == "ok"
    assert body["validation"]["validation_status"] == "not_found"
