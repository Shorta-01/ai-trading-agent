"""Task 130 — calibration step integration tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ForecastEntry,
    SqlAlchemyCalibrationDiaryRepository,
    SqlAlchemyForecastRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.forecasting.calibration_step import (
    run_calibration_step,
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
_LONG_AGO = _NOW - timedelta(days=30)


def _forecast(
    *,
    forecast_run_id: str = "fcst-1",
    generated_at: datetime = _LONG_AGO,
    p10: Decimal = Decimal("-0.05"),
    p90: Decimal = Decimal("0.07"),
    current_price: Decimal = Decimal("100"),
) -> ForecastEntry:
    return ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid="ASML.AS",
        generated_at=generated_at,
        generated_by_scheduled_run_id="srun-old",
        horizon_trading_days=20,
        forecast_valid_until=generated_at + timedelta(days=20),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=current_price,
        currency_local="EUR",
        p10_log_return=p10,
        p50_log_return=Decimal("0.02"),
        p90_log_return=p90,
        prob_positive=Decimal("0.60"),
        prob_loss_gt_5pct=Decimal("0.10"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level="Hoog",
        label="Bekijken",
        block_reason=None,
        expired_at=None,
    )


class _StubRealizedCloses:
    def __init__(self, *, by_conid: dict[str, Decimal | None]) -> None:
        self._by = by_conid

    def get_close_on_or_after(
        self, *, ibkr_conid: str, target_date: date  # noqa: ARG002
    ) -> Decimal | None:
        return self._by.get(ibkr_conid)


def _setup_repos(conn) -> tuple[SqlAlchemyForecastRepository, SqlAlchemyCalibrationDiaryRepository]:  # type: ignore[no-untyped-def]
    metadata.create_all(conn)
    forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
    diary_repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
    return forecast_repo, diary_repo


# ---- hit-status branches -----------------------------------------


def test_within_band_when_realized_lies_between_p10_and_p90() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast(p10=Decimal("-0.10"), p90=Decimal("0.10")))
        # Realized close 102 → realized log return ≈ 0.0198 (within band).
        result = run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("102.0")}
            ),
            now_provider=lambda: _NOW,
        )
        assert result.diary_rows_written == 1
        rows = diary_repo.list_recent(limit=10)
        assert rows.records[0].hit_status == "realized_within_p10_p90"


def test_above_p90_when_realized_above_band() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast(p10=Decimal("-0.10"), p90=Decimal("0.05")))
        # Realized close 120 → log return ≈ 0.182 → above p90 (0.05).
        run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("120.0")}
            ),
            now_provider=lambda: _NOW,
        )
        rows = diary_repo.list_recent(limit=10)
        assert rows.records[0].hit_status == "realized_above_p90"


def test_below_p10_when_realized_below_band() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast(p10=Decimal("-0.03"), p90=Decimal("0.05")))
        # Realized close 90 → log return ≈ -0.105 → below p10.
        run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("90.0")}
            ),
            now_provider=lambda: _NOW,
        )
        rows = diary_repo.list_recent(limit=10)
        assert rows.records[0].hit_status == "realized_below_p10"


# ---- idempotency + edge cases ------------------------------------


def test_calibration_marks_forecast_expired() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast(forecast_run_id="A"))
        run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("105.0")}
            ),
            now_provider=lambda: _NOW,
        )
        found = forecast_repo.get_by_run_id("A")
        assert found is not None
        assert found.expired_at is not None


def test_calibration_skips_when_no_realized_close() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast())
        result = run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": None}
            ),
            now_provider=lambda: _NOW,
        )
        assert result.diary_rows_written == 0
        # No diary row + forecast NOT marked expired.
        found = forecast_repo.get_by_run_id("fcst-1")
        assert found is not None
        assert found.expired_at is None


def test_calibration_skips_unexpired_forecast() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        # Generated 1 day ago, valid for 20 days → still valid.
        forecast_repo.append(
            _forecast(generated_at=_NOW - timedelta(days=1))
        )
        result = run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("105.0")}
            ),
            now_provider=lambda: _NOW,
        )
        assert result.diary_rows_written == 0
        assert result.forecasts_evaluated == 0


def test_calibration_idempotent_on_second_run() -> None:
    """Once a forecast is marked expired it's excluded from the next pass."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        forecast_repo, diary_repo = _setup_repos(conn)
        forecast_repo.append(_forecast(forecast_run_id="fcst-A"))
        first = run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("105.0")}
            ),
            now_provider=lambda: _NOW,
        )
        assert first.diary_rows_written == 1

        second = run_calibration_step(
            forecast_repo=forecast_repo,
            diary_repo=diary_repo,
            realized_close_provider=_StubRealizedCloses(
                by_conid={"ASML.AS": Decimal("105.0")}
            ),
            now_provider=lambda: _NOW,
        )
        assert second.forecasts_evaluated == 0
        assert second.diary_rows_written == 0
