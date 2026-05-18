from datetime import date
from decimal import Decimal

import pytest
from portfolio_outlook_domain import LotStatus, Money, PaperLot, Quantity

from portfolio_outlook_portfolio import (
    InsufficientLotQuantityError,
    InvalidAccountingInputError,
    calculate_allocated_cost_basis,
    calculate_remaining_quantity,
    derive_lot_status,
    validate_lot_quantities,
)


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
        cost_basis=Money(amount=Decimal("500"), currency="EUR"),
        status=LotStatus.OPEN,
    )
    base.update(kwargs)
    return PaperLot(**base)


def test_calculate_remaining_quantity_works() -> None:
    remaining = calculate_remaining_quantity(
        Quantity(value=Decimal("10")), Quantity(value=Decimal("3"))
    )
    assert remaining == Quantity(value=Decimal("7"))


def test_over_allocation_raises() -> None:
    with pytest.raises(InsufficientLotQuantityError):
        calculate_remaining_quantity(Quantity(value=Decimal("10")), Quantity(value=Decimal("11")))


def test_derive_open_status() -> None:
    assert (
        derive_lot_status(Quantity(value=Decimal("10")), Quantity(value=Decimal("10")))
        == LotStatus.OPEN
    )


def test_derive_partially_closed_status() -> None:
    assert (
        derive_lot_status(Quantity(value=Decimal("10")), Quantity(value=Decimal("4")))
        == LotStatus.PARTIALLY_CLOSED
    )


def test_derive_closed_status() -> None:
    assert (
        derive_lot_status(Quantity(value=Decimal("10")), Quantity(value=Decimal("0")))
        == LotStatus.CLOSED
    )


def test_invalid_remaining_gt_original_raises() -> None:
    with pytest.raises(InvalidAccountingInputError):
        derive_lot_status(Quantity(value=Decimal("10")), Quantity(value=Decimal("11")))


def test_validate_lot_quantities_passes() -> None:
    validate_lot_quantities(_lot())


def test_validate_lot_quantities_incoherent_raises() -> None:
    lot = _lot(remaining_quantity=Quantity(value=Decimal("4")), status=LotStatus.PARTIALLY_CLOSED)
    wrong = lot.model_copy(update={"status": LotStatus.OPEN})
    with pytest.raises(InvalidAccountingInputError):
        validate_lot_quantities(wrong)


def test_allocated_cost_basis_partial_lot() -> None:
    lot = _lot(remaining_quantity=Quantity(value=Decimal("6")), status=LotStatus.PARTIALLY_CLOSED)
    allocated = calculate_allocated_cost_basis(lot, Quantity(value=Decimal("2")))
    assert allocated == Money(amount=Decimal("100"), currency="EUR")


def test_allocated_cost_basis_rejects_zero_allocation() -> None:
    with pytest.raises(InvalidAccountingInputError):
        calculate_allocated_cost_basis(_lot(), Quantity(value=Decimal("0")))


def test_allocated_cost_basis_rejects_allocation_gt_remaining() -> None:
    lot = _lot(remaining_quantity=Quantity(value=Decimal("3")), status=LotStatus.PARTIALLY_CLOSED)
    with pytest.raises(InsufficientLotQuantityError):
        calculate_allocated_cost_basis(lot, Quantity(value=Decimal("4")))
