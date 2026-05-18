from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain import (
    AdviceAction,
    ApprovalDecision,
    ApprovalDecisionStatus,
    ApprovalRequest,
    ApprovedAction,
    ExecutionMode,
    Money,
)


def test_approvals() -> None:
    req = ApprovalRequest(
        approval_request_id="ar1",
        execution_intent_id="ei1",
        portfolio_id="p1",
        instrument_id="i1",
        action=AdviceAction.BUY,
        requested_amount=Money(amount=Decimal("1"), currency="EUR"),
        target_execution_mode=ExecutionMode.INTERNAL_PAPER,
        explanation_nl="x",
        created_at=datetime.now(UTC),
    )
    assert req.model_dump()["approval_request_id"] == "ar1"


    with pytest.raises(ValueError):
        ApprovalRequest(
            approval_request_id="ar2",
            execution_intent_id="ei1",
            portfolio_id="p1",
            instrument_id="i1",
            action=AdviceAction.BUY,
            target_execution_mode=ExecutionMode.INTERNAL_PAPER,
            explanation_nl="x",
            created_at=datetime.now(UTC),
        )

    ApprovalDecision(
        approval_decision_id="ad1",
        approval_request_id="ar1",
        decision=ApprovalDecisionStatus.APPROVED,
        decided_at=datetime.now(UTC),
        decided_by="user",
    )

    with pytest.raises(ValueError):
        ApprovalDecision(
            approval_decision_id="ad2",
            approval_request_id="ar1",
            decision=ApprovalDecisionStatus.PENDING,
            decided_at=datetime.now(UTC),
            decided_by="user",
        )

    with pytest.raises(ValueError):
        ApprovalDecision(
            approval_decision_id="ad3",
            approval_request_id="ar1",
            decision=ApprovalDecisionStatus.REJECTED,
            decided_at=datetime.now(UTC),
            decided_by="user",
        )

    with pytest.raises(ValueError):
        ApprovedAction(
            approval_request_id="ar1",
            approval_decision_id="ad1",
            execution_intent_id="ei1",
            portfolio_id="p1",
            instrument_id="i1",
            action=AdviceAction.BUY,
            target_execution_mode=ExecutionMode.BLOCKED_AUTO,
            approved_at=datetime.now(UTC),
        )
