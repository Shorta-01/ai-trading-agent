"""Tests for the reconciliation fetchers (fake read-only IB client).

Validate the fill/trade → reconciliation-record mapping. They do NOT verify
behaviour against a live broker (see the adapter module docstring)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from portfolio_outlook_worker.ibkr_reconciliation.ibkr_reconciliation_adapter import (
    IbkrExecutionFetcher,
    IbkrOrderStatusFetcher,
)

_NOW = datetime(2026, 5, 28, 10, 0, tzinfo=UTC)


class _Execution:
    def __init__(
        self,
        *,
        exec_id: str = "exec-1",
        perm_id: int = 100100,
        acct: str = "DU1234567",
        side: str = "BOT",
        price: float = 638.72,
        shares: float = 6.0,
        time: datetime | None = _NOW,
    ) -> None:
        self.execId = exec_id
        self.permId = perm_id
        self.acctNumber = acct
        self.side = side
        self.price = price
        self.shares = shares
        self.time = time


class _Contract:
    def __init__(self, con_id: int = 265598) -> None:
        self.conId = con_id


class _Fill:
    def __init__(self, execution: _Execution, contract: _Contract | None = None) -> None:
        self.execution = execution
        self.contract = contract or _Contract()


class _OrderStatus:
    def __init__(self, status: str) -> None:
        self.status = status


class _Order:
    def __init__(self, perm_id: int) -> None:
        self.permId = perm_id


class _Trade:
    def __init__(self, perm_id: int, status: str) -> None:
        self.order = _Order(perm_id)
        self.orderStatus = _OrderStatus(status)


class _FakeIB:
    def __init__(
        self,
        *,
        connected: bool = True,
        fills: list[_Fill] | None = None,
        trades: list[_Trade] | None = None,
    ) -> None:
        self._connected = connected
        self._fills = fills or []
        self._trades = trades or []

    def isConnected(self) -> bool:
        return self._connected

    def reqExecutions(self, *args: object, **kwargs: object) -> list[_Fill]:
        return self._fills

    def trades(self) -> list[_Trade]:
        return self._trades


# ---- execution fetcher --------------------------------------------------


def test_fetch_executions_maps_buy_fill() -> None:
    ib = _FakeIB(fills=[_Fill(_Execution(side="BOT"))])
    out = IbkrExecutionFetcher(ib_client=ib).fetch_recent_executions(
        account_id="DU1234567"
    )
    assert len(out) == 1
    rec = out[0]
    assert rec.ibkr_exec_id == "exec-1"
    assert rec.ibkr_perm_id == 100100
    assert rec.side == "BUY"
    assert rec.conid == "265598"
    assert rec.fill_price_local == Decimal("638.72")
    assert rec.fill_quantity == Decimal("6.0")
    assert rec.fill_time == _NOW


def test_fetch_executions_maps_sell_side() -> None:
    ib = _FakeIB(fills=[_Fill(_Execution(side="SLD"))])
    out = IbkrExecutionFetcher(ib_client=ib).fetch_recent_executions(
        account_id="DU1234567"
    )
    assert out[0].side == "SELL"


def test_fetch_executions_filters_other_accounts() -> None:
    ib = _FakeIB(fills=[_Fill(_Execution(acct="DU9999999"))])
    out = IbkrExecutionFetcher(ib_client=ib).fetch_recent_executions(
        account_id="DU1234567"
    )
    assert out == ()


def test_fetch_executions_skips_unknown_side_or_missing_fields() -> None:
    ib = _FakeIB(
        fills=[
            _Fill(_Execution(side="???")),  # unknown side
            _Fill(_Execution(exec_id="", side="BOT")),  # missing exec id
            _Fill(_Execution(time=None, side="BOT")),  # missing time
        ]
    )
    out = IbkrExecutionFetcher(ib_client=ib).fetch_recent_executions(
        account_id="DU1234567"
    )
    assert out == ()


def test_fetch_executions_empty_when_disconnected() -> None:
    ib = _FakeIB(connected=False, fills=[_Fill(_Execution())])
    assert (
        IbkrExecutionFetcher(ib_client=ib).fetch_recent_executions(
            account_id="DU1234567"
        )
        == ()
    )


# ---- order status fetcher ----------------------------------------------


def test_order_status_found_returns_raw_status() -> None:
    ib = _FakeIB(trades=[_Trade(100100, "Submitted")])
    res = IbkrOrderStatusFetcher(ib_client=ib).fetch_order_status(
        ibkr_perm_id=100100, account_id="DU1234567"
    )
    assert res.found_in_ibkr is True
    assert res.ibkr_raw_status == "Submitted"


def test_order_status_not_found_when_perm_id_absent() -> None:
    ib = _FakeIB(trades=[_Trade(999, "Filled")])
    res = IbkrOrderStatusFetcher(ib_client=ib).fetch_order_status(
        ibkr_perm_id=100100, account_id="DU1234567"
    )
    assert res.found_in_ibkr is False
    assert res.ibkr_raw_status is None


def test_order_status_not_found_when_disconnected() -> None:
    ib = _FakeIB(connected=False, trades=[_Trade(100100, "Submitted")])
    res = IbkrOrderStatusFetcher(ib_client=ib).fetch_order_status(
        ibkr_perm_id=100100, account_id="DU1234567"
    )
    assert res.found_in_ibkr is False
