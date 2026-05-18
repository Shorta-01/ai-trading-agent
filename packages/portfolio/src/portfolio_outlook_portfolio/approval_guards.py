from datetime import datetime, timezone

from portfolio_outlook_domain import ApprovalDecision, ApprovalDecisionStatus, ApprovalRequest, ApprovedAction, ExecutionMode

from .errors import InvalidAccountingInputError


def is_approval_decision_final(decision: ApprovalDecision) -> bool:
    return decision.decision in {
        ApprovalDecisionStatus.APPROVED,
        ApprovalDecisionStatus.REJECTED,
        ApprovalDecisionStatus.CANCELLED,
        ApprovalDecisionStatus.EXPIRED,
        ApprovalDecisionStatus.BLOCKED,
    }


def require_approved_decision(*, request: ApprovalRequest, decision: ApprovalDecision) -> None:
    if decision.approval_request_id != request.approval_request_id:
        raise InvalidAccountingInputError("Approval request mismatch")
    if decision.decision != ApprovalDecisionStatus.APPROVED:
        raise InvalidAccountingInputError("Approval decision must be approved")
    if request.target_execution_mode == ExecutionMode.BLOCKED_AUTO:
        raise InvalidAccountingInputError("blocked_auto is never approvable")


def build_approved_action(*, request: ApprovalRequest, decision: ApprovalDecision) -> ApprovedAction:
    require_approved_decision(request=request, decision=decision)
    if request.status not in {ApprovalDecisionStatus.PENDING, ApprovalDecisionStatus.APPROVED}:
        raise InvalidAccountingInputError("Approval request status must be pending or approved")
    return ApprovedAction(
        approval_request_id=request.approval_request_id,
        approval_decision_id=decision.approval_decision_id,
        execution_intent_id=request.execution_intent_id,
        portfolio_id=request.portfolio_id,
        instrument_id=request.instrument_id,
        action=request.action,
        target_execution_mode=request.target_execution_mode,
        approved_at=decision.decided_at or datetime.now(timezone.utc),
    )
