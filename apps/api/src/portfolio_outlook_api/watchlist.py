from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


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


class CreateWatchlistItemRequest(BaseModel):
    symbol: str
    asset_id: str | None = None
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    security_type: str | None = None
    note: str | None = None


class PatchWatchlistItemRequest(BaseModel):
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    security_type: str | None = None
    note: str | None = None


STORE: dict[str, WatchlistItem] = {}


def _norm(value: str | None) -> str:
    return (value or "").strip().upper()


@router.get("/items")
def list_watchlist_items() -> dict[str, object]:
    rows = [row for row in STORE.values() if row.status == "active"]
    return {
        "items": rows,
        "help_nl": "Lokale volglijstitems, gescheiden van IBKR-portefeuille.",
    }


@router.post("/items")
def create_watchlist_item(request: CreateWatchlistItemRequest) -> dict[str, object]:
    symbol = _norm(request.symbol)
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbool is verplicht.")

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
        "item": item,
        "message_nl": "Volglijst-item toegevoegd. Geen portefeuillepositie aangemaakt.",
    }


@router.get("/items/{watchlist_item_id}")
def get_watchlist_item(watchlist_item_id: str) -> dict[str, object]:
    item = STORE.get(watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Volglijst-item niet gevonden.")
    return {"item": item}


@router.patch("/items/{watchlist_item_id}")
def patch_watchlist_item(
    watchlist_item_id: str,
    request: PatchWatchlistItemRequest,
) -> dict[str, object]:
    item = STORE.get(watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Volglijst-item niet gevonden.")

    data = item.model_dump()
    for key, value in request.model_dump(exclude_unset=True).items():
        data[key] = value
    data["updated_at"] = datetime.now(UTC).isoformat()

    updated = WatchlistItem(**data)
    STORE[watchlist_item_id] = updated
    return {"item": updated, "message_nl": "Volglijst-item bijgewerkt."}


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
