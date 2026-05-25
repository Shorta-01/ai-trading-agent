"""Tests for the morning-chain orchestrator (Slice 21)."""

from __future__ import annotations

import pytest

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.morning_chain import (
    CHAIN_STATUS_FAILED,
    CHAIN_STATUS_SUCCEEDED,
    LEG_ACTION_DRAFT_SYNC,
    LEG_DAILY_BRIEFING_SYNC,
    LEG_DECISION_PACKAGE_SYNC,
    LEG_FORECAST_SYNC,
    LEG_MARKET_DATA_SYNC,
    LEG_STATUS_FAILED,
    LEG_STATUS_SKIPPED,
    LEG_STATUS_SUCCEEDED,
    LEG_SUGGESTION_SYNC,
    MORNING_CHAIN_LEG_NAMES,
    MorningChainFailed,
    MorningChainLegOutcome,
    build_default_morning_chain_legs,
    build_scheduler_chain_callable,
    run_morning_chain,
    serialize_morning_chain_result,
)


def _ok(leg_name: str) -> MorningChainLegOutcome:
    return MorningChainLegOutcome(
        leg_name=leg_name,
        status=LEG_STATUS_SUCCEEDED,
        failure_code=None,
        detail_nl="leg ok",
    )


def _fail(leg_name: str, code: str = "boom") -> MorningChainLegOutcome:
    return MorningChainLegOutcome(
        leg_name=leg_name,
        status=LEG_STATUS_FAILED,
        failure_code=code,
        detail_nl=f"{leg_name} faalde met {code}",
    )


def _skip(leg_name: str) -> MorningChainLegOutcome:
    return MorningChainLegOutcome(
        leg_name=leg_name,
        status=LEG_STATUS_SKIPPED,
        failure_code=None,
        detail_nl="leg overgeslagen",
    )


def _settings(**overrides: object) -> Settings:
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


# ---- Dataclass invariants --------------------------------------------------


def test_morning_chain_leg_names_are_in_locked_order() -> None:
    assert MORNING_CHAIN_LEG_NAMES == (
        LEG_MARKET_DATA_SYNC,
        LEG_FORECAST_SYNC,
        LEG_SUGGESTION_SYNC,
        LEG_DECISION_PACKAGE_SYNC,
        LEG_ACTION_DRAFT_SYNC,
        LEG_DAILY_BRIEFING_SYNC,
    )


def test_leg_outcome_rejects_unknown_leg_name() -> None:
    with pytest.raises(ValueError, match="not a recognised"):
        MorningChainLegOutcome(
            leg_name="unknown_leg",
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl="x",
        )


def test_leg_outcome_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="leg status"):
        MorningChainLegOutcome(
            leg_name=LEG_MARKET_DATA_SYNC,
            status="bogus",
            failure_code=None,
            detail_nl="x",
        )


def test_leg_outcome_failed_requires_failure_code() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        MorningChainLegOutcome(
            leg_name=LEG_MARKET_DATA_SYNC,
            status=LEG_STATUS_FAILED,
            failure_code=None,
            detail_nl="missing",
        )


# ---- Orchestrator behaviour -----------------------------------------------


def test_run_morning_chain_all_succeed() -> None:
    legs = [lambda n=name: _ok(n) for name in MORNING_CHAIN_LEG_NAMES]
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert result.failed_leg is None
    assert result.failure_code is None
    assert [leg.leg_name for leg in result.legs] == list(MORNING_CHAIN_LEG_NAMES)
    assert all(leg.status == LEG_STATUS_SUCCEEDED for leg in result.legs)


def test_run_morning_chain_stops_on_first_failure() -> None:
    # Fail at the 3rd leg (suggestion_sync). Subsequent legs must not run.
    invocations: list[str] = []

    def _leg(name: str, *, succeed: bool, code: str | None = None):
        def _runner() -> MorningChainLegOutcome:
            invocations.append(name)
            return _ok(name) if succeed else _fail(name, code or "boom")
        return _runner

    legs = [
        _leg(LEG_MARKET_DATA_SYNC, succeed=True),
        _leg(LEG_FORECAST_SYNC, succeed=True),
        _leg(LEG_SUGGESTION_SYNC, succeed=False, code="suggestion_boom"),
        _leg(LEG_DECISION_PACKAGE_SYNC, succeed=True),  # should not run
        _leg(LEG_ACTION_DRAFT_SYNC, succeed=True),  # should not run
        _leg(LEG_DAILY_BRIEFING_SYNC, succeed=True),  # should not run
    ]
    result = run_morning_chain(legs=legs)

    assert result.status == CHAIN_STATUS_FAILED
    assert result.failed_leg == LEG_SUGGESTION_SYNC
    assert result.failure_code == "suggestion_boom"
    # Only the first three legs ran.
    assert invocations == [
        LEG_MARKET_DATA_SYNC,
        LEG_FORECAST_SYNC,
        LEG_SUGGESTION_SYNC,
    ]
    assert len(result.legs) == 3


