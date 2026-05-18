from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from portfolio_outlook_domain import (
    AdviceAction,
    ApprovalDecision,
    ApprovalDecisionStatus,
    ApprovalRequest,
    ExecutionMode,
    Money,
)

from portfolio_outlook_portfolio import (
    build_approved_action,
    require_approved_decision,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def _req(mode: ExecutionMode = ExecutionMode.INTERNAL_PAPER) -> ApprovalRequest:
    return ApprovalRequest(
        approval_request_id="ar1",
        execution_intent_id="ei1",
        portfolio_id="p1",
        instrument_id="i1",
        action=AdviceAction.BUY,
        requested_amount=Money(amount=Decimal("1"), currency="EUR"),
        target_execution_mode=mode,
        explanation_nl="x",
        created_at=datetime.now(UTC),
    )


def test_approval_guards() -> None:
    req = _req()
    dec = ApprovalDecision(
        approval_decision_id="ad1",
        approval_request_id="ar1",
        decision=ApprovalDecisionStatus.APPROVED,
        decided_at=datetime.now(UTC),
        decided_by="u",
    )

    action = build_approved_action(request=req, decision=dec)
    assert action.model_dump()["approval_request_id"] == "ar1"

    rejected = ApprovalDecision(
        approval_decision_id="ad2",
        approval_request_id="ar1",
        decision=ApprovalDecisionStatus.REJECTED,
        decided_at=datetime.now(UTC),
        decided_by="u",
        reason_nl="no",
    )
    with pytest.raises(InvalidAccountingInputError):
        build_approved_action(request=req, decision=rejected)

    mismatched = ApprovalDecision(
        approval_decision_id="ad3",
        approval_request_id="other",
        decision=ApprovalDecisionStatus.APPROVED,
        decided_at=datetime.now(UTC),
        decided_by="u",
    )
    with pytest.raises(InvalidAccountingInputError):
        build_approved_action(request=req, decision=mismatched)

    with pytest.raises(ValidationError, match="blocked_auto"):
        _req(ExecutionMode.BLOCKED_AUTO)

    blocked_request = req.model_copy(
        update={"target_execution_mode": ExecutionMode.BLOCKED_AUTO}
    )
    with pytest.raises(InvalidAccountingInputError):
        build_approved_action(
            request=blocked_request,
            decision=dec.model_copy(update={"approval_request_id": "ar1"}),
        )

    require_approved_decision(request=req, decision=dec)

    with pytest.raises(InvalidAccountingInputError):
        require_approved_decision(request=req, decision=rejected)
