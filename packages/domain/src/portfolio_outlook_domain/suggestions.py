from datetime import datetime

from pydantic import field_validator, model_validator

from .enums import AdviceAction, DataQualityStatus, RiskLevel, SuggestionStatus
from .identifiers import InstrumentId, PortfolioId, SuggestionId
from .primitives import DomainBaseModel, Money, Percentage, Quantity


class ActionSuggestion(DomainBaseModel):
    suggestion_id: SuggestionId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    action: AdviceAction
    status: SuggestionStatus
    suggested_amount: Money | None = None
    suggested_quantity: Quantity | None = None
    target_price: Money | None = None
    reason_nl: str
    risk_level: RiskLevel
    confidence: Percentage | None = None
    data_quality_status: DataQualityStatus
    created_at: datetime
    expires_at: datetime | None = None

    @field_validator("reason_nl")
    @classmethod
    def validate_reason_nl(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl is required")
        return value

    @model_validator(mode="after")
    def validate_blocked_pairing(self) -> "ActionSuggestion":
        if self.action == AdviceAction.BLOCKED and self.status not in {
            SuggestionStatus.BLOCKED_BY_RISK,
            SuggestionStatus.BLOCKED_BY_DATA_QUALITY,
        }:
            raise ValueError("Blocked action requires a blocked status.")
        return self
