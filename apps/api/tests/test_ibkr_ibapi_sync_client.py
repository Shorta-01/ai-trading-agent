"""Tests for the real ibapi-backed read-only IBKR sync client.

The client is exercised with an injected fake ``ibapi`` app so no real network
or TWS/Gateway is needed in CI. ``build_sync_callbacks`` is the same callback
set used in production: the fake app simply forwards request calls to those
callbacks synchronously, so this proves the real parser/state-mutation logic.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest

from portfolio_outlook_api.ibkr_ibapi_sync_client import (
    IbapiReadOnlySyncClient,
    build_sync_callbacks,
)
from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
)
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError


class _FakeContract:
    def __init__(
        self,
        *,
        symbol: str,
        sec_type: str = "STK",
        currency: str = "USD",
        exchange: str = "SMART",
        primary_exchange: str = "NASDAQ",
        con_id: int = 0,
    ) -> None:
        self.symbol = symbol
        self.secType = sec_type
        self.currency = currency
        self.exchange = exchange
        self.primaryExchange = primary_exchange
        self.conId = con_id


class _FakeOrder:
    def __init__(
        self,
        *,
        account: str,
        action: str,
        order_type: str,
        total_quantity: Decimal,
        lmt_price: Decimal | None,
        tif: str,
        client_id: int,
        perm_id: int,
        filled: Decimal,
    ) -> None:
        self.account = account
        self.action = action
        self.orderType = order_type
        self.totalQuantity = total_quantity
        self.lmtPrice = lmt_price
        self.auxPrice = None
        self.tif = tif
        self.clientId = client_id
        self.permId = perm_id
        self.parentId = 0
        self.filledQuantity = filled


class _FakeOrderState:
    def __init__(self, *, status: str, remaining: Decimal, avg_fill_price: Decimal | None) -> None:
        self.status = status
        self.remainingQuantity = remaining
        self.avgFillPrice = avg_fill_price


class _FakeExecution:
    def __init__(
        self,
        *,
        exec_id: str,
        order_id: int,
        perm_id: int,
        account: str,
        exchange: str,
        side: str,
        shares: Decimal,
        price: Decimal,
        time_str: str,
    ) -> None:
        self.execId = exec_id
        self.orderId = order_id
        self.permId = perm_id
        self.acctNumber = account
        self.exchange = exchange
        self.side = side
        self.shares = shares
        self.price = price
        self.time = time_str


class _FakeCommissionReport:
    def __init__(
        self,
        *,
        exec_id: str,
        commission: Decimal,
        currency: str,
        realized_pnl: Decimal,
    ) -> None:
        self.execId = exec_id
        self.commission = commission
        self.currency = currency
        self.realizedPNL = realized_pnl


class _FakeIbapiApp:
    """Fake ibapi application that fires production callbacks synchronously."""

    def __init__(
        self,
        *,
        connect_error: Exception | None = None,
        connected_after_connect: bool = True,
        account_summary_rows: list[tuple[str, str, str, str]] | None = None,
        positions: list[tuple[str, _FakeContract, Decimal, Decimal]] | None = None,
        open_orders: list[tuple[int, _FakeContract, _FakeOrder, _FakeOrderState]] | None = None,
        executions: list[tuple[_FakeContract, _FakeExecution]] | None = None,
        commission_reports: list[_FakeCommissionReport] | None = None,
        error_on_account_summary: tuple[int, str] | None = None,
    ) -> None:
        self.connect_error = connect_error
        self.connected_after_connect = connected_after_connect
        self.account_summary_rows = account_summary_rows or []
        self.positions = positions or []
        self.open_orders = open_orders or []
        self.executions = executions or []
        self.commission_reports = commission_reports or []
        self.error_on_account_summary = error_on_account_summary

        self.connected = False
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.run_calls = 0
        self.req_account_summary_calls: list[tuple[int, str, str]] = []
        self.cancel_account_summary_calls: list[int] = []
        self.req_positions_calls = 0
        self.cancel_positions_calls = 0
        self.req_all_open_orders_calls = 0
        self.req_executions_calls: list[tuple[int, object]] = []

        # Production callbacks are installed by ``attach_callbacks`` below.
        self._cb: dict[str, Any] = {}

    def attach_callbacks(self, callbacks: dict[str, Any]) -> None:
        self._cb = callbacks

    # ---- ibapi-style protocol surface ----

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = self.connected_after_connect

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.connected = False

    def run(self) -> None:
        self.run_calls += 1

    def reqAccountSummary(self, reqId: int, group: str, tags: str) -> None:  # noqa: N802
        self.req_account_summary_calls.append((reqId, group, tags))
        if self.error_on_account_summary is not None:
            code, message = self.error_on_account_summary
            self._cb["error"](self, reqId, code, message)
            return
        for account, tag, value, currency in self.account_summary_rows:
            self._cb["accountSummary"](self, reqId, account, tag, value, currency)
        self._cb["accountSummaryEnd"](self, reqId)

    def cancelAccountSummary(self, reqId: int) -> None:  # noqa: N802
        self.cancel_account_summary_calls.append(reqId)

    def reqPositions(self) -> None:  # noqa: N802
        self.req_positions_calls += 1
        for account, contract, pos, avg in self.positions:
            self._cb["position"](self, account, contract, pos, avg)
        self._cb["positionEnd"](self)

    def cancelPositions(self) -> None:  # noqa: N802
        self.cancel_positions_calls += 1

    def reqAllOpenOrders(self) -> None:  # noqa: N802
        self.req_all_open_orders_calls += 1
        for order_id, contract, order, order_state in self.open_orders:
            self._cb["openOrder"](self, order_id, contract, order, order_state)
        self._cb["openOrderEnd"](self)

    def reqExecutions(self, reqId: int, exec_filter: object) -> None:  # noqa: N802
        self.req_executions_calls.append((reqId, exec_filter))
        for contract, execution in self.executions:
            self._cb["execDetails"](self, reqId, contract, execution)
        for report in self.commission_reports:
            self._cb["commissionReport"](self, report)
        self._cb["execDetailsEnd"](self, reqId)


@pytest.fixture
def opened_clients() -> Iterator[list[IbapiReadOnlySyncClient]]:
    """Track clients opened during a test so they all get closed."""

    bag: list[IbapiReadOnlySyncClient] = []
    yield bag
    for client in bag:
        client.close()


def _make_client(
    fake: _FakeIbapiApp,
    bag: list[IbapiReadOnlySyncClient],
    *,
    timeout_seconds: int = 5,
    tags: str = "TotalCashValue,AvailableFunds,BuyingPower",
) -> IbapiReadOnlySyncClient:
    client = IbapiReadOnlySyncClient(
        host="127.0.0.1",
        port=4002,
        client_id=11,
        timeout_seconds=timeout_seconds,
        account_summary_tags=tags,
        provider_code="ibkr",
        app=fake,
    )
    fake.attach_callbacks(build_sync_callbacks(client._state, client._lock))
    bag.append(client)
    return client


def test_sync_account_summary_returns_typed_cash_with_decimal_values(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        account_summary_rows=[
            ("DU12345", "TotalCashValue", "1500.75", "USD"),
            ("DU12345", "AvailableFunds", "1200.00", "USD"),
            ("DU12345", "BuyingPower", "2400.00", "USD"),
        ],
    )
    client = _make_client(fake, opened_clients)

    cash_items = client.sync_account_summary()

    assert len(cash_items) == 1
    item = cash_items[0]
    assert isinstance(item, IbkrCash)
    assert item.account_ref == "DU12345"
    assert item.base_currency == "USD"
    assert item.cash == Decimal("1500.75")
    assert item.available_funds == Decimal("1200.00")
    assert item.buying_power == Decimal("2400.00")
    assert fake.connect_calls == 1
    assert fake.req_account_summary_calls[0][1] == "All"
    assert fake.cancel_account_summary_calls == [fake.req_account_summary_calls[0][0]]


def test_sync_positions_returns_typed_positions_with_decimal_quantity(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        positions=[
            (
                "DU12345",
                _FakeContract(symbol="AAPL", con_id=265598),
                Decimal("10"),
                Decimal("175.50"),
            ),
            (
                "DU12345",
                _FakeContract(symbol="MSFT", con_id=272093),
                Decimal("3"),
                Decimal("300.10"),
            ),
        ],
    )
    client = _make_client(fake, opened_clients)

    positions = client.sync_positions()

    assert len(positions) == 2
    aapl, msft = positions
    assert isinstance(aapl, IbkrPosition)
    assert aapl.symbol == "AAPL"
    assert aapl.quantity == Decimal("10")
    assert aapl.average_cost == Decimal("175.50")
    assert aapl.conid == 265598
    assert msft.symbol == "MSFT"
    assert msft.quantity == Decimal("3")
    assert fake.req_positions_calls == 1
    assert fake.cancel_positions_calls == 1


def test_sync_open_orders_returns_typed_orders_with_remaining(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        open_orders=[
            (
                100,
                _FakeContract(symbol="GOOG"),
                _FakeOrder(
                    account="DU12345",
                    action="BUY",
                    order_type="LMT",
                    total_quantity=Decimal("5"),
                    lmt_price=Decimal("130.00"),
                    tif="DAY",
                    client_id=11,
                    perm_id=999,
                    filled=Decimal("0"),
                ),
                _FakeOrderState(
                    status="Submitted",
                    remaining=Decimal("5"),
                    avg_fill_price=None,
                ),
            ),
        ],
    )
    client = _make_client(fake, opened_clients)

    orders = client.sync_open_orders()

    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, IbkrOpenOrder)
    assert order.ibkr_order_id == 100
    assert order.symbol == "GOOG"
    assert order.action_side == "BUY"
    assert order.order_type == "LMT"
    assert order.quantity == Decimal("5")
    assert order.limit_price == Decimal("130.00")
    assert order.remaining_quantity == Decimal("5")
    assert order.filled_quantity == Decimal("0")
    assert order.status == "Submitted"
    assert order.tif == "DAY"
    assert fake.req_all_open_orders_calls == 1


def test_sync_executions_merges_commission_reports(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        executions=[
            (
                _FakeContract(symbol="TSLA"),
                _FakeExecution(
                    exec_id="0001.exec.1",
                    order_id=200,
                    perm_id=555,
                    account="DU12345",
                    exchange="SMART",
                    side="BOT",
                    shares=Decimal("2"),
                    price=Decimal("250.10"),
                    time_str="20250115 10:30:00",
                ),
            ),
        ],
        commission_reports=[
            _FakeCommissionReport(
                exec_id="0001.exec.1",
                commission=Decimal("1.05"),
                currency="USD",
                realized_pnl=Decimal("0"),
            )
        ],
    )
    client = _make_client(fake, opened_clients)

    executions = client.sync_executions()

    assert len(executions) == 1
    execution = executions[0]
    assert isinstance(execution, IbkrExecution)
    assert execution.execution_id == "0001.exec.1"
    assert execution.ibkr_order_id == 200
    assert execution.symbol == "TSLA"
    assert execution.side == "BOT"
    assert execution.quantity == Decimal("2")
    assert execution.price == Decimal("250.10")
    assert execution.commission == Decimal("1.05")
    assert execution.commission_currency == "USD"
    assert execution.realized_pnl == Decimal("0")
    assert execution.execution_time.year == 2025


def test_sync_account_summary_raises_on_connection_error_code(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(error_on_account_summary=(502, "couldn't connect"))
    client = _make_client(fake, opened_clients)

    with pytest.raises(IbkrTwsReadonlyAdapterError):
        client.sync_account_summary()


def test_sync_account_summary_times_out_when_end_never_fires(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    class _StuckApp(_FakeIbapiApp):
        def reqAccountSummary(self, reqId: int, group: str, tags: str) -> None:  # noqa: N802
            self.req_account_summary_calls.append((reqId, group, tags))
            # Deliberately never fire end-callback to trigger timeout.

    fake = _StuckApp()
    client = _make_client(fake, opened_clients, timeout_seconds=1)

    with pytest.raises(TimeoutError):
        client.sync_account_summary()


def test_connection_failure_raises_adapter_error(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(connect_error=OSError("refused"))
    client = _make_client(fake, opened_clients)

    with pytest.raises(IbkrTwsReadonlyAdapterError):
        client.sync_account_summary()


def test_not_connected_after_connect_raises_adapter_error(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(connected_after_connect=False)
    client = _make_client(fake, opened_clients)

    with pytest.raises(IbkrTwsReadonlyAdapterError):
        client.sync_account_summary()


def test_close_disconnects_when_previously_connected(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        account_summary_rows=[("DU12345", "TotalCashValue", "100.00", "USD")],
    )
    client = _make_client(fake, opened_clients)

    client.sync_account_summary()
    assert fake.disconnect_calls == 0
    client.close()
    assert fake.disconnect_calls == 1
    # Closing twice must be idempotent.
    client.close()
    assert fake.disconnect_calls == 1


def test_full_sync_cycle_calls_all_four_endpoints_with_single_connection(
    opened_clients: list[IbapiReadOnlySyncClient],
) -> None:
    fake = _FakeIbapiApp(
        account_summary_rows=[("DU12345", "TotalCashValue", "500.00", "USD")],
        positions=[
            (
                "DU12345",
                _FakeContract(symbol="AAPL"),
                Decimal("1"),
                Decimal("180.00"),
            )
        ],
    )
    client = _make_client(fake, opened_clients)

    client.sync_account_summary()
    client.sync_positions()
    client.sync_open_orders()
    client.sync_executions()

    # connect() must be called exactly once across all four requests.
    assert fake.connect_calls == 1
    assert fake.run_calls == 1
    assert fake.disconnect_calls == 0
