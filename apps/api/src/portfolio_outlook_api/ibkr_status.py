from portfolio_outlook_domain.broker_adapter import BrokerProvider

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_adapter_factory import (
    IbkrSessionAdapterSelectionDiagnostics,
    build_ibkr_session_status_adapter,
)
from portfolio_outlook_api.ibkr_session_status import IbkrSessionStatusAdapter

_KNOWN_CONNECTION_STATUSES = {
    "configured_not_connected",
    "connected_readonly",
    "connected_wrong_account_mode",
    "connection_failed",
    "authentication_required",
    "pacing_limited",
}
_KNOWN_ACCOUNT_MODE_STATUSES = {"unknown", "unverified", "match", "mismatch"}
_KNOWN_ACCOUNT_MODES = {"paper", "live"}


def _normalize_connection_status(raw_status: str | None) -> str:
    status = (raw_status or "").strip().lower()
    if status in _KNOWN_CONNECTION_STATUSES:
        return status
    return "unknown"


def _normalize_account_mode_status(raw_status: str | None) -> str:
    status = (raw_status or "").strip().lower()
    if status in _KNOWN_ACCOUNT_MODE_STATUSES:
        return status
    return "unknown"


def _normalize_account_mode(raw_mode: str | None) -> str | None:
    if raw_mode is None:
        return None
    normalized = raw_mode.strip().lower()
    if normalized in _KNOWN_ACCOUNT_MODES:
        return normalized
    return None


def _status_content(connection_status: str) -> tuple[str, str, str, str]:
    if connection_status == "disabled":
        return (
            "IBKR uitgeschakeld",
            "IBKR-sessiecontrole staat uit. Er worden geen verbindingen gestart.",
            "Activeer IBKR pas wanneer paper-only read-only configuratie volledig klaar staat.",
            "Geen automatische verbinding. Alleen read-only statusweergave.",
        )
    if connection_status == "not_configured":
        return (
            "IBKR niet geconfigureerd",
            "Host, account of client-id ontbreekt. Er wordt geen sessiecontrole uitgevoerd.",
            "Vul eerst veilige paper-only read-only configuratie aan.",
            "Controleer gateway-url, account-id hint en verwachte omgeving.",
        )
    if connection_status == "status_check_disabled":
        return (
            "Sessiecontrole uitgeschakeld",
            "Configuratie is aanwezig, maar actieve sessiecontrole staat uit.",
            "Zet sessiecontrole alleen handmatig aan als dit nodig is.",
            "Er wordt geen auto-connect gestart en orders blijven geblokkeerd.",
        )
    if connection_status == "connected_wrong_account_mode":
        return (
            "Verkeerde accountmodus",
            ("De sessie mag niet gebruikt worden zolang de accountmodus niet "
            "overeenkomt met de veilige instelling."),
            "Controleer accountmodus en blijf in veilige paper-only read-only modus.",
            "Geen sync, geen orders en geen brokeracties toegestaan.",
        )
    if connection_status == "connected_readonly":
        return (
            "Read-only sessie klaar",
            "De sessiecontrole meldt een read-only paper-sessie.",
            "Handmatige read-only sync mag alleen verder na de sync readiness-controle.",
            "Geen orders, geen brokeracties en geen automatische uitvoering.",
        )
    if connection_status == "connection_failed":
        return (
            "Verbinding mislukt",
            "Read-only sessiecontrole meldt een verbindingsfout.",
            "Controleer netwerk/gateway handmatig; er wordt niets automatisch herstart.",
            "Geen orders mogelijk; status blijft veilig geblokkeerd.",
        )
    if connection_status == "authentication_required":
        return (
            "Aanmelding vereist",
            "Read-only sessiecontrole vereist handmatige aanmelding.",
            "Meld handmatig veilig aan; er worden geen gegevens automatisch opgehaald.",
            "Geen sync, geen orders en geen automatische verbinding.",
        )
    if connection_status == "pacing_limited":
        return (
            "Snelheidslimiet actief",
            "Read-only sessiecontrole is tijdelijk beperkt door pacing.",
            "Wacht en probeer later opnieuw met handmatige controle.",
            "Orders blijven geblokkeerd en er draait geen marktdataruntime.",
        )
    if connection_status == "unknown":
        return (
            "IBKR-status onbekend",
            "De sessiecontrole gaf geen herkenbare status terug.",
            "Controleer de configuratie en probeer later opnieuw.",
            "Geen sync, geen suggesties en geen orders mogelijk.",
        )
    return (
        "IBKR geconfigureerd, nog niet verbonden",
        "Configuratie is aanwezig, maar er is geen actieve read-only sessie.",
        "Gebruik later een handmatige read-only sessiecheck; orders blijven uitgeschakeld.",
        "Alleen statusweergave. Geen auto-connect en geen brokerdata-sync.",
    )




