"""Real ibapi-backed read-only IBKR sync client.

Connects once via ``ibapi``, runs four read-only requests (account summary,
positions, open orders, executions) and disconnects. Returns typed
``IbkrCash`` / ``IbkrPosition`` / ``IbkrOpenOrder`` / ``IbkrExecution``
dataclasses defined in ``ibkr_sync_contracts``.

The client never submits, modifies or cancels orders. It is disabled-by-default
and is only constructed by the factory when
``settings.ibkr_sync_real_client_enabled`` is True and host/port/client-id are
configured.
"""

from __future__ import annotations

import importlib
import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, cast

from portfolio_outlook_api.ibkr_ibapi_client_facade import load_ibapi_preflight_modules
from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
    IbkrReadOnlyAdapter,
)
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError

logger = logging.getLogger(__name__)

CONNECTION_ERROR_CODES = frozenset({502, 504, 1100, 1101, 1102, 1300, 2110})


class IbapiSyncAppProtocol(Protocol):
    """Minimal protocol for the dynamic ibapi EClient+EWrapper subclass."""

    def connect(self, host: str, port: int, client_id: int) -> None: ...

    def isConnected(self) -> bool: ...  # noqa: N802

    def disconnect(self) -> None: ...

    def run(self) -> None: ...

    def reqAccountSummary(  # noqa: N802
        self, reqId: int, group: str, tags: str
    ) -> None: ...

    def cancelAccountSummary(self, reqId: int) -> None: ...  # noqa: N802

    def reqPositions(self) -> None: ...  # noqa: N802

    def cancelPositions(self) -> None: ...  # noqa: N802

    def reqAllOpenOrders(self) -> None: ...  # noqa: N802

    def reqExecutions(self, reqId: int, exec_filter: object) -> None: ...  # noqa: N802


@dataclass
class _AccountSummaryRow:
    account: str
    tag: str
    value: str
    currency: str | None


@dataclass
class _PositionRow:
    account: str
    symbol: str
    sec_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    conid: int | None
    quantity: str
    avg_cost: str | None


@dataclass
class _OpenOrderRow:
    account: str
    order_id: int
    perm_id: int | None
    parent_id: int | None
    client_id: int | None
    symbol: str
    sec_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    action_side: str
    order_type: str
    quantity: str
    limit_price: str | None
    stop_price: str | None
    tif: str | None
    status: str
    filled_quantity: str
    remaining_quantity: str
    avg_fill_price: str | None
    last_status_at: datetime | None


@dataclass
class _ExecutionRow:
    account: str
    execution_id: str
    order_id: int
    perm_id: int | None
    symbol: str
    sec_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    side: str
    quantity: str
    price: str
    execution_time: datetime
    commission: str | None
    commission_currency: str | None
    realized_pnl: str | None


@dataclass
class _SyncSessionState:
    connected: bool = False
    account_summary_rows: dict[tuple[str, str], _AccountSummaryRow] = field(default_factory=dict)
    positions: list[_PositionRow] = field(default_factory=list)
    open_orders: dict[int, _OpenOrderRow] = field(default_factory=dict)
    executions: dict[str, _ExecutionRow] = field(default_factory=dict)
    account_summary_done: threading.Event = field(default_factory=threading.Event)
    positions_done: threading.Event = field(default_factory=threading.Event)
    open_orders_done: threading.Event = field(default_factory=threading.Event)
    executions_done: threading.Event = field(default_factory=threading.Event)
    fatal_error: Exception | None = None


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    if text == "" or text.lower() in {"none", "nan"}:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_decimal_required(value: object, default: str = "0") -> Decimal:
    parsed = _parse_decimal(value)
    if parsed is None:
        return Decimal(default)
    return parsed


