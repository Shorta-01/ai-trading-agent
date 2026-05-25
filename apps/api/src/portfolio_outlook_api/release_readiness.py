"""V1 release-readiness scorecard (Slice 22).

Aggregates the per-leg `<x>_sync_enabled` flags + EODHD key presence
+ scheduler state + IBKR session reachability into a single Dutch
summary with a stable list of blocker codes. Pure Python; no I/O. The
route reads ``settings`` and hands the values to
:func:`compute_release_readiness`; tests pass ad-hoc settings shapes.

The scorecard is informational: a green scorecard never authorises an
order. Manual approval gate stays; safety booleans hard-False on the
response.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

# Stable blocker codes. Kept in one place so the UI can localise them
# without touching the backend.
BLOCKER_STORAGE_NOT_CONFIGURED: Final = "storage_not_configured"
BLOCKER_STORAGE_NOT_WRITABLE: Final = "storage_not_writable"
BLOCKER_EODHD_NOT_CONFIGURED: Final = "eodhd_not_configured"
BLOCKER_EODHD_API_KEY_MISSING: Final = "eodhd_api_key_missing"
BLOCKER_IBKR_NOT_ENABLED: Final = "ibkr_not_enabled"
BLOCKER_IBKR_SYNC_NOT_ENABLED: Final = "ibkr_sync_not_enabled"
BLOCKER_SCHEDULER_DISABLED: Final = "scheduler_disabled"
BLOCKER_MARKET_DATA_SYNC_DISABLED: Final = "market_data_sync_disabled"
BLOCKER_FORECAST_SYNC_DISABLED: Final = "forecast_sync_disabled"
BLOCKER_SUGGESTIONS_SYNC_DISABLED: Final = "suggestions_sync_disabled"
BLOCKER_DECISION_PACKAGES_SYNC_DISABLED: Final = "decision_packages_sync_disabled"
BLOCKER_ACTION_DRAFTS_SYNC_DISABLED: Final = "action_drafts_sync_disabled"
BLOCKER_DAILY_BRIEFING_SYNC_DISABLED: Final = "daily_briefing_sync_disabled"
BLOCKER_RECONCILIATION_SYNC_DISABLED: Final = "reconciliation_sync_disabled"
BLOCKER_PREDICTION_DIARY_SYNC_DISABLED: Final = "prediction_diary_sync_disabled"


STATUS_READY: Final = "ready"
STATUS_BLOCKED: Final = "blocked"


@dataclass(frozen=True)
class ReadinessCheck:
    """One named readiness check + outcome."""

    code: str
    passed: bool
    detail_nl: str


@dataclass(frozen=True)
class ReleaseReadinessReport:
    """Aggregated V1 release-readiness outcome."""

    status: str  # ready | blocked
    summary_nl: str
    help_nl: str
    blockers: tuple[str, ...]
    checks: tuple[ReadinessCheck, ...]


def _check(code: str, passed: bool, detail_nl: str) -> ReadinessCheck:
    return ReadinessCheck(code=code, passed=passed, detail_nl=detail_nl)


def _storage_checks(storage: object) -> Iterable[ReadinessCheck]:
    enabled = bool(getattr(storage, "enabled", False))
    db_url = getattr(storage, "database_url", None)
    writes = bool(getattr(storage, "writes_enabled", False))
    yield _check(
        BLOCKER_STORAGE_NOT_CONFIGURED,
        passed=enabled and bool(db_url),
        detail_nl=(
            "Opslag actief met geconfigureerde database-URL."
            if enabled and bool(db_url)
            else "Stel `STORAGE_ENABLED=true` + `STORAGE_DATABASE_URL=...` in."
        ),
    )
    yield _check(
        BLOCKER_STORAGE_NOT_WRITABLE,
        passed=writes,
        detail_nl=(
            "Schrijfrechten op opslag actief."
            if writes
            else "Stel `STORAGE_WRITES_ENABLED=true` in zodat de chain audit-rijen kan opslaan."
        ),
    )


def _eodhd_checks(runtime_settings: object) -> Iterable[ReadinessCheck]:
    enabled = bool(getattr(runtime_settings, "eodhd_enabled", False))
    api_key = getattr(runtime_settings, "eodhd_api_key", None)
    yield _check(
        BLOCKER_EODHD_NOT_CONFIGURED,
        passed=enabled,
        detail_nl=(
            "EODHD-provider actief."
            if enabled
            else "Stel `EODHD_ENABLED=true` in voor market-data + fundamentals."
        ),
    )
    yield _check(
        BLOCKER_EODHD_API_KEY_MISSING,
        passed=bool(api_key),
        detail_nl=(
            "EODHD API-sleutel aanwezig."
            if api_key
            else "Stel `EODHD_API_KEY=...` in (verplicht voor EODHD-aanroepen)."
        ),
    )


def _ibkr_checks(runtime_settings: object) -> Iterable[ReadinessCheck]:
    ibkr_enabled = bool(getattr(runtime_settings, "ibkr_enabled", False))
    ibkr_sync_enabled = bool(getattr(runtime_settings, "ibkr_sync_enabled", False))
    yield _check(
        BLOCKER_IBKR_NOT_ENABLED,
        passed=ibkr_enabled,
        detail_nl=(
            "IBKR-integratie actief."
            if ibkr_enabled
            else "Stel `IBKR_ENABLED=true` in om de paper-account te koppelen."
        ),
    )
    yield _check(
        BLOCKER_IBKR_SYNC_NOT_ENABLED,
        passed=ibkr_sync_enabled,
        detail_nl=(
            "IBKR read-only sync actief — positie/kasstroom worden gespiegeld."
            if ibkr_sync_enabled
            else "Stel `IBKR_SYNC_ENABLED=true` in zodat de chain de paper-state ziet."
        ),
    )


def _scheduler_checks(runtime_settings: object) -> Iterable[ReadinessCheck]:
    scheduler_enabled = bool(getattr(runtime_settings, "scheduler_enabled", False))
    yield _check(
        BLOCKER_SCHEDULER_DISABLED,
        passed=scheduler_enabled,
        detail_nl=(
            "APScheduler actief — morning chain wordt om 06:30 (Europe/Brussels) gevuurd."
            if scheduler_enabled
            else "Stel `SCHEDULER_ENABLED=true` in zodat de 06:30 morning chain automatisch draait."
        ),
    )


_MORNING_CHAIN_LEG_CHECKS: Final[tuple[tuple[str, str, str], ...]] = (
    # (settings_attribute, blocker_code, leg_label)
    ("market_data_sync_enabled", BLOCKER_MARKET_DATA_SYNC_DISABLED, "Market-data sync"),
    ("forecast_sync_enabled", BLOCKER_FORECAST_SYNC_DISABLED, "Forecast sync"),
    ("suggestions_sync_enabled", BLOCKER_SUGGESTIONS_SYNC_DISABLED, "Suggesties"),
    (
        "decision_packages_sync_enabled",
        BLOCKER_DECISION_PACKAGES_SYNC_DISABLED,
        "Decision Packages",
    ),
    (
        "action_drafts_sync_enabled",
        BLOCKER_ACTION_DRAFTS_SYNC_DISABLED,
        "Action drafts",
    ),
    (
        "daily_briefing_sync_enabled",
        BLOCKER_DAILY_BRIEFING_SYNC_DISABLED,
        "Dagbriefing",
    ),
)

_AUDIT_LEG_CHECKS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "reconciliation_sync_enabled",
        BLOCKER_RECONCILIATION_SYNC_DISABLED,
        "Reconciliatie",
    ),
    (
        "prediction_diary_sync_enabled",
        BLOCKER_PREDICTION_DIARY_SYNC_DISABLED,
        "Prediction Diary",
    ),
)


def _morning_chain_checks(runtime_settings: object) -> Iterable[ReadinessCheck]:
    for attr, code, label in _MORNING_CHAIN_LEG_CHECKS:
        enabled = bool(getattr(runtime_settings, attr, False))
        yield _check(
            code,
            passed=enabled,
            detail_nl=(
                f"{label}: leg actief in morning chain."
                if enabled
                else f"{label}: stel `{attr.upper()}=true` in om de leg uit te voeren."
            ),
        )


def _audit_checks(runtime_settings: object) -> Iterable[ReadinessCheck]:
    for attr, code, label in _AUDIT_LEG_CHECKS:
        enabled = bool(getattr(runtime_settings, attr, False))
        yield _check(
            code,
            passed=enabled,
            detail_nl=(
                f"{label}: audit-pad actief."
                if enabled
                else (
                    f"{label}: stel `{attr.upper()}=true` in voor het audit-pad "
                    "(fill-reconciliatie + Diary)."
                )
            ),
        )


def compute_release_readiness(runtime_settings: object) -> ReleaseReadinessReport:
    """Aggregate the V1 release-readiness scorecard from ``runtime_settings``.

    The function intentionally consumes ``runtime_settings`` via
    duck-typing (only ``getattr`` reads) so tests can pass ad-hoc
    namespaces / dataclasses without depending on the full FastAPI
    settings tree.
    """

    storage = getattr(runtime_settings, "storage", None)
    checks: list[ReadinessCheck] = []
    if storage is not None:
        checks.extend(_storage_checks(storage))
    else:
        checks.append(
            _check(
                BLOCKER_STORAGE_NOT_CONFIGURED,
                passed=False,
                detail_nl="`settings.storage` ontbreekt; configureer opslag.",
            )
        )
    checks.extend(_eodhd_checks(runtime_settings))
    checks.extend(_ibkr_checks(runtime_settings))
    checks.extend(_scheduler_checks(runtime_settings))
    checks.extend(_morning_chain_checks(runtime_settings))
    checks.extend(_audit_checks(runtime_settings))

    blockers = tuple(c.code for c in checks if not c.passed)
    ready = not blockers
    status = STATUS_READY if ready else STATUS_BLOCKED
    summary_nl = (
        "V1 is klaar voor productie."
        if ready
        else f"V1 nog niet klaar — {len(blockers)} blocker(s) actief."
    )
    help_nl = (
        "Alle vereiste vlaggen staan aan, EODHD + IBKR zijn geconfigureerd, "
        "opslag is schrijfbaar en de scheduler vuurt de morning chain. "
        "De manuele approval-gate blijft van kracht; geen order vertrekt "
        "automatisch."
        if ready
        else (
            "Werk de blockers in volgorde af. Elk blocker-code mapt op een "
            "settings-vlag in `apps/api/src/portfolio_outlook_api/config.py`."
        )
    )
    return ReleaseReadinessReport(
        status=status,
        summary_nl=summary_nl,
        help_nl=help_nl,
        blockers=blockers,
        checks=tuple(checks),
    )


def serialize_release_readiness(
    report: ReleaseReadinessReport,
) -> dict[str, object]:
    """JSON-friendly serialisation for the ``GET /v1/release-readiness`` route."""

    return {
        "status": report.status,
        "summary_nl": report.summary_nl,
        "help_nl": report.help_nl,
        "blockers": list(report.blockers),
        "checks": [
            {
                "code": check.code,
                "passed": check.passed,
                "detail_nl": check.detail_nl,
            }
            for check in report.checks
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


__all__ = [
    "BLOCKER_ACTION_DRAFTS_SYNC_DISABLED",
    "BLOCKER_DAILY_BRIEFING_SYNC_DISABLED",
    "BLOCKER_DECISION_PACKAGES_SYNC_DISABLED",
    "BLOCKER_EODHD_API_KEY_MISSING",
    "BLOCKER_EODHD_NOT_CONFIGURED",
    "BLOCKER_FORECAST_SYNC_DISABLED",
    "BLOCKER_IBKR_NOT_ENABLED",
    "BLOCKER_IBKR_SYNC_NOT_ENABLED",
    "BLOCKER_MARKET_DATA_SYNC_DISABLED",
    "BLOCKER_PREDICTION_DIARY_SYNC_DISABLED",
    "BLOCKER_RECONCILIATION_SYNC_DISABLED",
    "BLOCKER_SCHEDULER_DISABLED",
    "BLOCKER_STORAGE_NOT_CONFIGURED",
    "BLOCKER_STORAGE_NOT_WRITABLE",
    "BLOCKER_SUGGESTIONS_SYNC_DISABLED",
    "STATUS_BLOCKED",
    "STATUS_READY",
    "ReadinessCheck",
    "ReleaseReadinessReport",
    "compute_release_readiness",
    "serialize_release_readiness",
]
