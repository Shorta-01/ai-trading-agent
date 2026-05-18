from datetime import date
from decimal import Decimal

from pydantic import field_validator, model_validator

from .enums import TermDepositInterestType, TermDepositStatus, TermDepositTerm
from .identifiers import PortfolioId, TermDepositId
from .primitives import DomainBaseModel, Money, Percentage


class TermDepositInput(DomainBaseModel):
    term_deposit_id: TermDepositId
    portfolio_id: PortfolioId
    bank_name: str
    name: str
    principal: Money
    start_date: date
    term: TermDepositTerm
    interest_type: TermDepositInterestType
    gross_interest_rate: Percentage | None = None
    gross_interest_amount: Money | None = None
    costs: Money
    estimated_taxes: Money
    status: TermDepositStatus

    @field_validator("bank_name", "name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value is required and cannot be empty.")
        return value

    @field_validator("principal")
    @classmethod
    def validate_positive_principal(cls, value: Money) -> Money:
        if value.amount <= Decimal("0"):
            raise ValueError("principal must be greater than zero.")
        return value

    @field_validator("costs", "estimated_taxes")
    @classmethod
    def validate_non_negative_cost_values(cls, value: Money) -> Money:
        if value.amount < Decimal("0"):
            raise ValueError("costs and estimated_taxes must be zero or positive.")
        return value

    @model_validator(mode="after")
    def validate_interest_and_currency_rules(self) -> "TermDepositInput":
        if self.costs.currency != self.principal.currency:
            raise ValueError("costs currency must match principal currency.")
        if self.estimated_taxes.currency != self.principal.currency:
            raise ValueError("estimated_taxes currency must match principal currency.")

        if self.interest_type is TermDepositInterestType.FIXED_RATE:
            if self.gross_interest_rate is None:
                raise ValueError("gross_interest_rate is required for fixed_rate interest type.")
            if self.gross_interest_amount is not None:
                raise ValueError("gross_interest_amount must be None for fixed_rate interest type.")
            if self.gross_interest_rate.value < Decimal("0"):
                raise ValueError("gross_interest_rate must be zero or positive.")

        if self.interest_type is TermDepositInterestType.FIXED_AMOUNT:
            if self.gross_interest_amount is None:
                raise ValueError(
                    "gross_interest_amount is required for fixed_amount interest type."
                )
            if self.gross_interest_rate is not None:
                raise ValueError("gross_interest_rate must be None for fixed_amount interest type.")
            if self.gross_interest_amount.currency != self.principal.currency:
                raise ValueError("gross_interest_amount currency must match principal currency.")
            if self.gross_interest_amount.amount < Decimal("0"):
                raise ValueError("gross_interest_amount must be zero or positive.")

        return self


class TermDepositProjection(DomainBaseModel):
    term_deposit_id: TermDepositId
    portfolio_id: PortfolioId
    bank_name: str
    name: str
    principal: Money
    start_date: date
    maturity_date: date
    term: TermDepositTerm
    gross_interest: Money
    costs: Money
    estimated_taxes: Money
    net_interest: Money
    expected_maturity_value: Money
    days_until_maturity: int
    status: TermDepositStatus

    @model_validator(mode="after")
    def validate_projection_rules(self) -> "TermDepositProjection":
        if self.maturity_date <= self.start_date:
            raise ValueError("maturity_date must be after start_date.")

        if self.days_until_maturity < 0:
            raise ValueError("days_until_maturity cannot be negative.")

        currencies = {
            self.principal.currency,
            self.gross_interest.currency,
            self.costs.currency,
            self.estimated_taxes.currency,
            self.net_interest.currency,
            self.expected_maturity_value.currency,
        }
        if len(currencies) != 1:
            raise ValueError("All Money values must use the same currency as principal.")

        return self
