from datetime import date, datetime
from decimal import Decimal

from pydantic import model_validator

from .enums import LotStatus
from .identifiers import FifoAllocationId, InstrumentId, LotId, PortfolioId, TransactionId
from .primitives import CurrencyCode, DomainBaseModel, Money, Quantity


class PaperLot(DomainBaseModel):
    lot_id: LotId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    buy_transaction_id: TransactionId
    buy_date: date
    original_quantity: Quantity
    remaining_quantity: Quantity
    buy_price: Money
    buy_currency: CurrencyCode
    fees_allocated: Money | None = None
    cost_basis: Money
    status: LotStatus

    @model_validator(mode="after")
    def validate_lot(self) -> "PaperLot":
        if self.original_quantity.value <= Decimal("0"):
            raise ValueError("original_quantity must be greater than zero.")
        if self.remaining_quantity.value < Decimal("0"):
            raise ValueError("remaining_quantity must be zero or positive.")
        if self.remaining_quantity.value > self.original_quantity.value:
            raise ValueError("remaining_quantity cannot exceed original_quantity.")

        if self.buy_currency != self.buy_price.currency:
            raise ValueError("buy_currency must match buy_price currency.")
        if self.cost_basis.currency != self.buy_price.currency:
            raise ValueError("cost_basis currency must match buy_price currency.")
        if (
            self.fees_allocated is not None
            and self.fees_allocated.currency != self.buy_price.currency
        ):
            raise ValueError("fees_allocated currency must match buy_price currency.")

        remaining = self.remaining_quantity.value
        original = self.original_quantity.value
        if remaining == original and self.status is not LotStatus.OPEN:
            raise ValueError(
                "status must be open when remaining_quantity equals original_quantity."
            )
        if (
            Decimal("0") < remaining < original
            and self.status is not LotStatus.PARTIALLY_CLOSED
        ):
            raise ValueError("status must be partially_closed when lot is partially consumed.")
        if remaining == Decimal("0") and self.status is not LotStatus.CLOSED:
            raise ValueError("status must be closed when remaining_quantity is zero.")
        return self


class FifoLotAllocation(DomainBaseModel):
    fifo_allocation_id: FifoAllocationId
    sell_transaction_id: TransactionId
    lot_id: LotId
    allocated_quantity: Quantity
    allocated_cost_basis: Money
    allocated_at: datetime

    @model_validator(mode="after")
    def validate_allocation(self) -> "FifoLotAllocation":
        if self.allocated_quantity.value <= Decimal("0"):
            raise ValueError("allocated_quantity must be greater than zero.")
        return self
