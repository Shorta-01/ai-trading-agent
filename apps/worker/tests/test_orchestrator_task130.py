"""Task 130 — orchestrator calls forecasting + calibration on locked fires."""

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


class _RecordingForecastingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def run(
        self, *, ibkr_account_id: str, scheduled_run_id: str
    ) -> dict[str, object]:
        self.calls.append((ibkr_account_id, scheduled_run_id))
        return {"pilot_conids_attempted": 1, "forecasts_written": 1}


class _RecordingCalibrationRunner:
    def __init__(self) -> None:
        self.calls: int = 0

    def run(self) -> dict[str, object]:
        self.calls += 1
        return {"forecasts_evaluated": 0, "diary_rows_written": 0}


def _run(*, run_type: str, forecasting=None, calibration=None):  # type: ignore[no-untyped-def]
    audit = _AuditRepo()
    return audit, run_orchestrator(
        run_type=run_type,  # type: ignore[arg-type]
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(positions=1, watchlist=12),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        forecasting_runner=forecasting,
        calibration_runner=calibration,
    )


def test_forecasting_runner_called_on_morning_briefing_normal_fire() -> None:
    runner = _RecordingForecastingRunner()
    audit, result = _run(run_type="morning_briefing", forecasting=runner)
    assert result.mode_detected == "normal"
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == "DU1234567"
    # The forecast details fold into the audit row.
    assert audit.entries[0].error_details_json is not None
    assert "forecast" in audit.entries[0].error_details_json


def test_forecasting_runner_NOT_called_on_pre_briefing() -> None:
    runner = _RecordingForecastingRunner()
    audit, result = _run(run_type="pre_briefing", forecasting=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == []
    # No "forecast" section in the audit row.
    if audit.entries[0].error_details_json is not None:
        assert "forecast" not in audit.entries[0].error_details_json


def test_forecasting_runner_NOT_called_on_hourly_delta() -> None:
    runner = _RecordingForecastingRunner()
    audit, result = _run(run_type="hourly_delta", forecasting=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == []


def test_calibration_runner_called_on_pre_briefing_normal_fire() -> None:
    runner = _RecordingCalibrationRunner()
    audit, result = _run(run_type="pre_briefing", calibration=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == 1
    assert audit.entries[0].error_details_json is not None
    assert "calibration" in audit.entries[0].error_details_json


def test_calibration_runner_NOT_called_on_morning_briefing() -> None:
    runner = _RecordingCalibrationRunner()
    audit, result = _run(run_type="morning_briefing", calibration=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == 0


def test_calibration_runner_NOT_called_on_hourly_delta() -> None:
    runner = _RecordingCalibrationRunner()
    audit, result = _run(run_type="hourly_delta", calibration=runner)
    assert result.mode_detected == "normal"
    assert runner.calls == 0


def test_forecasting_runner_exception_does_not_crash_orchestrator() -> None:
    class _Boom:
        def run(self, *, ibkr_account_id: str, scheduled_run_id: str) -> dict[str, object]:  # noqa: ARG002
            raise RuntimeError("crash")

    audit, result = _run(run_type="morning_briefing", forecasting=_Boom())
    assert result.outcome == "completed"
    assert audit.entries[0].error_details_json is not None
    assert "forecasting_runner_exception" in audit.entries[0].error_details_json


def test_calibration_runner_exception_does_not_crash_orchestrator() -> None:
    class _Boom:
        def run(self) -> dict[str, object]:
            raise RuntimeError("crash")

    audit, result = _run(run_type="pre_briefing", calibration=_Boom())
    assert result.outcome == "completed"
    assert audit.entries[0].error_details_json is not None
    assert "calibration_runner_exception" in audit.entries[0].error_details_json
