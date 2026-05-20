from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from portfolio_outlook_api.config import Settings

VALIDATION_STATUSES = {
    "unvalidated",
    "valid",
    "ambiguous",
    "not_found",
    "unsupported",
    "error",
}


@dataclass(frozen=True)
class IbkrContractCandidate:
    candidate_id: str
    ibkr_conid: str
    symbol: str
    company_name: str | None
    asset_class: str | None
    exchange: str | None
    primary_exchange: str | None
    currency: str | None
    description: str | None
    restricted: bool | None
    raw_secdef_summary: dict[str, object] | None
    source: str
    searched_query: str
    searched_at: str
    validation_status: str


@dataclass(frozen=True)
class IbkrContractValidationResult:
    validation_id: str
    asset_id: str | None
    watchlist_item_id: str | None
    ibkr_conid: str
    symbol: str
    security_type: str | None
    exchange: str | None
    primary_exchange: str | None
    currency: str | None
    validation_status: str
    validation_message: str
    validated_at: str
    source: str
    raw_contract_reference: dict[str, object] | None


class IbkrContractSearchAdapter:
    def search_contracts(
        self, query: str, *, search_name: bool = False
    ) -> list[IbkrContractCandidate]:
        raise NotImplementedError

    def fetch_contract_details(
        self, conid: str, *, security_type: str | None = None
    ) -> IbkrContractValidationResult:
        raise NotImplementedError


class NotConfiguredIbkrContractSearchAdapter(IbkrContractSearchAdapter):
    def search_contracts(
        self, query: str, *, search_name: bool = False
    ) -> list[IbkrContractCandidate]:
        return []

    def fetch_contract_details(
        self, conid: str, *, security_type: str | None = None
    ) -> IbkrContractValidationResult:
        now = datetime.now(UTC).isoformat()
        return IbkrContractValidationResult(
            validation_id=f"ibkr-contract-validation-{uuid4()}",
            asset_id=None,
            watchlist_item_id=None,
            ibkr_conid=conid,
            symbol="",
            security_type=security_type,
            exchange=None,
            primary_exchange=None,
            currency=None,
            validation_status="unsupported",
            validation_message="IBKR contractvalidatie is niet ingesteld.",
            validated_at=now,
            source="ibkr_secdef_info",
            raw_contract_reference=None,
        )


DEFAULT_ADAPTER: IbkrContractSearchAdapter = NotConfiguredIbkrContractSearchAdapter()


def is_contract_search_configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_enabled and settings.ibkr_gateway_url and settings.ibkr_account_id_hint
    )


def search_ibkr_contracts(
    settings: Settings,
    query: str,
    *,
    search_name: bool,
    adapter: IbkrContractSearchAdapter | None = None,
) -> dict[str, object]:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return {
            "configured": is_contract_search_configured(settings),
            "query": normalized_query,
            "items": [],
            "status": "invalid_query",
            "message_nl": "Zoekterm moet minstens 2 tekens hebben.",
        }

    if not is_contract_search_configured(settings):
        return {
            "configured": False,
            "query": normalized_query,
            "items": [],
            "status": "not_configured",
            "message_nl": "IBKR contractzoekfunctie is nog niet ingesteld.",
        }

    active_adapter = adapter or DEFAULT_ADAPTER
    try:
        rows = active_adapter.search_contracts(normalized_query, search_name=search_name)
        return {
            "configured": True,
            "query": normalized_query,
            "items": [row.__dict__ for row in rows],
            "status": "ok",
            "message_nl": "Contractkandidaten opgehaald.",
        }
    except Exception:
        return {
            "configured": True,
            "query": normalized_query,
            "items": [],
            "status": "error",
            "message_nl": "IBKR contractzoekopdracht is mislukt.",
        }


def validate_ibkr_contract(
    settings: Settings,
    conid: str,
    *,
    security_type: str | None,
    adapter: IbkrContractSearchAdapter | None = None,
    asset_id: str | None = None,
    watchlist_item_id: str | None = None,
) -> dict[str, object]:
    normalized_conid = conid.strip()
    if normalized_conid == "":
        return {"status": "invalid", "message_nl": "conid is verplicht."}
    if not is_contract_search_configured(settings):
        return {
            "status": "not_configured",
            "message_nl": "IBKR contractvalidatie is niet ingesteld.",
        }

    active_adapter = adapter or DEFAULT_ADAPTER
    try:
        record = active_adapter.fetch_contract_details(
            normalized_conid, security_type=security_type
        )
        output = record.__dict__.copy()
        output["asset_id"] = asset_id
        output["watchlist_item_id"] = watchlist_item_id
        return {"status": "ok", "validation": output}
    except Exception:
        return {
            "status": "error",
            "message_nl": "IBKR contractvalidatie is mislukt.",
        }
