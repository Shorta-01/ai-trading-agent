"""Production reconciliation fetchers (T-045 §2, execution layer 2/5).

Real implementations of the two read-side adapters the IbkrReconciler depends
on (Pass A executions, Pass B order status). Both wrap the worker's existing
**read-only** TWS session — executions + order status are read operations, so
no writable connection is involved here.

Design notes:
- The IB client is **injected** (a Protocol), so these are unit-testable with
  fakes and this module imports no broker SDK — it reads attributes off the
  returned fill/trade objects by name. (The SDK-import allowlist is enforced by
  ``test_ibkr_client_dependency_preflight``; keeping the conversion here
  attribute-based keeps this file off that list.)
- UNVERIFIED against a live broker: the field names below mirror the SDK's
  ``Fill`` / ``Execution`` / ``Trade`` shapes but are exercised here only via
  fakes. They must be validated against an IBKR paper account.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from portfolio_outlook_worker.ibkr_reconciliation.pass_a_orphaned_executions import (
    IbkrExecutionForReconciliation,
)
from portfolio_outlook_worker.ibkr_reconciliation.pass_b_stale_in_flight import (
    IbkrOrderStatusForReconciliation,
)

# IBKR reports execution side as BOT/SLD; the reconciler uses BUY/SELL.
_SIDE_MAP: dict[str, Literal["BUY", "SELL"]] = {
    "BOT": "BUY",
    "BUY": "BUY",
    "SLD": "SELL",
    "SELL": "SELL",
}


class ReadCapableIbClientProtocol(Protocol):
    """The read-side subset of the TWS client the fetchers drive."""

    def isConnected(self) -> bool: ...  # noqa: N802 — SDK name

    def reqExecutions(self, *args: Any, **kwargs: Any) -> list[Any]: ...  # noqa: N802

    def trades(self) -> list[Any]: ...


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


class IbkrExecutionFetcher:
    """Polls ``reqExecutions`` and maps fills to reconciliation records."""

    def __init__(self, *, ib_client: ReadCapableIbClientProtocol) -> None:
        self._ib = ib_client

    def fetch_recent_executions(
        self, *, account_id: str
    ) -> tuple[IbkrExecutionForReconciliation, ...]:
        if not self._ib.isConnected():
            return ()
        out: list[IbkrExecutionForReconciliation] = []
        for fill in self._ib.reqExecutions():
            record = self._map_fill(fill, account_id=account_id)
            if record is not None:
                out.append(record)
        return tuple(out)

    def _map_fill(
        self, fill: Any, *, account_id: str
    ) -> IbkrExecutionForReconciliation | None:
        execution = getattr(fill, "execution", None)
        if execution is None:
            return None
        acct = str(getattr(execution, "acctNumber", "") or "")
        # Only reconcile fills for the account we manage.
        if account_id and acct and acct != account_id:
            return None
        side = _SIDE_MAP.get(str(getattr(execution, "side", "") or "").upper())
        if side is None:
            return None
        price = _to_decimal(getattr(execution, "price", None))
        shares = _to_decimal(getattr(execution, "shares", None))
        fill_time = getattr(execution, "time", None)
        exec_id = str(getattr(execution, "execId", "") or "")
        if price is None or shares is None or fill_time is None or not exec_id:
            return None
        contract = getattr(fill, "contract", None)
        perm_id = int(getattr(execution, "permId", 0) or 0)
        return IbkrExecutionForReconciliation(
            ibkr_exec_id=exec_id,
            ibkr_perm_id=perm_id,
            account_id=acct or account_id,
            conid=str(getattr(contract, "conId", "") or ""),
            side=side,
            fill_price_local=price,
            fill_quantity=shares,
            fill_time=fill_time,
            raw={"perm_id": perm_id, "exec_id": exec_id, "side": side},
        )


class IbkrOrderStatusFetcher:
    """Looks a perm_id up in the session's known trades for Pass B."""

    def __init__(self, *, ib_client: ReadCapableIbClientProtocol) -> None:
        self._ib = ib_client

    def fetch_order_status(
        self, *, ibkr_perm_id: int, account_id: str
    ) -> IbkrOrderStatusForReconciliation:
        if not self._ib.isConnected():
            return IbkrOrderStatusForReconciliation(
                ibkr_perm_id=ibkr_perm_id, found_in_ibkr=False
            )
        for trade in self._ib.trades():
            order = getattr(trade, "order", None)
            if order is None:
                continue
            if int(getattr(order, "permId", 0) or 0) != ibkr_perm_id:
                continue
            status = getattr(getattr(trade, "orderStatus", None), "status", None)
            raw_status = str(status) if status else None
            return IbkrOrderStatusForReconciliation(
                ibkr_perm_id=ibkr_perm_id,
                found_in_ibkr=True,
                ibkr_raw_status=raw_status,
                raw_payload={"status": raw_status},
            )
        # perm_id not among the session's trades. NOTE: a worker restart drops
        # the in-session trade cache, so a previously-placed order may read as
        # not-found here until a cross-session open-orders source is wired —
        # a known reconciliation edge to validate during paper testing.
        return IbkrOrderStatusForReconciliation(
            ibkr_perm_id=ibkr_perm_id, found_in_ibkr=False
        )


__all__ = [
    "IbkrExecutionFetcher",
    "IbkrOrderStatusFetcher",
    "ReadCapableIbClientProtocol",
]