def _default_adapter_selection_diagnostics() -> IbkrSessionAdapterSelectionDiagnostics:
    return IbkrSessionAdapterSelectionDiagnostics(
        session_adapter_family="default_safe",
        session_adapter_source="none",
        session_adapter_enabled=False,
        session_adapter_reason="status_check_not_attempted",
        tws_readonly_adapter_enabled=False,
        tws_readonly_adapter_runtime_available=False,
        tws_readonly_adapter_runtime_reason="default_safe_adapter",
        tws_readonly_adapter_blocked_reasons=("default_safe_adapter",),
        session_adapter_status_nl="Veilige standaardadapter actief",
        session_adapter_help_nl="Alleen read-only statusdiagnostiek zonder netwerk.",
        tws_readonly_adapter_next_step_nl="Expliciete instelling vereist.",
        tws_readonly_adapter_help_nl=(
            "TWS/Gateway adapter staat uit. Geen automatische verbinding."
        ),
    )


def _runtime_diagnostics(settings: Settings, selected_family: str) -> tuple[bool, str, bool, str]:
    if not settings.ibkr_enabled:
        return (False, "ibkr_not_configured", False, "status_check_disabled")
    if not settings.ibkr_tws_readonly_adapter_enabled:
        return (False, "tws_adapter_disabled", False, "explicit_opt_in_required")
    if selected_family != "tws_readonly":
        return (False, "default_safe_adapter", False, "adapter_selected_but_blocked")
    return (False, "network_runtime_not_implemented", False, "status_check_disabled")
