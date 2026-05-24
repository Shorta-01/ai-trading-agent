from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError
from portfolio_outlook_api.ibkr_tws_readonly_runtime import (
    run_manual_tws_readonly_status_check,
)


class FakeRuntimeClient:
    def __init__(
        self,
        *,
        account_mode: str | None = "paper",
        connect_error: Exception | None = None,
        disconnect_error: Exception | None = None,
    ) -> None:
        self.account_mode = account_mode
        self.connect_error = connect_error
        self.disconnect_error = disconnect_error
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.get_mode_calls = 0

    def connect_readonly(self, timeout_seconds: int) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error

    def is_connected(self) -> bool:
        return True

    def get_account_mode(self) -> str | None:
        self.get_mode_calls += 1
        return self.account_mode

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        if self.disconnect_error is not None:
            raise self.disconnect_error


def _settings(**updates: object) -> Settings:
    base = Settings(
        ibkr_enabled=False,
        ibkr_status_check_enabled=False,
        ibkr_tws_readonly_adapter_enabled=False,
        ibkr_tws_readonly_runtime_enabled=False,
        ibkr_expected_environment="paper",
        paper_only_mode=True,
    )
    return base.model_copy(update=updates)


def _fake_client_ready_settings(**updates: object) -> Settings:
    return _settings(
        ibkr_enabled=True,
        ibkr_status_check_enabled=True,
        ibkr_tws_readonly_adapter_enabled=True,
        ibkr_tws_readonly_runtime_enabled=True,
        ibkr_expected_environment="paper",
        paper_only_mode=True,
        **updates,
    )


def _assert_safety_flags_false(result: object) -> None:
    assert result.actions_allowed is False
    assert result.suggestions_allowed is False
    assert result.action_drafts_allowed is False
    assert result.orders_allowed is False
    assert result.order_submission_allowed is False
    assert result.order_modification_allowed is False
    assert result.order_cancellation_allowed is False
    assert result.can_submit_orders is False
    assert result.safe_for_orders is False
    assert result.blocks_orders is True


def test_default_runtime_disabled() -> None:
    result = run_manual_tws_readonly_status_check(_settings(), runtime_client=None)

    assert result.status == "runtime_disabled"
    assert result.connect_attempted is False
    assert result.disconnect_attempted is False
    _assert_safety_flags_false(result)


def test_enabled_flag_only_still_blocked() -> None:
    result = run_manual_tws_readonly_status_check(
        _settings(ibkr_enabled=True),
        runtime_client=None,
    )
    assert result.status == "runtime_disabled"
    assert result.connect_attempted is False


def test_status_check_enabled_only_still_blocked() -> None:
    result = run_manual_tws_readonly_status_check(
        _settings(ibkr_status_check_enabled=True),
        runtime_client=None,
    )
    assert result.status == "runtime_disabled"
    assert result.connect_attempted is False


def test_adapter_enabled_only_still_blocked() -> None:
    result = run_manual_tws_readonly_status_check(
        _settings(ibkr_tws_readonly_adapter_enabled=True),
        runtime_client=None,
    )

    assert result.status == "runtime_disabled"
    assert "runtime_disabled" in result.blocked_reasons
    assert result.connect_attempted is False


def test_runtime_opt_in_with_adapter_disabled_blocked() -> None:
    result = run_manual_tws_readonly_status_check(
        _settings(ibkr_tws_readonly_runtime_enabled=True),
        runtime_client=None,
    )

    assert "adapter_disabled" in result.blocked_reasons
    assert result.connect_attempted is False


def test_runtime_opt_in_without_client_blocked() -> None:
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=None,
    )
    assert "missing_runtime_client" in result.blocked_reasons
    assert result.connect_attempted is False


def test_expected_mode_not_paper_blocked() -> None:
    client = FakeRuntimeClient(account_mode="paper")
    result = run_manual_tws_readonly_status_check(
        _settings(
            ibkr_tws_readonly_runtime_enabled=True,
            ibkr_tws_readonly_adapter_enabled=True,
            ibkr_expected_environment="live",
        ),
        runtime_client=client,
    )
    assert "expected_account_mode_not_paper" in result.blocked_reasons
    assert client.connect_calls == 0


def test_happy_path_connect_check_disconnect() -> None:
    client = FakeRuntimeClient(account_mode="paper")
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "manual_status_check_completed"
    assert client.connect_calls == 1
    assert client.disconnect_calls == 1
    assert result.account_mode == "paper"
    assert result.account_mode_status == "match"
    _assert_safety_flags_false(result)


def test_wrong_account_mode_blocks() -> None:
    client = FakeRuntimeClient(account_mode="live")
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "wrong_account_mode"
    assert client.connect_calls == 1
    assert client.disconnect_calls == 1
    _assert_safety_flags_false(result)


def test_unknown_account_mode_blocks() -> None:
    client = FakeRuntimeClient(account_mode=None)
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "unknown_account_mode"
    assert client.disconnect_calls == 1


def test_timeout_maps_safely() -> None:
    client = FakeRuntimeClient(connect_error=TimeoutError("timeout"))
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "timeout"
    assert client.disconnect_calls == 1


def test_authentication_required_maps_safely() -> None:
    client = FakeRuntimeClient(
        connect_error=IbkrTwsReadonlyAdapterError("authentication_required")
    )
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "authentication_required"


def test_pacing_limited_maps_safely() -> None:
    client = FakeRuntimeClient(connect_error=IbkrTwsReadonlyAdapterError("pacing_limited"))
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "pacing_limited"


def test_connection_failed_maps_safely() -> None:
    client = FakeRuntimeClient(
        connect_error=IbkrTwsReadonlyAdapterError("connection_failed")
    )
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "connection_failed"


def test_unexpected_error_maps_safely() -> None:
    client = FakeRuntimeClient(connect_error=RuntimeError("boom"))
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(),
        runtime_client=client,
    )
    assert result.status == "unexpected_client_error"


def test_disconnect_error_ignored() -> None:
    client = FakeRuntimeClient(disconnect_error=RuntimeError("disconnect failed"))
    result = run_manual_tws_readonly_status_check(
        _settings(
            ibkr_tws_readonly_runtime_enabled=True,
            ibkr_tws_readonly_adapter_enabled=True,
        ),
        runtime_client=client,
    )
    assert result.disconnect_error_ignored is True


def test_no_secret_leak_in_result_text() -> None:
    client = FakeRuntimeClient()
    result = run_manual_tws_readonly_status_check(
        _fake_client_ready_settings(
            ibkr_tws_host="sensitive-host.local",
            ibkr_tws_port=40123,
            ibkr_client_id=98765,
            ibkr_account_id="DU1234567",
        ),
        runtime_client=client,
    )
    dumped = str(result).lower()
    assert "sensitive-host.local" not in dumped
    assert "40123" not in dumped
    assert "98765" not in dumped
    assert "du1234567" not in dumped
    assert "password" not in dumped
    assert "token" not in dumped
    assert "secret" not in dumped
