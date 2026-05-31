"""Orchestrator tests for the end-of-day digest runner.

The digest runner fires only on ``market_close`` and only when the
mode is ``normal``. Mirror tests of `test_orchestrator_task129.py`,
sized for the digest leg.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 5, 31, 17, 45, tzinfo=UTC)


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
class _RecordingDigestRunner:
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def run(
        self,
        *,
        ibkr_account_id: str,
        market_code: str,
        scheduled_run_id: str,
    ) -> dict[str, object]:
        self.calls.append(
            (ibkr_account_id, market_code, scheduled_run_id)
        )
        return {"persisted_digest_id": "digest-test-x"}


def _run(
    *,
    run_type: str,
    digest_runner: _RecordingDigestRunner | None,
    market_code: str | None = "EURONEXT",
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
        digest_runner=digest_runner,
        market_code=market_code,
    )


def test_digest_runner_called_on_market_close_normal_fire() -> None:
    runner = _RecordingDigestRunner()
    audit, result = _run(run_type="market_close", digest_runner=runner)
    assert len(runner.calls) == 1
    account, market, run_id = runner.calls[0]
    assert account == "DU1234567"
    assert market == "EURONEXT"
    # The orchestrator passes its scheduled-run id through to the runner;
    # it's also written into the audit row.
    assert audit.entries[0].run_id == run_id
    assert audit.entries[0].error_details_json is not None
    assert "digest" in audit.entries[0].error_details_json
    assert result.mode_detected == "normal"


def test_digest_runner_NOT_called_on_morning_briefing() -> None:
    runner = _RecordingDigestRunner()
    _run(run_type="morning_briefing", digest_runner=runner)
    assert runner.calls == []


def test_digest_runner_NOT_called_on_pre_briefing() -> None:
    runner = _RecordingDigestRunner()
    _run(run_type="pre_briefing", digest_runner=runner)
    assert runner.calls == []


def test_digest_runner_NOT_called_when_market_code_is_missing() -> None:
    runner = _RecordingDigestRunner()
    _run(run_type="market_close", digest_runner=runner, market_code=None)
    assert runner.calls == []