def build_ibkr_status_placeholder(
    runtime_settings: Settings,
    session_status_adapter: IbkrSessionStatusAdapter | None = None,
) -> dict[str, object]:
    host_configured = runtime_settings.ibkr_gateway_url is not None
    port_configured = host_configured
    client_id_configured = runtime_settings.ibkr_account_id_hint is not None
    configured = bool(runtime_settings.ibkr_enabled and host_configured and client_id_configured)

    expected_environment = runtime_settings.ibkr_expected_environment
    connection_status = "unknown"
    account_mode_status = "unknown"
    account_mode = expected_environment
    session_check_attempted = False
    session_check_source = "none"
    session_status_reason = "disabled"
    adapter_selection = _default_adapter_selection_diagnostics()

    if not runtime_settings.ibkr_enabled:
        connection_status = "disabled"
    elif not configured:
        connection_status = "not_configured"
        session_status_reason = "missing_required_config"
    elif not runtime_settings.ibkr_status_check_enabled:
        connection_status = "status_check_disabled"
        session_status_reason = "status_check_disabled"
    else:
        if session_status_adapter is None:
            adapter, adapter_selection = build_ibkr_session_status_adapter(runtime_settings)
        else:
            adapter = session_status_adapter
            adapter_selection = _default_adapter_selection_diagnostics()
        try:
            result = adapter.check_session_status(runtime_settings)
        except Exception:
            connection_status = "connection_failed"
            account_mode_status = "unknown"
            account_mode = expected_environment
            session_check_attempted = True
            session_check_source = "adapter"
            session_status_reason = "adapter_error"
        else:
            normalized_connection_status = _normalize_connection_status(
                result.connection_status
            )
            adapter_account_mode_status = _normalize_account_mode_status(
                result.account_mode_status
            )
            adapter_account_mode = _normalize_account_mode(result.account_mode)
            expected_mode = _normalize_account_mode(expected_environment)

            final_connection_status = normalized_connection_status
            final_account_mode_status = adapter_account_mode_status
            final_session_status_reason = result.session_status_reason or "adapter_result"

            if final_connection_status == "connected_wrong_account_mode":
                final_account_mode_status = "mismatch"

            if (
                final_account_mode_status != "mismatch"
                and expected_mode is not None
                and adapter_account_mode is not None
                and adapter_account_mode != expected_mode
            ):
                final_connection_status = "connected_wrong_account_mode"
                final_account_mode_status = "mismatch"
                final_session_status_reason = "account_mode_mismatch"

            if (
                final_account_mode_status == "unknown"
                and adapter_account_mode is not None
            ):
                if (
                    expected_mode is None
                    or adapter_account_mode == expected_mode
                ):
                    final_account_mode_status = "match"

            if (
                final_account_mode_status == "unknown"
                and adapter_account_mode is None
                and final_connection_status != "connected_wrong_account_mode"
            ):
                final_account_mode_status = "unknown"

            connection_status = final_connection_status
            account_mode_status = final_account_mode_status
            account_mode = adapter_account_mode or expected_environment
            session_check_attempted = True
            session_check_source = result.session_check_source
            if connection_status == "unknown":
                session_status_reason = "unknown_connection_status"
            else:
                session_status_reason = final_session_status_reason

    status_nl, message_nl, next_step_nl, connection_help_nl = _status_content(connection_status)
    runtime_connection_allowed, runtime_block_reason, manual_status_check_allowed, manual_reason = (
        _runtime_diagnostics(runtime_settings, adapter_selection.session_adapter_family)
    )

    return {
        "provider": BrokerProvider.IBKR.value,
        "enabled": runtime_settings.ibkr_enabled,
        "configured": configured,
        "connection_status": connection_status,
        "account_mode_status": account_mode_status,
        "account_mode": account_mode,
        "expected_environment": expected_environment,
        "paper_only_enforced": True,
        "readonly": True,
        "host_configured": host_configured,
        "port_configured": port_configured,
        "client_id_configured": client_id_configured,
        "account_id_hint_present": runtime_settings.ibkr_account_id_hint is not None,
        "gateway_url_configured": runtime_settings.ibkr_gateway_url is not None,
        "status_check_enabled": runtime_settings.ibkr_status_check_enabled,
        "session_check_attempted": session_check_attempted,
        "session_check_source": session_check_source,
        "session_status_reason": session_status_reason,
        "session_adapter_family": adapter_selection.session_adapter_family,
        "session_adapter_source": adapter_selection.session_adapter_source,
        "session_adapter_enabled": adapter_selection.session_adapter_enabled,
        "session_adapter_reason": adapter_selection.session_adapter_reason,
        "session_adapter_status_nl": adapter_selection.session_adapter_status_nl,
        "session_adapter_help_nl": adapter_selection.session_adapter_help_nl,
        "tws_readonly_adapter_enabled": adapter_selection.tws_readonly_adapter_enabled,
        "tws_readonly_adapter_runtime_available": (
            adapter_selection.tws_readonly_adapter_runtime_available
        ),
        "tws_readonly_adapter_runtime_reason": (
            adapter_selection.tws_readonly_adapter_runtime_reason
        ),
        "tws_readonly_adapter_blocked_reasons": (
            list(adapter_selection.tws_readonly_adapter_blocked_reasons)
        ),
        "tws_readonly_adapter_next_step_nl": (
            adapter_selection.tws_readonly_adapter_next_step_nl
        ),
        "tws_readonly_adapter_help_nl": (
            adapter_selection.tws_readonly_adapter_help_nl
        ),
        "runtime_connection_allowed": runtime_connection_allowed,
        "runtime_connection_allowed_nl": "Geen automatische verbinding",
        "runtime_connection_blocked_reason": runtime_block_reason,
        "manual_status_check_allowed": manual_status_check_allowed,
        "manual_status_check_allowed_nl": "Handmatige statuscontrole nog geblokkeerd",
        "session_diagnostics_ready": True,
        "session_diagnostics_status_nl": "Alleen read-only statusdiagnostiek",
        "runtime_connection_next_step_nl": "Paper-only blijft verplicht.",
        "manual_status_check_reason": manual_reason,
        "sync_allowed": False,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_sync": False,
        "safe_for_orders": False,
        "status_nl": status_nl,
        "message_nl": message_nl,
        "next_step_nl": next_step_nl,
        "connection_help_nl": connection_help_nl,
        "help_nl": (
            "Alleen papiermodus toegestaan. "
            "Geen automatische acties en geen orders mogelijk."
        ),
        "last_checked_at": None,
        "blocks_orders": True,
    }
