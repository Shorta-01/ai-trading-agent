from portfolio_outlook_domain.broker_adapter import (
    BrokerAccountModeStatus,
    BrokerConnectionStatus,
    BrokerProvider,
)


def build_ibkr_status_placeholder() -> dict[str, object]:
    return {
        "provider": BrokerProvider.IBKR.value,
        "configured": False,
        "connection_status": BrokerConnectionStatus.NOT_CONFIGURED.value,
        "account_mode_status": BrokerAccountModeStatus.UNKNOWN.value,
        "can_submit_orders": False,
        "status_nl": "Niet gekoppeld",
        "message_nl": (
            "IBKR-koppeling is nog niet actief. Er worden nog geen IBKR API-calls "
            "uitgevoerd."
        ),
        "blocks_orders": True,
    }
