from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from portfolio_outlook_api.config import Settings


@dataclass(frozen=True)
class IbkrSessionStatusAdapterResult:
    connection_status: str
    account_mode_status: str = "unknown"
    account_mode: str | None = None
    session_status_reason: str | None = None
    session_check_source: str = "adapter"


class IbkrSessionStatusAdapter(Protocol):
    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        """Return a safe read-only session status without placing orders."""


class DefaultSafeIbkrSessionStatusAdapter:
    """Disabled-by-default non-network adapter for Task 130."""

    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        return IbkrSessionStatusAdapterResult(
            connection_status="configured_not_connected",
            account_mode_status="unknown",
            account_mode=runtime_settings.ibkr_expected_environment,
            session_status_reason="default_safe_non_network",
            session_check_source="default_safe_non_network_adapter",
        )
