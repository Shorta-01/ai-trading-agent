from __future__ import annotations

import importlib
import importlib.util
import re
import socket
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
API_PYPROJECT = API_ROOT / "pyproject.toml"


DEPENDENCY_PATTERN_TEMPLATE = r'^[ \t]*"{dependency}(?:[<>=!~][^"\\]*)?"[ \t]*(?:,|$)'


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _iter_project_metadata_files() -> Iterator[Path]:
    root_pyproject = REPO_ROOT / "pyproject.toml"
    if root_pyproject.exists():
        yield root_pyproject

    for base_dir in (REPO_ROOT / "apps", REPO_ROOT / "packages"):
        yield from sorted(base_dir.rglob("pyproject.toml"))


def _iter_production_source_files() -> Iterator[Path]:
    source_roots = [
        REPO_ROOT / "apps" / "api" / "src",
        REPO_ROOT / "apps" / "worker" / "src",
        REPO_ROOT / "packages" / "domain" / "src",
        REPO_ROOT / "packages" / "storage" / "src",
        REPO_ROOT / "packages" / "portfolio" / "src",
    ]
    for source_root in source_roots:
        if not source_root.exists():
            continue
        yield from sorted(source_root.rglob("*.py"))


def _metadata_contains_dependency(metadata_text: str, dependency_name: str) -> bool:
    dependency_pattern = DEPENDENCY_PATTERN_TEMPLATE.format(
        dependency=re.escape(dependency_name)
    )
    return re.search(dependency_pattern, metadata_text, flags=re.MULTILINE) is not None


def test_api_metadata_includes_ibapi_dependency() -> None:
    pyproject_text = _read_text(API_PYPROJECT)

    assert _metadata_contains_dependency(pyproject_text, "ibapi")


def test_project_metadata_does_not_include_ib_insync_dependency() -> None:
    for metadata_path in _iter_project_metadata_files():
        metadata_text = _read_text(metadata_path)
        assert not _metadata_contains_dependency(metadata_text, "ib_insync")
        assert not _metadata_contains_dependency(metadata_text, "ib-insync")


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


def test_production_runtime_source_only_allows_ibapi_in_facade() -> None:
    disallowed_tokens = ("from ibapi", "import ibapi")
    allowed_files = {
        (
            REPO_ROOT
            / "apps"
            / "api"
            / "src"
            / "portfolio_outlook_api"
            / "ibkr_ibapi_client_facade.py"
        ).resolve(),
        (
            REPO_ROOT
            / "apps"
            / "api"
            / "src"
            / "portfolio_outlook_api"
            / "ibkr_ibapi_manual_status_client.py"
        ).resolve(),
        (
            REPO_ROOT
            / "apps"
            / "api"
            / "src"
            / "portfolio_outlook_api"
            / "ibkr_ibapi_account_snapshot_client.py"
        ).resolve(),
    }

    for file_path in _iter_production_source_files():
        source = _read_text(file_path)
        for token in disallowed_tokens:
            if token not in source:
                continue
            assert file_path.resolve() in allowed_files, (
                f"{token} found outside isolated facade: {file_path}"
            )


def test_production_runtime_source_does_not_import_ib_insync() -> None:
    disallowed_tokens = ("from ib_insync", "import ib_insync")

    for file_path in _iter_production_source_files():
        source = _read_text(file_path)
        for token in disallowed_tokens:
            assert token not in source, f"{token} found in production source file: {file_path}"
