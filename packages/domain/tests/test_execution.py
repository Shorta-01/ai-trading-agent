from datetime import datetime, timezone
from decimal import Decimal

import pytest
from portfolio_outlook_domain import *


def money(): return Money(amount=Decimal('10'), currency='EUR')
def qty(): return Quantity(value=Decimal('1'))

def test_targets_and_settings_and_intent():
    ExecutionTarget(execution_target_id='t1', mode=ExecutionMode.INTERNAL_PAPER, kind=ExecutionTargetKind.INTERNAL_PAPER_SIMULATOR, provider=BrokerProvider.NONE, account_mode=BrokerAccountMode.INTERNAL_PAPER, status=ExecutionModeStatus.AVAILABLE, approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl='ok')
    ExecutionTarget(execution_target_id='t2', mode=ExecutionMode.IBKR_PAPER, kind=ExecutionTargetKind.IBKR_PAPER_ACCOUNT, provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_PAPER, status=ExecutionModeStatus.REQUIRES_SETUP, approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl='ok')
    with pytest.raises(ValueError):
        ExecutionTarget(execution_target_id='t3', mode=ExecutionMode.IBKR_LIVE_READ_ONLY, kind=ExecutionTargetKind.IBKR_LIVE_READ_ONLY, provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_LIVE, status=ExecutionModeStatus.REQUIRES_SETUP, approval_requirement=ApprovalRequirement.NOT_APPLICABLE, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl='x')
    with pytest.raises(ValueError):
        ExecutionTarget(execution_target_id='t4', mode=ExecutionMode.BLOCKED_AUTO, kind=ExecutionTargetKind.BLOCKED_AUTOMATIC_EXECUTION, provider=BrokerProvider.NONE, account_mode=BrokerAccountMode.INTERNAL_PAPER, status=ExecutionModeStatus.BLOCKED, approval_requirement=ApprovalRequirement.BLOCKED, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=False, can_read_market_data=False, explanation_nl='x')
    s=ExecutionModeSettings(); assert s.default_execution_mode==ExecutionMode.INTERNAL_PAPER and s.approval_required_for_all_orders
    with pytest.raises(ValueError): ExecutionModeSettings(default_execution_mode=ExecutionMode.BLOCKED_AUTO)
    with pytest.raises(ValueError): ExecutionIntent(execution_intent_id='e1', suggestion_id=None, portfolio_id='p1', instrument_id='i1', action=AdviceAction.BUY, target_execution_mode=ExecutionMode.INTERNAL_PAPER, status=ExecutionIntentStatus.DRAFT, reason_nl='r', created_at=datetime.now(timezone.utc))
    with pytest.raises(ValueError): ExecutionIntent(execution_intent_id='e2', suggestion_id=None, portfolio_id='p1', instrument_id='i1', action=AdviceAction.BUY, requested_amount=money(), target_execution_mode=ExecutionMode.BLOCKED_AUTO, status=ExecutionIntentStatus.DRAFT, reason_nl='r', created_at=datetime.now(timezone.utc))
