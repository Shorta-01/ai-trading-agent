"""Real ``ibapi`` order-submission client (paper-only LMT/DAY/whole-share).

This is the *only* point in V1 where the application places a real order
against IBKR. The client is disabled-by-default and is constructed by the
factory only when every gate passes (paper mode, real-client flag, host/
port/client-id, account mode match).

For V1 Slice 7 the client implements just the placeOrder hand-off:

* connect → wait for ``nextValidId``
* build typed ``Contract`` (STK/ETF, ``primary_exchange``, currency)
* build typed ``Order`` (action, ``LMT`` + ``totalQuantity`` + ``lmtPrice`` +
  ``DAY`` tif, ``transmit=True``, no leverage, no short, no fractional)
* ``placeOrder(order_id, contract, order)``
* wait briefly for ``openOrder`` / ``orderStatus`` callback so we can record
  ``permId``
* disconnect

Reconciliation of fills/cancellations happens later via the existing IBKR
sync runtime — not here.
"""

from __future__ import annotations

import importlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, cast

from portfolio_outlook_api.ibkr_ibapi_client_facade import load_ibapi_preflight_modules
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError

logger = logging.getLogger(__name__)


CONNECTION_ERROR_CODES = frozenset({502, 504, 1100, 1101, 1102, 1300, 2110})


@dataclass(frozen=True)
class OrderSubmissionInputs:
    """Strongly-typed inputs the submission client needs."""

    symbol: str
    primary_exchange: str
    currency: str
    security_type: str
    action_side: str  # "BUY" or "SELL"
    quantity: Decimal
    limit_price: Decimal


@dataclass
class OrderSubmissionResult:
    """Outcome of one submission attempt."""

    accepted: bool
    ibkr_order_id: int | None
    ibkr_perm_id: int | None
    ibkr_client_id: int | None
    ibkr_status_text: str | None
    rejected_reason: str | None
    raw_diagnostic: str | None = None


class OrderSubmissionAppProtocol(Protocol):
    """Minimal protocol the order-submission app must implement."""

    def connect(self, host: str, port: int, client_id: int) -> None: ...

    def isConnected(self) -> bool: ...  # noqa: N802

    def disconnect(self) -> None: ...

    def run(self) -> None: ...

    def reqIds(self, num_ids: int) -> None: ...  # noqa: N802

    def placeOrder(  # noqa: N802
        self, order_id: int, contract: Any, order: Any
    ) -> None: ...


@dataclass
class _SubmissionState:
    connected: bool = False
    next_order_id: int | None = None
    next_order_id_event: threading.Event = field(default_factory=threading.Event)
    confirmation_event: threading.Event = field(default_factory=threading.Event)
    ibkr_perm_id: int | None = None
    ibkr_status_text: str | None = None
    rejected_reason: str | None = None
    fatal_error: Exception | None = None


def build_submission_callbacks(
    state: _SubmissionState,
    lock: threading.Lock,
) -> dict[str, Callable[..., None]]:
    """Build the EWrapper callback set used by both production and tests."""

    def next_valid_id(_self: Any, order_id: int) -> None:  # noqa: N802
        with lock:
            state.next_order_id = int(order_id)
        state.next_order_id_event.set()

    def open_order(  # noqa: N802
        _self: Any,
        order_id: int,
        _contract: Any,
        order: Any,
        order_state: Any,
    ) -> None:
        with lock:
            perm_id = int(getattr(order, "permId", 0))
            if perm_id:
                state.ibkr_perm_id = perm_id
            status_text = getattr(order_state, "status", None)
            if status_text:
                state.ibkr_status_text = str(status_text)
        state.confirmation_event.set()

    def order_status(  # noqa: N802
        _self: Any,
        _order_id: int,
        status: str,
        _filled: float,
        _remaining: float,
        _avg_fill_price: float,
        _perm_id: int,
        _parent_id: int,
        _last_fill_price: float,
        _client_id: int,
        why_held: str,
        _mkt_cap_price: float = 0,
    ) -> None:
        with lock:
            state.ibkr_status_text = str(status)
            if status in {"ApiCancelled", "Cancelled", "Inactive"}:
                state.rejected_reason = str(why_held or status)
        state.confirmation_event.set()

    def error(  # noqa: N802
        _self: Any,
        _req_id: int,
        error_code: int,
        error_string: str,
        *_extra: object,
    ) -> None:
        if error_code in CONNECTION_ERROR_CODES:
            state.fatal_error = IbkrTwsReadonlyAdapterError("connection_failed")
            state.confirmation_event.set()
            state.next_order_id_event.set()
        elif error_code >= 2100 and error_code < 2200:
            # 2100-series are warnings (account/security info); not fatal.
            logger.debug(
                "ibapi non-fatal callback warning code=%s message=%s",
                error_code,
                error_string,
            )
        else:
            with lock:
                state.rejected_reason = f"{error_code}:{error_string}"
            state.confirmation_event.set()

    return {
        "nextValidId": next_valid_id,
        "openOrder": open_order,
        "orderStatus": order_status,
        "error": error,
    }


