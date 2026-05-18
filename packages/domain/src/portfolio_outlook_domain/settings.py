from decimal import Decimal

from pydantic import model_validator

from .enums import PaperLiveMode
from .primitives import CurrencyCode, DomainBaseModel, Money, Percentage


class PortfolioSettings(DomainBaseModel):
    starting_paper_capital: Money = Money(amount=Decimal("10000"), currency="EUR")
    base_currency: CurrencyCode = "EUR"
    paper_live_mode: PaperLiveMode = PaperLiveMode.PAPER
    risk_profile: str = "balanced"
    normal_minimum_cash_reserve: Percentage = Percentage(value=Decimal("20"))
    first_run_minimum_cash_reserve: Percentage = Percentage(value=Decimal("40"))
    first_run_maximum_invested: Percentage = Percentage(value=Decimal("60"))
    daily_deep_analysis_enabled: bool = True
    intraday_watcher_enabled: bool = True
    weekly_deep_discovery_enabled: bool = True
    monthly_performance_review_enabled: bool = True
    interface_language: str = "nl"
    simple_ui_enabled: bool = True

    @model_validator(mode="after")
    def validate_paper_mode_and_percentages(self) -> "PortfolioSettings":
        if self.paper_live_mode is not PaperLiveMode.PAPER:
            raise ValueError("Version 1 is paper-only. paper_live_mode must be 'paper'.")

        first_run_total = (
            self.first_run_minimum_cash_reserve.value + self.first_run_maximum_invested.value
        )
        if first_run_total > Decimal("100"):
            raise ValueError("First-run reserve and invested percentages cannot exceed 100%.")
        return self
