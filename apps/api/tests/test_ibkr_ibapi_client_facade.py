from __future__ import annotations

import importlib
import socket
import sys
from pathlib import Path

from portfolio_outlook_api.ibkr_ibapi_client_facade import (
    check_ibapi_dependency_available,
    load_ibapi_preflight_modules,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_facade_module_import_has_no_top_level_ibapi_import() -> None:
    sys.modules.pop("portfolio_outlook_api.ibkr_ibapi_client_facade", None)
    preexisting_ibapi = sys.modules.get("ibapi")

    importlib.import_module("portfolio_outlook_api.ibkr_ibapi_client_facade")

    if preexisting_ibapi is None:
        assert "ibapi" not in sys.modules


def test_check_ibapi_dependency_available_reports_safe_flags() -> None:
    result = check_ibapi_dependency_available()

    assert result.dependency_name == "ibapi"
    assert result.installed is True
    assert result.status == "ibapi_available"
    assert result.runtime_connection_enabled is False
    assert result.connection_attempted is False
    assert result.socket_opened is False
    assert result.production_runtime_wired is False


def test_load_ibapi_preflight_modules_imports_safely_without_connect(monkeypatch) -> None:
    connect_attempted = False

    def _fail_connect(self: socket.socket, address: object) -> None:
        nonlocal connect_attempted
        connect_attempted = True
        raise AssertionError(f"unexpected socket connect attempt: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", _fail_connect)

    result = load_ibapi_preflight_modules()

    assert result.status == "ibapi_available"
    assert result.imported_modules == ("ibapi", "ibapi.wrapper")
    assert result.runtime_connection_enabled is False
    assert result.connection_attempted is False
    assert result.socket_opened is False
    assert result.production_runtime_wired is False
    assert connect_attempted is False


def test_no_runtime_or_route_wiring_to_ibapi_facade() -> None:
    checked_files = (
        REPO_ROOT / "apps/api/src/portfolio_outlook_api/status_routes.py",
        REPO_ROOT / "apps/api/src/portfolio_outlook_api/ibkr_tws_readonly_runtime.py",
        REPO_ROOT / "apps/api/src/portfolio_outlook_api/ibkr_session_adapter_factory.py",
    )

    for path in checked_files:
        source = path.read_text(encoding="utf-8")
        assert "ibkr_ibapi_client_facade" not in source
