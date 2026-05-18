from datetime import datetime, timezone
from decimal import Decimal
import pytest
from portfolio_outlook_domain import *
from portfolio_outlook_portfolio import *
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def _req(mode=ExecutionMode.INTERNAL_PAPER):
    return ApprovalRequest(approval_request_id='ar1', execution_intent_id='ei1', portfolio_id='p1', instrument_id='i1', action=AdviceAction.BUY, requested_amount=Money(amount=Decimal('1'), currency='EUR'), target_execution_mode=mode, explanation_nl='x', created_at=datetime.now(timezone.utc))

def test_approval_guards():
    req=_req(); dec=ApprovalDecision(approval_decision_id='ad1', approval_request_id='ar1', decision=ApprovalDecisionStatus.APPROVED, decided_at=datetime.now(timezone.utc), decided_by='u')
    act=build_approved_action(request=req, decision=dec); assert act.model_dump()['approval_request_id']=='ar1'
    rej=ApprovalDecision(approval_decision_id='ad2', approval_request_id='ar1', decision=ApprovalDecisionStatus.REJECTED, decided_at=datetime.now(timezone.utc), decided_by='u', reason_nl='no')
    with pytest.raises(InvalidAccountingInputError): build_approved_action(request=req, decision=rej)
    mis=ApprovalDecision(approval_decision_id='ad3', approval_request_id='other', decision=ApprovalDecisionStatus.APPROVED, decided_at=datetime.now(timezone.utc), decided_by='u')
    with pytest.raises(InvalidAccountingInputError): build_approved_action(request=req, decision=mis)
    with pytest.raises(InvalidAccountingInputError): build_approved_action(request=_req(ExecutionMode.BLOCKED_AUTO), decision=dec.model_copy(update={'approval_request_id':'ar1'}))
    require_approved_decision(request=req, decision=dec)
    with pytest.raises(InvalidAccountingInputError): require_approved_decision(request=req, decision=rej)
