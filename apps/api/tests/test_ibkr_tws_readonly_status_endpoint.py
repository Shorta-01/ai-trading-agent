from fastapi.testclient import TestClient

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError
from portfolio_outlook_api.ibkr_tws_readonly_runtime import (
    build_manual_tws_readonly_status_check_readiness,
)
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import (
    _run_manual_tws_readonly_status_check_endpoint,
)

client = TestClient(app)


class FakeRuntimeClient:
    def __init__(
        self,
        *,
        account_mode: str | None = "paper",
        connect_error: Exception | None = None,
        disconnect_error: Exception | None = None,
    ) -> None:
        self._account_mode = account_mode
        self._connect_error = connect_error
        self._disconnect_error = disconnect_error
        self.connect_calls = 0
        self.disconnect_calls = 0

    def connect_readonly(self, timeout_seconds: int) -> None:
        self.connect_calls += 1
        if self._connect_error is not None:
            raise self._connect_error

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        if self._disconnect_error is not None:
            raise self._disconnect_error

    def get_account_mode(self) -> str | None:
        return self._account_mode


def _settings(**kwargs: object) -> Settings:
    return Settings(**kwargs)


def _fake_client_ready_settings(**kwargs: object) -> Settings:
    defaults: dict[str, object] = {
        "ibkr_enabled": True,
        "ibkr_status_check_enabled": True,
        "ibkr_tws_readonly_adapter_enabled": True,
        "ibkr_tws_readonly_runtime_enabled": True,
        "ibkr_tws_readonly_real_client_enabled": True,
        "ibkr_expected_environment": "paper",
        "ibkr_sync_host": "127.0.0.1",
        "ibkr_sync_port": 4002,
        "ibkr_sync_client_id": 1,
    }
    defaults.update(kwargs)
    return _settings(**defaults)


def _assert_safety_flags_false(payload: dict[str, object]) -> None:
    assert payload["actions_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["action_drafts_allowed"] is False
    assert payload["orders_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["safe_for_orders"] is False
    assert payload["blocks_orders"] is True


def test_default_route_call_blocked_runtime_disabled() -> None:
    payload = client.post("/ibkr/session/manual-readonly-status-check").json()
    assert payload["status"] == "runtime_disabled"
    assert "runtime_disabled" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False
    assert payload["disconnect_attempted"] is False
    _assert_safety_flags_false(payload)


def test_runtime_enabled_adapter_disabled_blocked() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _settings(ibkr_tws_readonly_runtime_enabled=True),
        runtime_client=None,
    )
    assert "adapter_disabled" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False


def test_adapter_enabled_runtime_disabled_blocked() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _settings(ibkr_tws_readonly_adapter_enabled=True),
        runtime_client=None,
    )
    assert "runtime_disabled" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False


def test_runtime_enabled_adapter_enabled_missing_client_blocked() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=None,
    )
    assert "missing_runtime_client" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False


def test_injected_fake_paper_client_completed() -> None:
    fake = FakeRuntimeClient(account_mode="paper")
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=fake,
    )
    assert payload["status"] == "manual_status_check_completed"
    assert payload["connect_attempted"] is True
    assert payload["disconnect_attempted"] is True
    assert payload["account_mode"] == "paper"
    assert fake.connect_calls == 1
    assert fake.disconnect_calls == 1
    _assert_safety_flags_false(payload)


def test_injected_fake_wrong_mode_client_blocked() -> None:
    fake = FakeRuntimeClient(account_mode="live")
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=fake,
    )
    assert payload["status"] == "wrong_account_mode"
    assert payload["disconnect_attempted"] is True
    _assert_safety_flags_false(payload)


def test_injected_fake_unknown_mode_client_blocked() -> None:
    fake = FakeRuntimeClient(account_mode=None)
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=fake,
    )
    assert payload["status"] == "unknown_account_mode"
    assert payload["disconnect_attempted"] is True


