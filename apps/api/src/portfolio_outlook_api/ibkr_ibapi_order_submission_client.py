"""Real ``ibapi`` order-submission client (paper-only, §21.3 vocabulary).

This is the *only* point in V1 where the application places a real order
against IBKR. The client is disabled-by-default and is constructed by the
factory only when every gate passes (paper mode, real-client flag, host/
port/client-id, account mode match).

Order vocabulary (§21.3 lock):

* ``LMT``  — limit order (lmtPrice)
* ``MKT``  — market order
* ``STP``  — stop order (auxPrice)
* ``STP_LMT`` — stop-limit order (auxPrice + lmtPrice)
* ``TRAIL`` — trailing stop (auxPrice OR trailingPercent)
* ``TRAIL_LMT`` — trailing stop limit (trail + lmtPrice)
* ``BRACKET`` — parent LMT + take-profit LMT child + stop-loss STP child

For non-BRACKET types the client emits one ``placeOrder`` call. For
BRACKET it emits three calls (parent + two children) with the parent
receiving the next-valid order id and children parent-linked. The result
records the parent's ``order_id`` / ``perm_id``.

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

LOCKED_ORDER_TYPES = frozenset(
    {"LMT", "MKT", "STP", "STP_LMT", "TRAIL", "TRAIL_LMT", "BRACKET"}
)


@dataclass(frozen=True)
class OrderSubmissionInputs:
    """Strongly-typed inputs the submission client needs.

    ``order_type`` defaults to ``LMT`` so existing callers that only emit
    plain limit orders stay unchanged. The other price fields are only
    consumed when the chosen ``order_type`` requires them.
    """

    symbol: str
    primary_exchange: str
    currency: str
    security_type: str
    action_side: str  # "BUY" or "SELL"
    quantity: Decimal
    limit_price: Decimal
    order_type: str = "LMT"
    stop_price: Decimal | None = None
    trail_amount: Decimal | None = None
    trail_percent: Decimal | None = None
    bracket_take_profit_limit_price: Decimal | None = None
    bracket_stop_loss_price: Decimal | None = None


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


def _validate_common_inputs(inputs: OrderSubmissionInputs) -> None:
    if inputs.action_side not in {"BUY", "SELL"}:
        raise ValueError(f"action_side must be BUY or SELL, got {inputs.action_side!r}")
    if inputs.security_type != "STK":
        raise ValueError("V1 only supports STK security_type")
    if inputs.quantity <= 0 or inputs.quantity != inputs.quantity.to_integral_value():
        raise ValueError("quantity must be a positive whole share")
    if inputs.order_type not in LOCKED_ORDER_TYPES:
        raise ValueError(
            f"order_type {inputs.order_type!r} is outside the V1 §21.3 lock"
        )


def _load_ibapi_classes() -> tuple[type[Any], type[Any]]:
    load_ibapi_preflight_modules()
    contract_module = importlib.import_module("ibapi.contract")
    order_module = importlib.import_module("ibapi.order")
    contract_cls = cast(type[Any], cast(Any, contract_module).Contract)
    order_cls = cast(type[Any], cast(Any, order_module).Order)
    return contract_cls, order_cls


def _build_contract(contract_cls: type[Any], inputs: OrderSubmissionInputs) -> Any:
    contract = contract_cls()
    contract.symbol = inputs.symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.primaryExchange = inputs.primary_exchange
    contract.currency = inputs.currency
    return contract


def _new_order(
    order_cls: type[Any],
    *,
    action: str,
    quantity: Decimal,
    transmit: bool,
) -> Any:
    order = order_cls()
    order.action = action
    order.totalQuantity = quantity
    order.tif = "DAY"
    order.transmit = transmit
    return order


def _opposite_side(action_side: str) -> str:
    return "SELL" if action_side == "BUY" else "BUY"


def build_contract_and_orders(
    inputs: OrderSubmissionInputs,
) -> tuple[Any, list[Any]]:
    """Build typed ``ibapi`` Contract + ordered list of ``Order`` objects.

    Returns one order for the non-BRACKET vocabulary and three orders
    (parent, take-profit child, stop-loss child) for BRACKET. The
    children carry ``parentId=0`` here; the submission flow patches in
    the real parent ``order_id`` before each ``placeOrder`` call.

    Per-order-type validation mirrors the dry-run safety codes (§21.3).
    """

    _validate_common_inputs(inputs)
    contract_cls, order_cls = _load_ibapi_classes()
    contract = _build_contract(contract_cls, inputs)
    orders = _build_orders_for_type(order_cls, inputs)
    return contract, orders


def build_contract_and_order(inputs: OrderSubmissionInputs) -> tuple[Any, Any]:
    """Single-order builder kept for backward compatibility.

    For BRACKET use :func:`build_contract_and_orders` since BRACKET emits
    three orders that must be submitted together.
    """

    contract, orders = build_contract_and_orders(inputs)
    if len(orders) != 1:
        raise ValueError(
            "BRACKET produces multiple orders; use build_contract_and_orders instead"
        )
    return contract, orders[0]


def _build_orders_for_type(
    order_cls: type[Any], inputs: OrderSubmissionInputs
) -> list[Any]:
    order_type = inputs.order_type
    action = inputs.action_side
    quantity = inputs.quantity

    if order_type == "LMT":
        if inputs.limit_price <= 0:
            raise ValueError("limit_price must be positive for LMT")
        order = _new_order(order_cls, action=action, quantity=quantity, transmit=True)
        order.orderType = "LMT"
        order.lmtPrice = inputs.limit_price
        return [order]

    if order_type == "MKT":
        order = _new_order(order_cls, action=action, quantity=quantity, transmit=True)
        order.orderType = "MKT"
        return [order]

    if order_type == "STP":
        if inputs.stop_price is None or inputs.stop_price <= 0:
            raise ValueError("stop_price must be positive for STP")
        order = _new_order(order_cls, action=action, quantity=quantity, transmit=True)
        order.orderType = "STP"
        order.auxPrice = inputs.stop_price
        return [order]

    if order_type == "STP_LMT":
        if inputs.stop_price is None or inputs.stop_price <= 0:
            raise ValueError("stop_price must be positive for STP_LMT")
        if inputs.limit_price <= 0:
            raise ValueError("limit_price must be positive for STP_LMT")
        order = _new_order(order_cls, action=action, quantity=quantity, transmit=True)
        order.orderType = "STP LMT"
        order.auxPrice = inputs.stop_price
        order.lmtPrice = inputs.limit_price
        return [order]

    if order_type in {"TRAIL", "TRAIL_LMT"}:
        has_amount = inputs.trail_amount is not None and inputs.trail_amount > 0
        has_percent = inputs.trail_percent is not None and inputs.trail_percent > 0
        if has_amount == has_percent:
            raise ValueError(
                "exactly one of trail_amount or trail_percent must be set"
            )
        order = _new_order(order_cls, action=action, quantity=quantity, transmit=True)
        order.orderType = "TRAIL" if order_type == "TRAIL" else "TRAIL LIMIT"
        if has_amount:
            order.auxPrice = inputs.trail_amount
        else:
            order.trailingPercent = inputs.trail_percent
        if order_type == "TRAIL_LMT":
            if inputs.limit_price <= 0:
                raise ValueError("limit_price must be positive for TRAIL_LMT")
            order.lmtPrice = inputs.limit_price
        return [order]

    # BRACKET — parent LMT + opposite-side TP (LMT) [+ opposite-side SL (STP)]
    #
    # V1.2 §U: the take-profit pair (profit-harvest doctrine) emits
    # BRACKET without a stop-loss because the no-stop-loss rule is
    # locked in the doctrine. We detect that case here and emit a
    # 2-leg bracket instead of the 3-leg one.
    if inputs.limit_price <= 0:
        raise ValueError("limit_price must be positive for BRACKET")
    tp = inputs.bracket_take_profit_limit_price
    sl = inputs.bracket_stop_loss_price
    if tp is None or tp <= 0:
        raise ValueError("bracket_take_profit_limit_price must be positive")
    # ``sl=None`` is a deliberate doctrine signal (no stop-loss).
    # ``sl <= 0`` is still an error — the caller meant to set it but
    # passed garbage.
    if sl is not None and sl <= 0:
        raise ValueError("bracket_stop_loss_price must be positive when set")

    parent = _new_order(order_cls, action=action, quantity=quantity, transmit=False)
    parent.orderType = "LMT"
    parent.lmtPrice = inputs.limit_price

    opposite = _opposite_side(action)
    # When there is no stop-loss leg, the take-profit IS the last
    # leg and must transmit=True to release the bracket.
    take_profit_transmits = sl is None
    take_profit = _new_order(
        order_cls,
        action=opposite,
        quantity=quantity,
        transmit=take_profit_transmits,
    )
    take_profit.orderType = "LMT"
    take_profit.lmtPrice = tp
    take_profit.parentId = 0  # patched in submit() once parent_id is known
    if sl is None:
        return [parent, take_profit]

    stop_loss = _new_order(
        order_cls, action=opposite, quantity=quantity, transmit=True
    )
    stop_loss.orderType = "STP"
    stop_loss.auxPrice = sl
    stop_loss.parentId = 0  # patched in submit() once parent_id is known
    return [parent, take_profit, stop_loss]


class IbapiOrderSubmissionClient:
    """Disabled-by-default paper-only §21.3-vocabulary order-submission client."""

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
        contract_orders_builder: Callable[
            [OrderSubmissionInputs], tuple[Any, list[Any]]
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
        if contract_orders_builder is not None:
            self._contract_orders_builder = contract_orders_builder
        elif contract_order_builder is not None:
            # Adapt the legacy (single-order) injector by wrapping its result
            # in a one-element list. BRACKET cannot be tested through it.
            single_builder = contract_order_builder

            def _adapter(inputs: OrderSubmissionInputs) -> tuple[Any, list[Any]]:
                contract, order = single_builder(inputs)
                return contract, [order]

            self._contract_orders_builder = _adapter
        else:
            self._contract_orders_builder = build_contract_and_orders

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
        """Place one §21.3-vocabulary order (or a BRACKET parent + 2 children).

        Blocks until the ``openOrder`` / ``orderStatus`` callback fires for
        the parent or the timeout elapses. The result records the parent
        ``order_id`` / ``perm_id`` only; child IDs are derived as
        ``parent_id + 1`` and ``parent_id + 2`` per the IBKR convention.
        """

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
            contract, orders = self._contract_orders_builder(inputs)
        except ValueError as exc:
            return OrderSubmissionResult(
                accepted=False,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=self._client_id,
                ibkr_status_text=None,
                rejected_reason=f"invalid_inputs:{exc}",
            )

        # For BRACKET (or any multi-order build) wire child ``parentId``
        # to the parent's order_id so IBKR groups them.
        if len(orders) > 1:
            for child in orders[1:]:
                if hasattr(child, "parentId"):
                    child.parentId = order_id

        self._state.confirmation_event.clear()
        try:
            for offset, order in enumerate(orders):
                self._app.placeOrder(order_id + offset, contract, order)
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

        # Wait briefly for openOrder / orderStatus confirmation on the parent.
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
