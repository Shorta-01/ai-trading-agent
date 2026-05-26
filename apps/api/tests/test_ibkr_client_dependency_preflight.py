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


def test_project_metadata_only_allows_ib_insync_in_worker() -> None:
    """Task 126 product lock §1: the worker is the sole owner of the
    TWS API session, so ``ib_insync`` is allowed in ``apps/worker``
    but blocked everywhere else. The API + packages stay on
    ``ibapi``-via-facade.
    """

    worker_pyproject = REPO_ROOT / "apps" / "worker" / "pyproject.toml"
    for metadata_path in _iter_project_metadata_files():
        metadata_text = _read_text(metadata_path)
        contains = _metadata_contains_dependency(
            metadata_text, "ib_insync"
        ) or _metadata_contains_dependency(metadata_text, "ib-insync")
        if metadata_path.resolve() == worker_pyproject.resolve():
            assert contains, (
                "Task 126 expects apps/worker/pyproject.toml to declare ib_insync."
            )
            continue
        assert not contains, (
            f"ib_insync should only live in apps/worker; found in {metadata_path}"
        )


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


def test_production_runtime_source_only_allows_ib_insync_in_worker_gateway() -> None:
    """Task 126 + Task 134a — ``ib_insync`` imports live only in the
    worker's two intentional integration points:

    * ``ibkr_gateway.py`` (Task 126): the long-lived TWS session +
      account-mode detection.
    * ``ibkr_submission/order_builder.py`` (Task 134a): the locked
      Decimal → float boundary that builds the ``Contract`` + ``Order``
      pair for ``placeOrder()``. The import is lazy (inside the
      function body), but the source-scan looks for the text so the
      allowlist must include it.

    Every other production file must stay free of the SDK.
    """

    disallowed_tokens = ("from ib_insync", "import ib_insync")
    allowed_files = {
        (
            REPO_ROOT
            / "apps"
            / "worker"
            / "src"
            / "portfolio_outlook_worker"
            / "ibkr_gateway.py"
        ).resolve(),
        (
            REPO_ROOT
            / "apps"
            / "worker"
            / "src"
            / "portfolio_outlook_worker"
            / "ibkr_submission"
            / "order_builder.py"
        ).resolve(),
    }

    for file_path in _iter_production_source_files():
        source = _read_text(file_path)
        for token in disallowed_tokens:
            if token not in source:
                continue
            assert file_path.resolve() in allowed_files, (
                f"{token} found outside the worker gateway: {file_path}"
            )
