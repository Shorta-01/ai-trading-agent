"""Task 129 — orchestrator calls the market-data runner on the locked fires."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage import ScheduledRunAuditEntry

from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _Gateway:
    def is_connected(self) -> bool:
        return True


class _SnapshotCounts:
    def __init__(self, *, positions: int, watchlist: int) -> None:
        self._positions = positions
        self._watchlist = watchlist

    def position_snapshot_count_for_account(self, ibkr_account_id: str) -> int:  # noqa: ARG002
        return self._positions

    def watchlist_item_count_for_account(self, ibkr_account_id: str) -> int:  # noqa: ARG002
        return self._watchlist


class _AuditRepo:
    def __init__(self) -> None:
        self.entries: list[ScheduledRunAuditEntry] = []

    def append(self, entry: ScheduledRunAuditEntry) -> ScheduledRunAuditEntry:
        self.entries.append(entry)
        return entry


class _ConfirmedState:
    def get_state(self, ibkr_account_id: str) -> str:  # noqa: ARG002
        return "confirmed"


class _RecordingMarketDataRunner:
    def __init__(self, *, raises: BaseException | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._raises = raises

    def run(
        self, *, ibkr_account_id: str, run_type: str
    ) -> dict[str, object]:
        self.calls.append((ibkr_account_id, run_type))
        if self._raises is not None:
            raise self._raises
        return {"snapshots_succeeded": 12, "fx_rates_succeeded": 2}


def _run(
    *,
    run_type: str,
    market_data: _RecordingMarketDataRunner | None,
    audit: _AuditRepo | None = None,
):  # type: ignore[no-untyped-def]
    audit = audit or _AuditRepo()
    return audit, run_orchestrator(
        run_type=run_type,  # type: ignore[arg-type]
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(positions=1, watchlist=12),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        market_data_runner=market_data,
    )


def test_market_data_runner_called_on_morning_briefing_normal_fire() -> None:
    runner = _RecordingMarketDataRunner()
    audit, result = _run(run_type="morning_briefing", market_data=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == [("DU1234567", "morning_briefing")]
    # The result's details land in the audit row.
    assert audit.entries[0].error_details_json is not None
    assert "market_data" in audit.entries[0].error_details_json


def test_market_data_runner_called_on_pre_briefing_normal_fire() -> None:
    runner = _RecordingMarketDataRunner()
    audit, _ = _run(run_type="pre_briefing", market_data=runner)
    assert runner.calls == [("DU1234567", "pre_briefing")]


def test_market_data_runner_NOT_called_on_hourly_delta_fire() -> None:
    runner = _RecordingMarketDataRunner()
    audit, result = _run(run_type="hourly_delta", market_data=runner)
    assert result.mode_detected == "normal"
    # Hourly delta runs skip the market-data fetch per Task 129 §2.
    assert runner.calls == []
    # No market_data section in the audit row when runner not called.
    assert (
        audit.entries[0].error_details_json is None
        or "market_data" not in (audit.entries[0].error_details_json or "")
    )


def test_market_data_runner_exception_does_not_crash_orchestrator() -> None:
    runner = _RecordingMarketDataRunner(raises=RuntimeError("boom"))
    audit, result = _run(run_type="morning_briefing", market_data=runner)
    # Orchestrator still completes; failure folded into the audit row.
    assert result.mode_detected == "normal"
    assert result.outcome == "completed"
    assert audit.entries[0].error_details_json is not None
    assert "market_data_runner_exception" in audit.entries[0].error_details_json
