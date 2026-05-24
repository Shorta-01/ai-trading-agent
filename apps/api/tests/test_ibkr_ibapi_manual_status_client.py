from __future__ import annotations

import types

from portfolio_outlook_api.ibkr_ibapi_manual_status_client import (
    IbapiManualReadonlyStatusClient,
)


class _FakeEWrapper:
    pass


class _FakeEClient:
    def __init__(self, wrapper: object) -> None:
        self.wrapper = wrapper
        self.connected = False

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connected = True

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def reqManagedAccts(self) -> None:
        self.wrapper.managedAccounts("DU12345")

    def disconnect(self) -> None:
        self.connected = False


def test_manual_client_connect_check_disconnect(monkeypatch) -> None:
    monkeypatch.setattr(
        "portfolio_outlook_api.ibkr_ibapi_manual_status_client.load_ibapi_preflight_modules",
        lambda: object(),
    )
    sys_modules = __import__("sys").modules
    monkeypatch.setitem(
        sys_modules,
        "ibapi.client",
        types.SimpleNamespace(EClient=_FakeEClient),
    )
    monkeypatch.setitem(
        sys_modules,
        "ibapi.wrapper",
        types.SimpleNamespace(EWrapper=_FakeEWrapper),
    )

    client = IbapiManualReadonlyStatusClient(host="127.0.0.1", port=7497, client_id=11)
    client.connect_readonly(timeout_seconds=5)

    assert client.is_connected() is True
    assert client.get_account_mode() == "paper"

    client.disconnect()
    assert client.is_connected() is False
