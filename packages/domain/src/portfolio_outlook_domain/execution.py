from datetime import datetime

from pydantic import field_validator, model_validator

from .enums import (
    AdviceAction,
    ApprovalRequirement,
    BrokerAccountMode,
    BrokerProvider,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionModeStatus,
    ExecutionTargetKind,
)
from .identifiers import ExecutionIntentId, ExecutionTargetId, InstrumentId, PortfolioId, SuggestionId
from .primitives import DomainBaseModel, Money, Quantity


class ExecutionTarget(DomainBaseModel):
    execution_target_id: ExecutionTargetId
    mode: ExecutionMode
    kind: ExecutionTargetKind
    provider: BrokerProvider
    account_mode: BrokerAccountMode
    status: ExecutionModeStatus
    approval_requirement: ApprovalRequirement
    can_submit_orders: bool
    can_submit_real_money_orders: bool
    can_read_account_data: bool
    can_read_market_data: bool
    explanation_nl: str

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation_nl is required")
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> "ExecutionTarget":
        if self.mode in {ExecutionMode.INTERNAL_PAPER, ExecutionMode.IBKR_PAPER, ExecutionMode.IBKR_LIVE_MANUAL} and self.approval_requirement != ApprovalRequirement.ALWAYS_REQUIRED:
            raise ValueError("approval_requirement must be always_required")
        if self.mode == ExecutionMode.BLOCKED_AUTO:
            if self.status != ExecutionModeStatus.BLOCKED or self.can_submit_orders or self.can_submit_real_money_orders:
                raise ValueError("blocked_auto mode must stay blocked and non-submittable")
        if self.mode == ExecutionMode.IBKR_LIVE_READ_ONLY and self.can_submit_orders:
            raise ValueError("ibkr_live_read_only cannot submit orders")
        if self.mode in {ExecutionMode.INTERNAL_PAPER, ExecutionMode.IBKR_PAPER} and self.can_submit_real_money_orders:
            raise ValueError("paper execution modes cannot submit real-money orders")
        if self.mode == ExecutionMode.IBKR_LIVE_MANUAL and self.can_submit_real_money_orders and self.status == ExecutionModeStatus.AVAILABLE:
            raise ValueError("ibkr_live_manual real-money capability cannot be available by default")
        return self


class ExecutionIntent(DomainBaseModel):
    execution_intent_id: ExecutionIntentId
    suggestion_id: SuggestionId | None
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    action: AdviceAction
    requested_amount: Money | None = None
    requested_quantity: Quantity | None = None
    target_execution_mode: ExecutionMode
    status: ExecutionIntentStatus
    reason_nl: str
    created_at: datetime

    @field_validator("reason_nl")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_nl is required")
        return value

    @model_validator(mode="after")
    def validate_intent(self) -> "ExecutionIntent":
        if self.requested_amount is None and self.requested_quantity is None:
            raise ValueError("requested_amount or requested_quantity is required")
        if self.target_execution_mode == ExecutionMode.BLOCKED_AUTO:
            raise ValueError("blocked_auto is not a valid execution target")
        return self


class ExecutionModeSettings(DomainBaseModel):
    default_execution_mode: ExecutionMode = ExecutionMode.INTERNAL_PAPER
    allow_internal_paper: bool = True
    allow_ibkr_paper: bool = False
    allow_ibkr_live_read_only: bool = False
    allow_ibkr_live_manual: bool = False
    allow_blocked_auto: bool = False
    approval_required_for_all_orders: bool = True

    @model_validator(mode="after")
    def validate_settings(self) -> "ExecutionModeSettings":
        if not self.approval_required_for_all_orders:
            raise ValueError("approval_required_for_all_orders must be true")
        if self.allow_blocked_auto:
            raise ValueError("allow_blocked_auto must be false")
        if self.default_execution_mode == ExecutionMode.BLOCKED_AUTO:
            raise ValueError("default_execution_mode cannot be blocked_auto")
        if self.default_execution_mode == ExecutionMode.IBKR_PAPER and not self.allow_ibkr_paper:
            raise ValueError("ibkr_paper default requires allow_ibkr_paper")
        if self.default_execution_mode == ExecutionMode.IBKR_LIVE_READ_ONLY and not self.allow_ibkr_live_read_only:
            raise ValueError("ibkr_live_read_only default requires allow_ibkr_live_read_only")
        if self.default_execution_mode == ExecutionMode.IBKR_LIVE_MANUAL and not self.allow_ibkr_live_manual:
            raise ValueError("ibkr_live_manual default requires allow_ibkr_live_manual")
        return self
