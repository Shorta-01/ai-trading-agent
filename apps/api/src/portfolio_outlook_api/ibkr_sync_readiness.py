from __future__ import annotations

from portfolio_outlook_api.config import Settings

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
_SUPPORTED_MODES = {"paper", "live"}


def build_ibkr_sync_readiness(
    settings: Settings,
    session_status: dict[str, object],
    *,
    storage_required: bool = True,
) -> dict[str, object]:
    missing_config = not bool(
        settings.ibkr_sync_host
        and settings.ibkr_sync_port is not None
        and settings.ibkr_sync_client_id is not None
    )
    mode = settings.ibkr_sync_account_mode.strip().lower()
    expected = settings.ibkr_expected_environment.strip().lower()
    mode_supported = mode in _SUPPORTED_MODES
    mode_match = mode_supported and expected in _SUPPORTED_MODES and mode == expected
    conn = str(session_status.get("connection_status") or "unknown").strip().lower()
    mode_status = str(session_status.get("account_mode_status") or "unknown").strip().lower()
    check_attempted = bool(session_status.get("session_check_attempted"))
    check_enabled = bool(session_status.get("status_check_enabled"))

    storage = settings.storage
    storage_ready = bool(storage.enabled and storage.database_url and storage.writes_enabled)
    storage_uncertain = storage.enabled and not storage.database_url

    settings_ready = (
        settings.ibkr_sync_enabled
        and not missing_config
        and settings.ibkr_sync_readonly
        and mode_supported
    )
    session_ready = (
        check_attempted
        and conn not in _BLOCKED_SESSION
        and conn not in _CONTROL_SESSION
    )

    status = "needs_control"
    reason = "session_unverified"
    help_nl = "Controleer IBKR-sessie en instellingen handmatig voordat je sync start."

    if not settings.ibkr_sync_enabled:
        status = "blocked"
        reason = "sync_disabled"
        help_nl = "IBKR-sync staat uit in de instellingen."
    elif missing_config:
        status = "blocked"
        reason = "missing_sync_config"
        help_nl = "Vul host, poort en client-id in voor handmatige read-only sync."
    elif not settings.ibkr_sync_readonly:
        status = "blocked"
        reason = "readonly_required"
        help_nl = "Alleen read-only sync is toegestaan in versie 1."
    elif not mode_supported:
        status = "blocked"
        reason = "unsupported_account_mode"
        help_nl = "Alleen paper of live accountmodus wordt ondersteund."
    elif not mode_match or mode_status == "mismatch" or conn == "connected_wrong_account_mode":
        status = "blocked"
        reason = "account_mode_mismatch"
        help_nl = "Accountmodus komt niet overeen met de verwachte omgeving."
    elif conn in _BLOCKED_SESSION:
        status = "blocked"
        reason = f"session_{conn}"
        help_nl = "IBKR-sessie is niet veilig voor handmatige read-only sync."
    elif not check_enabled or not check_attempted or conn in _CONTROL_SESSION:
        status = "needs_control"
        reason = "session_check_required"
        help_nl = "Sessiecontrole ontbreekt of is nog niet bevestigd."
    elif storage_required and not storage_ready:
        status = "needs_control" if storage_uncertain else "blocked"
        reason = "storage_not_ready"
        help_nl = "Duurzame opslag is niet klaar; controleer storage-instellingen."
    else:
        status = "ready_for_manual_readonly_sync"
        reason = "manual_preflight_ready"
        help_nl = "Lokale preflight is geslaagd voor handmatige read-only sync."

    status_nl = {
        "blocked": "Geblokkeerd",
        "needs_control": "Controle nodig",
        "ready_for_manual_readonly_sync": "Klaar voor handmatige read-only sync",
    }[status]
    manual_sync_allowed = status == "ready_for_manual_readonly_sync"
    return {
        "sync_readiness_status": status,
        "sync_readiness_status_nl": status_nl,
        "sync_readiness_reason": reason,
        "sync_readiness_help_nl": help_nl,
        "manual_sync_allowed": manual_sync_allowed,
        "manual_sync_blocked": not manual_sync_allowed,
        "storage_ready_for_sync": storage_ready,
        "session_ready_for_sync": session_ready,
        "settings_ready_for_sync": settings_ready,
        "readonly_required": True,
        "readonly_configured": settings.ibkr_sync_readonly,
        "account_mode_status": mode_status,
        "connection_status": conn,
        "sync_allowed": False,
        "safe_for_sync": False,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }
