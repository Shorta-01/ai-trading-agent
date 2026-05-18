from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import FifoLotAllocation, LotStatus, Money, PaperLot, Quantity


def _lot(**kwargs: object) -> PaperLot:
    base = dict(
        lot_id="lot_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        buy_transaction_id="tx_buy_1",
        buy_date=date(2026, 1, 1),
        original_quantity=Quantity(value=Decimal("10")),
        remaining_quantity=Quantity(value=Decimal("10")),
        buy_price=Money(amount=Decimal("50"), currency="EUR"),
        buy_currency="EUR",
        fees_allocated=Money(amount=Decimal("2"), currency="EUR"),
        cost_basis=Money(amount=Decimal("502"), currency="EUR"),
        status=LotStatus.OPEN,
    )
    base.update(kwargs)
    return PaperLot(**base)


def test_open_lot_accepted() -> None:
    model = _lot()
    assert model.status == LotStatus.OPEN


def test_partially_closed_lot_accepted() -> None:
    model = _lot(remaining_quantity=Quantity(value=Decimal("4")), status=LotStatus.PARTIALLY_CLOSED)
    assert model.status == LotStatus.PARTIALLY_CLOSED


def test_closed_lot_accepted() -> None:
    model = _lot(remaining_quantity=Quantity(value=Decimal("0")), status=LotStatus.CLOSED)
    assert model.status == LotStatus.CLOSED


def test_remaining_quantity_greater_than_original_rejected() -> None:
    with pytest.raises(ValidationError):
        _lot(remaining_quantity=Quantity(value=Decimal("11")))


def test_incoherent_lot_status_rejected() -> None:
    with pytest.raises(ValidationError):
        _lot(remaining_quantity=Quantity(value=Decimal("0")), status=LotStatus.OPEN)


def test_currency_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        _lot(cost_basis=Money(amount=Decimal("500"), currency="USD"))


def test_fifo_allocation_accepts_valid_data() -> None:
    allocation = FifoLotAllocation(
        fifo_allocation_id="fifo_1",
        sell_transaction_id="tx_sell_1",
        lot_id="lot_1",
        allocated_quantity=Quantity(value=Decimal("2")),
        allocated_cost_basis=Money(amount=Decimal("100"), currency="EUR"),
        allocated_at=datetime(2026, 1, 2, 10, 0, 0),
    )
    assert allocation.allocated_quantity.value == Decimal("2")


def test_fifo_allocation_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        FifoLotAllocation(
            fifo_allocation_id="fifo_1",
            sell_transaction_id="tx_sell_1",
            lot_id="lot_1",
            allocated_quantity=Quantity(value=Decimal("0")),
            allocated_cost_basis=Money(amount=Decimal("100"), currency="EUR"),
            allocated_at=datetime(2026, 1, 2, 10, 0, 0),
        )


def test_lot_model_dump_contains_decimal() -> None:
    dumped = _lot().model_dump()
    assert dumped["cost_basis"]["amount"] == Decimal("502")
