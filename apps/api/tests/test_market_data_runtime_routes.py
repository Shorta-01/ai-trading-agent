"""Task 129 — market-data runtime route tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    FxRateRecord,
    MarketDataEodSnapshotEntry,
    ProviderCallAuditEntry,
    SqlAlchemyFxRateRepository,
    SqlAlchemyMarketDataEodSnapshotRepository,
    SqlAlchemyProviderCallAuditRepository,
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

_BASE_DATE = date(2026, 5, 24)
_BASE_TS = datetime(2026, 5, 24, 17, 0, tzinfo=UTC)


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
        latest_expected_revision_id="0048_market_data_eod_and_fx_runtime",
        database_revision_id=(
            "0048_market_data_eod_and_fx_runtime" if allowed else None
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


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "md.sqlite"
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
                "('0048_market_data_eod_and_fx_runtime')"
            )
        )
        snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        snap_repo.append(
            MarketDataEodSnapshotEntry(
                snapshot_id="snap-eur",
                ibkr_conid="111",
                symbol="ASML",
                exchange="AEB",
                currency_local="EUR",
                as_of_date=_BASE_DATE,
                as_of_close_ts=_BASE_TS,
                ingested_ts=_BASE_TS,
                open_local=Decimal("635.0"),
                high_local=Decimal("642.5"),
                low_local=Decimal("634.0"),
                close_local=Decimal("640.123456"),
                adj_close_local=Decimal("640.123456"),
                volume=123456,
                provider="eodhd",
                provider_response_hash="deadbeef" * 8,
            )
        )
        snap_repo.append(
            MarketDataEodSnapshotEntry(
                snapshot_id="snap-usd",
                ibkr_conid="222",
                symbol="NVDA",
                exchange="NASDAQ",
                currency_local="USD",
                as_of_date=_BASE_DATE,
                as_of_close_ts=_BASE_TS,
                ingested_ts=_BASE_TS,
                open_local=None,
                high_local=None,
                low_local=None,
                close_local=Decimal("900.00"),
                adj_close_local=Decimal("900.00"),
                volume=1_000_000,
                provider="eodhd",
                provider_response_hash="cafebabe" * 8,
            )
        )
        fx_repo = SqlAlchemyFxRateRepository(conn, _report(True))
        fx_repo.upsert(
            FxRateRecord(
                base_currency="USD",
                quote_currency="EUR",
                as_of_date=_BASE_DATE,
                rate=Decimal("0.91"),
                ingested_ts=_BASE_TS,
                provider="eodhd",
            )
        )
    return db_url


# ---- /market-data/eod/snapshots/latest --------------------------


def test_latest_returns_404_when_no_snapshot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/market-data/eod/snapshots/latest?conid=does-not-exist")
    assert response.status_code == 404


def test_latest_returns_503_when_storage_off() -> None:
    response = client.get("/market-data/eod/snapshots/latest?conid=111")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_latest_returns_eur_native_decimal_preserved(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/market-data/eod/snapshots/latest?conid=111")
    body = response.json()
    assert response.status_code == 200
    assert body["symbol"] == "ASML"
    assert body["close_local"] == "640.123456"
    assert body["currency_local"] == "EUR"
    # EUR-native: close_eur equals close_local + no FX rate applied.
    assert body["close_eur"] == "640.123456"
    assert body["fx_rate_used"] is None


def test_latest_applies_fx_join_for_non_eur(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/market-data/eod/snapshots/latest?conid=222")
    body = response.json()
    assert response.status_code == 200
    assert body["currency_local"] == "USD"
    # SQLite stores Numeric(20,8) with trailing zeros; compare via Decimal.
    assert Decimal(body["fx_rate_used"]) == Decimal("0.91")
    assert Decimal(body["close_eur"]) == Decimal("900.00") * Decimal("0.91")


# ---- /market-data/eod/snapshots/by-account ----------------------


def test_by_account_returns_empty_when_no_account_hint() -> None:
    response = client.get("/market-data/eod/snapshots/by-account")
    body = response.json()
    assert response.status_code == 200
    assert body["account_id"] is None
    assert body["items"] == []


# ---- /market-data/provider-calls --------------------------------


def test_provider_calls_returns_recent_audit_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyProviderCallAuditRepository(conn, _report(True))
        repo.append(
            ProviderCallAuditEntry(
                audit_id="aud-1",
                called_at=_BASE_TS,
                provider="eodhd",
                endpoint="/api/eod/ASML.AEB",
                request_params_json=None,
                response_status=200,
                response_size_bytes=512,
                duration_ms=150,
                error_class=None,
                error_details_json=None,
                account_id="DU1234567",
                triggered_by_run_id="srun-1",
            )
        )
    response = client.get("/market-data/provider-calls?limit=10")
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["audit_id"] == "aud-1"
    assert body["items"][0]["response_status"] == 200
    assert body["safe_for_orders"] is False


def test_provider_calls_rejects_bad_limit() -> None:
    response = client.get("/market-data/provider-calls?limit=0")
    assert response.status_code == 422
    response = client.get("/market-data/provider-calls?limit=999")
    assert response.status_code == 422


def test_provider_calls_returns_503_when_storage_off() -> None:
    response = client.get("/market-data/provider-calls")
    assert response.status_code == 503
