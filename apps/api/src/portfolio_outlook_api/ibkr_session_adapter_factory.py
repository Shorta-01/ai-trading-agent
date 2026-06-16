from __future__ import annotations

from dataclasses import dataclass

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import (
    DefaultSafeIbkrSessionStatusAdapter,
    IbkrSessionStatusAdapter,
)
from portfolio_outlook_api.ibkr_tws_readonly_adapter import (
    IbkrTwsReadonlyClient,
    IbkrTwsReadonlySessionStatusAdapter,
)


@dataclass(frozen=True)
class IbkrSessionAdapterSelectionDiagnostics:
    session_adapter_family: str
    session_adapter_source: str
    session_adapter_enabled: bool
    session_adapter_reason: str
    tws_readonly_adapter_enabled: bool
    tws_readonly_adapter_runtime_available: bool
    tws_readonly_adapter_runtime_reason: str
    tws_readonly_adapter_blocked_reasons: tuple[str, ...]
    session_adapter_status_nl: str
    session_adapter_help_nl: str
    tws_readonly_adapter_next_step_nl: str
    tws_readonly_adapter_help_nl: str


def build_ibkr_session_status_adapter(
    settings: Settings,
    client: IbkrTwsReadonlyClient | None = None,
) -> tuple[IbkrSessionStatusAdapter, IbkrSessionAdapterSelectionDiagnostics]:
    if not settings.ibkr_tws_readonly_adapter_enabled:
        return (
            DefaultSafeIbkrSessionStatusAdapter(),
            IbkrSessionAdapterSelectionDiagnostics(
                session_adapter_family="default_safe",
                session_adapter_source="default_safe_non_network_adapter",
                session_adapter_enabled=False,
                session_adapter_reason="tws_readonly_adapter_disabled_by_setting",
                tws_readonly_adapter_enabled=False,
                tws_readonly_adapter_runtime_available=False,
                tws_readonly_adapter_runtime_reason="default_safe_adapter",
                tws_readonly_adapter_blocked_reasons=(
                    "default_safe_adapter",
                    "tws_adapter_disabled",
                    "explicit_opt_in_required",
                    "status_check_disabled",
                ),
                session_adapter_status_nl="Veilige standaardadapter actief",
                session_adapter_help_nl="Alleen read-only statusdiagnostiek zonder netwerk.",
                tws_readonly_adapter_next_step_nl=(
                    "Expliciete instelling vereist voor TWS/Gateway skeleton."
                ),
                tws_readonly_adapter_help_nl="Veilige standaardadapter actief.",
            ),
        )

    return (
        IbkrTwsReadonlySessionStatusAdapter(client=client),
        IbkrSessionAdapterSelectionDiagnostics(
            session_adapter_family="tws_readonly",
            session_adapter_source="tws_readonly_adapter",
            session_adapter_enabled=True,
            session_adapter_reason=(
                "tws_readonly_injected_client"
                if client is not None
                else "tws_readonly_missing_injected_client"
            ),
            tws_readonly_adapter_enabled=True,
            tws_readonly_adapter_runtime_available=client is not None,
            tws_readonly_adapter_runtime_reason=(
                "read_only_status_check_ready_for_future_runtime"
                if client is not None
                else "runtime_client_missing"
            ),
            tws_readonly_adapter_blocked_reasons=(
                (
                    "network_runtime_not_implemented",
                    "adapter_selected_but_blocked",
                )
                if client is not None
                else (
                    "runtime_client_missing",
                    "network_runtime_not_implemented",
                    "adapter_selected_but_blocked",
                )
            ),
            session_adapter_status_nl="TWS/Gateway skeleton geselecteerd",
            session_adapter_help_nl=(
                "Alleen read-only statusdiagnostiek; orders en suggesties blijven geblokkeerd."
            ),
            tws_readonly_adapter_next_step_nl=(
                "Injecteer een paper testclient voor handmatige statuscontrole in tests."
            ),
            tws_readonly_adapter_help_nl=(
                "TWS/Gateway adapter is alleen testbaar met geïnjecteerde client."
                if client is None
                else "TWS/Gateway testadapter actief zonder automatische verbinding."
            ),
        ),
    )