def test_run_morning_chain_skipped_leg_does_not_stop_chain() -> None:
    legs = [
        lambda: _ok(LEG_MARKET_DATA_SYNC),
        lambda: _skip(LEG_FORECAST_SYNC),
        lambda: _ok(LEG_SUGGESTION_SYNC),
        lambda: _ok(LEG_DECISION_PACKAGE_SYNC),
        lambda: _ok(LEG_ACTION_DRAFT_SYNC),
        lambda: _ok(LEG_DAILY_BRIEFING_SYNC),
    ]
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert result.legs[1].status == LEG_STATUS_SKIPPED
    assert len(result.legs) == 6


def test_run_morning_chain_catches_exception_from_leg_callable() -> None:
    def _exploder() -> MorningChainLegOutcome:
        raise RuntimeError("kaboom")

    _exploder.leg_name = LEG_FORECAST_SYNC  # type: ignore[attr-defined]

    legs = [lambda: _ok(LEG_MARKET_DATA_SYNC), _exploder]
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_FAILED
    assert result.failed_leg == LEG_FORECAST_SYNC
    assert result.failure_code == "leg_callable_raised"
    assert "kaboom" in result.legs[1].detail_nl


# ---- Scheduler-wrapping callable ------------------------------------------


def test_scheduler_callable_returns_none_on_success() -> None:
    legs = tuple(lambda n=name: _ok(n) for name in MORNING_CHAIN_LEG_NAMES)
    runner = build_scheduler_chain_callable(legs_factory=lambda: legs)
    # Should not raise.
    assert runner() is None


def test_scheduler_callable_raises_morning_chain_failed_on_failure() -> None:
    legs = (
        lambda: _ok(LEG_MARKET_DATA_SYNC),
        lambda: _fail(LEG_FORECAST_SYNC, "forecast_explode"),
    )
    runner = build_scheduler_chain_callable(legs_factory=lambda: legs)
    with pytest.raises(MorningChainFailed) as exc_info:
        runner()
    assert exc_info.value.failed_leg == LEG_FORECAST_SYNC
    assert exc_info.value.failure_code == "forecast_explode"


# ---- Default leg factory --------------------------------------------------


def test_default_legs_all_skipped_when_flags_are_off() -> None:
    legs = build_default_morning_chain_legs(_settings())
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert [leg.status for leg in result.legs] == [LEG_STATUS_SKIPPED] * 6


def test_default_legs_succeed_when_all_flags_enabled() -> None:
    legs = build_default_morning_chain_legs(
        _settings(
            market_data_sync_enabled=True,
            forecast_sync_enabled=True,
            suggestions_sync_enabled=True,
            decision_packages_sync_enabled=True,
            action_drafts_sync_enabled=True,
            daily_briefing_sync_enabled=True,
        )
    )
    result = run_morning_chain(legs=legs)
    assert result.status == CHAIN_STATUS_SUCCEEDED
    assert [leg.status for leg in result.legs] == [LEG_STATUS_SUCCEEDED] * 6


def test_default_legs_partial_enable_yields_mixed_statuses() -> None:
    # market-data + forecast enabled; rest off.
    legs = build_default_morning_chain_legs(
        _settings(
            market_data_sync_enabled=True,
            forecast_sync_enabled=True,
        )
    )
    result = run_morning_chain(legs=legs)
    assert [leg.status for leg in result.legs] == [
        LEG_STATUS_SUCCEEDED,
        LEG_STATUS_SUCCEEDED,
        LEG_STATUS_SKIPPED,
        LEG_STATUS_SKIPPED,
        LEG_STATUS_SKIPPED,
        LEG_STATUS_SKIPPED,
    ]


# ---- Serialisation --------------------------------------------------------


def test_serialize_morning_chain_result_has_locked_safety_booleans() -> None:
    legs = [lambda n=name: _ok(n) for name in MORNING_CHAIN_LEG_NAMES]
    result = run_morning_chain(legs=legs)
    serialised = serialize_morning_chain_result(result)
    assert serialised["status"] == "succeeded"
    assert serialised["failed_leg"] is None
    assert serialised["safe_for_action_drafts"] is False
    assert serialised["safe_for_orders"] is False
    leg_names = [leg["leg_name"] for leg in serialised["legs"]]  # type: ignore[index]
    assert leg_names == list(MORNING_CHAIN_LEG_NAMES)


def test_serialize_morning_chain_result_surfaces_failed_leg() -> None:
    legs = (
        lambda: _ok(LEG_MARKET_DATA_SYNC),
        lambda: _fail(LEG_FORECAST_SYNC, "forecast_boom"),
    )
    result = run_morning_chain(legs=legs)
    serialised = serialize_morning_chain_result(result)
    assert serialised["status"] == "failed"
    assert serialised["failed_leg"] == LEG_FORECAST_SYNC
    assert serialised["failure_code"] == "forecast_boom"
