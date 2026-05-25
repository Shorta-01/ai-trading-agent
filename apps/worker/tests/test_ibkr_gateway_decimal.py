"""Task 126 — Decimal-only invariant at the gateway boundary.

Every monetary value returned by the gateway must be a ``Decimal``;
``ib_insync`` happens to return account-summary numbers as strings,
so the gateway must convert without ever falling back to ``float``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import IbkrConnectionAuditRecord

from portfolio_outlook_worker.ibkr_gateway import IbkrGateway


@dataclass
class _Entry:
    tag: str
    currency: str
    value: object


@dataclass
class _Contract:
    conId: int
    symbol: str
    exchange: str
    currency: str


@dataclass
class _PositionRow:
    contract: _Contract
    position: object
    avgCost: object


class _FakeIB:
    """Connected fake that returns mixed-type values for the Decimal tests."""

    def __init__(
        self,
        *,
        summary: list[_Entry],
        positions: list[_PositionRow],
    ) -> None:
        self._summary = summary
        self._positions = positions

    def connect(self, *args: object, **kwargs: object) -> object:
        return self

    def disconnect(self) -> object:
        return self

    def isConnected(self) -> bool:
        return True

    def managedAccounts(self) -> list[str]:
        return ["DU1234567"]

    def reqContractDetails(self, contract: object) -> list[object]:
        return []  # → paper

    def accountSummary(self, account: str = "") -> list[object]:
        return list(self._summary)

    def positions(self, account: str = "") -> list[object]:
        return list(self._positions)


class _Audit:
    def __init__(self) -> None:
        self.records: list[IbkrConnectionAuditRecord] = []

    def append(self, record: IbkrConnectionAuditRecord) -> object:
        self.records.append(record)
        return record


_FIXED_NOW = datetime(2026, 5, 25, 7, 0, 0, tzinfo=UTC)


def _connected_gateway(ib: _FakeIB) -> IbkrGateway:
    gw = IbkrGateway(
        ib_client_factory=lambda: ib,
        audit_repo=_Audit(),
        clock=lambda: _FIXED_NOW,
    )
    gw.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",
    )
    return gw


def test_fetch_account_summary_converts_string_values_to_decimal() -> None:
    """``ib_insync`` returns account-summary values as strings."""

    ib = _FakeIB(
        summary=[
            _Entry(tag="AvailableFunds", currency="EUR", value="12345.6789"),
            _Entry(tag="NetLiquidationValue", currency="EUR", value="99999.99"),
            _Entry(tag="TotalCashValue", currency="USD", value="500.00"),
        ],
        positions=[],
    )
    summary = _connected_gateway(ib).fetch_account_summary()

    assert len(summary.rows) == 3
    for row in summary.rows:
        assert isinstance(row.value, Decimal)
    assert summary.rows[0].value == Decimal("12345.6789")
    assert summary.rows[1].value == Decimal("99999.99")
    assert summary.rows[2].value == Decimal("500.00")
    assert summary.as_of == _FIXED_NOW


def test_fetch_account_summary_handles_none_and_blank_values() -> None:
    ib = _FakeIB(
        summary=[
            _Entry(tag="BuyingPower", currency="EUR", value=None),
            _Entry(tag="TotalCashValue", currency="EUR", value=""),
            _Entry(tag="GrossPositionValue", currency="EUR", value="abc"),
        ],
        positions=[],
    )
    summary = _connected_gateway(ib).fetch_account_summary()
    for row in summary.rows:
        assert isinstance(row.value, Decimal)
        assert row.value == Decimal("0")


def test_fetch_positions_returns_decimal_quantity_and_avg_cost() -> None:
    ib = _FakeIB(
        summary=[],
        positions=[
            _PositionRow(
                contract=_Contract(
                    conId=265598,
                    symbol="AAPL",
                    exchange="SMART",
                    currency="USD",
                ),
                position="100",
                avgCost="135.4567",
            ),
            _PositionRow(
                contract=_Contract(
                    conId=4391,
                    symbol="MSFT",
                    exchange="SMART",
                    currency="USD",
                ),
                position=Decimal("250.5"),
                avgCost=Decimal("310.123456"),
            ),
        ],
    )

    rows = _connected_gateway(ib).fetch_positions()

    assert len(rows) == 2
    assert isinstance(rows[0].quantity, Decimal)
    assert isinstance(rows[0].avg_cost, Decimal)
    assert rows[0].quantity == Decimal("100")
    assert rows[0].avg_cost == Decimal("135.4567")
    assert rows[0].conid == 265598
    assert rows[0].symbol == "AAPL"
    assert rows[0].exchange == "SMART"
    assert rows[0].currency == "USD"
    assert rows[0].as_of == _FIXED_NOW

    assert rows[1].quantity == Decimal("250.5")
    assert rows[1].avg_cost == Decimal("310.123456")
