"""Task 132 — Decision Package API route tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    GateOutcome,
    SqlAlchemyDecisionPackageRepository,
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
        latest_expected_revision_id="0050_decision_packages",
        database_revision_id=(
            "0050_decision_packages" if allowed else None
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


def _package(
    *,
    package_id: str = "dp-1",
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    account_id: str = "DU1234567",
    composed_at: datetime | None = None,
    audit_trail_hash: str = "hash-1",
    previous_package_hash: str | None = None,
    label: str = "Bekijken",
) -> DecisionPackageEntry:
    ts = composed_at or _BASE_TS
    return DecisionPackageEntry(
        decision_package_id=package_id,
        forecast_run_id=forecast_run_id,
        composed_at=ts,
        valid_until=ts + timedelta(days=28),
        ibkr_account_id=account_id,
        conid=conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("640.123456"),
        current_price_eur=Decimal("640.123456"),
        as_of_market_data_ts=ts - timedelta(hours=12),
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("608.769000"),
        p50_price_eur=Decimal("652.929000"),
        p90_price_eur=Decimal("693.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        forecast_confidence_level="Hoog",
        suggested_action_label=label,
        block_reason=None,
        gate_outcomes=(
            GateOutcome(
                gate_name="forecast_valid", passed=True, reason_nl=""
            ),
            GateOutcome(
                gate_name="data_fresh", passed=True, reason_nl=""
            ),
        ),
        evidence_references=(
            EvidenceReference(
                source_id="snap-1",
                source_type="market_data_snapshot",
                claim_summary="EOD-snapshot voor ASML",
            ),
        ),
        deterministic_dutch_explanation=(
            "Voor ASML duidt de voorspelling op een signaal om te bekijken."
        ),
        audit_trail_hash=audit_trail_hash,
        previous_package_hash=previous_package_hash,
    )


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "dp.sqlite"
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
                "('0050_decision_packages')"
            )
        )
    return db_url


# ---- /decision-package/{id} -------------------------------------


def test_get_by_id_returns_full_payload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        repo.append(_package())

    response = client.get("/decision-package/dp-1")
    assert response.status_code == 200
    body = response.json()
    assert body["decision_package_id"] == "dp-1"
    assert body["conid"] == "ASML.AS"
    assert body["suggested_action_label"] == "Bekijken"
    # Decimal preservation end-to-end. The Numeric(20, 8) column
    # normalizes scale, so the wire string carries the column scale
    # (not the input scale) — what matters is that no precision is
    # lost relative to the column definition.
    assert Decimal(body["current_price_local"]) == Decimal("640.123456")
    assert Decimal(body["current_price_eur"]) == Decimal("640.123456")
    assert Decimal(body["p50_price_eur"]) == Decimal("652.929000")
    assert Decimal(body["prob_positive"]) == Decimal("0.62")
    # Gate outcomes round-trip.
    assert len(body["gate_outcomes"]) == 2
    assert body["gate_outcomes"][0]["gate_name"] == "forecast_valid"
    assert body["gate_outcomes"][0]["passed"] is True
    # Evidence refs round-trip.
    assert body["evidence_references"][0]["source_type"] == (
        "market_data_snapshot"
    )
    # Safety booleans hard-False.
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False


def test_get_by_id_returns_404_for_unknown_id(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/decision-package/dp-missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Decision Package niet gevonden."}


def test_get_by_id_returns_503_when_storage_off() -> None:
    response = client.get("/decision-package/dp-1")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


# ---- /decision-package/latest -----------------------------------


def test_get_latest_returns_most_recent_package(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        repo.append(
            _package(
                package_id="dp-old",
                audit_trail_hash="h-old",
                composed_at=_BASE_TS - timedelta(days=2),
            )
        )
        repo.append(
            _package(
                package_id="dp-new",
                audit_trail_hash="h-new",
                previous_package_hash="h-old",
                composed_at=_BASE_TS,
            )
        )

    response = client.get(
        "/decision-package/latest?conid=ASML.AS&account_id=DU1234567"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision_package_id"] == "dp-new"
    assert body["previous_package_hash"] == "h-old"


def test_get_latest_returns_404_when_no_package(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get(
        "/decision-package/latest?conid=ASML.AS&account_id=DU1234567"
    )
    assert response.status_code == 404


def test_get_latest_returns_503_when_storage_off() -> None:
    response = client.get(
        "/decision-package/latest?conid=ASML.AS&account_id=DU1234567"
    )
    assert response.status_code == 503


# ---- /decision-package/chain -----------------------------------


def test_get_chain_returns_packages_newest_first(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        for i in range(3):
            repo.append(
                _package(
                    package_id=f"dp-{i}",
                    audit_trail_hash=f"h-{i}",
                    previous_package_hash=f"h-{i - 1}" if i > 0 else None,
                    composed_at=_BASE_TS + timedelta(hours=i),
                )
            )

    response = client.get(
        "/decision-package/chain?conid=ASML.AS&account_id=DU1234567&limit=10"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ibkr_account_id"] == "DU1234567"
    assert body["conid"] == "ASML.AS"
    ids = [p["decision_package_id"] for p in body["packages"]]
    assert ids == ["dp-2", "dp-1", "dp-0"]


def test_get_chain_returns_empty_list_when_no_packages(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get(
        "/decision-package/chain?conid=ASML.AS&account_id=DU1234567&limit=10"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["packages"] == []


def test_get_chain_rejects_limit_above_50() -> None:
    response = client.get(
        "/decision-package/chain?conid=X&account_id=Y&limit=51"
    )
    assert response.status_code == 422


def test_get_chain_returns_503_when_storage_off() -> None:
    response = client.get(
        "/decision-package/chain?conid=X&account_id=Y&limit=10"
    )
    assert response.status_code == 503
