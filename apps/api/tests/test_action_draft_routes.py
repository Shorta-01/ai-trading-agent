"""Task 133 — Action Draft API route tests.

Exercises all seven routes (list/get/create/patch/approve/dismiss/
delete) against a real SQLite database seeded with Decision Package
+ IBKR cash + IBKR position rows.

Storage 503 paths, 404 paths, 422 invalid-transition paths all covered.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    GateOutcome,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    SqlAlchemyDecisionPackageRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
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

_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


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
        latest_expected_revision_id="0051_action_drafts_and_audit",
        database_revision_id=(
            "0051_action_drafts_and_audit" if allowed else None
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


# ---- helpers ----------------------------------------------------------


def _package(
    *,
    package_id: str = "dp-1",
    label: str = "Kopen",
    confidence: str = "Hoog",
) -> DecisionPackageEntry:
    return DecisionPackageEntry(
        decision_package_id=package_id,
        forecast_run_id="fcst-1",
        composed_at=_BASE_TS,
        valid_until=_BASE_TS + timedelta(days=28),
        ibkr_account_id="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("640.00000000"),
        current_price_eur=Decimal("640.00000000"),
        as_of_market_data_ts=_BASE_TS - timedelta(hours=12),
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
        forecast_confidence_level=confidence,
        suggested_action_label=label,
        block_reason=None,
        gate_outcomes=(
            GateOutcome(gate_name="forecast_valid", passed=True, reason_nl=""),
        ),
        evidence_references=(
            EvidenceReference(
                source_id="snap-1",
                source_type="market_data_snapshot",
                claim_summary="snap",
            ),
        ),
        deterministic_dutch_explanation="ex",
        audit_trail_hash="dp-hash",
        previous_package_hash=None,
    )


def _ibkr_run() -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id="sync-1",
        started_at=_BASE_TS,
        completed_at=_BASE_TS + timedelta(seconds=1),
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="ok",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=1,
        cash_values_count=1,
        open_orders_count=0,
        executions_count=0,
        status_nl="ok",
        next_step_nl=None,
        help_nl=None,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=_BASE_TS + timedelta(seconds=1),
        ibkr_account_id="DU1234567",
    )


def _ibkr_cash(amount: Decimal = Decimal("50000")) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="cash-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        base_currency="EUR",
        cash=amount,
        available_funds=amount,
        buying_power=amount,
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


def _ibkr_position(
    qty: Decimal = Decimal("100"),
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id="pos-1",
        sync_run_id="sync-1",
        account_ref="DU1234567",
        conid="ASML.AS",
        symbol="ASML",
        security_type="STK",
        currency="EUR",
        exchange="AEB",
        primary_exchange="AEB",
        quantity=qty,
        average_cost=Decimal("500.00"),
        received_at=_BASE_TS,
        stored_at=_BASE_TS,
        ibkr_account_id="DU1234567",
    )


def _seed_db(tmp_path, *, with_position: bool = False) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "draft.sqlite"
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
                "('0075_runtime_config_profit_target')"
            )
        )
        dp_repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        dp_repo.append(_package())
        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        ibkr_repo.save_ibkr_sync_run(_ibkr_run())
        ibkr_repo.save_ibkr_account_cash_snapshots(
            "sync-1", [_ibkr_cash()]
        )
        if with_position:
            ibkr_repo.save_ibkr_position_snapshots(
                "sync-1", [_ibkr_position()]
            )
    return db_url


# ---- POST /action-draft (from decision package) ----------------------


def test_post_from_decision_package_creates_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.post(
        "/action-draft",
        json={"decision_package_id": "dp-1", "user_note": "test note"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["decision_package_id"] == "dp-1"
    assert body["side"] == "BUY"
    assert body["status"] == "proposed"
    # Hoog × Kopen + 50_000 EUR available + 640 close → 8% × 50_000 = 4000.
    # 4000 / 1 / 638.72 = 6.26 → floor = 6.
    assert Decimal(body["quantity"]) == Decimal("6")
    assert Decimal(body["limit_price_local"]) == Decimal("638.72000000")
    assert body["safe_for_submission"] is False
    assert body["user_note"] == "test note"


def test_post_blocks_when_package_not_found(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.post(
        "/action-draft", json={"decision_package_id": "dp-nope"}
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Decision Package niet gevonden."


def test_post_blocks_when_no_cash_snapshot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """No cash snapshot → 422 with Dutch message (Task 133 §7 validation)."""
    db_path = tmp_path / "draft.sqlite"
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
                "('0075_runtime_config_profit_target')"
            )
        )
        dp_repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        dp_repo.append(_package())
        # No IBKR cash snapshot seeded.
    r = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    assert r.status_code == 422
    assert "cashsnapshot" in r.json()["detail"]


def test_post_returns_503_when_storage_off() -> None:
    r = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    assert r.status_code == 503
    assert r.json()["detail"] == "Opslag is niet beschikbaar."


# ---- GET /action-draft/te-keuren -------------------------------------


def test_get_te_keuren_lists_active_drafts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    # Create one via the API so we have a real row.
    client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    r = client.get("/action-draft/te-keuren?account_id=DU1234567")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ibkr_account_id"] == "DU1234567"
    assert len(body["drafts"]) == 1
    assert body["drafts"][0]["status"] == "proposed"
    assert body["safe_for_submission"] is False


def test_get_te_keuren_uses_account_id_hint_fallback(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    r = client.get("/action-draft/te-keuren")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ibkr_account_id"] == "DU1234567"


def test_get_te_keuren_returns_404_without_account_hint() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "sqlite+pysqlite:///:memory:"
    api_settings.storage.writes_enabled = True
    r = client.get("/action-draft/te-keuren")
    assert r.status_code == 404
    assert r.json()["detail"] == "Geen IBKR-rekening geconfigureerd."


# ---- GET /action-draft/{id} ------------------------------------------


def test_get_by_id_returns_full_payload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    create_resp = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    draft_id = create_resp.json()["action_draft_id"]
    r = client.get(f"/action-draft/{draft_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["action_draft_id"] == draft_id
    assert body["side"] == "BUY"
    assert body["safe_for_submission"] is False


def test_get_by_id_returns_404_for_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/action-draft/missing-id")
    assert r.status_code == 404
    assert r.json()["detail"] == "Actiedraft niet gevonden."


# ---- PATCH /action-draft/{id} ----------------------------------------


def test_patch_updates_quantity_and_flips_to_edited(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.patch(
        f"/action-draft/{draft_id}",
        json={"quantity": "4", "user_note": "kleinere positie"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "edited"
    assert Decimal(body["quantity"]) == Decimal("4")
    assert body["user_note"] == "kleinere positie"
    # Notional recomputed: 4 × 638.72 = 2554.88.
    assert Decimal(body["notional_local"]) == Decimal("2554.88000000")


def test_patch_rejects_zero_quantity(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.patch(
        f"/action-draft/{draft_id}", json={"quantity": "0"}
    )
    assert r.status_code == 422
    assert "moet > 0" in r.json()["detail"]


def test_patch_missing_draft_returns_404(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.patch(
        "/action-draft/missing-id", json={"quantity": "1"}
    )
    assert r.status_code == 404


# ---- POST /action-draft/{id}/approve --------------------------------


def test_approve_proposed_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.post(f"/action-draft/{draft_id}/approve")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "user_approved"
    assert body["user_approved_at"] is not None
    # Safe-for-submission STAYS False — Task 134 will flip it.
    assert body["safe_for_submission"] is False


def test_approve_rejects_already_approved(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    client.post(f"/action-draft/{draft_id}/approve")
    r = client.post(f"/action-draft/{draft_id}/approve")
    assert r.status_code == 422


def test_approve_missing_draft_returns_404(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.post("/action-draft/missing-id/approve")
    assert r.status_code == 404


# ---- POST /action-draft/{id}/dismiss --------------------------------


def test_dismiss_with_reason(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.post(
        f"/action-draft/{draft_id}/dismiss",
        json={"reason": "wacht op event"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "dismissed"
    assert body["dismissed_reason"] == "wacht op event"


def test_dismiss_without_payload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.post(f"/action-draft/{draft_id}/dismiss", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "dismissed"


# ---- POST /action-draft/{id}/delete ----------------------------------


def test_delete_logical_keeps_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]

    r = client.post(f"/action-draft/{draft_id}/delete")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "deleted"
    # Row still exists.
    r2 = client.get(f"/action-draft/{draft_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "deleted"


# ---- state machine: invalid transitions ------------------------------


def test_cannot_dismiss_already_deleted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]
    client.post(f"/action-draft/{draft_id}/delete")
    r = client.post(f"/action-draft/{draft_id}/dismiss")
    assert r.status_code == 422


def test_cannot_patch_already_approved(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    draft_id = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    ).json()["action_draft_id"]
    client.post(f"/action-draft/{draft_id}/approve")
    r = client.patch(
        f"/action-draft/{draft_id}", json={"quantity": "2"}
    )
    assert r.status_code == 422


# ---- non-actionable package label -----------------------------------


def test_post_blocks_houden_package(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "draft.sqlite"
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
                "('0075_runtime_config_profit_target')"
            )
        )
        dp_repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        dp_repo.append(_package(label="Houden"))
        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        ibkr_repo.save_ibkr_sync_run(_ibkr_run())
        ibkr_repo.save_ibkr_account_cash_snapshots("sync-1", [_ibkr_cash()])
    r = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    assert r.status_code == 422
    detail = r.json()["detail"].lower()
    assert "niet actionable" in detail or "not actionable" in detail


# ---- SELL flow (Verkopen) -------------------------------------------


def test_sell_verkopen_uses_held_quantity(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "draft.sqlite"
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
                "('0075_runtime_config_profit_target')"
            )
        )
        dp_repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        dp_repo.append(_package(label="Verkopen"))
        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        ibkr_repo.save_ibkr_sync_run(_ibkr_run())
        ibkr_repo.save_ibkr_account_cash_snapshots("sync-1", [_ibkr_cash()])
        ibkr_repo.save_ibkr_position_snapshots(
            "sync-1", [_ibkr_position(Decimal("80"))]
        )
    r = client.post(
        "/action-draft", json={"decision_package_id": "dp-1"}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["side"] == "SELL"
    assert Decimal(body["quantity"]) == Decimal("80")
