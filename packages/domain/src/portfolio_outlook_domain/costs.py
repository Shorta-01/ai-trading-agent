from decimal import Decimal

from pydantic import field_validator

from .enums import CostType
from .identifiers import CostEstimateId
from .primitives import DomainBaseModel, Money


class CostEstimate(DomainBaseModel):
    cost_estimate_id: CostEstimateId
    cost_type: CostType
    amount: Money
    description_nl: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_non_negative_amount(cls, value: Money) -> Money:
        if value.amount < Decimal("0"):
            raise ValueError("Cost estimate amount must be zero or positive.")
        return value


class TotalCostEstimate(DomainBaseModel):
    costs: list[CostEstimate]

    def total_by_currency(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for cost in self.costs:
            currency = cost.amount.currency
            totals[currency] = totals.get(currency, Decimal("0")) + cost.amount.amount
        return totals
