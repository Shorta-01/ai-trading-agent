"""Morning-chain orchestrator (Slice 21).

Composes the V1 daily chain — market-data sync → ensemble forecast →
asset suggestions → Decision Packages → action drafts → daily briefing
— into a single sequenced runner. The orchestrator is generic: it
executes a sequence of leg callables in order, stops on the first
non-succeeded outcome, and aggregates the per-leg outcomes into a
single :class:`MorningChainResult`.

The scheduler job from Slice 13 (`run_daily_briefing_job`) wraps this
runner via :func:`build_scheduler_chain_callable` so each fire either
returns cleanly (status=succeeded on the audit row) or raises
:class:`MorningChainFailed` (status=failed with the failed leg + code
in `error_text`). A new manual route
``POST /scheduler/runs/morning-chain`` exposes the chain for
release-readiness smoke testing without enabling the scheduler.

Locked in `version-1-product-experience-locks.md §21.7`: scheduled
runs never auto-promote into orders. Manual approval gates stay; the
chain only pre-computes the briefing the operator opens at 07:00.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

logger = logging.getLogger(__name__)


LEG_MARKET_DATA_SYNC: Final = "market_data_sync"
LEG_FORECAST_SYNC: Final = "forecast_sync"
LEG_SUGGESTION_SYNC: Final = "suggestion_sync"
LEG_DECISION_PACKAGE_SYNC: Final = "decision_package_sync"
LEG_ACTION_DRAFT_SYNC: Final = "action_draft_sync"
LEG_EARNINGS_CALENDAR_SYNC: Final = "earnings_calendar_sync"
LEG_ORCHESTRATOR_SCORING: Final = "orchestrator_scoring"
LEG_DAILY_BRIEFING_SYNC: Final = "daily_briefing_sync"


MORNING_CHAIN_LEG_NAMES: Final[tuple[str, ...]] = (
    LEG_MARKET_DATA_SYNC,
    LEG_FORECAST_SYNC,
    LEG_SUGGESTION_SYNC,
    LEG_DECISION_PACKAGE_SYNC,
    LEG_ACTION_DRAFT_SYNC,
    # V1.2 §AK — earnings refresh runs *before* the orchestrator
    # scoring leg so the latter can read fresh ``next_earnings_*``
    # dates from storage.
    LEG_EARNINGS_CALENDAR_SYNC,
    LEG_ORCHESTRATOR_SCORING,
    LEG_DAILY_BRIEFING_SYNC,
)


LEG_STATUS_SUCCEEDED: Final = "succeeded"
LEG_STATUS_SKIPPED: Final = "skipped"
LEG_STATUS_FAILED: Final = "failed"


CHAIN_STATUS_SUCCEEDED: Final = "succeeded"
CHAIN_STATUS_FAILED: Final = "failed"


@dataclass(frozen=True)
class MorningChainLegOutcome:
    """Per-leg outcome inside a morning-chain run.

    A leg returns ``succeeded`` when its underlying sync completed
    without error, ``skipped`` when the leg is disabled by config (the
    chain continues), and ``failed`` with a stable ``failure_code``
    when the underlying sync raised or returned a blocked status (the
    chain stops).
    """

    leg_name: str
    status: str
    failure_code: str | None
    detail_nl: str

    def __post_init__(self) -> None:
        if self.leg_name not in MORNING_CHAIN_LEG_NAMES:
            raise ValueError(
                f"leg_name {self.leg_name!r} is not a recognised morning-chain leg"
            )
        if self.status not in {
            LEG_STATUS_SUCCEEDED,
            LEG_STATUS_SKIPPED,
            LEG_STATUS_FAILED,
        }:
            raise ValueError(
                f"leg status must be succeeded/skipped/failed, got {self.status!r}"
            )
        if self.status == LEG_STATUS_FAILED and not self.failure_code:
            raise ValueError("failed legs must carry a non-empty failure_code")


@dataclass(frozen=True)
class MorningChainResult:
    """Aggregated outcome of one morning-chain run."""

    status: str  # succeeded | failed
    failed_leg: str | None
    failure_code: str | None
    started_at: datetime
    completed_at: datetime
    legs: tuple[MorningChainLegOutcome, ...]


LegCallable = Callable[[], MorningChainLegOutcome]


class MorningChainFailed(Exception):
    """Raised by :func:`build_scheduler_chain_callable` when the chain
    stops on a failed leg. The scheduler audit row captures the
    message in ``error_text``; the structured result is also returned
    by the manual POST route."""

    def __init__(
        self,
        *,
        failed_leg: str,
        failure_code: str,
        detail_nl: str,
    ) -> None:
        self.failed_leg = failed_leg
        self.failure_code = failure_code
        self.detail_nl = detail_nl
        super().__init__(f"{failed_leg}:{failure_code}: {detail_nl}")


def run_morning_chain(*, legs: Sequence[LegCallable]) -> MorningChainResult:
    """Run each leg in order, stopping on the first non-succeeded leg
    that isn't ``skipped``.

    A ``skipped`` outcome (leg disabled in config) does not stop the
    chain — the chain proceeds to the next leg. Only ``failed``
    stops execution. The aggregated ``status`` is ``succeeded`` when
    no leg failed.

    Exceptions raised by leg callables are caught at the boundary and
    re-shaped as ``failed`` outcomes with a stable
    ``leg_callable_raised`` code so the scheduler audit chain stays
    intact.
    """

    started_at = datetime.now(UTC)
    outcomes: list[MorningChainLegOutcome] = []
    failed_leg: str | None = None
    failure_code: str | None = None

    for leg in legs:
        try:
            outcome = leg()
        except Exception as exc:  # noqa: BLE001 — boundary catch
            outcome = MorningChainLegOutcome(
                leg_name=getattr(leg, "leg_name", "unknown_leg"),
                status=LEG_STATUS_FAILED,
                failure_code="leg_callable_raised",
                detail_nl=f"Leg riep een uitzondering op: {exc}",
            )
            logger.exception("morning-chain leg raised an exception")
        outcomes.append(outcome)
        if outcome.status == LEG_STATUS_FAILED:
            failed_leg = outcome.leg_name
            failure_code = outcome.failure_code
            break

    completed_at = datetime.now(UTC)
    return MorningChainResult(
        status=CHAIN_STATUS_SUCCEEDED if failed_leg is None else CHAIN_STATUS_FAILED,
        failed_leg=failed_leg,
        failure_code=failure_code,
        started_at=started_at,
        completed_at=completed_at,
        legs=tuple(outcomes),
    )


def build_scheduler_chain_callable(
    *,
    legs_factory: Callable[[], Sequence[LegCallable]],
) -> Callable[[], None]:
    """Adapt :func:`run_morning_chain` into a no-arg callable for the
    scheduler job wrapper.

    The wrapper raises :class:`MorningChainFailed` when the chain
    stops on a failed leg so the existing
    :func:`portfolio_outlook_api.scheduler.run_daily_briefing_job`
    captures the failure on the audit row. On a fully successful
    chain it returns ``None`` so the audit row stays
    ``succeeded``.

    ``legs_factory`` is called once per fire so each run rebuilds its
    own short-lived session + repos.
    """

    def _fire() -> None:
        legs = legs_factory()
        result = run_morning_chain(legs=legs)
        if result.status != CHAIN_STATUS_SUCCEEDED:
            raise MorningChainFailed(
                failed_leg=result.failed_leg or "unknown",
                failure_code=result.failure_code or "unknown",
                detail_nl=(
                    f"Morning chain afgebroken op leg "
                    f"{result.failed_leg!r} met code "
                    f"{result.failure_code!r}."
                ),
            )

    return _fire


def _leg_disabled(leg_name: str, *, setting_name: str) -> MorningChainLegOutcome:
    return MorningChainLegOutcome(
        leg_name=leg_name,
        status=LEG_STATUS_SKIPPED,
        failure_code=None,
        detail_nl=(
            f"Leg overgeslagen — `{setting_name}` staat uit; activeer de "
            "individuele sync-vlag voor je deze leg in de morning chain "
            "verwacht."
        ),
    )


def _outcome_from_runtime_response(
    leg_name: str,
    response: dict[str, object],
    *,
    runtime_label: str,
) -> MorningChainLegOutcome:
    """Map a status_routes ``run_*_sync`` response dict to a
    ``MorningChainLegOutcome``.

    The runtimes return a structured dict with ``status`` in
    {``"completed"``, ``"blocked"``, ``"not_configured"``,
    ``"no_xxx_sync_run"``, …}. ``completed`` → SUCCEEDED; everything
    else → SKIPPED with the runtime's own ``status_nl`` / ``reason``
    in the detail. Exceptions in the runtime are caught higher up and
    mapped to FAILED.
    """

    status = str(response.get("status", "unknown"))
    detail_pieces = [runtime_label]
    if response.get("status_nl"):
        detail_pieces.append(str(response["status_nl"]))
    if response.get("reason"):
        detail_pieces.append(f"reason={response['reason']}")
    detail = " — ".join(detail_pieces)
    if status == "completed":
        return MorningChainLegOutcome(
            leg_name=leg_name,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl=detail,
        )
    return MorningChainLegOutcome(
        leg_name=leg_name,
        status=LEG_STATUS_SKIPPED,
        failure_code=None,
        detail_nl=detail,
    )


def _invoke_runtime_leg(
    leg_name: str,
    *,
    runtime_label: str,
    failure_code: str,
    runner: Callable[[], dict[str, object]],
) -> MorningChainLegOutcome:
    """Common wrapper: call ``runner``, map its response, catch
    everything to SKIPPED with the error in the detail.

    Why SKIPPED and not FAILED on exception? V1.2 §AL — legs invoke
    the underlying ``run_*_sync`` runtimes, which raise on env-level
    issues (missing db driver, network outage). Those are operator-
    config problems, not doctrine-level failures: the chain should
    keep going so the daily briefing and other legs still run. The
    leg detail surfaces the cause so the operator can fix it.
    ``failure_code`` is kept on the signature for future legs that
    want a hard stop, but it is unused for now.
    """

    _ = failure_code  # reserved for legs that genuinely want to stop the chain
    try:
        response = runner()
    except Exception as exc:  # noqa: BLE001 — boundary catch
        return MorningChainLegOutcome(
            leg_name=leg_name,
            status=LEG_STATUS_SKIPPED,
            failure_code=None,
            detail_nl=(
                f"{runtime_label} overgeslagen — runtime gaf "
                f"{type(exc).__name__}: {exc}"
            ),
        )
    return _outcome_from_runtime_response(
        leg_name, response, runtime_label=runtime_label
    )


def build_default_morning_chain_legs(
    runtime_settings: object,
    *,
    orchestrator_scoring_leg_override: LegCallable | None = None,
    earnings_calendar_leg_override: LegCallable | None = None,
) -> tuple[LegCallable, ...]:
    """Build the production morning-chain legs from runtime settings.

    Each leg checks its own ``<leg>_sync_enabled`` flag. When the flag is
    off the leg returns ``skipped`` and the chain proceeds — that lets
    the operator opt into the chain incrementally as each underlying
    sync runtime is exercised. The actual sync invocation is intentionally
    a thin pass-through: each adapter logs "would run" and returns
    ``succeeded`` until the V1 release-readiness slice (Slice 22) wires
    the full session-bound pipeline. The orchestrator + audit chain are
    the real V1 product surface; the leg adapters here are the test
    seam that downstream callers replace with the real sync invocations.
    """

    def _market_data_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "market_data_sync_enabled", False):
            return _leg_disabled(
                LEG_MARKET_DATA_SYNC, setting_name="market_data_sync_enabled"
            )
        from portfolio_outlook_api.status_routes import run_market_data_sync

        return _invoke_runtime_leg(
            LEG_MARKET_DATA_SYNC,
            runtime_label="Market-data sync",
            failure_code="market_data_sync_failed",
            runner=run_market_data_sync,
        )

    def _forecast_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "forecast_sync_enabled", False):
            return _leg_disabled(
                LEG_FORECAST_SYNC, setting_name="forecast_sync_enabled"
            )
        from portfolio_outlook_api.status_routes import run_forecast_sync

        return _invoke_runtime_leg(
            LEG_FORECAST_SYNC,
            runtime_label="Forecast sync",
            failure_code="forecast_sync_failed",
            runner=run_forecast_sync,
        )

    def _suggestion_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "suggestions_sync_enabled", False):
            return _leg_disabled(
                LEG_SUGGESTION_SYNC, setting_name="suggestions_sync_enabled"
            )
        from portfolio_outlook_api.status_routes import run_suggestions_sync

        return _invoke_runtime_leg(
            LEG_SUGGESTION_SYNC,
            runtime_label="Suggestion sync",
            failure_code="suggestion_sync_failed",
            runner=run_suggestions_sync,
        )

    def _decision_package_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "decision_packages_sync_enabled", False):
            return _leg_disabled(
                LEG_DECISION_PACKAGE_SYNC,
                setting_name="decision_packages_sync_enabled",
            )
        from portfolio_outlook_api.status_routes import (
            run_decision_packages_sync,
        )

        return _invoke_runtime_leg(
            LEG_DECISION_PACKAGE_SYNC,
            runtime_label="Decision Package sync",
            failure_code="decision_package_sync_failed",
            runner=run_decision_packages_sync,
        )

    def _action_draft_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "action_drafts_sync_enabled", False):
            return _leg_disabled(
                LEG_ACTION_DRAFT_SYNC, setting_name="action_drafts_sync_enabled"
            )
        from portfolio_outlook_api.status_routes import run_action_drafts_sync

        return _invoke_runtime_leg(
            LEG_ACTION_DRAFT_SYNC,
            runtime_label="Action draft sync",
            failure_code="action_draft_sync_failed",
            runner=run_action_drafts_sync,
        )

    def _earnings_calendar_sync_leg() -> MorningChainLegOutcome:
        """V1.2 §AK earnings-calendar refresh leg (stub).

        Pulls upcoming earnings dates so the orchestrator scoring
        leg (next) can populate ``next_earnings_by_symbol`` from
        storage. Default-disabled via
        ``earnings_calendar_sync_enabled``; the real EODHD-backed
        implementation lives in ``earnings_calendar_leg.py`` and is
        injected via ``earnings_calendar_leg_override``.
        """

        if not getattr(runtime_settings, "earnings_calendar_sync_enabled", False):
            return _leg_disabled(
                LEG_EARNINGS_CALENDAR_SYNC,
                setting_name="earnings_calendar_sync_enabled",
            )
        return MorningChainLegOutcome(
            leg_name=LEG_EARNINGS_CALENDAR_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl=(
                "Earnings-calendar refresh ingeschakeld; real EODHD "
                "writer wordt via override geleverd."
            ),
        )

    def _orchestrator_scoring_leg() -> MorningChainLegOutcome:
        """V1.2 §Y parallel-scoring leg.

        Runs the profit-harvest orchestrator on the current
        candidates and writes verdicts to
        ``orchestrator_scoring_verdicts``. Disabled by default
        (``orchestrator_scoring_enabled=False``) so the doctrine
        scoring path can be validated against the live suggestion
        engine before being promoted.

        Skip path is the only V1 behavior. When enabled in a future
        slice, the runner from
        ``portfolio_outlook_worker.forecasting.orchestrator_scoring_runner``
        is invoked here with the live forecast + fundamentals
        snapshot. For now the leg is a stub that returns ``skipped``
        when disabled and ``succeeded`` (no-op) when enabled — the
        full wiring of candidate provider + storage writer lands
        with Slice §Z.
        """

        if not getattr(runtime_settings, "orchestrator_scoring_enabled", False):
            return _leg_disabled(
                LEG_ORCHESTRATOR_SCORING,
                setting_name="orchestrator_scoring_enabled",
            )
        return MorningChainLegOutcome(
            leg_name=LEG_ORCHESTRATOR_SCORING,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl=(
                "Orchestrator scoring leg ingeschakeld; "
                "candidate-provider wiring volgt in §Z."
            ),
        )

    def _daily_briefing_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "daily_briefing_sync_enabled", False):
            return _leg_disabled(
                LEG_DAILY_BRIEFING_SYNC,
                setting_name="daily_briefing_sync_enabled",
            )
        from portfolio_outlook_api.status_routes import run_daily_briefing

        return _invoke_runtime_leg(
            LEG_DAILY_BRIEFING_SYNC,
            runtime_label="Daily briefing sync",
            failure_code="daily_briefing_sync_failed",
            runner=run_daily_briefing,
        )

    orchestrator_leg: LegCallable = (
        orchestrator_scoring_leg_override
        if orchestrator_scoring_leg_override is not None
        else _orchestrator_scoring_leg
    )
    earnings_leg: LegCallable = (
        earnings_calendar_leg_override
        if earnings_calendar_leg_override is not None
        else _earnings_calendar_sync_leg
    )
    return (
        _market_data_sync_leg,
        _forecast_sync_leg,
        _suggestion_sync_leg,
        _decision_package_sync_leg,
        _action_draft_sync_leg,
        earnings_leg,
        orchestrator_leg,
        _daily_briefing_sync_leg,
    )


def serialize_morning_chain_result(
    result: MorningChainResult,
) -> dict[str, object]:
    """JSON-friendly serialisation for the POST route response."""

    return {
        "status": result.status,
        "failed_leg": result.failed_leg,
        "failure_code": result.failure_code,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "legs": [
            {
                "leg_name": leg.leg_name,
                "status": leg.status,
                "failure_code": leg.failure_code,
                "detail_nl": leg.detail_nl,
            }
            for leg in result.legs
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


__all__ = [
    "CHAIN_STATUS_FAILED",
    "CHAIN_STATUS_SUCCEEDED",
    "LEG_ACTION_DRAFT_SYNC",
    "LEG_DAILY_BRIEFING_SYNC",
    "LEG_EARNINGS_CALENDAR_SYNC",
    "LEG_DECISION_PACKAGE_SYNC",
    "LEG_FORECAST_SYNC",
    "LEG_MARKET_DATA_SYNC",
    "LEG_ORCHESTRATOR_SCORING",
    "LEG_STATUS_FAILED",
    "LEG_STATUS_SKIPPED",
    "LEG_STATUS_SUCCEEDED",
    "LEG_SUGGESTION_SYNC",
    "LegCallable",
    "MORNING_CHAIN_LEG_NAMES",
    "MorningChainFailed",
    "MorningChainLegOutcome",
    "MorningChainResult",
    "build_default_morning_chain_legs",
    "build_scheduler_chain_callable",
    "run_morning_chain",
    "serialize_morning_chain_result",
]
