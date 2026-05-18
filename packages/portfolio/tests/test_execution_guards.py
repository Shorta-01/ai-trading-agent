import pytest
from portfolio_outlook_domain import (
    ApprovalRequirement,
    ExecutionMode,
    ExecutionModeSettings,
)

from portfolio_outlook_portfolio import (
    check_can_submit_order_to_target,
    check_execution_mode_available,
    get_default_execution_targets,
    require_execution_mode_available,
    require_manual_approval_required,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def test_execution_guards() -> None:
    targets = get_default_execution_targets()
    assert set(targets.keys()) == set(ExecutionMode)

    settings = ExecutionModeSettings()
    assert check_execution_mode_available(ExecutionMode.INTERNAL_PAPER, settings)
    assert not check_execution_mode_available(ExecutionMode.IBKR_PAPER, settings)
    assert check_execution_mode_available(
        ExecutionMode.IBKR_PAPER,
        settings.model_copy(update={"allow_ibkr_paper": True}),
    )
    assert not check_execution_mode_available(ExecutionMode.BLOCKED_AUTO, settings)

    assert not check_can_submit_order_to_target(targets[ExecutionMode.IBKR_LIVE_READ_ONLY])
    assert check_can_submit_order_to_target(targets[ExecutionMode.IBKR_PAPER])

    with pytest.raises(InvalidAccountingInputError):
        require_execution_mode_available(ExecutionMode.BLOCKED_AUTO, settings)

    bad_target = targets[ExecutionMode.IBKR_PAPER].model_copy(
        update={"approval_requirement": ApprovalRequirement.NOT_APPLICABLE}
    )
    with pytest.raises(InvalidAccountingInputError):
        require_manual_approval_required(bad_target)
