"""Tests for the production IBKR order adapter (fake ib_insync client).

These verify the call orchestration + result mapping + the paper-only fail-
closed guard. They do NOT verify behaviour against a live broker — that
requires an IBKR paper account (see module docstring of the adapter)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_worker.ibkr_submission.ibkr_order_adapter import (
    IbkrOrderAdapter,
    OrderSessionRefusedError,
    open_order_adapter,
)
from portfolio_outlook_worker.ibkr_submission.order_builder import TickSize
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrConnectionLostError,
)


class _FakeOrder:
    def __init__(self, *, perm_id: int = 0, order_id: int = 0) -> None:
        self.permId = perm_id
        self.orderId = order_id
        self.action = "BUY"
        self.totalQuantity = 6.0
        self.orderType = "LMT"
        self.lmtPrice = 638.72
        self.tif = "DAY"
        self.outsideRth = False


class _FakeContract:
    def __init__(self) -> None:
        self.secType = "STK"
        self.symbol = "ASML"
        self.exchange = "AEB"
        self.currency = "EUR"
        self.conId = 1234


class _FakeTrade:
    def __init__(self, order: _FakeOrder, contract: _FakeContract) -> None:
        self.order = order
        self.contract = contract


class _FakeDetails:
    def __init__(self, min_tick: float) -> None:
        self.minTick = min_tick


class _FakeIB:
    def __init__(
        self,
        *,
        connected: bool = True,
        managed: list[str] | None = None,
        min_tick: float = 0.005,
        open_trades: list[_FakeTrade] | None = None,
        place_perm_id: int = 100200,
        qualify_raises: bool = False,
        qualify_empty: bool = False,
    ) -> None:
        self._connected = connected
        self._managed = managed if managed is not None else ["DU1234567"]
        self._min_tick = min_tick
        self._open_trades = open_trades or []
        self._place_perm_id = place_perm_id
        self._qualify_raises = qualify_raises
        self._qualify_empty = qualify_empty
        self.qualified: list[object] = []
        self.canceled: list[_FakeOrder] = []
        self.disconnected = False

    def qualifyContracts(self, *contracts: object) -> list[object]:
        if self._qualify_raises:
            raise RuntimeError("connection dropped during qualify")
        self.qualified.extend(contracts)
        return [] if self._qualify_empty else list(contracts)

    def isConnected(self) -> bool:
        return self._connected

    def managedAccounts(self) -> list[str]:
        return self._managed

    def reqContractDetails(self, contract: object) -> list[_FakeDetails]:
        return [_FakeDetails(self._min_tick)] if self._min_tick else []

    def placeOrder(self, contract: object, order: _FakeOrder) -> _FakeTrade:
        order.permId = self._place_perm_id
        order.orderId = 7
        return _FakeTrade(order, _FakeContract())

    def cancelOrder(self, order: _FakeOrder) -> None:
        self.canceled.append(order)

    def openTrades(self) -> list[_FakeTrade]:
        return self._open_trades

    def sleep(self, seconds: float) -> None:
        return None

    def disconnect(self) -> None:
        self.disconnected = True


def _adapter(ib: _FakeIB, **kw: object) -> IbkrOrderAdapter:
    return IbkrOrderAdapter(
        ib_client=ib,
        account_id="DU1234567",
        session_id="sess-1",
        contract_factory=lambda spec: _FakeContract(),
        **kw,  # type: ignore[arg-type]
    )


# ---- account mode + managed account ------------------------------------


def test_account_mode_paper_for_du_prefix() -> None:
    assert _adapter(_FakeIB()).account_mode == "paper"


def test_account_mode_live_for_non_paper_prefix() -> None:
    a = IbkrOrderAdapter(
        ib_client=_FakeIB(managed=["U7654321"]),
        account_id="U7654321",
        session_id="s",
    )
    assert a.account_mode == "live"


def test_fetch_managed_account_id_returns_first() -> None:
    assert _adapter(_FakeIB()).fetch_managed_account_id() == "DU1234567"


def test_fetch_managed_account_id_raises_when_disconnected() -> None:
    with pytest.raises(IbkrConnectionLostError):
        _adapter(_FakeIB(connected=False)).fetch_managed_account_id()


# ---- tick size ----------------------------------------------------------


def test_fetch_tick_size_maps_min_tick() -> None:
    tick = _adapter(_FakeIB(min_tick=0.005)).fetch_tick_size(
        symbol="ASML", exchange="AEB", currency="EUR", conid=1234
    )
    assert tick == TickSize(tick_size_local=Decimal("0.005"))


def test_fetch_tick_size_raises_without_details() -> None:
    with pytest.raises(IbkrConnectionLostError):
        _adapter(_FakeIB(min_tick=0)).fetch_tick_size(
            symbol="ASML", exchange="AEB", currency="EUR", conid=None
        )


# ---- place order --------------------------------------------------------


def test_place_order_returns_submitted_trade_with_perm_id() -> None:
    result = _adapter(_FakeIB(place_perm_id=100200)).place_order(
        _FakeContract(), _FakeOrder()
    )
    assert result.perm_id == 100200
    assert result.order_id == 7
    assert result.contract_dict["symbol"] == "ASML"
    assert result.order_dict["action"] == "BUY"
    assert result.order_dict["orderType"] == "LMT"


def test_place_order_raises_when_perm_id_never_assigned() -> None:
    ib = _FakeIB(place_perm_id=0)  # IBKR never assigns a permId
    adapter = _adapter(ib, perm_id_timeout_s=0.0, perm_id_poll_s=0.01)
    with pytest.raises(IbkrConnectionLostError):
        adapter.place_order(_FakeContract(), _FakeOrder())


def test_place_order_raises_when_disconnected() -> None:
    with pytest.raises(IbkrConnectionLostError):
        _adapter(_FakeIB(connected=False)).place_order(_FakeContract(), _FakeOrder())


def test_place_order_sets_account_and_qualifies_contract() -> None:
    ib = _FakeIB(place_perm_id=100200)
    order = _FakeOrder()
    contract = _FakeContract()
    _adapter(ib).place_order(contract, order)
    # Explicit account targeting + contract qualification before transmit.
    assert order.account == "DU1234567"
    assert contract in ib.qualified


def test_place_order_rejects_unqualifiable_contract() -> None:
    ib = _FakeIB(qualify_empty=True)
    with pytest.raises(ValueError):
        _adapter(ib).place_order(_FakeContract(), _FakeOrder())


def test_place_order_qualify_connection_error_is_connection_lost() -> None:
    ib = _FakeIB(qualify_raises=True)
    with pytest.raises(IbkrConnectionLostError):
        _adapter(ib).place_order(_FakeContract(), _FakeOrder())


# ---- cancel order -------------------------------------------------------


def test_cancel_order_cancels_matching_open_trade() -> None:
    order = _FakeOrder(perm_id=555)
    ib = _FakeIB(open_trades=[_FakeTrade(order, _FakeContract())])
    _adapter(ib).cancel_order(555)
    assert ib.canceled == [order]


def test_cancel_order_noop_when_perm_id_not_open() -> None:
    order = _FakeOrder(perm_id=555)
    ib = _FakeIB(open_trades=[_FakeTrade(order, _FakeContract())])
    _adapter(ib).cancel_order(999)  # not present → fire-and-forget no-op
    assert ib.canceled == []


# ---- open_order_adapter fail-closed gate -------------------------------


def test_open_order_adapter_refuses_live_account_under_paper_only() -> None:
    with pytest.raises(OrderSessionRefusedError):
        open_order_adapter(
            host="127.0.0.1",
            port=7497,
            client_id=2,
            account_id="U7654321",  # live-looking
            session_id="s",
            paper_only_mode=True,
            ib_client_factory=lambda: _FakeIB(managed=["U7654321"]),
        )


def test_open_order_adapter_opens_for_paper_account() -> None:
    adapter = open_order_adapter(
        host="127.0.0.1",
        port=7497,
        client_id=2,
        account_id="DU1234567",
        session_id="s",
        paper_only_mode=True,
        ib_client_factory=lambda: _FakeIB(managed=["DU1234567"]),
    )
    assert adapter.account_mode == "paper"
    assert adapter.fetch_managed_account_id() == "DU1234567"


def test_open_order_adapter_refuses_unmanaged_account() -> None:
    with pytest.raises(OrderSessionRefusedError):
        open_order_adapter(
            host="127.0.0.1",
            port=7497,
            client_id=2,
            account_id="DU1234567",
            session_id="s",
            paper_only_mode=True,
            ib_client_factory=lambda: _FakeIB(managed=["DU9999999"]),
        )
