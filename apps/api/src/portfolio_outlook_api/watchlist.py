from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetListingRecord,
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.market_data_readiness import READINESS_BOUNDARY_TEXT_NL

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

VALID_STATUSES = {"valid", "unvalidated", "not_found", "ambiguous", "error", "unsupported"}

class AssetIdentitySummary(BaseModel):
    asset_id: str
    canonical_symbol: str | None = None
    asset_name: str | None = None
    primary_exchange: str | None = None
    primary_currency: str | None = None


class IbkrContractIdentity(BaseModel):
    ibkr_conid: str | None = None
    ibkr_symbol: str | None = None
    ibkr_contract_name: str | None = None
    ibkr_security_type: str | None = None
    ibkr_exchange: str | None = None
    ibkr_primary_exchange: str | None = None
    ibkr_currency: str | None = None
    ibkr_validation_status: str | None = None
    ibkr_validated_at: str | None = None
    ibkr_validation_source: str | None = None


class WatchlistItem(BaseModel):
    watchlist_item_id: str
    asset_id: str | None = None
    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    security_type: str | None = None
    note: str | None = None
    status: str
    source: str
    created_at: str
    updated_at: str
    ibkr_conid: str | None = None
    ibkr_symbol: str | None = None
    ibkr_contract_name: str | None = None
    ibkr_security_type: str | None = None
    ibkr_exchange: str | None = None
    ibkr_primary_exchange: str | None = None
    ibkr_currency: str | None = None
    ibkr_validation_status: str | None = None
    ibkr_validated_at: str | None = None
    ibkr_validation_source: str | None = None


class WatchlistAssetListingLinkStatus(StrEnum):
    MISSING_LISTING = "missing_listing"
    UNVALIDATED_LISTING = "unvalidated_listing"
    VALIDATED_LISTING = "validated_listing"
    STORAGE_UNAVAILABLE = "storage_unavailable"


class WatchlistAssetListingReadiness(BaseModel):
    link_status: WatchlistAssetListingLinkStatus
    listing_id: str | None = None
    asset_id: str | None = None
    ibkr_conid: str | None = None
    symbol: str | None = None
    security_type: str | None = None
    exchange: str | None = None
    primary_exchange: str | None = None
    currency: str | None = None
    validation_status: str | None = None
    validated_at: str | None = None
    market_data_ready: bool = Field(
        description=(
            "Read-only status only: altijd false; geen market-data runtime, "
            "geen runtime-fetch en geen live/current/latest prijs."
        )
    )
    analysis_ready: bool = Field(
        description="Read-only status only: altijd false; geen analysevrijgave."
    )
    suggestions_allowed: bool = Field(
        description=(
            "Read-only status only: altijd false; geen suggesties/"
            "Decision Packages."
        )
    )
    action_drafts_allowed: bool = Field(
        description="Read-only status only: altijd false; geen actiedrafts/orders."
    )
    blocker_code: str | None = None
    status_nl: str
    next_step_nl: str
    audit_help_nl: str = Field(
        description=(
            "Nederlandse auditgrens-tekst: read-only, geen market-data runtime, "
            "geen runtime-fetch, analysevrijgave, suggesties, Decision Packages, "
            "actiedrafts of orders."
        )
    )


class WatchlistItemResponse(BaseModel):
    item: WatchlistItem
    link_status: str
    linked_asset: AssetIdentitySummary | None = None
    ibkr_status_label_nl: str
    analysis_readiness_label_nl: str
    asset_listing_readiness: WatchlistAssetListingReadiness


class CreateWatchlistItemRequest(BaseModel):
    asset_id: str | None = None
    note: str | None = None
    ibkr_conid: str
    ibkr_symbol: str
    ibkr_contract_name: str | None = None
    ibkr_security_type: str | None = None
    ibkr_exchange: str | None = None
    ibkr_primary_exchange: str | None = None
    ibkr_currency: str | None = None
    ibkr_validation_status: str
    ibkr_validated_at: str | None = None
    ibkr_validation_source: str | None = None


