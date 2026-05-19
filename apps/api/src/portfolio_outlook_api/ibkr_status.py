from portfolio_outlook_domain.broker_adapter import BrokerProvider

from portfolio_outlook_api.config import Settings


def build_ibkr_status_placeholder(runtime_settings: Settings) -> dict[str, object]:
    configured = bool(
        runtime_settings.ibkr_enabled
        and runtime_settings.ibkr_gateway_url
        and runtime_settings.ibkr_account_id_hint
    )

    expected_environment = runtime_settings.ibkr_expected_environment
    if not runtime_settings.ibkr_enabled:
        status_nl = "Niet gekoppeld"
        message_nl = (
            "IBKR-koppeling is nog niet actief. "
            "Er worden nog geen IBKR API-calls uitgevoerd."
        )
    elif configured:
        status_nl = "Voorbereid, nog niet actief"
        message_nl = (
            "IBKR-instellingen zijn voorbereid, maar echte verbinding "
            "en accountcontrole zijn nog niet actief."
        )
    else:
        status_nl = "Geblokkeerd tot accountcontrole"
        message_nl = "Orders blijven geblokkeerd tot het IBKR-account veilig is gecontroleerd."

    return {
        "provider": BrokerProvider.IBKR.value,
        "enabled": runtime_settings.ibkr_enabled,
        "configured": configured,
        "connection_status": "not_connected",
        "account_mode_status": "unknown",
        "expected_environment": expected_environment,
        "account_id_hint_present": runtime_settings.ibkr_account_id_hint is not None,
        "gateway_url_configured": runtime_settings.ibkr_gateway_url is not None,
        "status_check_enabled": runtime_settings.ibkr_status_check_enabled,
        "can_submit_orders": False,
        "status_nl": status_nl,
        "message_nl": message_nl,
        "help_nl": "In versie 1 moet het gekoppelde IBKR-account paper-only zijn.",
        "blocks_orders": True,
    }
