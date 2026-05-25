"""Task 132 — orchestrator wires Decision Package runner after forecasting."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetListingRecord,
    ForecastEntry,
    FxRateRecord,
    IbkrPositionSnapshotRecord,
    MarketDataEodSnapshotEntry,
    ScheduledRunAuditEntry,
    SqlAlchemyDecisionPackageRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.decision_package.orchestration import (
    compose_and_persist_for_run,
)
from portfolio_outlook_worker.orchestrator import run_orchestrator
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0050_decision_packages",
        database_revision_id=(
            "0050_decision_packages" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


class _Gateway:
    def is_connected(self) -> bool:
        return True


class _SnapshotCounts:
    def position_snapshot_count_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> int:
        return 1

    def watchlist_item_count_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> int:
        return 12


class _ConfirmedState:
    def get_state(self, ibkr_account_id: str) -> str:  # noqa: ARG002
        return "confirmed"


class _AuditRepo:
    def __init__(self) -> None:
        self.entries: list[ScheduledRunAuditEntry] = []

    def append(self, entry: ScheduledRunAuditEntry) -> ScheduledRunAuditEntry:
        self.entries.append(entry)
        return entry


class _ForecastingRunner:
    def run(
        self, *, ibkr_account_id: str, scheduled_run_id: str  # noqa: ARG002
    ) -> dict[str, object]:
        return {"total_attempted": 12, "succeeded": 10, "total_blocked": 2}


class _RecordingDecisionPackageRunner:
    def __init__(self, *, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    def run(
        self, *, ibkr_account_id: str, scheduled_run_id: str
    ) -> dict[str, object]:
        self.calls.append((ibkr_account_id, scheduled_run_id))
        return self.payload


# ---- orchestrator-level wiring ----------------------------------


def test_decision_package_runner_called_after_forecasting_on_morning_briefing() -> None:
    audit = _AuditRepo()
    dp_runner = _RecordingDecisionPackageRunner(
        payload={"forecasts_seen": 12, "composed": 10, "skipped_geblokkeerd": 2}
    )
    result = run_orchestrator(
        run_type="morning_briefing",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        forecasting_runner=_ForecastingRunner(),
        decision_package_runner=dp_runner,
    )
    assert result.mode_detected == "normal"
    assert len(dp_runner.calls) == 1
    assert dp_runner.calls[0][0] == "DU1234567"
    # Decision Package summary folds into the audit row.
    details = json.loads(audit.entries[0].error_details_json or "{}")
    assert "decision_package" in details
    assert details["decision_package"]["composed"] == 10
    assert details["decision_package"]["skipped_geblokkeerd"] == 2


def test_decision_package_runner_NOT_called_on_pre_briefing() -> None:
    audit = _AuditRepo()
    dp_runner = _RecordingDecisionPackageRunner(payload={"composed": 0})
    run_orchestrator(
        run_type="pre_briefing",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        forecasting_runner=_ForecastingRunner(),
        decision_package_runner=dp_runner,
    )
    assert dp_runner.calls == []


def test_decision_package_runner_NOT_called_when_forecasting_failed() -> None:
    class _FailingForecast:
        def run(
            self, *, ibkr_account_id: str, scheduled_run_id: str  # noqa: ARG002
        ) -> dict[str, object]:
            return {"error": "forecasting_runner_exception"}

    audit = _AuditRepo()
    dp_runner = _RecordingDecisionPackageRunner(payload={"composed": 0})
    run_orchestrator(
        run_type="morning_briefing",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        forecasting_runner=_FailingForecast(),
        decision_package_runner=dp_runner,
    )
    assert dp_runner.calls == []


def test_decision_package_runner_exception_does_not_crash_orchestrator() -> None:
    class _Crash:
        def run(
            self, *, ibkr_account_id: str, scheduled_run_id: str  # noqa: ARG002
        ) -> dict[str, object]:
            raise RuntimeError("kaboom")

    audit = _AuditRepo()
    result = run_orchestrator(
        run_type="morning_briefing",
        ibkr_account_id="DU1234567",
        gateway=_Gateway(),
        snapshot_counts=_SnapshotCounts(),
        audit_repo=audit,  # type: ignore[arg-type]
        lock=InMemoryLock(),
        now_provider=lambda: _BASE,
        confirmation_state=_ConfirmedState(),
        forecasting_runner=_ForecastingRunner(),
        decision_package_runner=_Crash(),
    )
    assert result.outcome == "completed"
    details = json.loads(audit.entries[0].error_details_json or "{}")
    assert details["decision_package"]["error"] == (
        "decision_package_runner_exception"
    )


# ---- composition orchestration (compose_and_persist_for_run) ---


def _forecast(
    *,
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    label: str = "Bekijken",
    confidence: str = "Hoog",
    block_reason: str | None = None,
) -> ForecastEntry:
    return ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=_BASE,
        generated_by_scheduled_run_id="srun-1",
        horizon_trading_days=20,
        forecast_valid_until=_BASE + timedelta(days=28),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=Decimal("640.000000"),
        currency_local="EUR",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level=confidence,
        label=label,
        block_reason=block_reason,
        expired_at=None,
    )


def _snapshot(conid: str = "ASML.AS") -> MarketDataEodSnapshotEntry:
    return MarketDataEodSnapshotEntry(
        snapshot_id=f"snap-{conid}",
        ibkr_conid=conid,
        symbol=conid.split(".")[0],
        exchange="AEB",
        currency_local="EUR",
        as_of_date=_BASE.date(),
        as_of_close_ts=_BASE.replace(hour=20),
        ingested_ts=_BASE,
        open_local=Decimal("638.0"),
        high_local=Decimal("642.0"),
        low_local=Decimal("637.0"),
        close_local=Decimal("640.0"),
        adj_close_local=Decimal("640.0"),
        volume=1_000_000,
        provider="eodhd",
        provider_response_hash="abc",
    )


class _ForecastSource:
    def __init__(self, forecasts: tuple[ForecastEntry, ...]) -> None:
        self._forecasts = forecasts

    def list_forecasts_for_scheduled_run(
        self, *, ibkr_account_id: str, scheduled_run_id: str  # noqa: ARG002
    ) -> tuple[ForecastEntry, ...]:
        return self._forecasts


class _ContextProvider:
    def __init__(self, *, missing_snapshot_conids: set[str] | None = None) -> None:
        self._missing = missing_snapshot_conids or set()

    def market_snapshot_for_conid(
        self, *, conid: str
    ) -> MarketDataEodSnapshotEntry | None:
        if conid in self._missing:
            return None
        return _snapshot(conid)

    def fx_rate_for_currency(
        self, *, currency_local: str  # noqa: ARG002
    ) -> FxRateRecord | None:
        return None

    def asset_listing_for_conid(
        self, *, conid: str  # noqa: ARG002
    ) -> AssetListingRecord | None:
        return None

    def position_for_account_conid(
        self, *, ibkr_account_id: str, conid: str  # noqa: ARG002
    ) -> IbkrPositionSnapshotRecord | None:
        return None


def test_compose_skips_geblokkeerd_forecasts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        non_blocked = tuple(
            _forecast(forecast_run_id=f"fcst-good-{i}", conid=f"conid-{i}")
            for i in range(10)
        )
        blocked = tuple(
            _forecast(
                forecast_run_id=f"fcst-blocked-{i}",
                conid=f"blocked-{i}",
                label="Geblokkeerd",
                block_reason="insufficient_history",
                confidence="Laag",
            )
            for i in range(2)
        )
        result = compose_and_persist_for_run(
            ibkr_account_id="DU1234567",
            scheduled_run_id="srun-1",
            forecast_source=_ForecastSource(non_blocked + blocked),
            context_provider=_ContextProvider(),
            decision_package_repo=repo,
            now_provider=lambda: _BASE,
        )
        assert result.forecasts_seen == 12
        assert result.composed == 10
        assert result.skipped_geblokkeerd == 2
        assert result.missing_context == 0
        assert result.composition_errors == 0
        assert len(result.persisted_ids) == 10


def test_compose_skips_when_market_snapshot_missing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        forecasts = tuple(
            _forecast(forecast_run_id=f"fcst-{i}", conid=f"conid-{i}")
            for i in range(5)
        )
        provider = _ContextProvider(missing_snapshot_conids={"conid-2"})
        result = compose_and_persist_for_run(
            ibkr_account_id="DU1234567",
            scheduled_run_id="srun-1",
            forecast_source=_ForecastSource(forecasts),
            context_provider=provider,
            decision_package_repo=repo,
            now_provider=lambda: _BASE,
        )
        assert result.composed == 4
        assert result.missing_context == 1


def test_compose_continues_when_one_composition_errors() -> None:
    class _BoomRepo(SqlAlchemyDecisionPackageRepository):
        call_count: int = 0

        def append(self, record):  # type: ignore[no-untyped-def, override]  # noqa: ANN001
            type(self).call_count += 1
            if type(self).call_count == 3:
                raise RuntimeError("third append blew up")
            return super().append(record)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = _BoomRepo(conn, _report(True))
        forecasts = tuple(
            _forecast(forecast_run_id=f"fcst-{i}", conid=f"conid-{i}")
            for i in range(5)
        )
        result = compose_and_persist_for_run(
            ibkr_account_id="DU1234567",
            scheduled_run_id="srun-1",
            forecast_source=_ForecastSource(forecasts),
            context_provider=_ContextProvider(),
            decision_package_repo=repo,
            now_provider=lambda: _BASE,
        )
        # One persistence failure; the other 4 still ship.
        assert result.forecasts_seen == 5
        assert result.composed == 4
        assert result.composition_errors == 1


def test_compose_wires_previous_package_for_subsequent_runs() -> None:
    """The composer's chain check: second run for the same (account, conid)
    sets previous_package_hash to the first package's audit_trail_hash.
    """

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        # First run.
        forecasts_a = (_forecast(forecast_run_id="fcst-1", conid="ASML.AS"),)
        compose_and_persist_for_run(
            ibkr_account_id="DU1234567",
            scheduled_run_id="srun-1",
            forecast_source=_ForecastSource(forecasts_a),
            context_provider=_ContextProvider(),
            decision_package_repo=repo,
            now_provider=lambda: _BASE,
        )
        # Second run (next morning).
        forecasts_b = (_forecast(forecast_run_id="fcst-2", conid="ASML.AS"),)
        compose_and_persist_for_run(
            ibkr_account_id="DU1234567",
            scheduled_run_id="srun-2",
            forecast_source=_ForecastSource(forecasts_b),
            context_provider=_ContextProvider(),
            decision_package_repo=repo,
            now_provider=lambda: _BASE + timedelta(days=1),
        )
        chain = repo.list_chain(
            ibkr_account_id="DU1234567", conid="ASML.AS", limit=10
        )
        assert len(chain.records) == 2
        newest, oldest = chain.records
        assert newest.previous_package_hash == oldest.audit_trail_hash
        assert oldest.previous_package_hash is None
