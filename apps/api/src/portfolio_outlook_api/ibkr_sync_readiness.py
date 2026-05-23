from __future__ import annotations

from portfolio_outlook_api.config import Settings

_READY_SESSION = {"connected_readonly"}
_BLOCKED_SESSION = {
    "connected_wrong_account_mode",
    "connection_failed",
    "authentication_required",
    "pacing_limited",
    "unknown",
}
_CONTROL_SESSION = {
    "status_check_disabled",
    "configured_not_connected",
    "not_configured",
    "disabled",
}


def build_ibkr_sync_readiness(
    settings: Settings,
    ibkr_status: dict[str, object],
) -> dict[str, object]:
    sync_mode = settings.ibkr_sync_account_mode.strip().lower()
    expected_environment = settings.ibkr_expected_environment.strip().lower()
    session_status = str(ibkr_status.get("connection_status") or "unknown")
    account_mode_status = str(ibkr_status.get("account_mode_status") or "unknown")

    base = {
        "status": "blocked",
        "reason_code": "unknown",
        "status_nl": "Geblokkeerd",
        "message_nl": "Handmatige IBKR read-only sync is nu geblokkeerd.",
        "next_step_nl": "Controleer de readiness-voorwaarden en probeer daarna opnieuw.",
        "help_nl": "Geen orders, geen brokeracties en geen automatische uitvoering.",
        "manual_sync_allowed": False,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }

    if not settings.ibkr_sync_enabled:
        base["reason_code"] = "sync_disabled"
        return base
    if not settings.ibkr_sync_readonly:
        base["reason_code"] = "sync_readonly_required"
        return base
    if (
        not settings.ibkr_sync_host
        or settings.ibkr_sync_port is None
        or settings.ibkr_sync_client_id is None
    ):
        base["reason_code"] = "missing_sync_settings"
        return base
    if sync_mode != "paper" or expected_environment != "paper":
        base["reason_code"] = "version1_paper_only"
        base["message_nl"] = "Version 1 ondersteunt alleen IBKR paper-account sync."
        base["next_step_nl"] = "Controleer de accountomgeving voordat je verdergaat."
        return base
    if session_status in _BLOCKED_SESSION:
        base["reason_code"] = f"session_{session_status}"
        return base
    if account_mode_status != "match":
        base["reason_code"] = "account_mode_not_match"
        return base
    if session_status in _CONTROL_SESSION:
        base["status"] = "needs_control"
        base["reason_code"] = f"session_{session_status}"
        base["status_nl"] = "Controle nodig"
        base["message_nl"] = "Voer eerst handmatige sessiecontrole uit voordat sync mag starten."
        return base
    if session_status in _READY_SESSION:
        base["status"] = "ready_for_manual_readonly_sync"
        base["reason_code"] = "ready"
        base["status_nl"] = "Klaar voor handmatige read-only sync"
        base["message_nl"] = "De sessie is read-only en paper geverifieerd."
        base["next_step_nl"] = "Start handmatig een read-only sync."
        base["manual_sync_allowed"] = True
        return base
    base["reason_code"] = "unsupported_session_status"
    return base
