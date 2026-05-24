from __future__ import annotations

import importlib
import importlib.util
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
API_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
API_SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "portfolio_outlook_api"


def test_api_metadata_contains_ibapi_dependency_only() -> None:
    pyproject_text = API_PYPROJECT.read_text(encoding="utf-8")

    assert '"ibapi==9.81.1.post1"' in pyproject_text
    assert "ib_insync" not in pyproject_text
    assert "ib-insync" not in pyproject_text


def test_ibapi_import_succeeds_without_network_connect(monkeypatch) -> None:
    connect_attempted = False

    def _fail_connect(self: socket.socket, address: object) -> None:
        nonlocal connect_attempted
        connect_attempted = True
        raise AssertionError(f"unexpected socket connect attempt during ibapi import: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", _fail_connect)

    assert importlib.util.find_spec("ibapi") is not None

    ibapi_module = importlib.import_module("ibapi")
    ibapi_wrapper_module = importlib.import_module("ibapi.wrapper")

    assert ibapi_module is not None
    assert ibapi_wrapper_module is not None
    assert connect_attempted is False


def test_no_production_runtime_ibkr_client_imports_yet() -> None:
    disallowed_tokens = ("from ibapi", "import ibapi", "from ib_insync", "import ib_insync")

    for file_path in API_SRC_DIR.rglob("*.py"):
        source = file_path.read_text(encoding="utf-8")
        for token in disallowed_tokens:
            assert token not in source, f"{token} found in production source file: {file_path}"


def test_repository_does_not_introduce_ib_insync() -> None:
    disallowed_tokens = ("ib_insync", "ib-insync")
    allowed_files = {
        Path("apps/api/tests/test_ibkr_client_dependency_preflight.py"),
        Path("docs/product/ibkr-tws-client-dependency-ci-preflight-task-150.md"),
    }

    for file_path in REPO_ROOT.rglob("*.py"):
        if ".venv" in file_path.parts:
            continue
        relative = file_path.relative_to(REPO_ROOT)
        if relative in allowed_files:
            continue
        source = file_path.read_text(encoding="utf-8")
        for token in disallowed_tokens:
            assert token not in source, f"{token} unexpectedly found in: {relative}"
