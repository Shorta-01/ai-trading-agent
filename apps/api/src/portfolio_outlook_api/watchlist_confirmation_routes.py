"""Task 128: API surface for the cold-start onboarding flow.

Five routes back the dashboard banner + Volglijst confirmation UI:

* ``GET /watchlist/confirmation-state`` — banner + Volglijst gate.
* ``POST /watchlist/confirm`` — locked ``BEVESTIG`` phrase + non-empty
  watchlist + current ``unconfirmed`` state checks before flipping
  the per-account state to ``confirmed``.
* ``GET /watchlist/seed-audit`` — the cold-start seed audit row
  (or 404).
* ``GET /watchlist/cold-start-items`` — the DB-seeded starter rows
  the unconfirmed Volglijst view renders.
* ``DELETE /watchlist/cold-start-items/{watchlist_item_id}`` —
  archive a starter row before confirmation.

All routes Pydantic v2 typed; storage unavailable → HTTP 503 with
the locked Dutch body ``{"detail": "Opslag is niet beschikbaar."}``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from ai_trading_agent_storage import (
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistConfirmationAuditRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    WatchlistConfirmationAuditEntry,
    WatchlistConfirmationStateRecord,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from portfolio_outlook_api.config import settings

router = APIRouter()


STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."
LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"

BANNER_TEXT_NL = (
    "Welkom. Je IBKR-rekening is gesynchroniseerd. Het systeem heeft een "
    "startvoorstel voor je Volglijst klaargezet. Bekijk en bevestig in "
    "Volglijst voordat suggesties starten."
)


# ---- Pydantic v2 response models ---------------------------------


class WatchlistConfirmationStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str | None
    state: Literal["unconfirmed", "confirmed", "no_account_configured"]
    banner_text: str | None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class WatchlistConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_phrase: str = Field(..., min_length=1, max_length=64)


class WatchlistConfirmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["confirmed"]
    confirmed_at: str
    row_count: int
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ColdStartSeedAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seeded_at: str
    ibkr_account_id: str
    seeded_count: int
    failed_conids_json: str
    seed_version: str
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ColdStartWatchlistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watchlist_item_id: str
    symbol: str
    name: str | None
    exchange: str | None
    currency: str | None
    security_type: str | None


class ColdStartWatchlistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ColdStartWatchlistItem]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


# ---- helpers -----------------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _configured_account_id() -> str | None:
    """Returns the configured account hint or ``None``.

    The storage layer is per-account; routes that need account
    context fail-safe to ``no_account_configured`` rather than
    serving cross-account data.
    """

    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


# ---- routes ------------------------------------------------------


@router.get(
    "/watchlist/confirmation-state",
    response_model=WatchlistConfirmationStateResponse,
)
def read_watchlist_confirmation_state() -> dict[str, object]:
    """Return the per-account confirmation state.

    Returns ``no_account_configured`` when ``ibkr_account_id_hint``
    is missing — the banner stays hidden in that case (no point
    nudging the user to confirm an unconfigured account).
    """

    account_id = _configured_account_id()
    if account_id is None:
        return {
            "account_id": None,
            "state": "no_account_configured",
            "banner_text": None,
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return {
            "account_id": account_id,
            "state": "no_account_configured",
            "banner_text": None,
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
                checked.connection, checked.readiness
            )
            row = state_repo.get_by_account_id(account_id)
    except StorageConnectionError:
        _raise_storage_unavailable()

    if row is None or row.state == "confirmed":
        return {
            "account_id": account_id,
            "state": "confirmed" if row is not None else "no_account_configured",
            "banner_text": None,
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }
    return {
        "account_id": account_id,
        "state": "unconfirmed",
        "banner_text": BANNER_TEXT_NL,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.post("/watchlist/confirm", response_model=WatchlistConfirmResponse)
def confirm_watchlist(body: WatchlistConfirmRequest) -> dict[str, object]:
    if body.confirmation_phrase != LOCKED_CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=400, detail="Bevestigingscode is onjuist."
        )

    account_id = _configured_account_id()
    if account_id is None:
        raise HTTPException(
            status_code=409,
            detail="Geen IBKR-account geconfigureerd.",
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
                checked.connection, checked.readiness
            )
            audit_repo = SqlAlchemyWatchlistConfirmationAuditRepository(
                checked.connection, checked.readiness
            )
            wl_repo = SqlAlchemyWatchlistItemSeedRepository(
                checked.connection, checked.readiness
            )
            existing = state_repo.get_by_account_id(account_id)
            if existing is None or existing.state == "confirmed":
                if existing is not None and existing.state == "confirmed":
                    raise HTTPException(
                        status_code=409,
                        detail="Volglijst is al bevestigd.",
                    )
                # No state row at all — the seed hasn't run yet.
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Volglijst-startvoorstel is nog niet geseed. "
                        "Wacht tot de volgende geplande run."
                    ),
                )

            row_count = wl_repo.count_active_for_account(account_id)
            if row_count == 0:
                raise HTTPException(
                    status_code=422,
                    detail="Volglijst is leeg. Voeg eerst een asset toe.",
                )

            now = datetime.now(UTC)
            state_repo.upsert(
                WatchlistConfirmationStateRecord(
                    ibkr_account_id=account_id,
                    state="confirmed",
                    last_updated_at=now,
                )
            )
            audit_repo.append(
                WatchlistConfirmationAuditEntry(
                    event_at=now,
                    ibkr_account_id=account_id,
                    from_state="unconfirmed",
                    to_state="confirmed",
                    actor="user",
                    row_count_at_event=row_count,
                    details_json=None,
                )
            )
            checked.connection.commit()
            return {
                "state": "confirmed",
                "confirmed_at": now.isoformat(),
                "row_count": row_count,
                "safe_for_action_drafts": False,
                "safe_for_orders": False,
            }
    except StorageConnectionError:
        _raise_storage_unavailable()
    # Unreachable — _raise_storage_unavailable raises HTTPException.
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/watchlist/seed-audit",
    response_model=ColdStartSeedAuditResponse,
)
def read_cold_start_seed_audit() -> dict[str, object]:
    account_id = _configured_account_id()
    if account_id is None:
        raise HTTPException(
            status_code=404,
            detail="Geen IBKR-account geconfigureerd.",
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyColdStartSeedAuditRepository(
                checked.connection, checked.readiness
            )
            audit = repo.find_by_account_id(account_id)
    except StorageConnectionError:
        _raise_storage_unavailable()
    if audit is None:
        raise HTTPException(
            status_code=404,
            detail="Geen cold-start seed gevonden voor dit account.",
        )
    return {
        "seeded_at": audit.seeded_at.isoformat(),
        "ibkr_account_id": audit.ibkr_account_id,
        "seeded_count": audit.seeded_count,
        "failed_conids_json": audit.failed_conids_json,
        "seed_version": audit.seed_version,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/watchlist/cold-start-items",
    response_model=ColdStartWatchlistResponse,
)
def read_cold_start_items() -> dict[str, object]:
    account_id = _configured_account_id()
    if account_id is None:
        return {
            "items": [],
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyWatchlistItemSeedRepository(
                checked.connection, checked.readiness
            )
            rows = repo.list_starter_seed_for_account(account_id)
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [
            {
                "watchlist_item_id": row.watchlist_item_id,
                "symbol": row.symbol,
                "name": row.name,
                "exchange": row.exchange,
                "currency": row.currency,
                "security_type": row.security_type,
            }
            for row in rows.records
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.delete("/watchlist/cold-start-items/{watchlist_item_id}")
def archive_cold_start_item(watchlist_item_id: str) -> dict[str, object]:
    account_id = _configured_account_id()
    if account_id is None:
        raise HTTPException(
            status_code=409, detail="Geen IBKR-account geconfigureerd."
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyWatchlistItemSeedRepository(
                checked.connection, checked.readiness
            )
            archived = repo.archive_by_id(
                watchlist_item_id=watchlist_item_id,
                ibkr_account_id=account_id,
            )
            checked.connection.commit()
    except StorageConnectionError:
        _raise_storage_unavailable()
    if not archived:
        raise HTTPException(
            status_code=404, detail="Volglijst-item niet gevonden."
        )
    return {
        "archived": True,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
