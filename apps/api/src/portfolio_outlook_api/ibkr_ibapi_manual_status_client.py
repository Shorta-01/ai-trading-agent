from __future__ import annotations

import importlib
import threading
from dataclasses import dataclass
from typing import Any, Protocol, cast

from portfolio_outlook_api.ibkr_ibapi_client_facade import load_ibapi_preflight_modules
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyAdapterError


class _ManualIbapiAppProtocol(Protocol):
    def connect(self, host: str, port: int, client_id: int) -> None: ...

    def isConnected(self) -> bool: ...  # noqa: N802

    def reqManagedAccts(self) -> None: ...  # noqa: N802

    def disconnect(self) -> None: ...


@dataclass
class _SessionState:
    connected: bool = False
    managed_accounts: tuple[str, ...] = ()


class IbapiManualReadonlyStatusClient:
    """Manual read-only IBKR status client for one connect/check/disconnect cycle."""

    def __init__(
        self,
        host: str,
        port: int,
        client_id: int,
        app: _ManualIbapiAppProtocol | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._state = _SessionState()
        self._lock = threading.Lock()
        self._app = app if app is not None else self._build_app()

    def _build_app(self) -> _ManualIbapiAppProtocol:
        load_ibapi_preflight_modules()
        client_module = importlib.import_module("ibapi.client")
        wrapper_module = importlib.import_module("ibapi.wrapper")

        eclient_type = cast(type[Any], getattr(client_module, "EClient"))
        ewrapper_type = cast(type[Any], getattr(wrapper_module, "EWrapper"))

        state = self._state
        lock = self._lock

        class _ManualApp(ewrapper_type, eclient_type):  # type: ignore[misc]
            # ibapi is untyped; subclassing is isolated to this factory boundary.
            def __init__(self) -> None:
                eclient_type.__init__(self, self)

            def managedAccounts(self, accountsList: str) -> None:  # noqa: N802
                accounts = tuple(
                    part.strip() for part in accountsList.split(",") if part.strip()
                )
                with lock:
                    state.managed_accounts = accounts

            def error(
                self,
                reqId: int,
                errorCode: int,
                errorString: str,
                *args: object,
            ) -> None:  # noqa: N803
                if errorCode in {502, 504, 1100}:
                    raise IbkrTwsReadonlyAdapterError("connection_failed")

        return cast(_ManualIbapiAppProtocol, _ManualApp())

    def connect_readonly(self, timeout_seconds: int) -> None:
        try:
            self._app.connect(self._host, self._port, self._client_id)
        except TimeoutError:
            raise
        except Exception as exc:
            raise IbkrTwsReadonlyAdapterError("connection_failed") from exc
        if timeout_seconds <= 0:
            raise TimeoutError("timeout")
        if not self._app.isConnected():
            raise IbkrTwsReadonlyAdapterError("connection_failed")
        self._app.reqManagedAccts()
        with self._lock:
            self._state.connected = True

    def is_connected(self) -> bool:
        return bool(self._app.isConnected())

    def get_account_mode(self) -> str | None:
        with self._lock:
            accounts = self._state.managed_accounts
        if not accounts:
            return None
        if all(account.startswith("DU") for account in accounts):
            return "paper"
        if any(
            account.startswith(prefix)
            for prefix in ("U", "F", "I")
            for account in accounts
        ):
            return "live"
        return None

    def disconnect(self) -> None:
        self._app.disconnect()
