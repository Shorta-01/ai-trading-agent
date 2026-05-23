from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.ibkr_tws_readonly_adapter import (
    IbkrTwsReadonlyAdapterError,
    IbkrTwsReadonlySessionStatusAdapter,
)


class FakeReadonlyClient:
    def __init__(
        self,
        *,
        connected: bool = True,
        account_mode: str | None = "paper",
        connect_error: Exception | None = None,
        disconnect_error: Exception | None = None,
    ) -> None:
        self.connected = connected
        self.account_mode = account_mode
        self.connect_error = connect_error
        self.disconnect_error = disconnect_error
        self.connect_calls = 0
        self.disconnect_calls = 0

    def connect_readonly(self, timeout_seconds: int) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error

    def is_connected(self) -> bool:
        return self.connected

    def get_account_mode(self) -> str | None:
        return self.account_mode

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        if self.disconnect_error is not None:
            raise self.disconnect_error


def _settings() -> Settings:
    return Settings(
        ibkr_enabled=True,
        ibkr_status_check_enabled=True,
        ibkr_gateway_url="https://gateway.example",
        ibkr_account_id_hint="DU123",
        ibkr_expected_environment="paper",
    )


def test_default_without_client_is_safe_and_non_network() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(client=None)

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "configured_not_connected"
    assert result.session_status_reason == "tws_readonly_client_missing"
    assert result.session_check_source == "tws_readonly_adapter_disabled"
    assert "secret" not in str(result)
    assert "token" not in str(result)


def test_connected_paper_maps_to_connected_readonly() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(client=FakeReadonlyClient())

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "connected_readonly"
    assert result.account_mode_status == "match"
    assert result.account_mode == "paper"


def test_connected_wrong_mode_maps_to_mismatch() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(
        client=FakeReadonlyClient(account_mode="live")
    )

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "connected_wrong_account_mode"
    assert result.account_mode_status == "mismatch"
    assert result.account_mode == "live"


def test_connection_failure_maps_to_connection_failed_without_leak() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(
        client=FakeReadonlyClient(
            connect_error=IbkrTwsReadonlyAdapterError("connection_failed")
        )
    )

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "connection_failed"
    assert "password" not in str(result)
    assert "token" not in str(result)


def test_authentication_required_mapping() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(
        client=FakeReadonlyClient(
            connect_error=IbkrTwsReadonlyAdapterError("authentication_required")
        )
    )

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "authentication_required"
    assert result.session_status_reason == "authentication_required"


def test_pacing_limited_mapping() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(
        client=FakeReadonlyClient(
            connect_error=IbkrTwsReadonlyAdapterError("pacing_limited")
        )
    )

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "pacing_limited"


def test_timeout_maps_to_connection_failed() -> None:
    adapter = IbkrTwsReadonlySessionStatusAdapter(
        client=FakeReadonlyClient(connect_error=TimeoutError("timed out"))
    )

    result = adapter.check_session_status(_settings())

    assert result.connection_status == "connection_failed"
    assert result.session_status_reason == "timeout"


def test_status_builder_integration_keeps_safety_booleans_false() -> None:
    payload = build_ibkr_status_placeholder(
        _settings(),
        session_status_adapter=IbkrTwsReadonlySessionStatusAdapter(
            client=FakeReadonlyClient(connected=True, account_mode="paper")
        ),
    )

    assert payload["connection_status"] == "connected_readonly"
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["actions_allowed"] is False


def test_client_disconnect_called_once_on_check() -> None:
    client = FakeReadonlyClient()
    adapter = IbkrTwsReadonlySessionStatusAdapter(client=client)

    _ = adapter.check_session_status(_settings())

    assert client.connect_calls == 1
    assert client.disconnect_calls == 1
