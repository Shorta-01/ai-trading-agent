from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    CashLedgerEntry,
    LedgerEntryType,
    Money,
    PaperTransaction,
    Quantity,
    TransactionSide,
    TransactionStatus,
)

from portfolio_outlook_portfolio import (
    CurrencyMismatchError,
    InvalidAccountingInputError,
    build_paper_portfolio_snapshot,
    calculate_cash_balances,
    calculate_position_quantities,
    calculate_transaction_totals,
    validate_no_oversells,
)


def _entry(entry_id: str, amount: str, currency: str = "EUR") -> CashLedgerEntry:
    return CashLedgerEntry(
        ledger_entry_id=entry_id,
        portfolio_id="pf_1",
        entry_type=LedgerEntryType.CASH_ADJUSTMENT,
        amount=Money(amount=Decimal(amount), currency=currency),
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        reason_nl="Test",
    )


def _tx(
    tx_id: str,
    *,
    side: TransactionSide,
    quantity: str,
    gross: str,
    currency: str = "EUR",
    status: TransactionStatus = TransactionStatus.FILLED,
    instrument_id: str = "inst_1",
    occurred_at: datetime = datetime(2026, 1, 1, 10, 0, 0),
    portfolio_id: str = "pf_1",
) -> PaperTransaction:
    return PaperTransaction(
        transaction_id=tx_id,
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        side=side,
        status=status,
        quantity=Quantity(value=Decimal(quantity)),
        price=Money(amount=Decimal("10"), currency=currency),
        gross_amount=Money(amount=Decimal(gross), currency=currency),
        net_amount=Money(amount=Decimal(gross), currency=currency),
        costs=[],
        occurred_at=occurred_at,
        reason_nl="Test",
    )


def test_calculate_cash_balances_cases() -> None:
    assert calculate_cash_balances([]) == {}

    single = calculate_cash_balances([_entry("e1", "100")])
    assert single["EUR"] == Money(amount=Decimal("100"), currency="EUR")

    mix = calculate_cash_balances([_entry("e1", "100"), _entry("e2", "-40")])
    assert mix["EUR"] == Money(amount=Decimal("60"), currency="EUR")

    multiccy = calculate_cash_balances([_entry("e1", "10", "EUR"), _entry("e2", "20", "USD")])
    assert multiccy["EUR"] == Money(amount=Decimal("10"), currency="EUR")
    assert multiccy["USD"] == Money(amount=Decimal("20"), currency="USD")

    signed = calculate_cash_balances([_entry("e1", "-50"), _entry("e2", "49")])
    assert signed["EUR"] == Money(amount=Decimal("-1"), currency="EUR")


def test_calculate_position_quantities_cases() -> None:
    assert calculate_position_quantities([]) == {}

    one_buy = calculate_position_quantities(
        [_tx("t1", side=TransactionSide.BUY, quantity="2", gross="20")]
    )
    assert one_buy["inst_1"].quantity == Quantity(value=Decimal("2"))

    two_buys = calculate_position_quantities(
        [
            _tx("t1", side=TransactionSide.BUY, quantity="2", gross="20"),
            _tx("t2", side=TransactionSide.BUY, quantity="3", gross="30"),
        ]
    )
    assert two_buys["inst_1"].quantity == Quantity(value=Decimal("5"))

    reduced = calculate_position_quantities(
        [
            _tx("t1", side=TransactionSide.BUY, quantity="5", gross="50"),
            _tx("t2", side=TransactionSide.SELL, quantity="2", gross="20"),
        ]
    )
    assert reduced["inst_1"].quantity == Quantity(value=Decimal("3"))

    flat = calculate_position_quantities(
        [
            _tx("t1", side=TransactionSide.BUY, quantity="2", gross="20"),
            _tx("t2", side=TransactionSide.SELL, quantity="2", gross="20"),
        ]
    )
    assert flat == {}

    with pytest.raises(InvalidAccountingInputError):
        calculate_position_quantities(
            [_tx("t1", side=TransactionSide.SELL, quantity="1", gross="10")]
        )

    ignored = calculate_position_quantities(
        [
            _tx(
                "t1",
                side=TransactionSide.BUY,
                quantity="1",
                gross="10",
                status=TransactionStatus.PENDING,
            ),
            _tx("t2", side=TransactionSide.BUY, quantity="2", gross="20"),
        ]
    )
    assert ignored["inst_1"].quantity == Quantity(value=Decimal("2"))