def _parse_ibapi_time(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    for fmt in (
        "%Y%m%d %H:%M:%S",
        "%Y%m%d  %H:%M:%S",
        "%Y%m%d-%H:%M:%S",
        "%Y%m%d %H:%M:%S %Z",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            continue
    return None


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def build_sync_callbacks(
    state: _SyncSessionState,
    lock: threading.Lock,
) -> dict[str, Callable[..., None]]:
    """Build the EWrapper callback set used by both production and tests.

    Returning the callable set lets the production dynamic ibapi subclass and
    test fakes share the exact same parser/state-mutation logic, so a test
    that drives the fake app fires the same code paths the real ibapi event
    thread would.
    """

    def account_summary(  # noqa: N802
        _inner_self: Any,
        _req_id: int,
        account: str,
        tag: str,
        value: str,
        currency: str,
    ) -> None:
        with lock:
            state.account_summary_rows[(account, tag)] = _AccountSummaryRow(
                account=account,
                tag=tag,
                value=value,
                currency=_opt_str(currency),
            )

    def account_summary_end(_inner_self: Any, _req_id: int) -> None:  # noqa: N802
        state.account_summary_done.set()

    def position(  # noqa: N802
        _inner_self: Any,
        account: str,
        contract: Any,
        pos: Any,
        avg_cost: Any,
    ) -> None:
        with lock:
            state.positions.append(
                _PositionRow(
                    account=account,
                    symbol=str(getattr(contract, "symbol", "") or ""),
                    sec_type=str(getattr(contract, "secType", "") or ""),
                    currency=str(getattr(contract, "currency", "") or ""),
                    exchange=_opt_str(getattr(contract, "exchange", "")),
                    primary_exchange=_opt_str(getattr(contract, "primaryExchange", "")),
                    conid=int(getattr(contract, "conId", 0)) or None,
                    quantity=str(pos),
                    avg_cost=_opt_str(avg_cost),
                )
            )

    def position_end(_inner_self: Any) -> None:  # noqa: N802
        state.positions_done.set()

    def open_order(  # noqa: N802
        _inner_self: Any,
        order_id: int,
        contract: Any,
        order: Any,
        order_state: Any,
    ) -> None:
        account_value = str(getattr(order, "account", "") or "")
        remaining_attr = getattr(order_state, "remainingQuantity", "")
        remaining_text = str(remaining_attr) if remaining_attr is not None else ""
        if remaining_text == "":
            remaining_text = "0"
        with lock:
            state.open_orders[int(order_id)] = _OpenOrderRow(
                account=account_value,
                order_id=int(order_id),
                perm_id=int(getattr(order, "permId", 0)) or None,
                parent_id=int(getattr(order, "parentId", 0)) or None,
                client_id=int(getattr(order, "clientId", 0)) or None,
                symbol=str(getattr(contract, "symbol", "") or ""),
                sec_type=str(getattr(contract, "secType", "") or ""),
                currency=str(getattr(contract, "currency", "") or ""),
                exchange=_opt_str(getattr(contract, "exchange", "")),
                primary_exchange=_opt_str(getattr(contract, "primaryExchange", "")),
                action_side=str(getattr(order, "action", "") or ""),
                order_type=str(getattr(order, "orderType", "") or ""),
                quantity=str(getattr(order, "totalQuantity", "0")),
                limit_price=_opt_str(getattr(order, "lmtPrice", None)),
                stop_price=_opt_str(getattr(order, "auxPrice", None)),
                tif=_opt_str(getattr(order, "tif", "")),
                status=str(getattr(order_state, "status", "") or ""),
                filled_quantity=str(getattr(order, "filledQuantity", "0")),
                remaining_quantity=remaining_text,
                avg_fill_price=_opt_str(getattr(order_state, "avgFillPrice", None)),
                last_status_at=datetime.now(UTC),
            )

    def open_order_end(_inner_self: Any) -> None:  # noqa: N802
        state.open_orders_done.set()

    def exec_details(  # noqa: N802
        _inner_self: Any,
        _req_id: int,
        contract: Any,
        execution: Any,
    ) -> None:
        execution_id = str(getattr(execution, "execId", "") or "")
        if not execution_id:
            return
        with lock:
            state.executions[execution_id] = _ExecutionRow(
                account=str(getattr(execution, "acctNumber", "") or ""),
                execution_id=execution_id,
                order_id=int(getattr(execution, "orderId", 0) or 0),
                perm_id=int(getattr(execution, "permId", 0)) or None,
                symbol=str(getattr(contract, "symbol", "") or ""),
                sec_type=str(getattr(contract, "secType", "") or ""),
                currency=str(getattr(contract, "currency", "") or ""),
                exchange=_opt_str(getattr(execution, "exchange", "")),
                primary_exchange=_opt_str(getattr(contract, "primaryExchange", "")),
                side=str(getattr(execution, "side", "") or ""),
                quantity=str(getattr(execution, "shares", "0")),
                price=str(getattr(execution, "price", "0")),
                execution_time=_parse_ibapi_time(getattr(execution, "time", None))
                or datetime.now(UTC),
                commission=None,
                commission_currency=None,
                realized_pnl=None,
            )

    def commission_report(_inner_self: Any, report: Any) -> None:  # noqa: N802
        execution_id = str(getattr(report, "execId", "") or "")
        if not execution_id:
            return
        with lock:
            row = state.executions.get(execution_id)
            if row is None:
                return
            row.commission = _opt_str(getattr(report, "commission", None))
            row.commission_currency = _opt_str(getattr(report, "currency", ""))
            row.realized_pnl = _opt_str(getattr(report, "realizedPNL", None))

    def exec_details_end(_inner_self: Any, _req_id: int) -> None:  # noqa: N802
        state.executions_done.set()

    def error(  # noqa: N802
        _inner_self: Any,
        req_id: int,
        error_code: int,
        error_string: str,
        *_extra: object,
    ) -> None:
        if error_code in CONNECTION_ERROR_CODES:
            state.fatal_error = IbkrTwsReadonlyAdapterError("connection_failed")
            for event in (
                state.account_summary_done,
                state.positions_done,
                state.open_orders_done,
                state.executions_done,
            ):
                event.set()
        else:
            logger.debug(
                "ibapi non-fatal callback error reqId=%s code=%s message=%s",
                req_id,
                error_code,
                error_string,
            )

    return {
        "accountSummary": account_summary,
        "accountSummaryEnd": account_summary_end,
        "position": position,
        "positionEnd": position_end,
        "openOrder": open_order,
        "openOrderEnd": open_order_end,
        "execDetails": exec_details,
        "execDetailsEnd": exec_details_end,
        "commissionReport": commission_report,
        "error": error,
    }


class IbapiReadOnlySyncClient(IbkrReadOnlyAdapter):
    """Real ibapi read-only sync adapter.

    Holds a single ibapi connection across all four read-only requests
    (account summary, positions, open orders, executions). Each request blocks
    until its terminator callback fires or the timeout elapses. The caller is
    responsible for invoking ``close()`` afterwards (or using the client as a
    context manager).
    """

    def __init__(
        self,
        host: str,
        port: int,
        client_id: int,
        timeout_seconds: int,
        *,
        account_summary_tags: str,
        provider_code: str,
        app: IbapiSyncAppProtocol | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._timeout = max(1, int(timeout_seconds))
        self._account_summary_tags = account_summary_tags
        self._provider_code = provider_code
        self._lock = threading.Lock()
        self._state = _SyncSessionState()
        self._next_req_id_value = 1000
        self._thread: threading.Thread | None = None
        self._connect_attempted = False
        self._closed = False
        self._app = app if app is not None else self._build_app()

    def _next_req_id(self) -> int:
        with self._lock:
            value = self._next_req_id_value
            self._next_req_id_value += 1
            return value

    def _build_app(self) -> IbapiSyncAppProtocol:
        load_ibapi_preflight_modules()
        client_module = importlib.import_module("ibapi.client")
        wrapper_module = importlib.import_module("ibapi.wrapper")

        eclient_type = cast(type[Any], cast(Any, client_module).EClient)
        ewrapper_type = cast(type[Any], cast(Any, wrapper_module).EWrapper)

        callbacks = build_sync_callbacks(self._state, self._lock)

        def _init(inner_self: Any) -> None:
            eclient_type.__init__(inner_self, inner_self)

        manual_bases: tuple[type[Any], type[Any]] = (ewrapper_type, eclient_type)
        app_type = type(
            "_SyncApp",
            manual_bases,
            {"__init__": _init, **callbacks},
        )
        return cast(IbapiSyncAppProtocol, app_type())

    def _ensure_connected(self) -> None:
        with self._lock:
            if self._state.connected:
                return
            if self._closed:
                raise IbkrTwsReadonlyAdapterError("connection_failed")
            self._connect_attempted = True
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
            name=f"ibapi-sync-{self._client_id}",
            daemon=True,
        )
        thread.start()
        with self._lock:
            self._thread = thread
            self._state.connected = True

    def _wait_or_raise(self, event: threading.Event, label: str) -> None:
        if not event.wait(self._timeout):
            raise TimeoutError(f"{label}_timeout")
        if self._state.fatal_error is not None:
            raise self._state.fatal_error

    def sync_account_summary(self) -> list[IbkrCash]:
        self._ensure_connected()
        req_id = self._next_req_id()
        with self._lock:
            self._state.account_summary_rows.clear()
        self._state.account_summary_done.clear()
        self._app.reqAccountSummary(req_id, "All", self._account_summary_tags)
        try:
            self._wait_or_raise(self._state.account_summary_done, "account_summary")
        finally:
            try:
                self._app.cancelAccountSummary(req_id)
            except Exception:
                logger.debug("cancelAccountSummary raised; ignoring", exc_info=True)
        with self._lock:
            rows = list(self._state.account_summary_rows.values())
        return _build_cash_items(rows)

    def sync_positions(self) -> list[IbkrPosition]:
        self._ensure_connected()
        with self._lock:
            self._state.positions.clear()
        self._state.positions_done.clear()
        self._app.reqPositions()
        try:
            self._wait_or_raise(self._state.positions_done, "positions")
        finally:
            try:
                self._app.cancelPositions()
            except Exception:
                logger.debug("cancelPositions raised; ignoring", exc_info=True)
        with self._lock:
            rows = list(self._state.positions)
        return [_position_row_to_contract(row) for row in rows]

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        self._ensure_connected()
        with self._lock:
            self._state.open_orders.clear()
        self._state.open_orders_done.clear()
        self._app.reqAllOpenOrders()
        self._wait_or_raise(self._state.open_orders_done, "open_orders")
        with self._lock:
            rows = list(self._state.open_orders.values())
        return [_open_order_row_to_contract(row) for row in rows]

    def sync_executions(self) -> list[IbkrExecution]:
        self._ensure_connected()
        req_id = self._next_req_id()
        with self._lock:
            self._state.executions.clear()
        self._state.executions_done.clear()
        exec_filter = self._build_execution_filter()
        self._app.reqExecutions(req_id, exec_filter)
        self._wait_or_raise(self._state.executions_done, "executions")
        with self._lock:
            rows = list(self._state.executions.values())
        return [_execution_row_to_contract(row) for row in rows]

    def _build_execution_filter(self) -> object:
        try:
            module = importlib.import_module("ibapi.execution")
            execution_filter_cls = cast(Any, module).ExecutionFilter
            return cast(object, execution_filter_cls())
        except Exception:
            return object()

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
                logger.debug("ibapi disconnect raised; ignoring", exc_info=True)
        if thread is not None and thread.is_alive():
            thread.join(timeout=self._timeout)

    def __enter__(self) -> IbapiReadOnlySyncClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


@contextmanager
def real_sync_client_session(
    client: IbkrReadOnlyAdapter | None,
) -> Iterator[IbkrReadOnlyAdapter | None]:
    """Yield ``client`` and call ``close()`` afterwards when applicable."""
    try:
        yield client
    finally:
        close_method = getattr(client, "close", None)
        if callable(close_method):
            try:
                close_method()
            except Exception:
                logger.debug("real sync client close raised; ignoring", exc_info=True)


def _build_cash_items(rows: list[_AccountSummaryRow]) -> list[IbkrCash]:
    grouped: dict[str, dict[str, _AccountSummaryRow]] = {}
    for row in rows:
        grouped.setdefault(row.account, {})[row.tag] = row
    items: list[IbkrCash] = []
    for account_ref, by_tag in grouped.items():
        cash_row = by_tag.get("TotalCashValue")
        cash_value = _parse_decimal_required(cash_row.value if cash_row else "0")
        base_currency = (cash_row.currency if cash_row else None) or _infer_currency(by_tag)
        available_row = by_tag.get("AvailableFunds")
        buying_power_row = by_tag.get("BuyingPower")
        items.append(
            IbkrCash(
                account_ref=account_ref,
                base_currency=base_currency or "USD",
                cash=cash_value,
                available_funds=_parse_decimal(available_row.value) if available_row else None,
                buying_power=_parse_decimal(buying_power_row.value) if buying_power_row else None,
            )
        )
    return items


def _infer_currency(by_tag: dict[str, _AccountSummaryRow]) -> str | None:
    for row in by_tag.values():
        if row.currency:
            return row.currency
    return None


def _position_row_to_contract(row: _PositionRow) -> IbkrPosition:
    return IbkrPosition(
        account_ref=row.account,
        symbol=row.symbol,
        security_type=row.sec_type,
        currency=row.currency,
        quantity=_parse_decimal_required(row.quantity),
        average_cost=_parse_decimal(row.avg_cost),
        conid=row.conid,
        exchange=row.exchange,
        primary_exchange=row.primary_exchange,
    )


def _open_order_row_to_contract(row: _OpenOrderRow) -> IbkrOpenOrder:
    quantity = _parse_decimal_required(row.quantity)
    filled = _parse_decimal_required(row.filled_quantity)
    remaining_parsed = _parse_decimal(row.remaining_quantity)
    remaining = (
        remaining_parsed
        if remaining_parsed is not None
        else max(quantity - filled, Decimal("0"))
    )
    return IbkrOpenOrder(
        account_ref=row.account,
        ibkr_order_id=row.order_id,
        ibkr_perm_id=row.perm_id,
        parent_order_id=row.parent_id,
        client_id=row.client_id,
        symbol=row.symbol,
        security_type=row.sec_type,
        currency=row.currency,
        exchange=row.exchange,
        primary_exchange=row.primary_exchange,
        action_side=row.action_side,
        order_type=row.order_type,
        quantity=quantity,
        limit_price=_parse_decimal(row.limit_price),
        stop_price=_parse_decimal(row.stop_price),
        tif=row.tif,
        status=row.status or "Unknown",
        filled_quantity=filled,
        remaining_quantity=remaining,
        average_fill_price=_parse_decimal(row.avg_fill_price),
        last_status_at=row.last_status_at,
        raw_status_reference=None,
    )


def _execution_row_to_contract(row: _ExecutionRow) -> IbkrExecution:
    return IbkrExecution(
        account_ref=row.account,
        execution_id=row.execution_id,
        ibkr_order_id=row.order_id,
        ibkr_perm_id=row.perm_id,
        symbol=row.symbol,
        security_type=row.sec_type,
        currency=row.currency,
        exchange=row.exchange,
        primary_exchange=row.primary_exchange,
        side=row.side,
        quantity=_parse_decimal_required(row.quantity),
        price=_parse_decimal_required(row.price),
        execution_time=row.execution_time,
        commission=_parse_decimal(row.commission),
        commission_currency=row.commission_currency,
        realized_pnl=_parse_decimal(row.realized_pnl),
        raw_execution_reference=None,
    )
