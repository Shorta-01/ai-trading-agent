from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import (
    IbkrSessionStatusAdapter,
    IbkrSessionStatusAdapterResult,
)


class IbkrTwsReadonlyClient(Protocol):
    """Low-level read-only session client boundary for future TWS/Gateway wiring."""

    def connect_readonly(self, timeout_seconds: int) -> None:
        """Open a read-only session within timeout."""

    def is_connected(self) -> bool:
        """Return whether the low-level session is connected."""

    def get_account_mode(self) -> str | None:
        """Return detected account mode, e.g. 'paper' or 'live'."""

    def disconnect(self) -> None:
        """Close low-level session resources."""


@dataclass(frozen=True)
class IbkrTwsReadonlyAdapterError(RuntimeError):
    code: str


class IbkrTwsReadonlySessionStatusAdapter(IbkrSessionStatusAdapter):
    """Disabled-by-default, injected-client-only TWS read-only status adapter skeleton."""

    def __init__(self, client: IbkrTwsReadonlyClient | None = None) -> None:
        self._client = client

    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        if self._client is None:
            return IbkrSessionStatusAdapterResult(
                connection_status="configured_not_connected",
                account_mode_status="unknown",
                account_mode=runtime_settings.ibkr_expected_environment,
                session_status_reason="tws_readonly_client_missing",
                session_check_source="tws_readonly_adapter_disabled",
            )

        try:
            self._client.connect_readonly(
                timeout_seconds=runtime_settings.ibkr_connection_timeout_seconds
            )
            if not self._client.is_connected():
                return IbkrSessionStatusAdapterResult(
                    connection_status="configured_not_connected",
                    account_mode_status="unknown",
                    account_mode=runtime_settings.ibkr_expected_environment,
                    session_status_reason="not_connected_after_connect",
                    session_check_source="tws_readonly_adapter",
                )

            account_mode = _normalize_mode(self._client.get_account_mode())
            expected_mode = _normalize_mode(runtime_settings.ibkr_expected_environment)

            if account_mode is None:
                return IbkrSessionStatusAdapterResult(
                    connection_status="unknown",
                    account_mode_status="unknown",
                    account_mode=expected_mode,
                    session_status_reason="account_mode_unavailable",
                    session_check_source="tws_readonly_adapter",
                )

            if expected_mode is not None and account_mode != expected_mode:
                return IbkrSessionStatusAdapterResult(
                    connection_status="connected_account_mode_mismatch",
                    account_mode_status="mismatch",
                    account_mode=account_mode,
                    session_status_reason="account_mode_mismatch",
                    session_check_source="tws_readonly_adapter",
                )

            return IbkrSessionStatusAdapterResult(
                connection_status="connected_readonly",
                account_mode_status="match",
                account_mode=account_mode,
                session_status_reason="readonly_session_connected",
                session_check_source="tws_readonly_adapter",
            )
        except TimeoutError:
            return IbkrSessionStatusAdapterResult(
                connection_status="connection_failed",
                account_mode_status="unknown",
                account_mode=runtime_settings.ibkr_expected_environment,
                session_status_reason="timeout",
                session_check_source="tws_readonly_adapter",
            )
        except IbkrTwsReadonlyAdapterError as error:
            return IbkrSessionStatusAdapterResult(
                connection_status=_map_error_code(error.code),
                account_mode_status="unknown",
                account_mode=runtime_settings.ibkr_expected_environment,
                session_status_reason=_safe_reason_from_code(error.code),
                session_check_source="tws_readonly_adapter",
            )
        except Exception:
            return IbkrSessionStatusAdapterResult(
                connection_status="unknown",
                account_mode_status="unknown",
                account_mode=runtime_settings.ibkr_expected_environment,
                session_status_reason="unexpected_client_error",
                session_check_source="tws_readonly_adapter",
            )
        finally:
            try:
                self._client.disconnect()
            except Exception:
                # Keep status checks resilient; never escalate disconnect errors.
                pass


def _normalize_mode(mode: str | None) -> str | None:
    if mode is None:
        return None
    normalized = mode.strip().lower()
    if normalized in {"paper", "live"}:
        return normalized
    return None


def _map_error_code(code: str) -> str:
    normalized = code.strip().lower()
    if normalized == "authentication_required":
        return "authentication_required"
    if normalized == "pacing_limited":
        return "pacing_limited"
    if normalized == "connection_failed":
        return "connection_failed"
    return "unknown"


def _safe_reason_from_code(code: str) -> str:
    normalized = code.strip().lower()
    if normalized in {
        "authentication_required",
        "pacing_limited",
        "connection_failed",
    }:
        return normalized
    return "unknown_error_code"
