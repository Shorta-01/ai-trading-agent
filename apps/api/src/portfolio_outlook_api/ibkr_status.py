from portfolio_outlook_domain.broker_adapter import BrokerProvider

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import (
    DefaultSafeIbkrSessionStatusAdapter,
    IbkrSessionStatusAdapter,
)


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
    return (
        "IBKR geconfigureerd, nog niet verbonden",
        "Configuratie is aanwezig, maar er is geen actieve read-only sessie.",
        "Gebruik later een handmatige read-only sessiecheck; orders blijven uitgeschakeld.",
        "Alleen statusweergave. Geen auto-connect en geen brokerdata-sync.",
    )


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

    if not runtime_settings.ibkr_enabled:
        connection_status = "disabled"
    elif not configured:
        connection_status = "not_configured"
        session_status_reason = "missing_required_config"
    elif not runtime_settings.ibkr_status_check_enabled:
        connection_status = "status_check_disabled"
        session_status_reason = "status_check_disabled"
    else:
        adapter = session_status_adapter or DefaultSafeIbkrSessionStatusAdapter()
        result = adapter.check_session_status(runtime_settings)
        connection_status = result.connection_status
        account_mode_status = result.account_mode_status
        account_mode = result.account_mode or expected_environment
        session_check_attempted = True
        session_check_source = result.session_check_source
        session_status_reason = result.session_status_reason or "adapter_result"

    status_nl, message_nl, next_step_nl, connection_help_nl = _status_content(connection_status)

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
