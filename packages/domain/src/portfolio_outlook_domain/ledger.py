from datetime import date, datetime
from decimal import Decimal

from pydantic import field_validator, model_validator

from .costs import CostEstimate
from .enums import LedgerEntryType, PaperLiveMode, TransactionSide, TransactionStatus
from .identifiers import (
    InstrumentId,
    LedgerEntryId,
    OrderId,
    PortfolioId,
    RunId,
    SuggestionId,
    TransactionId,
)
from .primitives import DomainBaseModel, Money, Quantity


class CashLedgerEntry(DomainBaseModel):
    ledger_entry_id: LedgerEntryId
    portfolio_id: PortfolioId
    entry_type: LedgerEntryType
    amount: Money
    occurred_at: datetime
    reason_nl: str
    related_instrument_id: InstrumentId | None = None
    related_transaction_id: TransactionId | None = None
    related_order_id: OrderId | None = None
    related_suggestion_id: SuggestionId | None = None
    source_run_id: RunId | None = None

    @field_validator("reason_nl")
    @classmethod
    def validate_reason_nl(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl is required")
        return value


class PaperTransaction(DomainBaseModel):
    transaction_id: TransactionId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    side: TransactionSide
    status: TransactionStatus
    quantity: Quantity
    price: Money
    gross_amount: Money
    net_amount: Money
    costs: list[CostEstimate]
    occurred_at: datetime
    settlement_date: date | None = None
    reason_nl: str
    related_order_id: OrderId | None = None
    related_suggestion_id: SuggestionId | None = None
    mode: PaperLiveMode = PaperLiveMode.PAPER

    @field_validator("reason_nl")
    @classmethod
    def validate_reason_nl(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl is required")
        return value

    @model_validator(mode="after")
    def validate_transaction(self) -> "PaperTransaction":
        if self.mode is not PaperLiveMode.PAPER:
            raise ValueError("Version 1 is paper-only. PaperTransaction.mode must be 'paper'.")

        if self.quantity.value <= Decimal("0"):
            raise ValueError("quantity must be greater than zero.")

        if self.price.amount < Decimal("0"):
            raise ValueError("price amount must be zero or positive.")

        price_currency = self.price.currency
        if self.gross_amount.currency != price_currency:
            raise ValueError("gross_amount currency must match price currency.")
        if self.net_amount.currency != price_currency:
            raise ValueError("net_amount currency must match price currency.")

        return self
