"""Tests for the IBKR real sync adapter factory.

The factory must return ``None`` whenever any safety gate is off (real-client
flag, sync-enabled flag, account-mode, readonly, host, port, client-id), and a
real ``IbapiReadOnlySyncClient`` only when every gate passes.
"""

from __future__ import annotations

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_ibapi_sync_client import IbapiReadOnlySyncClient
from portfolio_outlook_api.ibkr_sync_adapter_factory import build_real_sync_adapter


def _ready_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "ibkr_sync_enabled": True,
        "ibkr_sync_host": "127.0.0.1",
        "ibkr_sync_port": 4002,
        "ibkr_sync_client_id": 11,
        "ibkr_sync_account_mode": "paper",
        "ibkr_sync_readonly": True,
        "ibkr_sync_real_client_enabled": True,
        "ibkr_sync_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings(**values)


class _NoopApp:
    def connect(self, host: str, port: int, client_id: int) -> None:
        return None

    def isConnected(self) -> bool:  # noqa: N802
        return True

    def disconnect(self) -> None:
        return None

    def run(self) -> None:
        return None

    def reqAccountSummary(self, reqId: int, group: str, tags: str) -> None:  # noqa: N802
        return None

    def cancelAccountSummary(self, reqId: int) -> None:  # noqa: N802
        return None

    def reqPositions(self) -> None:  # noqa: N802
        return None

    def cancelPositions(self) -> None:  # noqa: N802
        return None

    def reqAllOpenOrders(self) -> None:  # noqa: N802
        return None

    def reqExecutions(self, reqId: int, exec_filter: object) -> None:  # noqa: N802
        return None


def test_factory_returns_real_client_when_fully_configured() -> None:
    adapter = build_real_sync_adapter(_ready_settings(), app=_NoopApp())
    assert isinstance(adapter, IbapiReadOnlySyncClient)


def test_factory_returns_none_when_real_client_flag_off() -> None:
    settings = _ready_settings(ibkr_sync_real_client_enabled=False)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_sync_disabled() -> None:
    settings = _ready_settings(ibkr_sync_enabled=False)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_account_mode_is_not_paper() -> None:
    settings = _ready_settings(ibkr_sync_account_mode="live")
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_readonly_is_off() -> None:
    settings = _ready_settings(ibkr_sync_readonly=False)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_host_missing() -> None:
    settings = _ready_settings(ibkr_sync_host=None)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_port_missing() -> None:
    settings = _ready_settings(ibkr_sync_port=None)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_returns_none_when_client_id_missing() -> None:
    settings = _ready_settings(ibkr_sync_client_id=None)
    assert build_real_sync_adapter(settings, app=_NoopApp()) is None


def test_factory_uses_injected_app_so_no_real_socket_opens() -> None:
    app = _NoopApp()
    adapter = build_real_sync_adapter(_ready_settings(), app=app)
    assert isinstance(adapter, IbapiReadOnlySyncClient)
    adapter.close()
