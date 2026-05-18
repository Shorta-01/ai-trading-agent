from portfolio_outlook_domain import (
    ApprovalRequirement,
    BrokerAccountMode,
    BrokerProvider,
    ExecutionMode,
    ExecutionModeSettings,
    ExecutionModeStatus,
    ExecutionTarget,
    ExecutionTargetKind,
)

from .errors import InvalidAccountingInputError


def get_default_execution_targets() -> dict[ExecutionMode, ExecutionTarget]:
    return {
        ExecutionMode.INTERNAL_PAPER: ExecutionTarget(execution_target_id="target_internal_paper", mode=ExecutionMode.INTERNAL_PAPER, kind=ExecutionTargetKind.INTERNAL_PAPER_SIMULATOR, provider=BrokerProvider.NONE, account_mode=BrokerAccountMode.INTERNAL_PAPER, status=ExecutionModeStatus.AVAILABLE, approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl="Interne paper simulator met verplichte goedkeuring."),
        ExecutionMode.IBKR_PAPER: ExecutionTarget(execution_target_id="target_ibkr_paper", mode=ExecutionMode.IBKR_PAPER, kind=ExecutionTargetKind.IBKR_PAPER_ACCOUNT, provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_PAPER, status=ExecutionModeStatus.REQUIRES_SETUP, approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED, can_submit_orders=True, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl="IBKR paperrekening als toekomstig doel met verplichte goedkeuring."),
        ExecutionMode.IBKR_LIVE_READ_ONLY: ExecutionTarget(execution_target_id="target_ibkr_live_read_only", mode=ExecutionMode.IBKR_LIVE_READ_ONLY, kind=ExecutionTargetKind.IBKR_LIVE_READ_ONLY, provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_LIVE, status=ExecutionModeStatus.REQUIRES_SETUP, approval_requirement=ApprovalRequirement.NOT_APPLICABLE, can_submit_orders=False, can_submit_real_money_orders=False, can_read_account_data=True, can_read_market_data=True, explanation_nl="Alleen lezen; geen orderplaatsing."),
        ExecutionMode.IBKR_LIVE_MANUAL: ExecutionTarget(execution_target_id="target_ibkr_live_manual", mode=ExecutionMode.IBKR_LIVE_MANUAL, kind=ExecutionTargetKind.IBKR_LIVE_MANUAL, provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_LIVE, status=ExecutionModeStatus.REQUIRES_EXPLICIT_ACTIVATION, approval_requirement=ApprovalRequirement.ALWAYS_REQUIRED, can_submit_orders=True, can_submit_real_money_orders=True, can_read_account_data=True, can_read_market_data=True, explanation_nl="Toekomstige handmatige live modus met expliciete activatie en verplichte goedkeuring."),
        ExecutionMode.BLOCKED_AUTO: ExecutionTarget(execution_target_id="target_blocked_auto", mode=ExecutionMode.BLOCKED_AUTO, kind=ExecutionTargetKind.BLOCKED_AUTOMATIC_EXECUTION, provider=BrokerProvider.NONE, account_mode=BrokerAccountMode.INTERNAL_PAPER, status=ExecutionModeStatus.BLOCKED, approval_requirement=ApprovalRequirement.BLOCKED, can_submit_orders=False, can_submit_real_money_orders=False, can_read_account_data=False, can_read_market_data=False, explanation_nl="Automatische uitvoering blijft geblokkeerd."),
    }


def check_execution_mode_available(mode: ExecutionMode, settings: ExecutionModeSettings) -> bool:
    if mode == ExecutionMode.BLOCKED_AUTO or not settings.approval_required_for_all_orders:
        return False
    return {
        ExecutionMode.INTERNAL_PAPER: settings.allow_internal_paper,
        ExecutionMode.IBKR_PAPER: settings.allow_ibkr_paper,
        ExecutionMode.IBKR_LIVE_READ_ONLY: settings.allow_ibkr_live_read_only,
        ExecutionMode.IBKR_LIVE_MANUAL: settings.allow_ibkr_live_manual,
    }.get(mode, False)


def require_execution_mode_available(mode: ExecutionMode, settings: ExecutionModeSettings) -> None:
    if not check_execution_mode_available(mode, settings):
        raise InvalidAccountingInputError(f"Execution mode not available: {mode}")


def check_can_submit_order_to_target(target: ExecutionTarget) -> bool:
    return target.can_submit_orders and target.approval_requirement == ApprovalRequirement.ALWAYS_REQUIRED


def require_manual_approval_required(target: ExecutionTarget) -> None:
    if target.can_submit_orders and target.approval_requirement != ApprovalRequirement.ALWAYS_REQUIRED:
        raise InvalidAccountingInputError("Manual approval is required for order-capable execution targets")
