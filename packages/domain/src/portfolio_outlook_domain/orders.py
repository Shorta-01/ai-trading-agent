from datetime import datetime
from decimal import Decimal

from pydantic import field_validator, model_validator

from .costs import CostEstimate
from .enums import OrderStatus, OrderType, PaperLiveMode, TransactionSide
from .identifiers import FillId, InstrumentId, OrderId, PortfolioId, SuggestionId, TransactionId
from .primitives import DomainBaseModel, Money, Quantity


class PaperOrder(DomainBaseModel):
    order_id: OrderId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    side: TransactionSide
    order_type: OrderType
    status: OrderStatus
    requested_quantity: Quantity | None = None
    requested_amount: Money | None = None
    limit_price: Money | None = None
    suggested_by: SuggestionId | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    expires_at: datetime | None = None
    reason_nl: str
    mode: PaperLiveMode = PaperLiveMode.PAPER

    @field_validator("reason_nl")
    @classmethod
    def validate_reason_nl(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl is required")
        return value

    @model_validator(mode="after")
    def validate_order(self) -> "PaperOrder":
        if self.mode is not PaperLiveMode.PAPER:
            raise ValueError("Version 1 is paper-only. PaperOrder.mode must be 'paper'.")

        has_quantity = self.requested_quantity is not None
        has_amount = self.requested_amount is not None
        if not has_quantity and not has_amount:
            raise ValueError("Either requested_quantity or requested_amount must be provided.")
        if has_quantity and has_amount:
            raise ValueError("Provide requested_quantity or requested_amount, not both.")

        if (
            has_quantity
            and self.requested_quantity is not None
            and self.requested_quantity.value <= Decimal("0")
        ):
            raise ValueError("requested_quantity must be greater than zero.")
        if (
            has_amount
            and self.requested_amount is not None
            and self.requested_amount.amount <= Decimal("0")
        ):
            raise ValueError("requested_amount must be greater than zero.")

        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit_price is required for limit orders.")

        return self


class ExecutionFill(DomainBaseModel):
    fill_id: FillId
    order_id: OrderId
    transaction_id: TransactionId | None = None
    filled_quantity: Quantity
    fill_price: Money
    gross_amount: Money
    costs: list[CostEstimate]
    filled_at: datetime
    status_after_fill: OrderStatus

    @model_validator(mode="after")
    def validate_fill(self) -> "ExecutionFill":
        if self.filled_quantity.value <= Decimal("0"):
            raise ValueError("filled_quantity must be greater than zero.")
        if self.fill_price.amount < Decimal("0"):
            raise ValueError("fill_price amount must be zero or positive.")
        if self.gross_amount.currency != self.fill_price.currency:
            raise ValueError("gross_amount currency must match fill_price currency.")
        if self.status_after_fill not in {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED}:
            raise ValueError("status_after_fill must be partially_filled or filled.")
        return self
