from decimal import Decimal

from portfolio_outlook_domain import LotStatus, Money, PaperLot, Quantity

from .errors import InsufficientLotQuantityError, InvalidAccountingInputError


def calculate_remaining_quantity(
    original_quantity: Quantity, allocated_quantity: Quantity
) -> Quantity:
    if allocated_quantity.value > original_quantity.value:
        raise InsufficientLotQuantityError("allocated_quantity cannot exceed original_quantity.")
    return Quantity(value=original_quantity.value - allocated_quantity.value)


def derive_lot_status(original_quantity: Quantity, remaining_quantity: Quantity) -> LotStatus:
    if remaining_quantity.value > original_quantity.value:
        raise InvalidAccountingInputError("remaining_quantity cannot exceed original_quantity.")
    if remaining_quantity.value == original_quantity.value:
        return LotStatus.OPEN
    if remaining_quantity.value == Decimal("0"):
        return LotStatus.CLOSED
    return LotStatus.PARTIALLY_CLOSED


def validate_lot_quantities(lot: PaperLot) -> None:
    if lot.remaining_quantity.value > lot.original_quantity.value:
        raise InvalidAccountingInputError("remaining_quantity cannot exceed original_quantity.")

    expected_status = derive_lot_status(lot.original_quantity, lot.remaining_quantity)
    if lot.status is not expected_status:
        raise InvalidAccountingInputError("lot.status does not match the derived lot status.")


def calculate_allocated_cost_basis(lot: PaperLot, allocated_quantity: Quantity) -> Money:
    if allocated_quantity.value <= Decimal("0"):
        raise InvalidAccountingInputError("allocated_quantity must be greater than zero.")
    if allocated_quantity.value > lot.remaining_quantity.value:
        raise InsufficientLotQuantityError(
            "allocated_quantity cannot exceed lot.remaining_quantity."
        )

    amount = (
        lot.cost_basis.amount * allocated_quantity.value / lot.original_quantity.value
    )
    return Money(amount=amount, currency=lot.cost_basis.currency)
