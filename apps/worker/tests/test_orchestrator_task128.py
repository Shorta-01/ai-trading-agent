"""Task 128 — orchestrator gate against the watchlist confirmation state.

The orchestrator now overrides ``normal`` → ``awaiting_watchlist_confirmation``
when the per-account confirmation state row says ``unconfirmed``,
and triggers the cold-start seed once on the very first cold-start
fire.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage import ScheduledRunAuditEntry

from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _Gateway:
    def __init__(self, *, connected: bool = True) -> None:
        self._connected = connected

    def is_connected(self) -> bool:
        return self._connected


class _SnapshotCounts:
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


class _AuditRepo:
    def __init__(self) -> None:
        self.entries: list[ScheduledRunAuditEntry] = []

    def append(self, entry: ScheduledRunAuditEntry) -> ScheduledRunAuditEntry:
        self.entries.append(entry)
        return entry


class _ConfirmationState:
    def __init__(self, state: str | None) -> None:
        self._state = state

    def get_state(self, ibkr_account_id: str) -> str | None:  # noqa: ARG002
        return self._state


class _SeedRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def seed(self, ibkr_account_id: str) -> bool:
        self.calls.append(ibkr_account_id)
        return True


# ---- awaiting_watchlist_confirmation -----------------------------


def test_orchestrator_overrides_normal_to_awaiting_when_unconfirmed() -> None:
    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=0, watchlist=12),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmationState("unconfirmed"),
    )
    assert result.mode_detected == "awaiting_watchlist_confirmation"
    assert audit.entries[0].mode_detected == "awaiting_watchlist_confirmation"


def test_orchestrator_stays_normal_when_state_is_confirmed() -> None:
    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=0, watchlist=12),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmationState("confirmed"),
    )
    assert result.mode_detected == "normal"


def test_orchestrator_stays_normal_when_state_protocol_absent() -> None:
    """Backwards compatibility: existing tests that don't inject the
    confirmation_state protocol keep their old behaviour."""

    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=1, watchlist=0),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
    )
    assert result.mode_detected == "normal"


# ---- cold_start seed-trigger -------------------------------------


def test_orchestrator_calls_seed_when_cold_start_detected() -> None:
    seed = _SeedRunner()
    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=0, watchlist=0),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmationState(None),
        seed_runner=seed,
    )
    # Audit row stays "cold_start" on the very first detected fire
    # — the unconfirmed gate kicks in on the *next* fire (where
    # watchlist_count > 0 + state == "unconfirmed").
    assert result.mode_detected == "cold_start"
    # And the seed was triggered exactly once.
    assert seed.calls == ["DU1234567"]


def test_orchestrator_does_not_seed_when_not_cold_start() -> None:
    seed = _SeedRunner()
    audit = _AuditRepo()
    run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=1, watchlist=0),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmationState(None),
        seed_runner=seed,
    )
    assert seed.calls == []


def test_orchestrator_swallows_seed_runner_exception() -> None:
    """Seed runner failure must not crash the orchestrator — the
    next fire will retry."""

    class _FailingSeed:
        def seed(self, ibkr_account_id: str) -> bool:  # noqa: ARG002
            raise RuntimeError("storage transient")

    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="hourly_delta",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(connected=True),
        snapshot_counts=_SnapshotCounts(positions=0, watchlist=0),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmationState(None),
        seed_runner=_FailingSeed(),  # type: ignore[arg-type]
    )
    # Still records the cold_start audit row.
    assert result.mode_detected == "cold_start"
    assert audit.entries[0].mode_detected == "cold_start"
    assert result.outcome == "completed"
