"""Quantitative research domain contracts (no runtime execution)."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from .primitives import DomainBaseModel
from .research_suggestions import SuggestionAction


class MarketDataProvider(StrEnum):
    IBKR = "ibkr"
    UNKNOWN = "unknown"


class HistoricalDataType(StrEnum):
    TRADES = "trades"
    UNKNOWN = "unknown"


class HistoricalBarSize(StrEnum):
    ONE_DAY = "one_day"
    UNKNOWN = "unknown"


class RegularTradingHoursMode(StrEnum):
    REGULAR_TRADING_HOURS_ONLY = "regular_trading_hours_only"
    UNKNOWN = "unknown"


class HistoricalDataRequestSpec(DomainBaseModel):
    request_id: str
    provider: MarketDataProvider
    asset_symbol: str
    currency: str
    data_type: HistoricalDataType
    bar_size: HistoricalBarSize
    regular_trading_hours_mode: RegularTradingHoursMode
    start_at: datetime | None = None
    end_at: datetime | None = None
    requested_at: datetime
    reason_nl: str

    @field_validator("request_id", "asset_symbol", "currency", "reason_nl")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> "HistoricalDataRequestSpec":
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class HistoricalMarketBar(DomainBaseModel):
    bar_id: str
    provider: MarketDataProvider
    asset_symbol: str
    currency: str
    bar_start_at: datetime
    bar_end_at: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    trade_count: int | None = None
    data_type: HistoricalDataType
    bar_size: HistoricalBarSize
    regular_trading_hours_mode: RegularTradingHoursMode
    received_at: datetime

    @field_validator("open_price", "high_price", "low_price", "close_price", mode="before")
    @classmethod
    def reject_float_price(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("float is not allowed")
        return value

    @field_validator("trade_count")
    @classmethod
    def validate_trade_count(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("trade_count must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_bar_order(self) -> "HistoricalMarketBar":
        if self.bar_end_at <= self.bar_start_at:
            raise ValueError("bar_end_at must be after bar_start_at")
        if self.high_price < self.low_price:
            raise ValueError("high_price must be >= low_price")
        return self


class ActionProbabilityEstimate(DomainBaseModel):
    action: SuggestionAction
    probability_score: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    reason_nl: str

    @field_validator("probability_score", mode="before")
    @classmethod
    def reject_float_probability(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("float is not allowed")
        return value


class QuantitativeResearchHelpText(DomainBaseModel):
    key: str
    label_nl: str
    help_nl: str


def get_quantitative_research_help_texts() -> tuple[QuantitativeResearchHelpText, ...]:
    return (
        QuantitativeResearchHelpText(
            key="forecast_range",
            label_nl="Verwachte bandbreedte",
            help_nl="Dit is een scenario, geen zekerheid.",
        ),
    )
