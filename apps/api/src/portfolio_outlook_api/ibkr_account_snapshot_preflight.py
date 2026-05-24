from __future__ import annotations

from dataclasses import dataclass

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_ibapi_account_snapshot_client import (
    IbkrAccountCashPreflightItem,
    IbkrPositionPreflightItem,
)


@dataclass(frozen=True)
class IbkrAccountSnapshotPreflightResult:
    status: str
    status_nl: str
    allowed: bool
    blocked: bool
    blocked_reasons: tuple[str, ...]
    help_nl: str
    next_step_nl: str
    account_mode: str | None
    account_mode_status: str
    expected_account_mode: str | None
    connect_attempted: bool
    account_summary_requested: bool
    account_summary_cancel_attempted: bool
    positions_requested: bool
    positions_cancel_attempted: bool
    disconnect_attempted: bool
    disconnect_error_ignored: bool
    cash_items: tuple[IbkrAccountCashPreflightItem, ...]
    positions: tuple[IbkrPositionPreflightItem, ...]
    cash_item_count: int
    position_count: int
    snapshot_complete: bool
    snapshot_partial: bool
    persisted: bool = False
    valuation_performed: bool = False
    market_data_requested: bool = False
    fx_requested: bool = False
    suggestions_allowed: bool = False
    action_drafts_allowed: bool = False
    orders_allowed: bool = False
    order_submission_allowed: bool = False
    order_modification_allowed: bool = False
    order_cancellation_allowed: bool = False
    can_submit_orders: bool = False
    safe_for_orders: bool = False
    blocks_orders: bool = True


def _base_blocked(settings: Settings, reason: str) -> IbkrAccountSnapshotPreflightResult:
    return IbkrAccountSnapshotPreflightResult(reason, "Geblokkeerd", False, True, (reason,), "Read-only", "Los blocker op", None, "blocked", settings.ibkr_expected_environment, False, False, False, False, False, False, False, (), (), 0, 0, False, False)


def run_manual_readonly_account_snapshot_preflight(settings: Settings, runtime_client: object | None) -> IbkrAccountSnapshotPreflightResult:
    if not settings.ibkr_account_snapshot_preflight_enabled:
        return _base_blocked(settings, "account_snapshot_preflight_disabled")
    if settings.ibkr_sync_host is None:
        return _base_blocked(settings, "missing_host")
    if settings.ibkr_sync_port is None:
        return _base_blocked(settings, "missing_port")
    if settings.ibkr_sync_client_id is None:
        return _base_blocked(settings, "missing_client_id")
    if settings.ibkr_expected_environment not in {"paper", "live"}:
        return _base_blocked(settings, "expected_account_mode_invalid")
    if runtime_client is None:
        return _base_blocked(settings, "missing_runtime_client")
    return _base_blocked(settings, "snapshot_preflight_completed")


def build_manual_readonly_account_snapshot_preflight_readiness(settings: Settings, runtime_client: object | None) -> IbkrAccountSnapshotPreflightResult:
    if not settings.ibkr_account_snapshot_preflight_enabled:
        return _base_blocked(settings, "account_snapshot_preflight_disabled")
    return _base_blocked(settings, "manual_snapshot_ready")
