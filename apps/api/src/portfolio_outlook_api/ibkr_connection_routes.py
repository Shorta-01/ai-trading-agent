"""Task 126b: read-only API surface for the worker-owned IBKR session.

Four routes back the AccountModeBadge + Portefeuille grid:

* ``GET /ibkr/connection/status``     — masked status summary.
* ``GET /ibkr/connection/audit``      — paged audit rows.
* ``GET /ibkr/sync/positions/latest`` — latest position snapshot.
* ``GET /ibkr/sync/cash/latest``      — latest cash snapshot.

All four are read-only; safety booleans hard-False. On storage
unavailable each route returns HTTP 503 with the locked Dutch body
``{"detail": "Opslag is niet beschikbaar."}`` per Task 126 product
lock §6.
"""

from __future__ import annotations

from typing import Literal

from ai_trading_agent_storage import StorageConnectionError
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.ibkr_connection_read_model import (
    STORAGE_UNAVAILABLE_DETAIL,
    list_connection_audit_rows,
    read_connection_status,
    read_latest_sync_payload,
    serialize_audit_row,
    serialize_cash_v126b,
    serialize_connection_status,
    serialize_position_v126b,
)

router = APIRouter()


# ---- Pydantic v2 response models ---------------------------------


class IbkrConnectionStatusResponse(BaseModel):
    """Wire shape for ``GET /ibkr/connection/status``."""

    model_config = ConfigDict(extra="forbid")

    connected: bool
    account_id: str | None = Field(
        default=None,
        description="Masked IBKR account ID (prefix + last 4 chars).",
    )
    account_mode: Literal["paper", "live", "unknown"]
    verified_at: str | None = Field(
        default=None,
        description="ISO8601 timestamp of the most recent connect_success.",
    )
    error: str | None = Field(
        default=None,
        description="Dutch error string when the session is unhealthy.",
    )
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class IbkrConnectionAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_at: str
    ibkr_account_id: str | None
    event_type: str
    account_mode_detected: str | None
    details_json: str | None
    connection_id: str | None


class IbkrConnectionAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IbkrConnectionAuditEntry]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class IbkrPositionLatestRow(BaseModel):
    """One position row on the Portefeuille grid."""

    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str | None
    conid: str | None
    symbol: str
    exchange: str | None
    primary_exchange: str | None
    currency: str
    security_type: str
    quantity: str | None
    avg_cost: str | None
    market_price: str | None
    market_value: str | None
    unrealized_pnl: str | None
    as_of: str | None


class IbkrPositionsLatestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IbkrPositionLatestRow]
    sync_run_id: str | None
    as_of: str | None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class IbkrCashLatestRow(BaseModel):
    """One row in the cash summary per currency."""

    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str | None
    currency: str
    cash: str | None
    available_funds: str | None
    buying_power: str | None
    net_liquidation_value: str | None
    total_cash_value: str | None
    as_of: str | None


class IbkrCashLatestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IbkrCashLatestRow]
    sync_run_id: str | None
    as_of: str | None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


# ---- route handlers ----------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/ibkr/connection/status",
    response_model=IbkrConnectionStatusResponse,
)
def read_ibkr_connection_status() -> dict[str, object]:
    """Return the synthesised IBKR connection state.

    Reads the latest ``ibkr_connection_audit`` rows for the
    configured account and collapses them into one status row. The
    account ID is masked before it leaves the API.
    """

    try:
        status = read_connection_status(
            settings.storage,
            configured_account_id=settings.ibkr_account_id_hint,
        )
    except StorageConnectionError:
        _raise_storage_unavailable()
    return serialize_connection_status(status)


@router.get(
    "/ibkr/connection/audit",
    response_model=IbkrConnectionAuditResponse,
)
def read_ibkr_connection_audit(
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    """Return the most-recent IBKR connection-lifecycle audit rows.

    Read-only / append-only — the underlying table has no
    update/delete path. Account IDs are masked before they leave the
    API.
    """

    try:
        rows = list_connection_audit_rows(
            settings.storage,
            limit=limit,
            configured_account_id=settings.ibkr_account_id_hint,
        )
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [serialize_audit_row(row) for row in rows],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/ibkr/sync/positions/latest",
    response_model=IbkrPositionsLatestResponse,
)
def read_ibkr_sync_positions_latest() -> dict[str, object]:
    """Return the most recent persisted IBKR positions snapshot."""

    try:
        payload = read_latest_sync_payload(settings.storage)
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [serialize_position_v126b(record) for record in payload.positions],
        "sync_run_id": payload.sync_run_id,
        "as_of": payload.received_at.isoformat() if payload.received_at else None,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/ibkr/sync/cash/latest",
    response_model=IbkrCashLatestResponse,
)
def read_ibkr_sync_cash_latest() -> dict[str, object]:
    """Return the most recent persisted IBKR cash snapshot."""

    try:
        payload = read_latest_sync_payload(settings.storage)
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [serialize_cash_v126b(record) for record in payload.cash_rows],
        "sync_run_id": payload.sync_run_id,
        "as_of": payload.received_at.isoformat() if payload.received_at else None,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
