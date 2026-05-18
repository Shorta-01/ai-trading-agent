from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class DomainBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Money(DomainBaseModel):
    amount: Decimal
    currency: CurrencyCode

    @field_validator("currency")
    @classmethod
    def validate_currency_supported(cls, value: str) -> str:
        supported = {"EUR", "USD", "GBP", "CHF", "JPY"}
        if value not in supported:
            raise ValueError(f"Unsupported currency code: {value}")
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_amount(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float amounts are not allowed. Use Decimal, int, or string.")
        return value

    @property
    def display(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


class Percentage(DomainBaseModel):
    value: Decimal

    @field_validator("value", mode="before")
    @classmethod
    def reject_float_value(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float percentages are not allowed.")
        return value

    @field_validator("value")
    @classmethod
    def validate_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Percentage must be finite.")
        return value


class Quantity(DomainBaseModel):
    value: Decimal = Field(ge=Decimal("0"))

    @field_validator("value", mode="before")
    @classmethod
    def reject_float_value(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float quantities are not allowed.")
        return value
