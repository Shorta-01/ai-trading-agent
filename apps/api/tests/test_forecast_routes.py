"""Task 130 — forecast + calibration API route tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    CalibrationDiaryEntry,
    ForecastEntry,
    FxRateRecord,
    SqlAlchemyCalibrationDiaryRepository,
    SqlAlchemyForecastRepository,
    SqlAlchemyFxRateRepository,
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
_BASE_DATE = date(2026, 5, 25)


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
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    generated_at: datetime | None = None,
    currency_local: str = "EUR",
    label: str = "Bekijken",
    block_reason: str | None = None,
) -> ForecastEntry:
    ts = generated_at or _BASE_TS
    return ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=ts,
        generated_by_scheduled_run_id="srun-1",
        horizon_trading_days=20,
        forecast_valid_until=ts + timedelta(days=28),
        method="historical_bootstrap_v1",
        history_window_days=252,
        history_closes_count=252,
        current_price_local=Decimal("640.000000"),
        currency_local=currency_local,
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


# ---- /forecast/latest -------------------------------------------


def test_latest_returns_503_when_storage_off() -> None:
    response = client.get("/forecast/latest?conid=ASML.AS")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_latest_returns_404_when_no_forecast(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/forecast/latest?conid=ASML.AS")
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Geen geldige voorspelling voor dit asset."
    }


def test_latest_returns_full_payload_with_eur_native_levels(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast())
    response = client.get("/forecast/latest?conid=ASML.AS")
    assert response.status_code == 200
    body = response.json()
    assert body["conid"] == "ASML.AS"
    assert body["currency_local"] == "EUR"
    assert body["label"] == "Bekijken"
    assert body["confidence_level"] == "Hoog"
    assert body["method"] == "historical_bootstrap_v1"
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False
    # EUR-native: eur fields equal local fields (no FX conversion).
    assert body["p50_price_eur"] == body["p50_price_local"]
    # p50 price ≈ 640 * exp(0.02) = ~653.... Validate Decimal-as-string round-trip.
    assert Decimal(body["p50_price_local"]) > Decimal("640")
    assert Decimal(body["p10_price_local"]) < Decimal(body["p50_price_local"])
    assert Decimal(body["p50_price_local"]) < Decimal(body["p90_price_local"])


def test_latest_applies_fx_conversion_for_non_eur(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(conid="NVDA", currency_local="USD"))
        fx = SqlAlchemyFxRateRepository(conn, _report(True))
        fx.upsert(
            FxRateRecord(
                base_currency="USD",
                quote_currency="EUR",
                as_of_date=_BASE_DATE,
                rate=Decimal("0.91"),
                ingested_ts=_BASE_TS,
                provider="eodhd",
            )
        )
    response = client.get("/forecast/latest?conid=NVDA")
    assert response.status_code == 200
    body = response.json()
    assert body["currency_local"] == "USD"
    assert Decimal(body["p50_price_eur"]) == (
        Decimal(body["p50_price_local"]) * Decimal("0.91")
    ).quantize(Decimal("0.000001"))


def test_latest_eur_levels_null_when_fx_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast(conid="NVDA", currency_local="USD"))
    response = client.get("/forecast/latest?conid=NVDA")
    assert response.status_code == 200
    body = response.json()
    assert body["p10_price_eur"] is None
    assert body["p50_price_eur"] is None
    assert body["p90_price_eur"] is None


# ---- /forecast/by-account ---------------------------------------


def test_by_account_returns_empty_when_no_account_hint() -> None:
    response = client.get("/forecast/by-account")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] is None
    assert body["items"] == []
    assert body["safe_for_action_drafts"] is False


def test_by_account_returns_items_for_configured_pilot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast())
    response = client.get("/forecast/by-account")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "DU1234567"
    assert len(body["items"]) == 1
    assert body["items"][0]["conid"] == "ASML.AS"
    assert body["items"][0]["label"] == "Bekijken"
    assert body["items"][0]["user_holds_position"] is False


def test_by_account_skips_pilot_conids_without_valid_forecast(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.forecast_pilot_conids = "ASML.AS,SAP.DE"
    response = client.get("/forecast/by-account")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []


def test_by_account_returns_503_when_storage_off() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get("/forecast/by-account")
    assert response.status_code == 503


def test_by_account_accepts_account_id_query_param(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyForecastRepository(conn, _report(True))
        repo.append(_forecast())
    response = client.get("/forecast/by-account?account_id=DU9999999")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "DU9999999"


# ---- /calibration/coverage --------------------------------------


def test_coverage_returns_503_when_storage_off() -> None:
    response = client.get("/calibration/coverage")
    assert response.status_code == 503


def test_coverage_returns_nones_when_diary_empty(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/calibration/coverage?window_days=90")
    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 90
    assert body["forecasts_evaluated"] == 0
    assert body["hit_rate_within_band"] is None
    assert body["safe_for_orders"] is False


def test_coverage_returns_hit_rate_when_diary_has_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    now = datetime.now(UTC)
    with engine.begin() as conn:
        diary = SqlAlchemyCalibrationDiaryRepository(conn, _report(True))
        for index, status in enumerate(
            [
                "realized_within_p10_p90",
                "realized_within_p10_p90",
                "realized_above_p90",
            ]
        ):
            diary.append(
                CalibrationDiaryEntry(
                    forecast_run_id=f"fcst-{index}",
                    evaluated_at=now - timedelta(days=index),
                    realized_log_return=Decimal("0.01"),
                    hit_status=status,
                    realized_close_price=Decimal("600.00"),
                )
            )
    response = client.get("/calibration/coverage?window_days=90")
    assert response.status_code == 200
    body = response.json()
    assert body["forecasts_evaluated"] == 3
    assert Decimal(body["hit_rate_within_band"]) == Decimal("2") / Decimal("3")


def test_coverage_rejects_bad_window_days() -> None:
    response = client.get("/calibration/coverage?window_days=0")
    assert response.status_code == 422
    response = client.get("/calibration/coverage?window_days=999")
    assert response.status_code == 422
