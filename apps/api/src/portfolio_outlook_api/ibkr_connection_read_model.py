"""Task 126b: API surface that reads worker-persisted IBKR state.

The worker (Task 126a) writes connect/disconnect audit rows to
``ibkr_connection_audit``; the API exposes that state through four
read-only routes:

* ``GET /ibkr/connection/status``  — synthesised connection state.
* ``GET /ibkr/connection/audit``   — recent audit rows, masked.
* ``GET /ibkr/sync/positions/latest`` — last persisted position
  snapshot.
* ``GET /ibkr/sync/cash/latest``      — last persisted cash snapshot.

All routes are read-only; safety booleans hard-False. When durable
storage is unreachable they return HTTP 503 with a Dutch error body
— no in-memory fallback per the Task 126 product locks §6.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrConnectionAuditRecord,
    IbkrPositionSnapshotRecord,
    SqlAlchemyIbkrConnectionAuditRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_api.config import StorageSettings

AccountMode = Literal["paper", "live", "unknown"]

# Locked Dutch error body the four 126b routes share when the storage
# layer is unreachable (Task 126 product lock §6: no in-memory
# fallback; the system fails closed with HTTP 503).
STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."


# ---- account-id masking ------------------------------------------


def mask_account_id(account_id: str | None) -> str | None:
    """Mask an IBKR account ID for display.

    ``DU1234567`` → ``DU•••4567``. Empty / ``None`` → ``None``.
    Short IDs (< 6 chars) → returned as-is (already short enough to
    expose without aiding reconstruction).
    """

    if not account_id:
        return None
    text = account_id.strip()
    if len(text) <= 6:
        return text
    prefix = text[:2]
    suffix = text[-4:]
    return f"{prefix}•••{suffix}"


# ---- connection-status synthesis ---------------------------------


@dataclass(frozen=True)
class IbkrConnectionStatus:
    """Synthesised view of the worker's IBKR session state.

    Derived from the latest ``ibkr_connection_audit`` rows. Because
    Task 126a's worker performs a connect-and-disconnect cycle on
    startup, ``connected`` will report ``False`` shortly after the
    worker boots; the persistent session loop lands in a follow-up
    slice. The ``account_mode`` + ``verified_at`` fields persist
    across that gap so the badge still surfaces the right colour.
    """

    connected: bool
    account_id: str | None
    account_mode: AccountMode
    verified_at: datetime | None
    error_nl: str | None


def synthesise_connection_status(
    audit_rows: tuple[IbkrConnectionAuditRecord, ...],
    *,
    configured_account_id: str | None,
) -> IbkrConnectionStatus:
    """Collapse a sequence of audit rows into the latest status.

    Algorithm:
    1. Filter to rows matching ``configured_account_id`` (if set).
    2. Find the most recent ``connect_success``: its mode + event_at
       feed ``account_mode`` + ``verified_at``.
    3. ``connected`` is true iff that ``connect_success`` is not
       followed by a ``disconnect`` / ``session_error`` /
       ``connect_refused`` for the same connection_id.
    4. ``error_nl`` carries the most recent refusal/error message if
       no later success rescinded it.
    """

    filtered = (
        tuple(
            row
            for row in audit_rows
            if row.ibkr_account_id == configured_account_id
        )
        if configured_account_id
        else audit_rows
    )
    # Sort newest first.
    ordered = sorted(filtered, key=lambda r: r.event_at, reverse=True)

    latest_success: IbkrConnectionAuditRecord | None = None
    later_terminator: IbkrConnectionAuditRecord | None = None
    latest_refused: IbkrConnectionAuditRecord | None = None

    for row in ordered:
        if row.event_type == "connect_success" and latest_success is None:
            latest_success = row
            break
        if row.event_type in ("disconnect", "session_error"):
            if later_terminator is None:
                later_terminator = row
        if row.event_type == "connect_refused" and latest_refused is None:
            latest_refused = row

    account_id = (
        configured_account_id
        if configured_account_id
        else (latest_success.ibkr_account_id if latest_success else None)
    )

    if latest_success is None:
        # No prior success: connected=False, mode=unknown.
        error_nl: str | None = None
        if latest_refused is not None:
            error_nl = _refusal_reason_nl(latest_refused)
        return IbkrConnectionStatus(
            connected=False,
            account_id=account_id,
            account_mode="unknown",
            verified_at=None,
            error_nl=error_nl,
        )

    connected = later_terminator is None and latest_refused is None
    mode: AccountMode = "unknown"
    if latest_success.account_mode_detected in ("paper", "live", "unknown"):
        mode = latest_success.account_mode_detected  # type: ignore[assignment]

    error_nl = None
    if not connected:
        if later_terminator is not None and later_terminator.event_type == "session_error":
            error_nl = "IBKR-sessie is afgebroken; herstart vereist."
        elif latest_refused is not None:
            error_nl = _refusal_reason_nl(latest_refused)
        elif later_terminator is not None:
            error_nl = "IBKR-verbinding gesloten."

    return IbkrConnectionStatus(
        connected=connected,
        account_id=account_id,
        account_mode=mode,
        verified_at=latest_success.event_at,
        error_nl=error_nl,
    )


def _refusal_reason_nl(row: IbkrConnectionAuditRecord) -> str:
    """Best-effort Dutch description of a refusal/error event."""

    if row.event_type == "connect_refused":
        return "IBKR-verbinding geweigerd; controleer Instellingen."
    if row.event_type == "session_error":
        return "IBKR-sessie is afgebroken; herstart vereist."
    return "IBKR-verbinding niet beschikbaar."


# ---- storage I/O -------------------------------------------------


@dataclass(frozen=True)
class _OpenedConnection:
    audit_repo: SqlAlchemyIbkrConnectionAuditRepository
    sync_repo: SqlAlchemyIbkrSyncSnapshotRepository


def read_connection_status(
    storage: StorageSettings,
    *,
    configured_account_id: str | None,
    audit_limit: int = 200,
) -> IbkrConnectionStatus:
    """Open a read-only connection and synthesise the status.

    Raises :class:`StorageConnectionError` (re-raised) when the DB
    is unreachable; the route maps that to HTTP 503.
    """

    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage not configured")

    provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    with provider.checked_connection(require_writable=False) as checked:
        audit_repo = SqlAlchemyIbkrConnectionAuditRepository(
            checked.connection, checked.readiness
        )
        result = audit_repo.list_recent(
            ibkr_account_id=configured_account_id, limit=audit_limit
        )
        return synthesise_connection_status(
            result.records,
            configured_account_id=configured_account_id,
        )


def list_connection_audit_rows(
    storage: StorageSettings,
    *,
    limit: int,
    configured_account_id: str | None = None,
) -> tuple[IbkrConnectionAuditRecord, ...]:
    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage not configured")
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    with provider.checked_connection(require_writable=False) as checked:
        audit_repo = SqlAlchemyIbkrConnectionAuditRepository(
            checked.connection, checked.readiness
        )
        result = audit_repo.list_recent(
            ibkr_account_id=configured_account_id, limit=limit
        )
        return result.records


@dataclass(frozen=True)
class LatestSyncReadResult:
    sync_run_id: str | None
    received_at: datetime | None
    positions: tuple[IbkrPositionSnapshotRecord, ...]
    cash_rows: tuple[IbkrAccountCashSnapshotRecord, ...]


def read_latest_sync_payload(storage: StorageSettings) -> LatestSyncReadResult:
    """Read the most recent sync run + its position/cash children."""

    if not storage.enabled or not storage.database_url:
        raise StorageConnectionError("storage not configured")
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    with provider.checked_connection(require_writable=False) as checked:
        sync_repo = SqlAlchemyIbkrSyncSnapshotRepository(
            checked.connection, checked.readiness
        )
        latest_run = sync_repo.get_latest_ibkr_sync_run()
        if latest_run is None:
            return LatestSyncReadResult(
                sync_run_id=None,
                received_at=None,
                positions=tuple(),
                cash_rows=tuple(),
            )
        positions = sync_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
        cash = sync_repo.list_ibkr_account_cash_snapshots(latest_run.sync_run_id)
        return LatestSyncReadResult(
            sync_run_id=latest_run.sync_run_id,
            received_at=latest_run.completed_at or latest_run.started_at,
            positions=tuple(positions),
            cash_rows=tuple(cash),
        )


# ---- serialisation -----------------------------------------------


def _decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def serialize_connection_status(
    status: IbkrConnectionStatus,
) -> dict[str, object]:
    return {
        "connected": status.connected,
        "account_id": mask_account_id(status.account_id),
        "account_mode": status.account_mode,
        "verified_at": _iso(status.verified_at),
        "error": status.error_nl,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


def serialize_audit_row(row: IbkrConnectionAuditRecord) -> dict[str, object]:
    return {
        "id": row.audit_id,
        "event_at": row.event_at.isoformat(),
        "ibkr_account_id": mask_account_id(row.ibkr_account_id),
        "event_type": row.event_type,
        "account_mode_detected": row.account_mode_detected,
        "details_json": row.details_json,
        "connection_id": row.connection_id,
    }


def serialize_position_v126b(
    record: IbkrPositionSnapshotRecord,
) -> dict[str, object]:
    """Task 126b position-row serialiser.

    Adds the fields the Portefeuille grid renders. ``market_price``,
    ``market_value``, ``unrealized_pnl`` are reported as ``null``
    until the worker sync loop persists them (deferred to a follow-up
    slice). Decimal precision preserved end-to-end as strings.
    """

    return {
        "ibkr_account_id": mask_account_id(record.ibkr_account_id),
        "conid": record.conid,
        "symbol": record.symbol,
        "exchange": record.exchange,
        "primary_exchange": record.primary_exchange,
        "currency": record.currency,
        "security_type": record.security_type,
        "quantity": _decimal_str(record.quantity),
        "avg_cost": _decimal_str(record.average_cost),
        "market_price": None,
        "market_value": None,
        "unrealized_pnl": None,
        "as_of": _iso(record.received_at),
    }


def serialize_cash_v126b(
    record: IbkrAccountCashSnapshotRecord,
) -> dict[str, object]:
    """Task 126b cash-row serialiser.

    ``net_liquidation_value`` + ``total_cash_value`` are reported as
    ``null`` until the worker persists them (the storage record
    currently holds ``cash`` + ``available_funds`` + ``buying_power``).
    """

    return {
        "ibkr_account_id": mask_account_id(record.ibkr_account_id),
        "currency": record.base_currency,
        "cash": _decimal_str(record.cash),
        "available_funds": _decimal_str(record.available_funds),
        "buying_power": _decimal_str(record.buying_power),
        "net_liquidation_value": None,
        "total_cash_value": None,
        "as_of": _iso(record.received_at),
    }


__all__ = [
    "STORAGE_UNAVAILABLE_DETAIL",
    "IbkrConnectionStatus",
    "LatestSyncReadResult",
    "list_connection_audit_rows",
    "mask_account_id",
    "read_connection_status",
    "read_latest_sync_payload",
    "serialize_audit_row",
    "serialize_cash_v126b",
    "serialize_connection_status",
    "serialize_position_v126b",
    "synthesise_connection_status",
]
