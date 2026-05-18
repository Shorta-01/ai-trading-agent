from decimal import Decimal

from pydantic import Field, model_validator

from .enums import AssetType
from .primitives import DomainBaseModel, Percentage


class InvestmentPolicyStatement(DomainBaseModel):
    goal: str
    risk_profile: str
    time_horizon_years: int | None = Field(default=None, ge=1)
    maximum_drawdown_tolerance: Percentage | None = None
    allowed_asset_types: list[AssetType] = [
        AssetType.CASH,
        AssetType.FX,
        AssetType.UCITS_ETF,
        AssetType.STOCK,
        AssetType.BENCHMARK,
    ]
    blocked_asset_types: list[AssetType] = [AssetType.OTHER]
    minimum_cash_reserve: Percentage = Percentage(value=Decimal("20"))
    maximum_single_etf_allocation: Percentage = Percentage(value=Decimal("25"))
    maximum_single_stock_allocation: Percentage = Percentage(value=Decimal("10"))
    minimum_holding_period_days: int | None = Field(default=None, ge=0)
    allow_leverage: bool = False
    allow_short_selling: bool = False
    allow_options: bool = False
    allow_crypto: bool = False
    allow_penny_stocks: bool = False

    @model_validator(mode="after")
    def validate_allocations(self) -> "InvestmentPolicyStatement":
        if self.maximum_single_stock_allocation.value >= self.maximum_single_etf_allocation.value:
            raise ValueError("Stock allocation must be lower than ETF allocation.")
        return self