def test_calculate_transaction_totals_cases() -> None:
    assert calculate_transaction_totals([]) == {}

    totals = calculate_transaction_totals(
        [
            _tx("b1", side=TransactionSide.BUY, quantity="2", gross="20"),
            _tx("b2", side=TransactionSide.BUY, quantity="3", gross="30"),
            _tx("s1", side=TransactionSide.SELL, quantity="1", gross="15"),
        ]
    )
    inst = totals["inst_1"]
    assert inst.bought_quantity == Quantity(value=Decimal("5"))
    assert inst.sold_quantity == Quantity(value=Decimal("1"))
    assert inst.buy_gross_amount == Money(amount=Decimal("50"), currency="EUR")
    assert inst.sell_gross_amount == Money(amount=Decimal("15"), currency="EUR")

    sell_only = calculate_transaction_totals(
        [
            _tx("s1", side=TransactionSide.SELL, quantity="1", gross="10"),
        ]
    )["inst_1"]
    assert sell_only.buy_gross_amount is None

    buy_only = calculate_transaction_totals(
        [
            _tx("b1", side=TransactionSide.BUY, quantity="1", gross="10"),
        ]
    )["inst_1"]
    assert buy_only.sell_gross_amount is None

    with pytest.raises(CurrencyMismatchError):
        calculate_transaction_totals(
            [
                _tx("b1", side=TransactionSide.BUY, quantity="1", gross="10", currency="EUR"),
                _tx("b2", side=TransactionSide.BUY, quantity="1", gross="10", currency="USD"),
            ]
        )

    with pytest.raises(CurrencyMismatchError):
        calculate_transaction_totals(
            [
                _tx("s1", side=TransactionSide.SELL, quantity="1", gross="10", currency="EUR"),
                _tx("s2", side=TransactionSide.SELL, quantity="1", gross="10", currency="USD"),
            ]
        )


def test_validate_no_oversells_cases() -> None:
    validate_no_oversells(
        [
            _tx(
                "b1",
                side=TransactionSide.BUY,
                quantity="2",
                gross="20",
                occurred_at=datetime(2026, 1, 1, 10, 0, 0),
            ),
            _tx(
                "s1",
                side=TransactionSide.SELL,
                quantity="1",
                gross="10",
                occurred_at=datetime(2026, 1, 1, 11, 0, 0),
            ),
        ]
    )

    with pytest.raises(InvalidAccountingInputError):
        validate_no_oversells(
            [
                _tx(
                    "s1",
                    side=TransactionSide.SELL,
                    quantity="1",
                    gross="10",
                    occurred_at=datetime(2026, 1, 1, 10, 0, 0),
                ),
                _tx(
                    "b1",
                    side=TransactionSide.BUY,
                    quantity="2",
                    gross="20",
                    occurred_at=datetime(2026, 1, 1, 11, 0, 0),
                ),
            ]
        )

    with pytest.raises(InvalidAccountingInputError):
        validate_no_oversells(
            [
                _tx("s1", side=TransactionSide.SELL, quantity="1", gross="10"),
                _tx("b1", side=TransactionSide.BUY, quantity="1", gross="10"),
            ]
        )

    validate_no_oversells(
        [
            _tx(
                "s1",
                side=TransactionSide.SELL,
                quantity="1",
                gross="10",
                status=TransactionStatus.PENDING,
            ),
        ]
    )


def test_build_paper_portfolio_snapshot_cases() -> None:
    snap = build_paper_portfolio_snapshot(
        portfolio_id="pf_1",
        cash_entries=[_entry("e1", "100")],
        transactions=[_tx("b1", side=TransactionSide.BUY, quantity="2", gross="20")],
    )
    assert snap.portfolio_id == "pf_1"
    assert "EUR" in snap.cash_balances
    assert "inst_1" in snap.positions
    assert snap.positions["inst_1"].instrument_id == "inst_1"
    assert isinstance(asdict(snap), dict)

    with pytest.raises(InvalidAccountingInputError):
        build_paper_portfolio_snapshot(
            portfolio_id="pf_1",
            cash_entries=[_entry("e1", "100").model_copy(update={"portfolio_id": "pf_2"})],
            transactions=[],
        )

    with pytest.raises(InvalidAccountingInputError):
        build_paper_portfolio_snapshot(
            portfolio_id="pf_1",
            cash_entries=[],
            transactions=[
                _tx("b1", side=TransactionSide.BUY, quantity="2", gross="20", portfolio_id="pf_2")
            ],
        )
