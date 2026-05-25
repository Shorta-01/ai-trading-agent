"""Task 131 — multi-asset extensions to the forecast + calibration repos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

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
    run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    generated_at: datetime | None = None,
    label: str = "Bekijken",
    block_reason: str | None = None,
) -> ForecastEntry:
    ts = generated_at or _BASE_TS
    return ForecastEntry(
        forecast_run_id=run_id,
        conid=conid,
        generated_at=ts,
        generated_by_scheduled_run_id="srun-1",
        horizon_trading_days=20,
        forecast_valid_until=ts + timedelta(days=28),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=Decimal("640.0"),
        currency_local="EUR",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        confidence_level="Hoog",
        label=label,
        block_reason=block_reason,
        expired_at=None,
    )


# ---- get_latest_valid_for_conids ---------------------------------


def test_latest_for_conids_returns_one_per_conid() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(run_id="A", conid="ASML.AS"))
        repo.append(
            _forecast(
                run_id="B",
                conid="ASML.AS",
                generated_at=_BASE_TS + timedelta(hours=1),
                label="Kopen",
            )
        )
        repo.append(_forecast(run_id="C", conid="SAP.DE"))
        rows = repo.get_latest_valid_for_conids(
            conids=("ASML.AS", "SAP.DE"),
            now=_BASE_TS + timedelta(days=1),
        )
        assert len(rows) == 2
        by_conid = {r.conid: r for r in rows}
        # ASML.AS returns the most-recent (Kopen) row, not the earlier one.
        assert by_conid["ASML.AS"].label == "Kopen"
        assert by_conid["SAP.DE"].label == "Bekijken"


def test_latest_for_conids_omits_conids_with_no_valid_forecast() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(run_id="A", conid="ASML.AS"))
        rows = repo.get_latest_valid_for_conids(
            conids=("ASML.AS", "MISSING.DE"),
            now=_BASE_TS + timedelta(days=1),
        )
        assert len(rows) == 1
        assert rows[0].conid == "ASML.AS"


def test_latest_for_conids_excludes_expired_forecasts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(
            _forecast(
                run_id="A",
                conid="ASML.AS",
                generated_at=_BASE_TS - timedelta(days=60),
            )
        )
        rows = repo.get_latest_valid_for_conids(
            conids=("ASML.AS",), now=_BASE_TS
        )
        assert rows == ()


def test_latest_for_conids_empty_input_returns_empty() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        assert repo.get_latest_valid_for_conids(
            conids=(), now=_BASE_TS
        ) == ()


# ---- list_for_date_summary ---------------------------------------


def test_date_summary_counts_labels_per_conid_latest() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        # Three conids, all generated today.
        repo.append(_forecast(run_id="A", conid="X", label="Kopen"))
        repo.append(
            _forecast(
                run_id="B",
                conid="Y",
                generated_at=_BASE_TS + timedelta(minutes=1),
                label="Bekijken",
            )
        )
        repo.append(
            _forecast(
                run_id="C",
                conid="Z",
                generated_at=_BASE_TS + timedelta(minutes=2),
                label="Geblokkeerd",
                block_reason="insufficient_history",
            )
        )
        summary = repo.list_for_date_summary(
            conids=("X", "Y", "Z"), as_of_date=_BASE_TS.date()
        )
        assert summary["total_forecasts"] == 3
        assert summary["total_blocked"] == 1
        assert summary["label_counts"] == {
            "Kopen": 1,
            "Bekijken": 1,
            "Geblokkeerd": 1,
        }
        assert summary["block_reasons"] == {"insufficient_history": 1}


def test_date_summary_takes_only_latest_per_conid_on_date() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        # Two forecasts for the same conid on the same day.
        repo.append(_forecast(run_id="A", conid="X", label="Bekijken"))
        repo.append(
            _forecast(
                run_id="B",
                conid="X",
                generated_at=_BASE_TS + timedelta(hours=1),
                label="Kopen",
            )
        )
        summary = repo.list_for_date_summary(
            conids=("X",), as_of_date=_BASE_TS.date()
        )
        assert summary["total_forecasts"] == 1
        assert summary["label_counts"] == {"Kopen": 1}


def test_date_summary_empty_when_no_forecasts_on_date() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(run_id="A", conid="X"))
        summary = repo.list_for_date_summary(
            conids=("X",),
            as_of_date=(_BASE_TS + timedelta(days=5)).date(),
        )
        assert summary["total_forecasts"] == 0
        assert summary["label_counts"] == {}


# ---- coverage_stats_by_conid -------------------------------------


def test_coverage_by_conid_hit_rate_and_sufficient_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        diary_repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        now = datetime.now(UTC)
        # 6 forecasts for ASML, all evaluated within the last 90 days.
        for index, status in enumerate(
            [
                "realized_within_p10_p90",
                "realized_within_p10_p90",
                "realized_within_p10_p90",
                "realized_within_p10_p90",
                "realized_above_p90",
                "realized_below_p10",
            ]
        ):
            run_id = f"fcst-asml-{index}"
            forecast_repo.append(
                _forecast(
                    run_id=run_id,
                    conid="ASML.AS",
                    generated_at=now - timedelta(days=index + 30),
                )
            )
            diary_repo.append(
                CalibrationDiaryEntry(
                    forecast_run_id=run_id,
                    evaluated_at=now - timedelta(days=index),
                    realized_log_return=Decimal("0.01"),
                    hit_status=status,
                    realized_close_price=Decimal("650.00"),
                )
            )
        stats = diary_repo.coverage_stats_by_conid(
            conid="ASML.AS", window_days=90
        )
        assert stats["conid"] == "ASML.AS"
        assert stats["forecasts_evaluated"] == 6
        assert stats["hit_rate_within_band"] == Decimal("4") / Decimal("6")
        assert stats["sufficient_history"] is True


def test_coverage_by_conid_insufficient_history_flag() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        diary_repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        now = datetime.now(UTC)
        # Only 2 evaluations.
        for index in range(2):
            run_id = f"fcst-{index}"
            forecast_repo.append(
                _forecast(
                    run_id=run_id,
                    conid="SAP.DE",
                    generated_at=now - timedelta(days=index + 30),
                )
            )
            diary_repo.append(
                CalibrationDiaryEntry(
                    forecast_run_id=run_id,
                    evaluated_at=now - timedelta(days=index),
                    realized_log_return=Decimal("0.01"),
                    hit_status="realized_within_p10_p90",
                    realized_close_price=Decimal("100.00"),
                )
            )
        stats = diary_repo.coverage_stats_by_conid(
            conid="SAP.DE", window_days=90, min_sample_size=5
        )
        assert stats["forecasts_evaluated"] == 2
        assert stats["sufficient_history"] is False


def test_coverage_by_conid_other_assets_excluded() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        diary_repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        now = datetime.now(UTC)
        forecast_repo.append(_forecast(run_id="A", conid="ASML.AS"))
        forecast_repo.append(_forecast(run_id="B", conid="SAP.DE"))
        diary_repo.append(
            CalibrationDiaryEntry(
                forecast_run_id="A",
                evaluated_at=now,
                realized_log_return=Decimal("0"),
                hit_status="realized_within_p10_p90",
                realized_close_price=Decimal("100"),
            )
        )
        diary_repo.append(
            CalibrationDiaryEntry(
                forecast_run_id="B",
                evaluated_at=now,
                realized_log_return=Decimal("0"),
                hit_status="realized_above_p90",
                realized_close_price=Decimal("100"),
            )
        )
        asml = diary_repo.coverage_stats_by_conid(conid="ASML.AS")
        assert asml["forecasts_evaluated"] == 1
        assert asml["hit_rate_within_band"] == Decimal("1")
        sap = diary_repo.coverage_stats_by_conid(conid="SAP.DE")
        assert sap["forecasts_evaluated"] == 1
        assert sap["hit_rate_within_band"] == Decimal("0")


def test_coverage_by_conid_empty_returns_nones() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        diary_repo = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        stats = diary_repo.coverage_stats_by_conid(conid="NOPE.AS")
        assert stats["forecasts_evaluated"] == 0
        assert stats["hit_rate_within_band"] is None
        assert stats["sufficient_history"] is False


# ---- ForecastEntry block_reason validation -----------------------


def test_forecast_record_rejects_unknown_block_reason() -> None:
    with pytest.raises(ValueError, match="block_reason"):
        _forecast(
            label="Geblokkeerd", block_reason="totally_made_up_reason"
        )


def test_forecast_record_accepts_task_131_block_reasons() -> None:
    # Smoke: all four Task 131 reasons construct cleanly.
    for reason in (
        "stale_market_data",
        "missing_asset_listing",
        "computation_error",
        "excessive_volatility",
    ):
        rec = _forecast(label="Geblokkeerd", block_reason=reason)
        assert rec.block_reason == reason
