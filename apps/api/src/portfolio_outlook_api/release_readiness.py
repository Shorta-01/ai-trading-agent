"""V1 / V1.1 release-readiness scorecard (Slices 22 + 34).

Aggregates the per-leg `<x>_sync_enabled` flags + EODHD key presence
+ scheduler state + IBKR session reachability into a single Dutch
summary with a stable list of blocker codes. Pure Python; no I/O. The
route reads ``settings`` and hands the values to
:func:`compute_release_readiness`; tests pass ad-hoc settings shapes.

The scorecard is informational: a green scorecard never authorises an
order. Manual approval gate stays; safety booleans hard-False on the
response.

V1.1 (Slice 34) extends the scorecard with five new blocker codes
covering the §22 surface: ensemble weight strategy, predictor
backtesting, real Claude AI provider key, monthly budget cap (live
check via the ``claude_ai_budget_usage`` audit table), and the
operator-selectable universe set. The budget gate runs only when the
caller threads a ``budget_repo`` through; existing callers stay
backward-compatible by passing ``budget_repo=None``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from ai_trading_agent_storage import ClaudeAiBudgetUsageRecord

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

# V1.1 Slice 34: §22 surface blockers.
BLOCKER_ENSEMBLE_WEIGHT_STRATEGY_INVALID: Final = "ensemble_weight_strategy_invalid"
BLOCKER_PREDICTOR_BACKTEST_DISABLED: Final = "predictor_backtest_disabled"
BLOCKER_CLAUDE_AI_API_KEY_MISSING_WHEN_REAL_CLIENT_ENABLED: Final = (
    "claude_ai_api_key_missing_when_real_client_enabled"
)
BLOCKER_CLAUDE_AI_BUDGET_EXCEEDED: Final = "claude_ai_budget_exceeded"
BLOCKER_UNIVERSE_SET_UNKNOWN: Final = "universe_set_unknown"

# Locked V1.1 enumerations consumed by the V1.1 checks.
_LOCKED_ENSEMBLE_WEIGHT_STRATEGIES: Final[frozenset[str]] = frozenset(
    {"equal_weight", "auto"}
)
_LOCKED_UNIVERSE_SETS: Final[frozenset[str]] = frozenset(
    {"SP500", "EU600", "ALL_5K"}
)


STATUS_READY: Final = "ready"
STATUS_BLOCKED: Final = "blocked"


class _BudgetRepoProtocol(Protocol):
    """Matches :class:`claude_ai_budget._BudgetRepoProtocol`.

    Declared locally so the readiness module stays loadable in
    stub-only contexts; structurally identical so the readiness
    check can hand the same repo through to
    :func:`monthly_budget_status`.
    """

    def monthly_total_eur(self, budget_month: str) -> Decimal: ...

    def save_usage(self, record: ClaudeAiBudgetUsageRecord) -> object: ...


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


def _v1_1_checks(
    runtime_settings: object,
    *,
    budget_repo: _BudgetRepoProtocol | None,
) -> Iterable[ReadinessCheck]:
    """V1.1 §22-surface checks (Slice 34).

    Five blockers: ensemble strategy locked set, backtesting opt-in,
    real Claude key present when the real provider is on, monthly
    budget cap not breached (live check via ``budget_repo`` — skipped
    when no repo is threaded), universe set inside the locked frozen
    set.
    """

    ensemble_strategy = str(
        getattr(runtime_settings, "ensemble_weight_strategy", "equal_weight")
    )
    yield _check(
        BLOCKER_ENSEMBLE_WEIGHT_STRATEGY_INVALID,
        passed=ensemble_strategy in _LOCKED_ENSEMBLE_WEIGHT_STRATEGIES,
        detail_nl=(
            f"Ensemble-strategie `{ensemble_strategy}` zit in de "
            "locked set (`equal_weight` of `auto`)."
            if ensemble_strategy in _LOCKED_ENSEMBLE_WEIGHT_STRATEGIES
            else (
                f"`ENSEMBLE_WEIGHT_STRATEGY={ensemble_strategy}` zit buiten "
                "de locked set. Kies `equal_weight` (V1-gedrag) of `auto` "
                "(inverse-Brier weging)."
            )
        ),
    )

    backtest_enabled = bool(
        getattr(runtime_settings, "predictor_backtest_enabled", False)
    )
    yield _check(
        BLOCKER_PREDICTOR_BACKTEST_DISABLED,
        passed=backtest_enabled,
        detail_nl=(
            "Predictor-backtesting actief — de leaderboard krijgt "
            "verse Brier-scores en de auto-weights kunnen draaien."
            if backtest_enabled
            else (
                "Stel `PREDICTOR_BACKTEST_ENABLED=true` in zodat de "
                "morning chain backtest-rijen voor de leaderboard "
                "kan persisteren."
            )
        ),
    )

    real_client_enabled = bool(
        getattr(runtime_settings, "ai_explanation_real_client_enabled", False)
    ) or bool(
        getattr(runtime_settings, "ai_ts_predictor_real_client_enabled", False)
    )
    api_key = getattr(runtime_settings, "claude_ai_api_key", None)
    api_key_ok = bool(api_key) if real_client_enabled else True
    yield _check(
        BLOCKER_CLAUDE_AI_API_KEY_MISSING_WHEN_REAL_CLIENT_ENABLED,
        passed=api_key_ok,
        detail_nl=(
            "Claude AI API-sleutel aanwezig voor de actieve real-client "
            "paden."
            if api_key_ok
            else (
                "De real Anthropic-client staat aan maar `CLAUDE_AI_API_KEY` "
                "ontbreekt. Stel de sleutel in of zet de real-client toggle "
                "uit (de stub blijft werken)."
            )
        ),
    )

    universe_set = str(
        getattr(runtime_settings, "universe_set", "SP500")
    )
    yield _check(
        BLOCKER_UNIVERSE_SET_UNKNOWN,
        passed=universe_set in _LOCKED_UNIVERSE_SETS,
        detail_nl=(
            f"`UNIVERSE_SET={universe_set}` zit in de locked set "
            "(`SP500`, `EU600`, `ALL_5K`)."
            if universe_set in _LOCKED_UNIVERSE_SETS
            else (
                f"`UNIVERSE_SET={universe_set}` zit buiten de locked set. "
                "Kies `SP500` (default), `EU600` of `ALL_5K`."
            )
        ),
    )

    if budget_repo is None:
        # Backward-compat path: no repo threaded, no live budget check.
        # The cap is informational only in this branch.
        return
    monthly_cap_eur = getattr(
        runtime_settings, "claude_ai_budget_monthly_eur", Decimal("50")
    )
    # Use the shared helper so behaviour stays in lockstep with the
    # provider's own enforcement (same month tag, same Decimal math).
    from portfolio_outlook_api.claude_ai_budget import monthly_budget_status

    status = monthly_budget_status(
        repo=budget_repo, monthly_cap_eur=monthly_cap_eur
    )
    yield _check(
        BLOCKER_CLAUDE_AI_BUDGET_EXCEEDED,
        passed=not status.exceeded,
        detail_nl=(
            f"Claude AI budget binnen cap voor {status.budget_month} "
            f"(€{status.monthly_total_eur:.2f} / €{monthly_cap_eur})."
            if not status.exceeded
            else (
                f"Claude AI maand-cap bereikt voor {status.budget_month} "
                f"(€{status.monthly_total_eur:.2f} ≥ €{monthly_cap_eur}); "
                "de real provider valt terug op de stub."
            )
        ),
    )


def compute_release_readiness(
    runtime_settings: object,
    *,
    budget_repo: _BudgetRepoProtocol | None = None,
) -> ReleaseReadinessReport:
    """Aggregate the V1 + V1.1 release-readiness scorecard.

    The function intentionally consumes ``runtime_settings`` via
    duck-typing (only ``getattr`` reads) so tests can pass ad-hoc
    namespaces / dataclasses without depending on the full FastAPI
    settings tree.

    ``budget_repo`` is the optional V1.1 plumbing for the
    ``claude_ai_budget_exceeded`` gate. When ``None`` (the default,
    matching every V1 caller), the budget gate is skipped and the
    scorecard reports the other 19 V1+V1.1 checks. When the route
    threads a real repo through, the gate runs against the
    ``claude_ai_budget_usage`` audit table.
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
    checks.extend(_v1_1_checks(runtime_settings, budget_repo=budget_repo))

    blockers = tuple(c.code for c in checks if not c.passed)
    ready = not blockers
    status = STATUS_READY if ready else STATUS_BLOCKED
    summary_nl = (
        "V1.1 is klaar voor productie."
        if ready
        else f"V1.1 nog niet klaar — {len(blockers)} blocker(s) actief."
    )
    help_nl = (
        "Alle vereiste vlaggen staan aan, EODHD + IBKR zijn geconfigureerd, "
        "opslag is schrijfbaar en de scheduler vuurt de morning chain. "
        "De §22-rebuild knoppen (ensemble-strategie, backtest, Claude AI, "
        "universe-set) zitten binnen de locked set. De manuele approval-gate "
        "blijft van kracht; geen order vertrekt automatisch."
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
    "BLOCKER_CLAUDE_AI_API_KEY_MISSING_WHEN_REAL_CLIENT_ENABLED",
    "BLOCKER_CLAUDE_AI_BUDGET_EXCEEDED",
    "BLOCKER_DAILY_BRIEFING_SYNC_DISABLED",
    "BLOCKER_DECISION_PACKAGES_SYNC_DISABLED",
    "BLOCKER_ENSEMBLE_WEIGHT_STRATEGY_INVALID",
    "BLOCKER_EODHD_API_KEY_MISSING",
    "BLOCKER_EODHD_NOT_CONFIGURED",
    "BLOCKER_FORECAST_SYNC_DISABLED",
    "BLOCKER_IBKR_NOT_ENABLED",
    "BLOCKER_IBKR_SYNC_NOT_ENABLED",
    "BLOCKER_MARKET_DATA_SYNC_DISABLED",
    "BLOCKER_PREDICTION_DIARY_SYNC_DISABLED",
    "BLOCKER_PREDICTOR_BACKTEST_DISABLED",
    "BLOCKER_RECONCILIATION_SYNC_DISABLED",
    "BLOCKER_SCHEDULER_DISABLED",
    "BLOCKER_STORAGE_NOT_CONFIGURED",
    "BLOCKER_STORAGE_NOT_WRITABLE",
    "BLOCKER_SUGGESTIONS_SYNC_DISABLED",
    "BLOCKER_UNIVERSE_SET_UNKNOWN",
    "STATUS_BLOCKED",
    "STATUS_READY",
    "ReadinessCheck",
    "ReleaseReadinessReport",
    "compute_release_readiness",
    "serialize_release_readiness",
]
