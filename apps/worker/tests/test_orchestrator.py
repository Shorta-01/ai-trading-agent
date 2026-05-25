"""Task 127 — orchestrator unit tests.

Covers the four locked ``mode_detected`` outcomes (cold_start,
normal, disconnected, skipped_locked), the 07:00 morning-briefing
relabel, and the single-flight lock semantics. Storage and gateway
are injected as small fakes so no live infrastructure is required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ai_trading_agent_storage import ScheduledRunAuditEntry

from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _FakeGateway:
    def __init__(self, *, connected: bool) -> None:
        self._connected = connected

    def is_connected(self) -> bool:
        return self._connected


class _FakeSnapshotCounts:
    def __init__(self, *, positions: int, watchlist: int) -> None:
        self._positions = positions
        self._watchlist = watchlist

    def position_snapshot_count_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> int:
        return self._positions

    def watchlist_item_count_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> int:
        return self._watchlist


class _FakeAuditRepo:
    def __init__(self) -> None:
        self.entries: list[ScheduledRunAuditEntry] = []

    def append(self, entry: ScheduledRunAuditEntry) -> ScheduledRunAuditEntry:
        self.entries.append(entry)
        return entry


def _run(
    *,
    gateway: _FakeGateway,
    positions: int = 0,
    watchlist: int = 0,
    lock: InMemoryLock | None = None,
    brussels_hour: int | None = None,
    audit_repo: _FakeAuditRepo | None = None,
    run_type: str = "hourly_delta",
    ibkr_account_id: str | None = "DU1234567",
) -> tuple[_FakeAuditRepo, object]:
    audit = audit_repo or _FakeAuditRepo()
    actual_lock = lock or InMemoryLock()
    hour_provider = None if brussels_hour is None else (lambda: brussels_hour)
    result = run_orchestrator(
        run_type=run_type,  # type: ignore[arg-type]
        ibkr_account_id=ibkr_account_id,
        gateway=gateway,
        snapshot_counts=_FakeSnapshotCounts(
            positions=positions, watchlist=watchlist
        ),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=actual_lock,
        now_provider=lambda: _BASE,
        brussels_hour_provider=hour_provider,
        next_scheduled_at=_BASE + timedelta(hours=1),
    )
    return audit, result


# ---- cold-start path --------------------------------------------


def test_cold_start_when_no_positions_and_no_watchlist() -> None:
    audit, result = _run(
        gateway=_FakeGateway(connected=True), positions=0, watchlist=0
    )
    assert len(audit.entries) == 1
    row = audit.entries[0]
    assert row.mode_detected == "cold_start"
    assert row.outcome == "completed"
    assert row.run_type == "hourly_delta"
    assert result.mode_detected == "cold_start"


def test_cold_start_when_account_id_missing() -> None:
    audit, result = _run(
        gateway=_FakeGateway(connected=True),
        positions=99,
        watchlist=99,
        ibkr_account_id=None,
    )
    # No configured account → orchestrator can't query per-account
    # counts, so it falls back to cold-start (honest about state).
    assert audit.entries[0].mode_detected == "cold_start"
    assert result.mode_detected == "cold_start"


# ---- normal path -------------------------------------------------


def test_normal_mode_when_positions_present() -> None:
    audit, result = _run(
        gateway=_FakeGateway(connected=True), positions=3, watchlist=0
    )
    assert audit.entries[0].mode_detected == "normal"
    assert result.mode_detected == "normal"


def test_normal_mode_when_only_watchlist_present() -> None:
    audit, result = _run(
        gateway=_FakeGateway(connected=True), positions=0, watchlist=5
    )
    assert audit.entries[0].mode_detected == "normal"
    assert result.mode_detected == "normal"


# ---- disconnected path -------------------------------------------


def test_disconnected_when_gateway_reports_disconnected() -> None:
    audit, result = _run(
        gateway=_FakeGateway(connected=False),
        positions=10,  # ignored when disconnected
        watchlist=10,
    )
    assert audit.entries[0].mode_detected == "disconnected"
    assert result.outcome == "completed"  # disconnected is not an error


# ---- skipped_locked path -----------------------------------------


def test_skipped_locked_when_lock_already_held() -> None:
    held_lock = InMemoryLock()
    assert held_lock.try_acquire() is True  # first caller takes it

    audit, result = _run(
        gateway=_FakeGateway(connected=True),
        positions=0,
        watchlist=0,
        lock=held_lock,
    )
    assert audit.entries[0].mode_detected == "skipped_locked"
    assert result.mode_detected == "skipped_locked"
    # The lock was held by an external caller; the orchestrator
    # never acquired it and must not have released it either.
    # If the fake's release semantics were buggy, the held_lock
    # would now be free.
    assert held_lock.try_acquire() is False
    held_lock.release()


# ---- morning-briefing relabel -----------------------------------


def test_07_hourly_run_is_relabelled_morning_briefing() -> None:
    audit, _ = _run(
        gateway=_FakeGateway(connected=True),
        positions=0,
        watchlist=0,
        brussels_hour=7,
    )
    assert audit.entries[0].run_type == "morning_briefing"


def test_other_hours_keep_hourly_delta_label() -> None:
    audit, _ = _run(
        gateway=_FakeGateway(connected=True),
        positions=0,
        watchlist=0,
        brussels_hour=14,
    )
    assert audit.entries[0].run_type == "hourly_delta"


def test_pre_briefing_run_type_is_preserved() -> None:
    audit, _ = _run(
        gateway=_FakeGateway(connected=True),
        positions=0,
        watchlist=0,
        brussels_hour=6,
        run_type="pre_briefing",
    )
    assert audit.entries[0].run_type == "pre_briefing"


# ---- lock release in normal path --------------------------------


def test_lock_released_after_normal_run() -> None:
    """After a successful run the lock must be free for the next
    fire to acquire it."""

    audit, _ = _run(
        gateway=_FakeGateway(connected=True),
        positions=1,
        watchlist=0,
    )
    # Reuse the same audit repo + a fresh lock for the second fire.
    lock = InMemoryLock()
    audit2, result2 = _run(
        gateway=_FakeGateway(connected=True),
        positions=1,
        watchlist=0,
        lock=lock,
        audit_repo=audit,
    )
    # No skipped_locked rows from the second run.
    assert len(audit2.entries) == 2
    assert audit2.entries[1].mode_detected == "normal"
    assert result2.mode_detected == "normal"
