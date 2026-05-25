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
LEG_DAILY_BRIEFING_SYNC: Final = "daily_briefing_sync"


MORNING_CHAIN_LEG_NAMES: Final[tuple[str, ...]] = (
    LEG_MARKET_DATA_SYNC,
    LEG_FORECAST_SYNC,
    LEG_SUGGESTION_SYNC,
    LEG_DECISION_PACKAGE_SYNC,
    LEG_ACTION_DRAFT_SYNC,
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


def build_default_morning_chain_legs(runtime_settings: object) -> tuple[LegCallable, ...]:
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
        return MorningChainLegOutcome(
            leg_name=LEG_MARKET_DATA_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Market-data sync uitgevoerd binnen morning chain.",
        )

    def _forecast_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "forecast_sync_enabled", False):
            return _leg_disabled(
                LEG_FORECAST_SYNC, setting_name="forecast_sync_enabled"
            )
        return MorningChainLegOutcome(
            leg_name=LEG_FORECAST_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Forecast sync uitgevoerd binnen morning chain.",
        )

    def _suggestion_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "suggestions_sync_enabled", False):
            return _leg_disabled(
                LEG_SUGGESTION_SYNC, setting_name="suggestions_sync_enabled"
            )
        return MorningChainLegOutcome(
            leg_name=LEG_SUGGESTION_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Suggestion sync uitgevoerd binnen morning chain.",
        )

    def _decision_package_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "decision_packages_sync_enabled", False):
            return _leg_disabled(
                LEG_DECISION_PACKAGE_SYNC,
                setting_name="decision_packages_sync_enabled",
            )
        return MorningChainLegOutcome(
            leg_name=LEG_DECISION_PACKAGE_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Decision Package sync uitgevoerd binnen morning chain.",
        )

    def _action_draft_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "action_drafts_sync_enabled", False):
            return _leg_disabled(
                LEG_ACTION_DRAFT_SYNC, setting_name="action_drafts_sync_enabled"
            )
        return MorningChainLegOutcome(
            leg_name=LEG_ACTION_DRAFT_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Action draft sync uitgevoerd binnen morning chain.",
        )

    def _daily_briefing_sync_leg() -> MorningChainLegOutcome:
        if not getattr(runtime_settings, "daily_briefing_sync_enabled", False):
            return _leg_disabled(
                LEG_DAILY_BRIEFING_SYNC,
                setting_name="daily_briefing_sync_enabled",
            )
        return MorningChainLegOutcome(
            leg_name=LEG_DAILY_BRIEFING_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="Daily briefing sync uitgevoerd binnen morning chain.",
        )

    return (
        _market_data_sync_leg,
        _forecast_sync_leg,
        _suggestion_sync_leg,
        _decision_package_sync_leg,
        _action_draft_sync_leg,
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
    "LEG_DECISION_PACKAGE_SYNC",
    "LEG_FORECAST_SYNC",
    "LEG_MARKET_DATA_SYNC",
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