class PatchWatchlistItemRequest(BaseModel):
    asset_id: str | None = None
    note: str | None = None


STORE: dict[str, WatchlistItem] = {}


def _norm(value: str | None) -> str:
    return (value or "").strip().upper()


def _with_repository[T](
    operation: Callable[[SqlAlchemyResearchSourceArchiveRepository], T],
) -> T | None:
    storage_settings = settings.storage
    if not storage_settings.enabled:
        return None
    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return None
    provider = StorageConnectionProvider(build_database_connection_settings(database_url))
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyResearchSourceArchiveRepository(checked.connection, checked.readiness)
            return operation(repo)
    except (StorageConnectionError, StoragePersistenceBlockedError):
        return None


def _resolve_asset_summary(
    asset_id: str | None, *, fail_if_missing: bool
) -> AssetIdentitySummary | None:
    if asset_id is None:
        return None

    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> AssetIdentitySummary | None:
        record = repo.get_asset_by_asset_id(asset_id)
        if record is None:
            if fail_if_missing:
                raise HTTPException(status_code=404, detail="Asset-identiteit niet gevonden.")
            return None
        return AssetIdentitySummary(
            asset_id=record.asset_id,
            canonical_symbol=record.canonical_symbol,
            asset_name=record.asset_name,
            primary_exchange=record.primary_exchange,
            primary_currency=record.primary_currency,
        )

    result = _with_repository(op)
    if fail_if_missing and result is None:
        raise HTTPException(status_code=422, detail="Asset-identiteit kon niet worden gevalideerd.")
    return result


def _ibkr_status_label(status: str | None) -> str:
    if status == "valid":
        return "Gevalideerd"
    if status == "ambiguous":
        return "Meerdere matches / keuze nodig"
    if status == "not_found":
        return "Validatie mislukt"
    return "Niet gevalideerd"


def _analysis_readiness(item: WatchlistItem) -> str:
    if item.ibkr_validation_status == "valid" and item.ibkr_conid:
        return "Klaar voor latere data-opbouw"
    return "Niet klaar voor analyse"


def _asset_listing_readiness(item: WatchlistItem) -> WatchlistAssetListingReadiness:
    if not settings.storage.enabled or not settings.storage.database_url:
        return WatchlistAssetListingReadiness(
            link_status=WatchlistAssetListingLinkStatus.STORAGE_UNAVAILABLE,
            ibkr_conid=item.ibkr_conid,
            market_data_ready=False,
            analysis_ready=False,
            suggestions_allowed=False,
            action_drafts_allowed=False,
            blocker_code="storage_unavailable",
            status_nl="AssetListing-opslag niet beschikbaar",
            next_step_nl=(
                "Configureer opslag om AssetListing-identiteit aan de volglijst "
                "te koppelen."
            ),
            audit_help_nl="Read-only koppelstatus. " + READINESS_BOUNDARY_TEXT_NL,
        )
    if not item.ibkr_conid:
        return WatchlistAssetListingReadiness(
            link_status=WatchlistAssetListingLinkStatus.MISSING_LISTING,
            ibkr_conid=None,
            market_data_ready=False,
            analysis_ready=False,
            suggestions_allowed=False,
            action_drafts_allowed=False,
            blocker_code="missing_ibkr_conid",
            status_nl="Geen IBKR-contract gekoppeld",
            next_step_nl=(
                "Voeg eerst een gevalideerd IBKR-contract (conid) toe en koppel "
                "daarna een AssetListing."
            ),
            audit_help_nl=(
                "Zonder contractidentiteit blijft alles geblokkeerd. "
                + READINESS_BOUNDARY_TEXT_NL
            ),
        )

    ibkr_conid = item.ibkr_conid

    def op(repo: SqlAlchemyResearchSourceArchiveRepository) -> AssetListingRecord | None:
        return repo.get_asset_listing_by_ibkr_conid(ibkr_conid)

    listing = _with_repository(op)
    if listing is None:
        return WatchlistAssetListingReadiness(
            link_status=WatchlistAssetListingLinkStatus.MISSING_LISTING,
            ibkr_conid=ibkr_conid,
            market_data_ready=False,
            analysis_ready=False,
            suggestions_allowed=False,
            action_drafts_allowed=False,
            blocker_code="missing_asset_listing",
            status_nl="AssetListing ontbreekt",
            next_step_nl=(
                "Maak of koppel een AssetListing op basis van dit IBKR-contract "
                "vóór latere market-data/analysestappen."
            ),
            audit_help_nl=(
                "AssetListing ontbreekt; status blijft read-only. "
                + READINESS_BOUNDARY_TEXT_NL
            ),
        )

    validated = listing.validation_status == "valid" and listing.safe_to_use_for_market_data
    if not validated:
        return WatchlistAssetListingReadiness(
            link_status=WatchlistAssetListingLinkStatus.UNVALIDATED_LISTING,
            listing_id=listing.listing_id,
            asset_id=listing.asset_id,
            ibkr_conid=listing.ibkr_conid,
            symbol=listing.symbol,
            security_type=listing.security_type,
            exchange=listing.exchange,
            primary_exchange=listing.primary_exchange,
            currency=listing.currency,
            validation_status=listing.validation_status,
            validated_at=listing.validated_at.isoformat() if listing.validated_at else None,
            market_data_ready=False,
            analysis_ready=False,
            suggestions_allowed=False,
            action_drafts_allowed=False,
            blocker_code="listing_not_validated_or_safe",
            status_nl="AssetListing nog niet veilig gevalideerd",
            next_step_nl=(
                "Valideer de listing-identiteit en veiligheidsvlaggen; dit blijft daarna "
                "nog steeds read-only zonder analysevrijgave of runtime-fetch."
            ),
            audit_help_nl="Contractstatus-only. " + READINESS_BOUNDARY_TEXT_NL,
        )

    return WatchlistAssetListingReadiness(
        link_status=WatchlistAssetListingLinkStatus.VALIDATED_LISTING,
        listing_id=listing.listing_id,
        asset_id=listing.asset_id,
        ibkr_conid=listing.ibkr_conid,
        symbol=listing.symbol,
        security_type=listing.security_type,
        exchange=listing.exchange,
        primary_exchange=listing.primary_exchange,
        currency=listing.currency,
        validation_status=listing.validation_status,
        validated_at=listing.validated_at.isoformat() if listing.validated_at else None,
        market_data_ready=False,
        analysis_ready=False,
        suggestions_allowed=False,
        action_drafts_allowed=False,
        blocker_code="runtime_not_active",
        status_nl="AssetListing gevalideerd (read-only)",
        next_step_nl=(
            "Contractstatus gekend, maar dit blijft read-only zonder market-data runtime, "
            "runtime-fetch of analysevrijgave."
        ),
        audit_help_nl="Read-only status. " + READINESS_BOUNDARY_TEXT_NL,
    )


def _serialize_item(item: WatchlistItem) -> WatchlistItemResponse:
    linked_asset = _resolve_asset_summary(item.asset_id, fail_if_missing=False)
    return WatchlistItemResponse(
        item=item,
        link_status=(
            "gelinkt" if item.asset_id is not None and linked_asset is not None else "niet_gelinkt"
        ),
        linked_asset=linked_asset,
        ibkr_status_label_nl=_ibkr_status_label(item.ibkr_validation_status),
        analysis_readiness_label_nl=_analysis_readiness(item),
        asset_listing_readiness=_asset_listing_readiness(item),
    )


@router.get("/items")
def list_watchlist_items() -> dict[str, object]:
    rows = [row for row in STORE.values() if row.status == "active"]
    return {
        "items": [_serialize_item(row) for row in rows],
        "help_nl": "Geen actief Volglijst-item zonder IBKR-contract.",
    }