def test_timeout_maps_safely_with_dutch_help() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=FakeRuntimeClient(connect_error=TimeoutError("timeout")),
    )
    assert payload["status"] == "timeout"
    assert payload["help_nl"]


def test_authentication_required_maps_safely() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=FakeRuntimeClient(
            connect_error=IbkrTwsReadonlyAdapterError("authentication_required")
        ),
    )
    assert payload["status"] == "authentication_required"


def test_pacing_limited_maps_safely() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=FakeRuntimeClient(
            connect_error=IbkrTwsReadonlyAdapterError("pacing_limited")
        ),
    )
    assert payload["status"] == "pacing_limited"


def test_connection_failed_maps_safely() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=FakeRuntimeClient(
            connect_error=IbkrTwsReadonlyAdapterError("connection_failed")
        ),
    )
    assert payload["status"] == "connection_failed"


def test_unexpected_client_error_maps_safely() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(),
        runtime_client=FakeRuntimeClient(connect_error=RuntimeError("boom")),
    )
    assert payload["status"] == "unexpected_client_error"


def test_disconnect_failure_ignored_and_safe() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(
            ibkr_sync_host="sensitive-host.local",
            ibkr_sync_port=40123,
            ibkr_sync_client_id=98765,
            ibkr_account_id="DU1234567",
        ),
        runtime_client=FakeRuntimeClient(disconnect_error=RuntimeError("disconnect boom")),
    )
    assert payload["disconnect_error_ignored"] is True
    _assert_safety_flags_false(payload)


def test_no_secret_regression() -> None:
    payload = _run_manual_tws_readonly_status_check_endpoint(
        _fake_client_ready_settings(
            ibkr_sync_host="sensitive-host.local",
            ibkr_sync_port=40123,
            ibkr_sync_client_id=98765,
            ibkr_account_id="DU1234567",
        ),
        runtime_client=FakeRuntimeClient(account_mode="paper"),
    )
    blob = str(payload).lower()
    assert "sensitive-host.local" not in blob
    assert "40123" not in blob
    assert "98765" not in blob
    assert "du1234567" not in blob
    assert "password" not in blob
    assert "token" not in blob
    assert "secret" not in blob


def test_readiness_default_route_blocked_runtime_disabled() -> None:
    payload = client.get("/ibkr/session/manual-readonly-status-check/readiness").json()
    assert payload["status"] == "manual_status_check_blocked"
    assert payload["ready"] is False
    assert "runtime_disabled" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False
    assert payload["disconnect_attempted"] is False
    assert payload["runtime_connection_allowed"] is False
    assert payload["manual_status_check_allowed"] is False
    _assert_safety_flags_false(payload)


def test_readiness_runtime_enabled_adapter_disabled() -> None:
    payload = build_manual_tws_readonly_status_check_readiness(
        _settings(ibkr_tws_readonly_runtime_enabled=True),
        runtime_client=None,
    ).__dict__
    assert "adapter_disabled" in payload["blocked_reasons"]
    assert payload["connect_attempted"] is False


def test_readiness_no_longer_blocks_on_paper_only_or_expected_mode() -> None:
    """V1.2 §BZ — software werkt VOLLEDIG in beide modi. Geen van
    ``paper_only_required`` of ``expected_account_mode_not_paper``
    mogen nog in ``blocked_reasons`` zitten, zelfs niet wanneer de
    expected environment ``live`` is."""

    payload = build_manual_tws_readonly_status_check_readiness(
        _settings(
            ibkr_tws_readonly_runtime_enabled=True,
            ibkr_tws_readonly_adapter_enabled=True,
            ibkr_expected_environment="live",
        ),
        runtime_client=None,
    ).__dict__
    assert "paper_only_required" not in payload["blocked_reasons"]
    assert "expected_account_mode_not_paper" not in payload["blocked_reasons"]
    assert payload["runtime_client_available"] is False
    assert payload["endpoint"] == "/ibkr/session/manual-readonly-status-check"
    assert payload["method"] == "POST"
