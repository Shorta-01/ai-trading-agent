from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain import (
    AdviceAction,
    ApprovalRequirement,
    BrokerAccountMode,
    BrokerProvider,
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionModeSettings,
    ExecutionModeStatus,
    ExecutionTarget,
    ExecutionTargetKind,
    Money,
)


def test_execution_models() -> None:
    ExecutionTarget(
        execution_target_id="t1",
        mode=ExecutionMode.INTERNAL_PAPER,
        kind=ExecutionTargetKind.INTERNAL_PAPER_SIMULATOR,
        provider=BrokerProvider.NONE,
        account_mode=BrokerAccountMode.INTERNAL_PAPER,
        status=ExecutionModeStatus.AVAILABLE,
        approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED,
        can_submit_orders=True,
        can_submit_real_money_orders=False,
        can_read_account_data=True,
        can_read_market_data=True,
        explanation_nl="ok",
    )

    with pytest.raises(ValueError):
        ExecutionTarget(
            execution_target_id="t2",
            mode=ExecutionMode.BLOCKED_AUTO,
            kind=ExecutionTargetKind.BLOCKED_AUTOMATIC_EXECUTION,
            provider=BrokerProvider.NONE,
            account_mode=BrokerAccountMode.INTERNAL_PAPER,
            status=ExecutionModeStatus.AVAILABLE,
            approval_requirement=ApprovalRequirement.BLOCKED,
            can_submit_orders=False,
            can_submit_real_money_orders=False,
            can_read_account_data=False,
            can_read_market_data=False,
            explanation_nl="x",
        )

    ExecutionIntent(
        execution_intent_id="ei1",
        suggestion_id=None,
        portfolio_id="p1",
        instrument_id="i1",
        action=AdviceAction.BUY,
        requested_amount=Money(amount=Decimal("1"), currency="EUR"),
        target_execution_mode=ExecutionMode.INTERNAL_PAPER,
        status=ExecutionIntentStatus.WAITING_FOR_APPROVAL,
        reason_nl="ok",
        created_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError):
        ExecutionIntent(
            execution_intent_id="ei2",
            suggestion_id=None,
            portfolio_id="p1",
            instrument_id="i1",
            action=AdviceAction.BUY,
            target_execution_mode=ExecutionMode.INTERNAL_PAPER,
            status=ExecutionIntentStatus.WAITING_FOR_APPROVAL,
            reason_nl="ok",
            created_at=datetime.now(UTC),
        )

    with pytest.raises(ValueError):
        ExecutionModeSettings(approval_required_for_all_orders=False)
