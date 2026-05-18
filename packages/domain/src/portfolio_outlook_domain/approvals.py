from datetime import datetime

from pydantic import field_validator, model_validator

from .enums import AdviceAction, ApprovalDecisionStatus, ExecutionMode
from .identifiers import (
    ApprovalDecisionId,
    ApprovalRequestId,
    ExecutionIntentId,
    InstrumentId,
    PortfolioId,
    SuggestionId,
)
from .primitives import DomainBaseModel, Money, Quantity


class ApprovalRequest(DomainBaseModel):
    approval_request_id: ApprovalRequestId
    execution_intent_id: ExecutionIntentId
    portfolio_id: PortfolioId
    suggestion_id: SuggestionId | None = None
    instrument_id: InstrumentId
    action: AdviceAction
    requested_amount: Money | None = None
    requested_quantity: Quantity | None = None
    target_execution_mode: ExecutionMode
    status: ApprovalDecisionStatus = ApprovalDecisionStatus.PENDING
    explanation_nl: str
    created_at: datetime
    expires_at: datetime | None = None

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation_nl is required")
        return value

    @model_validator(mode="after")
    def validate_request(self) -> "ApprovalRequest":
        if self.target_execution_mode == ExecutionMode.BLOCKED_AUTO:
            raise ValueError("blocked_auto is not a valid approval target")
        if self.requested_amount is None and self.requested_quantity is None:
            raise ValueError("requested_amount or requested_quantity is required")
        return self


class ApprovalDecision(DomainBaseModel):
    approval_decision_id: ApprovalDecisionId
    approval_request_id: ApprovalRequestId
    decision: ApprovalDecisionStatus
    decided_at: datetime
    decided_by: str
    reason_nl: str | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> "ApprovalDecision":
        if self.decision == ApprovalDecisionStatus.PENDING:
            raise ValueError("ApprovalDecision cannot be pending")
        if not self.decided_by.strip():
            raise ValueError("decided_by is required")
        if self.decision in {
            ApprovalDecisionStatus.REJECTED,
            ApprovalDecisionStatus.BLOCKED,
        } and not (self.reason_nl and self.reason_nl.strip()):
            raise ValueError("reason_nl is required for rejected/blocked decisions")
        return self


class ApprovedAction(DomainBaseModel):
    approval_request_id: ApprovalRequestId
    approval_decision_id: ApprovalDecisionId
    execution_intent_id: ExecutionIntentId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    action: AdviceAction
    target_execution_mode: ExecutionMode
    approved_at: datetime

    @model_validator(mode="after")
    def validate_mode(self) -> "ApprovedAction":
        if self.target_execution_mode == ExecutionMode.BLOCKED_AUTO:
            raise ValueError("blocked_auto cannot be approved")
        return self
