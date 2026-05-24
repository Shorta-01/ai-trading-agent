from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class IbapiDependencyAvailability:
    dependency_name: str
    installed: bool
    import_checked: bool
    safe_modules_checked: tuple[str, ...]
    status: str
    status_nl: str
    help_nl: str
    runtime_connection_enabled: bool = False
    connection_attempted: bool = False
    socket_opened: bool = False
    production_runtime_wired: bool = False


@dataclass(frozen=True)
class IbapiFacadeImportResult:
    imported_modules: tuple[str, ...]
    status: str
    status_nl: str
    help_nl: str
    runtime_connection_enabled: bool = False
    connection_attempted: bool = False
    socket_opened: bool = False
    production_runtime_wired: bool = False


def check_ibapi_dependency_available() -> IbapiDependencyAvailability:
    dependency_name = "ibapi"
    safe_modules_checked = ("ibapi",)
    installed = importlib.util.find_spec(dependency_name) is not None
    if installed:
        return IbapiDependencyAvailability(
            dependency_name=dependency_name,
            installed=True,
            import_checked=False,
            safe_modules_checked=safe_modules_checked,
            status="ibapi_available",
            status_nl="ibapi dependency is beschikbaar",
            help_nl=(
                "Alleen importcontrole, geen verbinding. "
                "Geen TWS/Gateway verbinding geprobeerd. "
                "Geen runtime-wiring actief."
            ),
        )

    return IbapiDependencyAvailability(
        dependency_name=dependency_name,
        installed=False,
        import_checked=False,
        safe_modules_checked=safe_modules_checked,
        status="ibapi_not_available",
        status_nl="ibapi dependency is niet beschikbaar",
        help_nl="Alleen importcontrole, geen verbinding.",
    )


def load_ibapi_preflight_modules() -> IbapiFacadeImportResult:
    module_names = ("ibapi", "ibapi.wrapper")
    imported_names: list[str] = []
    try:
        for module_name in module_names:
            module = importlib.import_module(module_name)
            _assert_module(module, module_name)
            imported_names.append(module_name)
    except Exception:
        return IbapiFacadeImportResult(
            imported_modules=tuple(imported_names),
            status="ibapi_preflight_import_failed",
            status_nl="ibapi preflight import mislukt",
            help_nl="Alleen importcontrole, geen verbinding.",
        )

    return IbapiFacadeImportResult(
        imported_modules=tuple(imported_names),
        status="ibapi_available",
        status_nl="ibapi dependency is beschikbaar",
        help_nl=(
            "Alleen importcontrole, geen verbinding. "
            "Geen TWS/Gateway verbinding geprobeerd."
        ),
    )


def _assert_module(module: ModuleType, expected_name: str) -> None:
    if module.__name__ != expected_name:
        raise ValueError(f"Unexpected module loaded for {expected_name}: {module.__name__}")
