from __future__ import annotations

from portfolio_outlook_api.config import Settings


def build_ibkr_sync_readiness(
    settings: Settings, session_status: dict[str, object]
) -> dict[str, object]:
    connection_status = str(session_status.get("connection_status", "unknown"))
    account_mode_status = str(session_status.get("account_mode_status", "unknown"))
    session_attempted = bool(session_status.get("session_check_attempted", False))
    session_checks_enabled = bool(session_status.get("status_check_enabled", False))

    settings_ready = bool(
        settings.ibkr_sync_enabled
        and settings.ibkr_sync_host
        and settings.ibkr_sync_port is not None
        and settings.ibkr_sync_client_id is not None
    )
    readonly_configured = bool(settings.ibkr_sync_readonly)
    storage_ready = True
    session_ready = connection_status == "connected_readonly" and account_mode_status == "match"

    status = "needs_control"
    status_nl = "Controle nodig"
    reason = "unverified_session_status"
    help_nl = "Controleer eerst handmatig of de read-only paper-sessie expliciet is bevestigd."

    if not settings.ibkr_sync_enabled:
        status = "blocked"
        status_nl = "Geblokkeerd"
        reason = "sync_disabled"
        help_nl = "IBKR read-only sync staat uit."
    elif not settings_ready:
        status = "blocked"
        status_nl = "Geblokkeerd"
        reason = "missing_sync_config"
        help_nl = "Vul host, poort en client-id in voor handmatige read-only sync."
    elif not readonly_configured:
        status = "blocked"
        status_nl = "Geblokkeerd"
        reason = "readonly_required"
        help_nl = "Schakel read-only in; brokeracties blijven geblokkeerd."
    # V1 §21.1 relock + V1.2 §BZ: account-mode is reported, not gated.
    # ``connected_account_mode_mismatch`` (en de legacy variant
    # ``connected_wrong_account_mode``) zit bewust NIET in de blocking
    # set — een mode-mismatch blokkeert de sync niet meer; de #665
    # mismatch detector schrijft een operator-zichtbare SystemEvent
    # voor die situatie.
    elif connection_status in {
        "connection_failed",
        "authentication_required",
        "pacing_limited",
        "unknown",
    }:
        status = "blocked"
        status_nl = "Geblokkeerd"
        reason = f"session_{connection_status}"
        help_nl = "Sessiecontrole blokkeert handmatige read-only sync."
    elif connection_status == "status_check_disabled" or not session_checks_enabled:
        status = "needs_control"
        status_nl = "Controle nodig"
        reason = "status_check_disabled"
        help_nl = "Zonder sessiecontrole kan read-only paper-veiligheid niet worden bevestigd."
    elif not session_attempted:
        status = "needs_control"
        status_nl = "Controle nodig"
        reason = "session_not_attempted"
    elif session_ready and settings_ready and readonly_configured and storage_ready:
        status = "ready_for_manual_readonly_sync"
        status_nl = "Klaar voor handmatige read-only sync"
        reason = "ready"
        help_nl = (
            "Read-only paper-sessie is bevestigd; "
            "alleen handmatige read-only sync is toegestaan."
        )

    manual_sync_allowed = status == "ready_for_manual_readonly_sync"
    return {
        "sync_readiness_status": status,
        "sync_readiness_status_nl": status_nl,
        "sync_readiness_reason": reason,
        "sync_readiness_help_nl": help_nl,
        "manual_sync_allowed": manual_sync_allowed,
        "manual_sync_blocked": not manual_sync_allowed,
        "settings_ready_for_sync": settings_ready,
        "session_ready_for_sync": session_ready,
        "storage_ready_for_sync": storage_ready,
        "readonly_required": True,
        "readonly_configured": readonly_configured,
        "account_mode_status": account_mode_status,
        "connection_status": connection_status,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_orders": False,
        "blocks_orders": True,
        "safe_for_sync": False,
    }