@router.post("/items")
def create_watchlist_item(request: CreateWatchlistItemRequest) -> dict[str, object]:
    if _norm(request.ibkr_conid) == "":
        raise HTTPException(status_code=400, detail="IBKR-contract (conid) is verplicht.")
    if request.ibkr_validation_status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Onbekende IBKR-validatiestatus.")
    if request.ibkr_validation_status != "valid":
        raise HTTPException(
            status_code=422, detail="Alleen gevalideerde IBKR-contracten kunnen actief worden."
        )

    symbol = _norm(request.ibkr_symbol)
    if not symbol:
        raise HTTPException(status_code=400, detail="IBKR-symbool is verplicht.")
    _resolve_asset_summary(request.asset_id, fail_if_missing=True)
    normalized_exchange = _norm(request.ibkr_exchange)
    normalized_currency = _norm(request.ibkr_currency)
    for row in STORE.values():
        has_matching_identity = (
            row.status == "active"
            and _norm(row.ibkr_conid) == _norm(request.ibkr_conid)
            and _norm(row.ibkr_exchange) == normalized_exchange
            and _norm(row.ibkr_currency) == normalized_currency
        )
        if has_matching_identity:
            raise HTTPException(
                status_code=409,
                detail="Actief volglijst-item bestaat al voor dit IBKR-contract.",
            )

    now = datetime.now(UTC).isoformat()
    item = WatchlistItem(
        watchlist_item_id=f"watchlist-{uuid4()}",
        symbol=symbol,
        asset_id=request.asset_id,
        name=request.ibkr_contract_name,
        exchange=request.ibkr_exchange,
        currency=request.ibkr_currency,
        security_type=request.ibkr_security_type,
        note=request.note,
        status="active",
        source="manual",
        created_at=now,
        updated_at=now,
        ibkr_conid=request.ibkr_conid,
        ibkr_symbol=symbol,
        ibkr_contract_name=request.ibkr_contract_name,
        ibkr_security_type=request.ibkr_security_type,
        ibkr_exchange=request.ibkr_exchange,
        ibkr_primary_exchange=request.ibkr_primary_exchange,
        ibkr_currency=request.ibkr_currency,
        ibkr_validation_status=request.ibkr_validation_status,
        ibkr_validated_at=request.ibkr_validated_at or now,
        ibkr_validation_source=request.ibkr_validation_source or "ibkr_secdef_info",
    )
    STORE[item.watchlist_item_id] = item
    return {
        "item": _serialize_item(item),
        "message_nl": "Volglijst-item toegevoegd met gevalideerd IBKR-contract.",
    }


@router.get("/items/{watchlist_item_id}")
def get_watchlist_item(watchlist_item_id: str) -> dict[str, object]:
    item = STORE.get(watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Volglijst-item niet gevonden.")
    return {"item": _serialize_item(item)}


@router.patch("/items/{watchlist_item_id}")
def patch_watchlist_item(
    watchlist_item_id: str, request: PatchWatchlistItemRequest
) -> dict[str, object]:
    item = STORE.get(watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Volglijst-item niet gevonden.")
    _resolve_asset_summary(request.asset_id, fail_if_missing=True)
    data = item.model_dump()
    for key, value in request.model_dump(exclude_unset=True).items():
        data[key] = value
    data["updated_at"] = datetime.now(UTC).isoformat()
    updated = WatchlistItem(**data)
    STORE[watchlist_item_id] = updated
    return {"item": _serialize_item(updated), "message_nl": "Volglijst-item bijgewerkt."}


@router.delete("/items/{watchlist_item_id}")
def archive_watchlist_item(watchlist_item_id: str) -> dict[str, object]:
    item = STORE.get(watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Volglijst-item niet gevonden.")
    data = item.model_dump()
    data["status"] = "archived"
    data["updated_at"] = datetime.now(UTC).isoformat()
    STORE[watchlist_item_id] = WatchlistItem(**data)
    return {"archived": True, "message_nl": "Volglijst-item gearchiveerd."}
