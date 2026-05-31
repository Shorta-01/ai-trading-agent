"""Orchestrator branch tests for the morning-alerts runner injection.

Mirrors the digest-runner tests: assert that the runner fires only
on ``morning_briefing`` in ``normal`` mode, and that a forecasting or
decision-package failure flips ``chain_failed=True`` on the call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 6, 1, 7, 5, tzinfo=UTC)


class _Gateway:
    def is_connected(self) -> bool:
        return True


@dataclass
class _SnapshotCounts:
    positions: int = 1
    watchlist: int = 12

    def position_snapshot_count_for_account(self, _id: str) -> int:
        return self.positions

    def watchlist_item_count_for_account(self, _id: str) -> int:
        return self.watchlist


class _ConfirmedState:
    def get_state(self, _id: str) -> str:
        return "confirmed"


class _AuditRepo:
    def __init__(self) -> None:
        self.entries: list[object] = []

    def append(self, entry):  # type: ignore[no-untyped-def]
        self.entries.append(entry)
        return entry


@dataclass
class _RecordingMorningAlertsRunner:
    calls: list[dict[str, object]] = field(default_factory=list)

    def run(
        self,
        *,
        ibkr_account_id: str,
        scheduled_run_id: str,
        chain_failed: bool = False,
        failure_reason_nl: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "ibkr_account_id": ibkr_account_id,
                "scheduled_run_id": scheduled_run_id,
                "chain_failed": chain_failed,
                "failure_reason_nl": failure_reason_nl,
            }
        )
        return {"alert_count": 0, "email": {"sent": False, "reason": "no_alerts"}}


@dataclass
class _FailingForecastingRunner:
    """Raises on every call so the orchestrator's chain_failed path
    triggers."""

    def run(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("forecast boom")


def _run(
    *,
    run_type: str,
    morning_alerts_runner: _RecordingMorningAlertsRunner | None = None,
    forecasting_runner=None,
):  # type: ignore[no-untyped-def]
    audit = _AuditRepo()
    return audit, run_orchestrator(
        run_type=run_type,  # type: ignore[arg-type]
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        morning_alerts_runner=morning_alerts_runner,
        forecasting_runner=forecasting_runner,
    )


def test_morning_alerts_runner_called_on_morning_briefing_normal_fire() -> None:
    runner = _RecordingMorningAlertsRunner()
    audit, _ = _run(
        run_type="morning_briefing", morning_alerts_runner=runner
    )
    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["ibkr_account_id"] == "DU1234567"
    assert call["chain_failed"] is False
    # The audit payload includes the morning_alerts details.
    assert "morning_alerts" in audit.entries[0].error_details_json


def test_morning_alerts_runner_NOT_called_on_pre_briefing() -> None:
    runner = _RecordingMorningAlertsRunner()
    _run(run_type="pre_briefing", morning_alerts_runner=runner)
    assert runner.calls == []


def test_morning_alerts_runner_NOT_called_on_market_close() -> None:
    runner = _RecordingMorningAlertsRunner()
    _run(run_type="market_close", morning_alerts_runner=runner)
    assert runner.calls == []


def test_chain_failure_flag_passes_through_when_forecasting_errors() -> None:
    runner = _RecordingMorningAlertsRunner()
    _run(
        run_type="morning_briefing",
        morning_alerts_runner=runner,
        forecasting_runner=_FailingForecastingRunner(),
    )
    assert len(runner.calls) == 1
    assert runner.calls[0]["chain_failed"] is True
    assert "Voorspellings" in str(runner.calls[0]["failure_reason_nl"])