def build_contract_and_order(inputs: OrderSubmissionInputs) -> tuple[Any, Any]:
    """Build typed ``ibapi`` Contract + Order objects for a paper LMT/DAY order.

    Validates the locked V1 scope:

    * ``action_side`` must be BUY or SELL
    * ``security_type`` must be ``STK``
    * ``quantity`` must be a positive whole share
    * ``limit_price`` must be positive

    The function is the *only* module that imports ``ibapi.contract`` and
    ``ibapi.order``; the rest of the codebase stays dependency-isolated.
    """

    if inputs.action_side not in {"BUY", "SELL"}:
        raise ValueError(f"action_side must be BUY or SELL, got {inputs.action_side!r}")
    if inputs.security_type != "STK":
        raise ValueError("V1 only supports STK security_type")
    if inputs.quantity <= 0 or inputs.quantity != inputs.quantity.to_integral_value():
        raise ValueError("quantity must be a positive whole share")
    if inputs.limit_price <= 0:
        raise ValueError("limit_price must be positive")

    load_ibapi_preflight_modules()
    contract_module = importlib.import_module("ibapi.contract")
    order_module = importlib.import_module("ibapi.order")
    contract_cls = cast(type[Any], cast(Any, contract_module).Contract)
    order_cls = cast(type[Any], cast(Any, order_module).Order)

    contract = contract_cls()
    contract.symbol = inputs.symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.primaryExchange = inputs.primary_exchange
    contract.currency = inputs.currency

    order = order_cls()
    order.action = inputs.action_side
    order.orderType = "LMT"
    order.totalQuantity = inputs.quantity
    order.lmtPrice = inputs.limit_price
    order.tif = "DAY"
    order.transmit = True
    return contract, order


class IbapiOrderSubmissionClient:
    """Disabled-by-default paper-only LMT/DAY order-submission client."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: int,
        timeout_seconds: int,
        provider_code: str = "ibkr",
        app: OrderSubmissionAppProtocol | None = None,
        contract_order_builder: Callable[
            [OrderSubmissionInputs], tuple[Any, Any]
        ]
        | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._timeout = max(1, int(timeout_seconds))
        self._provider_code = provider_code
        self._lock = threading.Lock()
        self._state = _SubmissionState()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._app = app if app is not None else self._build_app()
        self._contract_order_builder = contract_order_builder or build_contract_and_order

    def _build_app(self) -> OrderSubmissionAppProtocol:
        load_ibapi_preflight_modules()
        client_module = importlib.import_module("ibapi.client")
        wrapper_module = importlib.import_module("ibapi.wrapper")
        eclient_type = cast(type[Any], cast(Any, client_module).EClient)
        ewrapper_type = cast(type[Any], cast(Any, wrapper_module).EWrapper)

        callbacks = build_submission_callbacks(self._state, self._lock)

        def _init(inner_self: Any) -> None:
            eclient_type.__init__(inner_self, inner_self)

        manual_bases: tuple[type[Any], type[Any]] = (ewrapper_type, eclient_type)
        app_type = type(
            "_SubmissionApp",
            manual_bases,
            {"__init__": _init, **callbacks},
        )
        return cast(OrderSubmissionAppProtocol, app_type())

    def _ensure_connected(self) -> None:
        with self._lock:
            if self._state.connected:
                return
            if self._closed:
                raise IbkrTwsReadonlyAdapterError("connection_failed")
        try:
            self._app.connect(self._host, self._port, self._client_id)
        except TimeoutError:
            raise
        except Exception as exc:
            raise IbkrTwsReadonlyAdapterError("connection_failed") from exc
        if not self._app.isConnected():
            raise IbkrTwsReadonlyAdapterError("connection_failed")
        thread = threading.Thread(
            target=self._app.run,
            name=f"ibapi-submit-{self._client_id}",
            daemon=True,
        )
        thread.start()
        with self._lock:
            self._thread = thread
            self._state.connected = True

    def submit(self, inputs: OrderSubmissionInputs) -> OrderSubmissionResult:
        """Place one LMT/DAY/whole-share order. The call blocks until either
        the ``openOrder`` / ``orderStatus`` callback fires or the timeout
        elapses."""

        self._ensure_connected()

        self._state.next_order_id_event.clear()
        self._app.reqIds(-1)
        if not self._state.next_order_id_event.wait(self._timeout):
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason="next_valid_id_timeout",
            )
        if self._state.fatal_error is not None:
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason="connection_failed",
                raw_diagnostic=str(self._state.fatal_error),
            )
        order_id = self._state.next_order_id
        if order_id is None:
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason="missing_next_valid_id",
            )

        try:
            contract, order = self._contract_order_builder(inputs)
        except ValueError as exc:
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason=f"invalid_inputs:{exc}",
            )

        self._state.confirmation_event.clear()
        try:
            self._app.placeOrder(order_id, contract, order)
        except Exception as exc:
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=order_id,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason="place_order_raised",
                raw_diagnostic=str(exc),
            )

        # Wait briefly for openOrder / orderStatus confirmation.
        self._state.confirmation_event.wait(self._timeout)
        rejected_reason = self._state.rejected_reason
        return OrderSubmissionResult(
            accepted=rejected_reason is None,
            ibkr_order_id=order_id,
            ibkr_perm_id=self._state.ibkr_perm_id,
            ibkr_client_id=self._client_id,
            ibkr_status_text=self._state.ibkr_status_text,
            rejected_reason=rejected_reason,
        )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            thread = self._thread
            self._thread = None
            connected = self._state.connected
            self._state.connected = False
        if connected:
            try:
                self._app.disconnect()
            except Exception:
                logger.debug("ibapi submission disconnect raised; ignoring", exc_info=True)
        if thread is not None and thread.is_alive():
            thread.join(timeout=self._timeout)

    def __enter__(self) -> IbapiOrderSubmissionClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
