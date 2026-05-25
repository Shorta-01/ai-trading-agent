"""Task 130 — forecast + calibration-diary repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage import (
    CalibrationDiaryEntry,
    ForecastEntry,
    SqlAlchemyCalibrationDiaryRepository,
    SqlAlchemyForecastRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
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


_BASE_TS = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _forecast(
    *,
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    generated_at: datetime | None = None,
    label: str = "Bekijken",
    confidence: str = "Hoog",
    block_reason: str | None = None,
    p50: Decimal = Decimal("0.020"),
) -> ForecastEntry:
    return ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=generated_at or _BASE_TS,
        generated_by_scheduled_run_id="srun-1",
        horizon_trading_days=20,
        forecast_valid_until=(generated_at or _BASE_TS) + timedelta(days=28),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=Decimal("640.123456"),
        currency_local="EUR",
        p10_log_return=Decimal("-0.050"),
        p50_log_return=p50,
        p90_log_return=Decimal("0.080"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level=confidence,
        label=label,
        block_reason=block_reason,
        expired_at=None,
    )


# ---- forecasts -----------------------------------------------------


def test_forecast_append_then_get_by_run_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast())
        found = repo.get_by_run_id("fcst-1")
        assert found is not None
        assert found.conid == "ASML.AS"
        assert found.p50_log_return == Decimal("0.020")


def test_forecast_unique_constraint_blocks_duplicate_conid_generated_at() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(forecast_run_id="A"))
        with pytest.raises(IntegrityError):
            repo.append(_forecast(forecast_run_id="B"))  # same conid+generated_at


def test_forecast_get_latest_valid_returns_most_recent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        early = _forecast(
            forecast_run_id="A", generated_at=_BASE_TS - timedelta(days=2)
        )
        recent = _forecast(
            forecast_run_id="B", generated_at=_BASE_TS
        )
        repo.append(early)
        repo.append(recent)
        latest = repo.get_latest_valid_for_conid(
            conid="ASML.AS", now=_BASE_TS + timedelta(days=1)
        )
        assert latest is not None
        assert latest.forecast_run_id == "B"


def test_forecast_get_latest_valid_excludes_expired() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        # Generated long ago + valid_until well in the past.
        repo.append(
            _forecast(
                forecast_run_id="A",
                generated_at=_BASE_TS - timedelta(days=100),
            )
        )
        latest = repo.get_latest_valid_for_conid(
            conid="ASML.AS", now=_BASE_TS
        )
        assert latest is None


def test_forecast_list_expired_unprocessed_filters_correctly() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        # Two expired (well in the past), one still valid.
        repo.append(
            _forecast(
                forecast_run_id="X",
                generated_at=_BASE_TS - timedelta(days=100),
            )
        )
        repo.append(
            _forecast(
                forecast_run_id="Y",
                conid="VWCE.XETRA",
                generated_at=_BASE_TS - timedelta(days=60),
            )
        )
        repo.append(_forecast(forecast_run_id="Z", conid="SAP.DE"))
        rows = repo.list_expired_unprocessed(now=_BASE_TS)
        ids = {r.forecast_run_id for r in rows.records}
        assert ids == {"X", "Y"}


def test_forecast_mark_expired_updates_only_expired_at() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(forecast_run_id="A"))
        repo.mark_expired(
            forecast_run_id="A", expired_at=_BASE_TS + timedelta(days=30)
        )
        found = repo.get_by_run_id("A")
        assert found is not None
        # SQLite strips tzinfo on round-trip; compare naive components.
        assert found.expired_at is not None
        assert found.expired_at.replace(tzinfo=None) == (
            _BASE_TS + timedelta(days=30)
        ).replace(tzinfo=None)
        # Other fields unchanged.
        assert found.p50_log_return == Decimal("0.020")


def test_forecast_record_rejects_geblokkeerd_without_block_reason() -> None:
    with pytest.raises(ValueError, match="block_reason"):
        _forecast(label="Geblokkeerd", block_reason=None)


def test_forecast_record_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="label"):
        _forecast(label="Freaky")


def test_forecast_record_rejects_prob_out_of_range() -> None:
    with pytest.raises(ValueError, match="prob_positive"):
        ForecastEntry(
            forecast_run_id="x",
            conid="x",
            generated_at=_BASE_TS,
            generated_by_scheduled_run_id="s",
            horizon_trading_days=20,
            forecast_valid_until=_BASE_TS,
            method="historical_bootstrap_v1",
            history_window_days=252,
            history_closes_count=252,
            current_price_local=Decimal("100"),
            currency_local="EUR",
            p10_log_return=Decimal("0"),
            p50_log_return=Decimal("0"),
            p90_log_return=Decimal("0"),
            prob_positive=Decimal("1.5"),
            prob_loss_gt_5pct=Decimal("0.0"),
            expected_volatility_annualized=Decimal("0.2"),
            confidence_level="Hoog",
            label="Bekijken",
            block_reason=None,
            expired_at=None,
        )


# ---- calibration_diary --------------------------------------------


def test_calibration_diary_append_then_list_recent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        repo.append(
            CalibrationDiaryEntry(
                forecast_run_id="fcst-1",
                evaluated_at=_BASE_TS,
                realized_log_return=Decimal("0.0123456789"),
                hit_status="realized_within_p10_p90",
                realized_close_price=Decimal("650.987654"),
            )
        )
        rows = repo.list_recent(limit=10)
        assert len(rows.records) == 1
        assert rows.records[0].hit_status == "realized_within_p10_p90"


def test_calibration_diary_unique_constraint_one_row_per_forecast() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        row = CalibrationDiaryEntry(
            forecast_run_id="fcst-1",
            evaluated_at=_BASE_TS,
            realized_log_return=Decimal("0.01"),
            hit_status="realized_within_p10_p90",
            realized_close_price=Decimal("650.00"),
        )
        repo.append(row)
        with pytest.raises(IntegrityError):
            repo.append(row)


def test_calibration_diary_coverage_stats_with_mixed_outcomes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        from datetime import datetime as _dt

        now = _dt.now(UTC)
        # 3 within band, 1 above, 1 below.
        outcomes = [
            ("realized_within_p10_p90"),
            ("realized_within_p10_p90"),
            ("realized_within_p10_p90"),
            ("realized_above_p90"),
            ("realized_below_p10"),
        ]
        for index, status in enumerate(outcomes):
            repo.append(
                CalibrationDiaryEntry(
                    forecast_run_id=f"fcst-{index}",
                    evaluated_at=now - timedelta(days=index),
                    realized_log_return=Decimal("0.01"),
                    hit_status=status,
                    realized_close_price=Decimal("600.00"),
                )
            )
        stats = repo.coverage_stats(window_days=90)
        assert stats["forecasts_evaluated"] == 5
        assert stats["hit_rate_within_band"] == Decimal("3") / Decimal("5")


def test_calibration_diary_coverage_stats_empty_returns_nones() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        stats = repo.coverage_stats(window_days=90)
        assert stats["forecasts_evaluated"] == 0
        assert stats["hit_rate_within_band"] is None


def test_calibration_diary_rejects_unknown_hit_status() -> None:
    with pytest.raises(ValueError, match="hit_status"):
        CalibrationDiaryEntry(
            forecast_run_id="x",
            evaluated_at=_BASE_TS,
            realized_log_return=Decimal("0"),
            hit_status="weird",
            realized_close_price=Decimal("100"),
        )
