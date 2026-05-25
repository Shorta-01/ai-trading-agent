"""Task 131 — /forecast/day-summary API route tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ForecastEntry,
    SqlAlchemyForecastRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_BASE_TS = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


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


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ibkr_account_id_hint = None
    api_settings.forecast_pilot_conids = "ASML.AS"


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


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


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "fcst.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0049_forecasts_and_calibration_diary')"
            )
        )
    return db_url


# ---- happy paths -----------------------------------------------


def test_day_summary_returns_label_counts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.forecast_pilot_conids = "ASML.AS,SAP.DE,NVDA"
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(run_id="A", conid="ASML.AS", label="Kopen"))
        repo.append(
            _forecast(
                run_id="B",
                conid="SAP.DE",
                label="Bekijken",
                generated_at=_BASE_TS + timedelta(minutes=1),
            )
        )
        repo.append(
            _forecast(
                run_id="C",
                conid="NVDA",
                label="Geblokkeerd",
                block_reason="insufficient_history",
                generated_at=_BASE_TS + timedelta(minutes=2),
            )
        )
    response = client.get(
        f"/forecast/day-summary?as_of_date={_BASE_TS.date().isoformat()}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "DU1234567"
    assert body["as_of_date"] == _BASE_TS.date().isoformat()
    assert body["total_forecasts"] == 3
    assert body["total_blocked"] == 1
    assert body["label_counts"] == {
        "Kopen": 1,
        "Bekijken": 1,
        "Geblokkeerd": 1,
    }
    assert body["block_reasons"] == {"insufficient_history": 1}
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False


def test_day_summary_returns_empty_when_no_forecasts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get(
        f"/forecast/day-summary?as_of_date={_BASE_TS.date().isoformat()}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_forecasts"] == 0
    assert body["total_blocked"] == 0
    assert body["label_counts"] == {}
    assert body["block_reasons"] == {}


def test_day_summary_returns_empty_when_no_account_configured(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    # ibkr_account_id_hint is None — no account.
    response = client.get(
        f"/forecast/day-summary?as_of_date={_BASE_TS.date().isoformat()}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] is None
    assert body["total_forecasts"] == 0


def test_day_summary_accepts_account_id_query_param(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get(
        "/forecast/day-summary?account_id=DU9999999&as_of_date=2026-05-25"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "DU9999999"


def test_day_summary_defaults_to_today_when_no_date_provided(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get("/forecast/day-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["as_of_date"] == datetime.now(UTC).date().isoformat()


# ---- error paths -----------------------------------------------


def test_day_summary_returns_503_when_storage_off() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get(
        f"/forecast/day-summary?as_of_date={_BASE_TS.date().isoformat()}"
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_day_summary_rejects_malformed_date() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get("/forecast/day-summary?as_of_date=not-a-date")
    assert response.status_code == 422


# ---- multi-conid by-account behavior (Task 131 extension) ------


def test_by_account_returns_multiple_conids_after_task_131(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.forecast_pilot_conids = "ASML.AS,SAP.DE,NVDA"
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(run_id="A", conid="ASML.AS", label="Kopen"))
        repo.append(
            _forecast(
                run_id="B",
                conid="SAP.DE",
                label="Bekijken",
                generated_at=_BASE_TS + timedelta(minutes=1),
            )
        )
        # NVDA omitted on purpose: response should omit that conid.
    response = client.get("/forecast/by-account")
    assert response.status_code == 200
    body = response.json()
    conids = sorted(item["conid"] for item in body["items"])
    assert conids == ["ASML.AS", "SAP.DE"]


def test_forecast_latest_includes_per_asset_coverage_block(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(conid="ASML.AS"))
    response = client.get("/forecast/latest?conid=ASML.AS")
    assert response.status_code == 200
    body = response.json()
    assert "per_asset_coverage" in body
    coverage = body["per_asset_coverage"]
    assert coverage["forecasts_evaluated"] == 0
    assert coverage["hit_rate_within_band"] is None
    # No diary rows yet → not sufficient.
    assert coverage["sufficient_history"] is False
