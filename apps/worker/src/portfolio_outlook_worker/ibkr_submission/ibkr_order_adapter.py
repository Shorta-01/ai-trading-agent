"""Production ``IbkrSubmitProtocol`` adapter over ``ib_insync`` (T-045 §1/§3).

This is the real network-write adapter the submission + cancel sweeps depend
on. The orchestration (``IbkrSubmitter`` / ``SubmissionSweep``) is fully
tested with fakes; this module is the part that actually drives an IBKR TWS
session, so it carries two hard constraints:

* **Order-capable session is NOT read-only.** The long-lived sync gateway
  (``ibkr_gateway.py``) connects ``readonly=True`` on purpose — orders are
  rejected on a read-only API session. Order placement therefore needs a
  separate, non-read-only session, opened only via :func:`open_order_adapter`,
  which **fails closed**: under ``paper_only_mode`` it refuses to open against
  anything that doesn't look like a paper account (``DU*`` / ``DF*``).
* **UNVERIFIED against a live broker.** The logic below (async permId wait,
  open-trade cancel lookup, contract-detail tick size) is exercised here only
  through a fake ``ib_insync`` client. It MUST be validated against an IBKR
  *paper* account through full order lifecycles before any real-money use.
  Nothing here flips ``paper_only_mode``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Protocol

from portfolio_outlook_worker.ibkr_submission.order_builder import TickSize
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrConnectionLostError,
    SubmittedTrade,
)

logger = logging.getLogger(__name__)

_PAPER_PREFIXES = ("DU", "DF")
_DEFAULT_PERM_ID_TIMEOUT_S = 5.0
_DEFAULT_PERM_ID_POLL_S = 0.1


class OrderCapableIbClientProtocol(Protocol):
    """The subset of ``ib_insync.IB`` the order adapter drives.

    Intentionally permissive (``Any``) so the real SDK and lightweight test
    fakes both satisfy it without importing ``ib_insync`` at module load.
    """

    def isConnected(self) -> bool: ...  # noqa: N802 — SDK name

    def managedAccounts(self) -> list[str]: ...  # noqa: N802 — SDK name

    def reqContractDetails(self, contract: Any) -> list[Any]: ...  # noqa: N802

    def placeOrder(self, contract: Any, order: Any) -> Any: ...  # noqa: N802

    def cancelOrder(self, order: Any) -> Any: ...  # noqa: N802

    def openTrades(self) -> list[Any]: ...  # noqa: N802 — SDK name

    def sleep(self, seconds: float) -> None: ...


class OrderSessionRefusedError(RuntimeError):
    """Raised when an order-capable session is refused (e.g. paper-only)."""


@dataclass(frozen=True)
class _StockContractSpec:
    symbol: str
    exchange: str
    currency: str
    conid: int | None


def _mode_from_account_id(account_id: str) -> Literal["paper", "live"]:
    return "paper" if account_id.upper().startswith(_PAPER_PREFIXES) else "live"


def _contract_to_dict(contract: Any) -> dict[str, object]:
    """Canonical JSON-friendly snapshot of an ``ib_insync`` Contract."""

    return {
        "secType": getattr(contract, "secType", None),
        "symbol": getattr(contract, "symbol", None),
        "exchange": getattr(contract, "exchange", None),
        "currency": getattr(contract, "currency", None),
        "conId": getattr(contract, "conId", None),
    }


def _order_to_dict(order: Any) -> dict[str, object]:
    """Canonical JSON-friendly snapshot of an ``ib_insync`` Order."""

    return {
        "action": getattr(order, "action", None),
        "totalQuantity": _num(getattr(order, "totalQuantity", None)),
        "orderType": getattr(order, "orderType", None),
        "lmtPrice": _num(getattr(order, "lmtPrice", None)),
        "tif": getattr(order, "tif", None),
        "outsideRth": getattr(order, "outsideRth", None),
    }


def _num(value: Any) -> object:
    if value is None:
        return None
    return str(value)


class IbkrOrderAdapter:
    """Real ``IbkrSubmitProtocol`` implementation over an order-capable session.

    The IB client is injected (constructed by :func:`open_order_adapter` in
    production, a fake in tests) so the call orchestration is unit-testable
    without the SDK.
    """

    def __init__(
        self,
        *,
        ib_client: OrderCapableIbClientProtocol,
        account_id: str,
        session_id: str,
        contract_factory: Callable[[_StockContractSpec], Any] | None = None,
        perm_id_timeout_s: float = _DEFAULT_PERM_ID_TIMEOUT_S,
        perm_id_poll_s: float = _DEFAULT_PERM_ID_POLL_S,
    ) -> None:
        self._ib = ib_client
        self._account_id = account_id
        self._session_id = session_id
        self._contract_factory = contract_factory or _default_stock_contract
        self._perm_id_timeout_s = perm_id_timeout_s
        self._perm_id_poll_s = perm_id_poll_s

    @property
    def gateway_session_id(self) -> str:
        return self._session_id

    @property
    def account_mode(self) -> Literal["paper", "live"]:
        return _mode_from_account_id(self._account_id)

    def fetch_managed_account_id(self) -> str:
        if not self._ib.isConnected():
            raise IbkrConnectionLostError("IBKR session is niet verbonden.")
        managed = self._ib.managedAccounts()
        if not managed:
            raise IbkrConnectionLostError("Geen managed account beschikbaar.")
        return str(managed[0])

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize:
        if not self._ib.isConnected():
            raise IbkrConnectionLostError("IBKR session is niet verbonden.")
        contract = self._contract_factory(
            _StockContractSpec(
                symbol=symbol, exchange=exchange, currency=currency, conid=conid
            )
        )
        details = self._ib.reqContractDetails(contract)
        if not details:
            raise IbkrConnectionLostError(
                f"Geen contractdetails voor {symbol}.{exchange}."
            )
        min_tick = getattr(details[0], "minTick", None)
        if min_tick is None or Decimal(str(min_tick)) <= 0:
            raise IbkrConnectionLostError(
                f"Ongeldige tick size voor {symbol}.{exchange}."
            )
        return TickSize(tick_size_local=Decimal(str(min_tick)))

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        if not self._ib.isConnected():
            raise IbkrConnectionLostError("IBKR session is niet verbonden.")
        trade = self._ib.placeOrder(contract, order)
        perm_id = self._await_perm_id(trade)
        order_id = int(getattr(getattr(trade, "order", None), "orderId", 0) or 0)
        placed_contract = getattr(trade, "contract", contract)
        placed_order = getattr(trade, "order", order)
        return SubmittedTrade(
            perm_id=perm_id,
            order_id=order_id,
            contract_dict=_contract_to_dict(placed_contract),
            order_dict=_order_to_dict(placed_order),
        )

    def cancel_order(self, perm_id: int) -> None:
        if not self._ib.isConnected():
            raise IbkrConnectionLostError("IBKR session is niet verbonden.")
        for trade in self._ib.openTrades():
            order = getattr(trade, "order", None)
            if order is not None and int(getattr(order, "permId", 0) or 0) == perm_id:
                self._ib.cancelOrder(order)
                return
        # Fire-and-forget per order-lifecycle.md §3: an order that IBKR no
        # longer reports open (already filled/cancelled) is a no-op here; the
        # reconciler's Pass B converges the local status from IBKR truth.
        logger.info(
            "cancel_order: perm_id %s not found among open trades (no-op)", perm_id
        )

    def _await_perm_id(self, trade: Any) -> int:
        """Wait for IBKR to assign the async ``permId`` after placeOrder."""

        waited = 0.0
        while waited <= self._perm_id_timeout_s:
            perm_id = int(getattr(getattr(trade, "order", None), "permId", 0) or 0)
            if perm_id:
                return perm_id
            self._ib.sleep(self._perm_id_poll_s)
            waited += self._perm_id_poll_s
        raise IbkrConnectionLostError(
            "IBKR kende geen permId toe binnen de time-out; status onzeker."
        )


def _default_stock_contract(spec: _StockContractSpec) -> Any:
    from ib_insync import Stock  # lazy: keep module import-safe without the SDK

    contract = Stock(spec.symbol, spec.exchange, spec.currency)
    if spec.conid is not None:
        contract.conId = spec.conid
    return contract


def open_order_adapter(
    *,
    host: str,
    port: int,
    client_id: int,
    account_id: str,
    session_id: str,
    paper_only_mode: bool,
    ib_client_factory: Callable[[], OrderCapableIbClientProtocol] | None = None,
) -> IbkrOrderAdapter:
    """Open a NON-read-only order session, failing closed under paper-only.

    Refuses (``OrderSessionRefusedError``) when ``paper_only_mode`` is set and
    ``account_id`` does not look like a paper account (``DU*`` / ``DF*``) — so
    a misconfiguration can never open an order-capable session against a live
    account while the system is in paper-only mode.

    NOTE: this opens a real TWS connection and is unverified against a live
    broker; it must be exercised against an IBKR paper account first.
    """

    mode = _mode_from_account_id(account_id)
    if paper_only_mode and mode != "paper":
        raise OrderSessionRefusedError(
            f"Weiger order-sessie: paper_only_mode actief maar account "
            f"{account_id!r} lijkt live. Order-sessie niet geopend."
        )

    if ib_client_factory is None:

        def ib_client_factory() -> OrderCapableIbClientProtocol:
            from ib_insync import IB

            ib = IB()  # type: ignore[no-untyped-call]
            # readonly=False — orders require a writable API session.
            ib.connect(host, port, clientId=client_id, readonly=False)
            return ib  # type: ignore[return-value]

    client = ib_client_factory()
    if account_id not in client.managedAccounts():
        client.disconnect() if hasattr(client, "disconnect") else None
        raise OrderSessionRefusedError(
            f"Account {account_id} niet beheerd door deze TWS-sessie."
        )
    return IbkrOrderAdapter(
        ib_client=client, account_id=account_id, session_id=session_id
    )


__all__ = [
    "IbkrOrderAdapter",
    "OrderCapableIbClientProtocol",
    "OrderSessionRefusedError",
    "open_order_adapter",
]
