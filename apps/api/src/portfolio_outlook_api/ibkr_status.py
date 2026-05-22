from portfolio_outlook_domain.broker_adapter import BrokerProvider

from portfolio_outlook_api.config import Settings


def build_ibkr_status_placeholder(runtime_settings: Settings) -> dict[str, object]:
    host_configured = runtime_settings.ibkr_gateway_url is not None
    port_configured = host_configured
    client_id_configured = runtime_settings.ibkr_account_id_hint is not None
    configured = bool(runtime_settings.ibkr_enabled and host_configured and client_id_configured)

    expected_environment = runtime_settings.ibkr_expected_environment
    if not runtime_settings.ibkr_enabled:
        connection_status = "disabled"
        status_nl = "IBKR uitgeschakeld"
        message_nl = "IBKR-sessiecontrole staat uit. Er worden geen verbindingen gestart."
        next_step_nl = (
            "Activeer IBKR pas wanneer paper-only read-only "
            "configuratie volledig klaar staat."
        )
    elif configured:
        connection_status = "configured_not_connected"
        status_nl = "IBKR geconfigureerd, nog niet verbonden"
        message_nl = (
            "Configuratie is aanwezig, maar er is bewust nog "
            "geen runtime-verbinding gestart."
        )
        next_step_nl = (
            "Gebruik later een handmatige read-only sessiecheck; "
            "orders blijven uitgeschakeld."
        )
    else:
        connection_status = "not_configured"
        status_nl = "IBKR niet geconfigureerd"
        message_nl = "Host/client-id ontbreken of zijn onvolledig; daarom geen sessiecontrole."
        next_step_nl = "Vul eerst veilige paper-only read-only configuratie aan."

    return {
        "provider": BrokerProvider.IBKR.value,
        "enabled": runtime_settings.ibkr_enabled,
        "configured": configured,
        "connection_status": connection_status,
        "account_mode_status": "unknown",
        "account_mode": expected_environment,
        "expected_environment": expected_environment,
        "paper_only_enforced": True,
        "readonly": True,
        "host_configured": host_configured,
        "port_configured": port_configured,
        "client_id_configured": client_id_configured,
        "account_id_hint_present": runtime_settings.ibkr_account_id_hint is not None,
        "gateway_url_configured": runtime_settings.ibkr_gateway_url is not None,
        "status_check_enabled": runtime_settings.ibkr_status_check_enabled,
        "sync_allowed": False,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "status_nl": status_nl,
        "message_nl": message_nl,
        "next_step_nl": next_step_nl,
        "help_nl": (
            "Alleen papiermodus toegestaan. Geen automatische acties "
            "en nog geen orders mogelijk."
        ),
        "last_checked_at": None,
        "blocks_orders": True,
    }
