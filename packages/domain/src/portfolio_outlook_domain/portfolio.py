from datetime import datetime

from pydantic import model_validator

from .enums import AdviceAction, PaperLiveMode, RiskLevel
from .identifiers import InstrumentId, PortfolioId
from .primitives import CurrencyCode, DomainBaseModel, Money, Quantity


class PortfolioSummary(DomainBaseModel):
    portfolio_id: PortfolioId
    name: str
    base_currency: CurrencyCode
    mode: PaperLiveMode = PaperLiveMode.PAPER
    starting_capital: Money
    cash_available: Money | None = None
    invested_value: Money | None = None
    current_value: Money | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_mode(self) -> "PortfolioSummary":
        if self.mode is not PaperLiveMode.PAPER:
            raise ValueError("Version 1 is paper-only. PortfolioSummary.mode must be 'paper'.")
        return self


class PositionSnapshot(DomainBaseModel):
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    quantity: Quantity
    average_buy_price: Money | None = None
    current_price: Money | None = None
    current_value: Money | None = None
    unrealized_gain_loss: Money | None = None
    realized_gain_loss: Money | None = None
    risk_level: RiskLevel | None = None
    advice_action: AdviceAction | None = None
    as_of: datetime
