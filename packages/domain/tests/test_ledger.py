from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    CashLedgerEntry,
    CostEstimate,
    CostType,
    LedgerEntryType,
    Money,
    PaperLiveMode,
    PaperTransaction,
    Quantity,
    TransactionSide,
    TransactionStatus,
)


def _tx(**kwargs: object) -> PaperTransaction:
    base = dict(
        transaction_id="tx_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        side=TransactionSide.BUY,
        status=TransactionStatus.FILLED,
        quantity=Quantity(value=Decimal("2")),
        price=Money(amount=Decimal("10"), currency="EUR"),
        gross_amount=Money(amount=Decimal("20"), currency="EUR"),
        net_amount=Money(amount=Decimal("20"), currency="EUR"),
        costs=[],
        occurred_at=datetime(2026, 1, 1, 10, 0, 0),
        settlement_date=date(2026, 1, 3),
        reason_nl="Paperaankoop",
    )
    base.update(kwargs)
    return PaperTransaction(**base)


def test_valid_buy_transaction_accepted() -> None:
    model = _tx(side=TransactionSide.BUY)
    assert model.side == TransactionSide.BUY


def test_valid_sell_transaction_accepted() -> None:
    model = _tx(side=TransactionSide.SELL)
    assert model.side == TransactionSide.SELL


def test_non_paper_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        _tx(mode=PaperLiveMode.LIVE_READ_ONLY)


def test_zero_quantity_rejected() -> None:
    with pytest.raises(ValidationError):
        _tx(quantity=Quantity(value=Decimal("0")))


def test_empty_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _tx(reason_nl="  ")


def test_currency_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        _tx(gross_amount=Money(amount=Decimal("20"), currency="USD"))


def test_costs_accepted() -> None:
    model = _tx(
        costs=[
            CostEstimate(
                cost_estimate_id="cost_1",
                cost_type=CostType.BROKER_FEE,
                amount=Money(amount=Decimal("0.50"), currency="EUR"),
            )
        ]
    )
    assert len(model.costs) == 1


def test_no_floats_accepted_for_money_and_quantity() -> None:
    with pytest.raises(ValidationError):
        _tx(quantity=Quantity(value=1.0))


def test_cash_ledger_model_dump_and_decimal_preserved() -> None:
    entry = CashLedgerEntry(
        ledger_entry_id="led_1",
        portfolio_id="pf_1",
        entry_type=LedgerEntryType.DEPOSIT,
        amount=Money(amount=Decimal("100.10"), currency="EUR"),
        occurred_at=datetime(2026, 1, 1, 10, 0, 0),
        reason_nl="Startkapitaal",
    )
    dumped = entry.model_dump()
    assert dumped["amount"]["amount"] == Decimal("100.10")
