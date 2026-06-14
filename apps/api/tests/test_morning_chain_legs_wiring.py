"""Tests voor de §BG morning-chain legs wiring helper.

Verifies dat de helper de echte EODHD-backed earnings-calendar leg
en de echte orchestrator-scoring leg injecteert wanneer de
bijbehorende runtime-flags ingeschakeld zijn. Wanneer een flag uit
staat moet de bestaande no-op stub blijven draaien — geen
gedragsverandering t.o.v. pre-§BG.

Cruciaal voor het worker-trigger pad: tot V1.2 §BG injecteerde
alleen het legacy in-process scheduler-pad de real legs. De HTTP
trigger (``POST /scheduler/runs/morning-chain``) viel terug op de
stub. Dat is wat §BG repareert.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from portfolio_outlook_api.morning_chain import (
    LEG_EARNINGS_CALENDAR_SYNC,
    LEG_ORCHESTRATOR_SCORING,
    LEG_STATUS_SKIPPED,
)
from portfolio_outlook_api.morning_chain_legs_wiring import (
    build_morning_chain_legs_with_real_overrides,
)


@dataclass
class _StorageStub:
    enabled: bool = False
    database_url: str | None = None
    writes_enabled: bool = False


@dataclass
class _SettingsStub:
    earnings_calendar_sync_enabled: bool = False
    orchestrator_scoring_enabled: bool = False
    eodhd_api_key: str | None = None
    market_data_sync_enabled: bool = False
    forecast_sync_enabled: bool = False
    suggestion_sync_enabled: bool = False
    decision_package_sync_enabled: bool = False
    action_draft_sync_enabled: bool = False
    daily_briefing_sync_enabled: bool = False
    storage: _StorageStub = field(default_factory=_StorageStub)


def _names(legs) -> list[str]:  # type: ignore[no-untyped-def]
    out: list[str] = []
    for leg in legs:
        outcome = leg()
        out.append(outcome.leg_name)
    return out


def test_returns_default_stubs_when_all_flags_off() -> None:
    """Zonder flags blijft het gedrag identiek aan pre-§BG: alle
    legs skippen (geen real-leg wiring nodig)."""

    settings = _SettingsStub()
    legs = build_morning_chain_legs_with_real_overrides(settings)
    # All legs should fire and skip (since no flags are on).
    outcomes = [leg() for leg in legs]
    assert all(o.status == LEG_STATUS_SKIPPED for o in outcomes)
    # Earnings + orchestrator legs are still present in the chain.
    leg_names = [o.leg_name for o in outcomes]
    assert LEG_EARNINGS_CALENDAR_SYNC in leg_names
    assert LEG_ORCHESTRATOR_SCORING in leg_names


def test_real_earnings_leg_wired_when_flag_on() -> None:
    """Met ``earnings_calendar_sync_enabled=True`` (en zonder
    storage) moet de real leg ``skipped`` teruggeven met de
    storage-skip boodschap — die boodschap onderscheidt zich
    nadrukkelijk van de stub-leg die alleen
    ``earnings_calendar_sync_enabled`` controleert."""

    settings = _SettingsStub(earnings_calendar_sync_enabled=True)
    legs = build_morning_chain_legs_with_real_overrides(settings)
    outcomes = [leg() for leg in legs]
    earnings = next(
        o for o in outcomes if o.leg_name == LEG_EARNINGS_CALENDAR_SYNC
    )
    assert earnings.status == LEG_STATUS_SKIPPED
    # Real leg's storage-precondition message. Stub leg would say
    # "real EODHD writer wordt via override geleverd" — explicitly
    # different so we can prove the override is wired.
    assert "opslag" in earnings.detail_nl.lower()
    assert "EODHD writer" not in earnings.detail_nl


def test_real_earnings_leg_skips_when_eodhd_key_missing() -> None:
    """Met flag aan + storage aan + geen EODHD-key → real leg
    blijft skippen maar met de EODHD-specifieke boodschap."""

    settings = _SettingsStub(
        earnings_calendar_sync_enabled=True,
        eodhd_api_key=None,
        storage=_StorageStub(
            enabled=True,
            database_url="sqlite:///:memory:",
            writes_enabled=True,
        ),
    )
    legs = build_morning_chain_legs_with_real_overrides(settings)
    outcomes = [leg() for leg in legs]
    earnings = next(
        o for o in outcomes if o.leg_name == LEG_EARNINGS_CALENDAR_SYNC
    )
    assert earnings.status == LEG_STATUS_SKIPPED
    assert "EODHD" in earnings.detail_nl


def test_real_orchestrator_leg_wired_when_flag_on() -> None:
    """Met ``orchestrator_scoring_enabled=True`` (en zonder storage)
    moet de real leg de bekende NL boodschap teruggeven — die
    boodschap onderscheidt zich van de stub-leg."""

    settings = _SettingsStub(orchestrator_scoring_enabled=True)
    legs = build_morning_chain_legs_with_real_overrides(settings)
    outcomes = [leg() for leg in legs]
    orch = next(
        o for o in outcomes if o.leg_name == LEG_ORCHESTRATOR_SCORING
    )
    assert orch.status == LEG_STATUS_SKIPPED
    # The real leg's pauze/storage skip messages are different from
    # the stub's "ingeschakeld; candidate-provider wiring volgt".
    assert (
        "opslag" in orch.detail_nl.lower()
        or "pauzeerd" in orch.detail_nl.lower()
    )


def test_stub_leg_used_for_orchestrator_when_flag_off() -> None:
    """Wanneer ``orchestrator_scoring_enabled=False`` blijft de
    stub-leg actief. De stub geeft een specifieke NL boodschap die
    afwijkt van de real-leg skip message."""

    settings = _SettingsStub(orchestrator_scoring_enabled=False)
    legs = build_morning_chain_legs_with_real_overrides(settings)
    outcomes = [leg() for leg in legs]
    orch = next(
        o for o in outcomes if o.leg_name == LEG_ORCHESTRATOR_SCORING
    )
    assert orch.status == LEG_STATUS_SKIPPED
    assert (
        "orchestrator_scoring_enabled" in orch.detail_nl
        or "uit" in orch.detail_nl.lower()
    )


def test_helper_returns_a_chain_with_all_legs() -> None:
    """Sanity-check: de chain bevat alle 8 verwachte legs."""

    settings = _SettingsStub()
    legs = build_morning_chain_legs_with_real_overrides(settings)
    assert len(list(legs)) == 8
