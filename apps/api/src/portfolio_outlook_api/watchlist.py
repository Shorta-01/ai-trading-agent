from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import (
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AssetIdentitySummary(BaseModel):
    asset_id: str
    canonical_symbol: str | None = None
    asset_name: str | None = None
    primary_exchange: str | None = None
    primary_currency: str | None = None


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


class WatchlistItemResponse(BaseModel):
    item: WatchlistItem
    link_status: str
    linked_asset: AssetIdentitySummary | None = None


class CreateWatchlistItemRequest(BaseModel):
    symbol: str
    asset_id: str | None = None
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    security_type: str | None = None
    note: str | None = None


class PatchWatchlistItemRequest(BaseModel):
    asset_id: str | None = None
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    security_type: str | None = None
    note: str | None = None


STORE: dict[str, WatchlistItem] = {}


def _norm(value: str | None) -> str:
    return (value or "").strip().upper()


def _with_repository(
    operation: Callable[[SqlAlchemyResearchSourceArchiveRepository], AssetIdentitySummary | None],
) -> AssetIdentitySummary | None:
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


def _serialize_item(item: WatchlistItem) -> WatchlistItemResponse:
    linked_asset = _resolve_asset_summary(item.asset_id, fail_if_missing=False)
    return WatchlistItemResponse(
        item=item,
        link_status=(
            "gelinkt" if item.asset_id is not None and linked_asset is not None else "niet_gelinkt"
        ),
        linked_asset=linked_asset,
    )


@router.get("/items")
def list_watchlist_items() -> dict[str, object]:
    rows = [row for row in STORE.values() if row.status == "active"]
    return {
        "items": [_serialize_item(row) for row in rows],
        "help_nl": "Lokale volglijstitems, gescheiden van IBKR-portefeuille.",
    }


@router.post("/items")
def create_watchlist_item(request: CreateWatchlistItemRequest) -> dict[str, object]:
    symbol = _norm(request.symbol)
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbool is verplicht.")
    _resolve_asset_summary(request.asset_id, fail_if_missing=True)
    normalized_exchange = _norm(request.exchange)
    normalized_currency = _norm(request.currency)
    for row in STORE.values():
        has_matching_identity = (
            row.status == "active"
            and _norm(row.symbol) == symbol
            and _norm(row.exchange) == normalized_exchange
            and _norm(row.currency) == normalized_currency
        )
        if has_matching_identity:
            raise HTTPException(
                status_code=409,
                detail="Actief volglijst-item bestaat al voor dit symbool/beurs/valuta.",
            )

    now = datetime.now(UTC).isoformat()
    item = WatchlistItem(
        watchlist_item_id=f"watchlist-{uuid4()}",
        symbol=symbol,
        asset_id=request.asset_id,
        name=request.name,
        exchange=request.exchange,
        currency=request.currency,
        security_type=request.security_type,
        note=request.note,
        status="active",
        source="manual",
        created_at=now,
        updated_at=now,
    )
    STORE[item.watchlist_item_id] = item
    return {
        "item": _serialize_item(item),
        "message_nl": "Volglijst-item toegevoegd. Geen portefeuillepositie aangemaakt.",
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
