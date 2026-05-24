from __future__ import annotations

import pytest

from portfolio_outlook_api.ibkr_ibapi_manual_status_client import (
    IbapiManualReadonlyStatusClient,
)
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError


class FakeManualIbapiApp:
    def __init__(
        self,
        *,
        accounts: tuple[str, ...] = ("DU12345",),
        connect_error: Exception | None = None,
        connected_after_connect: bool = True,
    ) -> None:
        self.accounts = accounts
        self.connect_error = connect_error
        self.connected_after_connect = connected_after_connect
        self.connected = False
        self.connect_calls = 0
        self.req_managed_accts_calls = 0
        self.disconnect_calls = 0
        self.client: IbapiManualReadonlyStatusClient | None = None

    def connect(self, host: str, port: int, client_id: int) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = self.connected_after_connect

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def reqManagedAccts(self) -> None:  # noqa: N802
        self.req_managed_accts_calls += 1
        if self.client is not None:
            self.client._state.managed_accounts = self.accounts

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.connected = False


def test_manual_client_connect_check_disconnect_with_fake_app() -> None:
    fake = FakeManualIbapiApp(accounts=("DU12345",))
    client = IbapiManualReadonlyStatusClient(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        app=fake,
    )
    fake.client = client

    client.connect_readonly(timeout_seconds=5)

    assert client.is_connected() is True
    assert client.get_account_mode() == "paper"
    assert fake.connect_calls == 1
    assert fake.req_managed_accts_calls == 1

    client.disconnect()
    assert client.is_connected() is False
    assert fake.disconnect_calls == 1


def test_manual_client_returns_live_mode_for_non_du_accounts() -> None:
    fake = FakeManualIbapiApp(accounts=("U12345",))
    client = IbapiManualReadonlyStatusClient("127.0.0.1", 7497, 11, app=fake)
    fake.client = client

    client.connect_readonly(timeout_seconds=5)

    assert client.get_account_mode() == "live"


def test_manual_client_returns_unknown_mode_for_unrecognized_accounts() -> None:
    fake = FakeManualIbapiApp(accounts=("X12345",))
    client = IbapiManualReadonlyStatusClient("127.0.0.1", 7497, 11, app=fake)
    fake.client = client

    client.connect_readonly(timeout_seconds=5)

    assert client.get_account_mode() is None


def test_manual_client_maps_connection_failure() -> None:
    fake = FakeManualIbapiApp(connect_error=RuntimeError("boom"))
    client = IbapiManualReadonlyStatusClient("127.0.0.1", 7497, 11, app=fake)

    with pytest.raises(IbkrTwsReadonlyAdapterError, match="connection_failed"):
        client.connect_readonly(timeout_seconds=5)


def test_manual_client_fails_when_ibapi_not_connected() -> None:
    fake = FakeManualIbapiApp(connected_after_connect=False)
    client = IbapiManualReadonlyStatusClient("127.0.0.1", 7497, 11, app=fake)

    with pytest.raises(IbkrTwsReadonlyAdapterError, match="connection_failed"):
        client.connect_readonly(timeout_seconds=5)
