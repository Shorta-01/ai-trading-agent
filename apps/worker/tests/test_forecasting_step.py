"""Task 130 — forecasting step integration tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import SqlAlchemyForecastRepository
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.forecasting.forecasting_step import (
    run_forecasting_step,
)


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
        latest_expected_revision_id="0049_forecasts_and_calibration_diary",
        database_revision_id=(
            "0049_forecasts_and_calibration_diary" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_NOW = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _StubCloseProvider:
    def __init__(
        self, *, closes_by_conid: dict[str, tuple[tuple[date, Decimal], ...]]
    ) -> None:
        self._closes = closes_by_conid

    def list_recent_closes(
        self, *, ibkr_conid: str, days: int  # noqa: ARG002
    ) -> tuple[tuple[date, Decimal], ...]:
        return self._closes.get(ibkr_conid, tuple())


class _StubHoldings:
    def __init__(self, *, held_conids: set[str]) -> None:
        self._held = held_conids

    def holds_conid(
        self, *, ibkr_account_id: str, ibkr_conid: str  # noqa: ARG002
    ) -> bool:
        return ibkr_conid in self._held


def _make_history(*, count: int, latest_date: date) -> tuple[tuple[date, Decimal], ...]:
    rows: list[tuple[date, Decimal]] = []
    base = latest_date - timedelta(days=count - 1)
    price = Decimal("640.123456")
    for i in range(count):
        rows.append((base + timedelta(days=i), price))
    return tuple(rows)


def test_forecasting_step_writes_one_row_per_pilot_conid() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        close_provider = _StubCloseProvider(
            closes_by_conid={
                "ASML.AS": _make_history(count=252, latest_date=_NOW.date()),
            }
        )
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            pilot_conids=("ASML.AS",),
            close_provider=close_provider,
            holdings=_StubHoldings(held_conids=set()),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=500,
        )
        assert result.pilot_conids_attempted == 1
        assert result.forecasts_written == 1
        # One row in storage.
        latest = forecast_repo.get_latest_valid_for_conid(
            conid="ASML.AS", now=_NOW
        )
        assert latest is not None
        assert latest.method == "historical_bootstrap_v1"
        # Flat-price history → not Kopen/Verkopen; expected Bekijken or Houden.
        assert latest.label in ("Bekijken", "Houden")


def test_forecasting_step_blocks_insufficient_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        close_provider = _StubCloseProvider(
            closes_by_conid={
                "ASML.AS": _make_history(count=100, latest_date=_NOW.date()),
            }
        )
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            pilot_conids=("ASML.AS",),
            close_provider=close_provider,
            holdings=_StubHoldings(held_conids=set()),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-2",
            now_provider=lambda: _NOW,
            rng_seed=42,
        )
        assert result.forecasts_written == 1
        latest = forecast_repo.get_latest_valid_for_conid(
            conid="ASML.AS", now=_NOW
        )
        assert latest is not None
        assert latest.label == "Geblokkeerd"
        assert latest.block_reason == "insufficient_history"


def test_forecasting_step_handles_missing_data_gracefully() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        close_provider = _StubCloseProvider(closes_by_conid={})
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            pilot_conids=("ASML.AS",),
            close_provider=close_provider,
            holdings=_StubHoldings(held_conids=set()),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-3",
            now_provider=lambda: _NOW,
            rng_seed=42,
        )
        # Empty close list → blocked (no forecast row written).
        assert result.forecasts_written == 0
        assert result.per_conid[0].label == "Geblokkeerd"
        assert result.per_conid[0].block_reason == "data_unavailable"


def test_forecasting_step_handles_multiple_pilot_conids() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        close_provider = _StubCloseProvider(
            closes_by_conid={
                "ASML.AS": _make_history(count=252, latest_date=_NOW.date()),
                "VWCE.XETRA": _make_history(count=252, latest_date=_NOW.date()),
            }
        )
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            pilot_conids=("ASML.AS", "VWCE.XETRA"),
            close_provider=close_provider,
            holdings=_StubHoldings(held_conids=set()),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-4",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=300,
        )
        assert result.pilot_conids_attempted == 2
        assert result.forecasts_written == 2
