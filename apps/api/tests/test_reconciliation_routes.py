"""Task 135b — reconciliation API route tests.

Covers all six new routes against a real SQLite database seeded with
reconciliation_audit, reconciliation_run_audit, manual_review_queue,
and unmatched_execution_audit rows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ManualReviewQueueEntry,
    ReconciliationAuditEntry,
    ReconciliationRunAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyReconciliationRunAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
    UnmatchedExecutionAuditEntry,
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

_LATEST = "0053_reconciliation_audit_and_manual_review"
# Seed relative to the real clock: the /reconciliation/status route computes
# its "last 24h" window from datetime.now(UTC) (reconciliation.py), so a fixed
# past _NOW makes the seeded healed-event age out of the window over time.
_NOW = datetime.now(UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=_LATEST,
        database_revision_id=_LATEST,
        persistence_allowed=True,
        blocks_runtime_writes=False,
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


def _seed_db(  # type: ignore[no-untyped-def]
    tmp_path,
    *,
    with_run: bool = True,
    with_audit: bool = True,
    with_queue: bool = True,
    with_unmatched: bool = True,
) -> str:
    db_path = tmp_path / "recon.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_account_id_hint = "DU1234567"

    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                f"INSERT INTO alembic_version (version_num) VALUES ('{_LATEST}')"
            )
        )

        if with_run:
            run_repo = SqlAlchemyReconciliationRunAuditRepository(
                conn, _report()
            )
            run_repo.append(
                ReconciliationRunAuditEntry(
                    reconciliation_run_id="run-1",
                    started_at=_NOW - timedelta(minutes=10),
                    completed_at=_NOW - timedelta(minutes=9),
                    account_id="DU1234567",
                    pass_a_orphaned_count=1,
                    pass_b_stale_count=0,
                    pass_c_timeout_count=2,
                    divergences_found=3,
                    mode_detected="completed",
                    error_details_json=None,
                )
            )

        if with_audit:
            # Need a draft for the FK + the dashboard widget query.
            draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
            draft_repo.append(
                ActionDraftEntry(
                    action_draft_id="d-healed",
                    decision_package_id=None,
                    forecast_run_id=None,
                    created_at=_NOW - timedelta(hours=1),
                    created_by="user",
                    ibkr_account_id="DU1234567",
                    conid="12345",
                    symbol="ASML",
                    exchange="AEB",
                    currency_local="EUR",
                    side="BUY",
                    quantity=Decimal("6"),
                    order_type="LMT",
                    limit_price_local=Decimal("638.72"),
                    time_in_force="DAY",
                    notional_local=Decimal("3832.32"),
                    notional_eur=Decimal("3832.32"),
                    fx_rate_at_creation=Decimal("1"),
                    usable_cash_eur_at_creation=Decimal("50000"),
                    held_quantity_at_creation=None,
                    status="proposed",
                    last_edited_at=None,
                    user_approved_at=_NOW - timedelta(minutes=45),
                    dismissed_at=None,
                    deleted_at=None,
                    dismissed_reason=None,
                    user_note=None,
                    superseded_by_decision_package_id=None,
                    audit_trail_hash="hash-d-healed",
                    previous_draft_hash=None,
                    safe_for_submission=False,
                )
            )
            audit_repo = SqlAlchemyReconciliationAuditRepository(
                conn, _report()
            )
            audit_repo.append(
                ReconciliationAuditEntry(
                    reconciliation_run_id="run-1",
                    action_draft_id="d-healed",
                    event_at=_NOW - timedelta(minutes=9, seconds=30),
                    pass_name="orphaned_execution",
                    divergence_type="missing_execution_applied",
                    before_status="submitted",
                    after_status="submitted",
                    ibkr_evidence_json={"ibkr_exec_id": "exec-A"},
                    notes_dutch=(
                        "Ontbrekende IBKR-uitvoering teruggevonden."
                    ),
                )
            )
            audit_repo.append(
                ReconciliationAuditEntry(
                    reconciliation_run_id="run-1",
                    action_draft_id="d-healed",
                    event_at=_NOW - timedelta(minutes=9, seconds=29),
                    pass_name="orphaned_execution",
                    divergence_type="status_corrected_to_filled",
                    before_status="submitted",
                    after_status="filled",
                    ibkr_evidence_json={"ibkr_exec_id": "exec-A"},
                    notes_dutch="Status hersteld.",
                )
            )

        if with_queue:
            # Need a draft + walk it to a status the queue can target.
            draft_repo2 = SqlAlchemyActionDraftRepository(conn, _report())
            draft_repo2.append(
                ActionDraftEntry(
                    action_draft_id="d-review",
                    decision_package_id=None,
                    forecast_run_id=None,
                    created_at=_NOW - timedelta(hours=30),
                    created_by="user",
                    ibkr_account_id="DU1234567",
                    conid="67890",
                    symbol="ASML",
                    exchange="AEB",
                    currency_local="EUR",
                    side="BUY",
                    quantity=Decimal("6"),
                    order_type="LMT",
                    limit_price_local=Decimal("638.72"),
                    time_in_force="DAY",
                    notional_local=Decimal("3832.32"),
                    notional_eur=Decimal("3832.32"),
                    fx_rate_at_creation=Decimal("1"),
                    usable_cash_eur_at_creation=Decimal("50000"),
                    held_quantity_at_creation=None,
                    status="proposed",
                    last_edited_at=None,
                    user_approved_at=_NOW - timedelta(hours=29),
                    dismissed_at=None,
                    deleted_at=None,
                    dismissed_reason=None,
                    user_note=None,
                    superseded_by_decision_package_id=None,
                    audit_trail_hash="hash-d-review",
                    previous_draft_hash=None,
                    safe_for_submission=False,
                )
            )
            queue_repo = SqlAlchemyManualReviewQueueRepository(
                conn, _report()
            )
            queue_repo.append(
                ManualReviewQueueEntry(
                    flagged_at=_NOW - timedelta(minutes=5),
                    action_draft_id="d-review",
                    reason="timeout_24h_no_data",
                    details_dutch=(
                        "24 uur geen IBKR-data — handmatige beoordeling."
                    ),
                    resolution_status="pending",
                )
            )

        if with_unmatched:
            unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
                conn, _report()
            )
            unmatched_repo.append(
                UnmatchedExecutionAuditEntry(
                    event_at=_NOW - timedelta(minutes=2),
                    ibkr_perm_id=900900,
                    ibkr_exec_id="tws-1",
                    account_id="DU1234567",
                    conid="98765",
                    side="BUY",
                    fill_price_local=Decimal("100.50"),
                    fill_quantity=Decimal("10"),
                    fill_time=_NOW - timedelta(minutes=3),
                    raw_execution_json={"source": "TWS"},
                    resolution_status="unresolved",
                )
            )
    return db_url


# ---- GET /reconciliation/status ----------------------------------


def test_status_returns_full_payload_when_seeded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/reconciliation/status")
    assert response.status_code == 200
    body = response.json()
    assert body["ibkr_account_id"] == "DU1234567"
    assert body["latest_run"] is not None
    assert body["latest_run"]["reconciliation_run_id"] == "run-1"
    assert body["latest_run"]["pass_a_orphaned_count"] == 1
    assert body["pending_manual_review_count"] == 1
    assert body["unresolved_unmatched_count"] == 1
    assert body["drafts_healed_last_24h"] == 1


def test_status_404_when_no_account_configured() -> None:
    response = client.get("/reconciliation/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Geen IBKR-rekening geconfigureerd."


def test_status_503_when_storage_disabled() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    response = client.get("/reconciliation/status")
    assert response.status_code == 503
    assert response.json()["detail"] == "Opslag is niet beschikbaar."


# ---- GET /reconciliation/runs ------------------------------------


def test_runs_returns_history_newest_first(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    # Add a second, more recent run.
    engine = create_engine(db_url)
    with engine.begin() as conn:
        run_repo = SqlAlchemyReconciliationRunAuditRepository(
            conn, _report()
        )
        run_repo.append(
            ReconciliationRunAuditEntry(
                reconciliation_run_id="run-2",
                started_at=_NOW - timedelta(minutes=1),
                completed_at=_NOW,
                account_id="DU1234567",
                pass_a_orphaned_count=0,
                pass_b_stale_count=0,
                pass_c_timeout_count=0,
                divergences_found=0,
                mode_detected="completed",
                error_details_json=None,
            )
        )

    response = client.get("/reconciliation/runs")
    body = response.json()
    assert response.status_code == 200
    assert [r["reconciliation_run_id"] for r in body["runs"]] == [
        "run-2",
        "run-1",
    ]


def test_runs_returns_empty_list_when_no_runs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path, with_run=False, with_audit=False, with_queue=False, with_unmatched=False)
    response = client.get("/reconciliation/runs")
    assert response.status_code == 200
    assert response.json()["runs"] == []


# ---- GET /reconciliation/audit -----------------------------------


def test_audit_returns_recent_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/reconciliation/audit")
    body = response.json()
    assert response.status_code == 200
    divergences = {row["divergence_type"] for row in body["rows"]}
    assert "missing_execution_applied" in divergences
    assert "status_corrected_to_filled" in divergences


# ---- GET /reconciliation/manual-review ---------------------------


def test_manual_review_returns_pending_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/reconciliation/manual-review")
    body = response.json()
    assert response.status_code == 200
    assert len(body["rows"]) == 1
    assert body["rows"][0]["action_draft_id"] == "d-review"
    assert body["rows"][0]["reason"] == "timeout_24h_no_data"
    assert body["rows"][0]["resolution_status"] == "pending"


# ---- POST /reconciliation/manual-review/{id}/acknowledge -------


def test_acknowledge_flips_pending_to_acknowledged(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    # Find the queue row id.
    engine = create_engine(db_url)
    with engine.begin() as conn:
        queue_repo = SqlAlchemyManualReviewQueueRepository(
            conn, _report()
        )
        pending = queue_repo.list_pending_for_account("DU1234567")
        queue_id = pending[0].id
    assert queue_id is not None

    response = client.post(
        f"/reconciliation/manual-review/{queue_id}/acknowledge",
        params={"note": "Door gebruiker bevestigd."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_status"] == "acknowledged"
    assert body["resolution_note"] == "Door gebruiker bevestigd."

    # Pending list is now empty.
    listing = client.get("/reconciliation/manual-review").json()
    assert listing["rows"] == []


def test_acknowledge_returns_404_for_unknown_id(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.post(
        "/reconciliation/manual-review/9999/acknowledge"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Beoordelingsrij niet gevonden."


# ---- GET /reconciliation/unmatched-executions --------------------


def test_unmatched_returns_unresolved_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    response = client.get("/reconciliation/unmatched-executions")
    body = response.json()
    assert response.status_code == 200
    assert len(body["rows"]) == 1
    assert body["rows"][0]["ibkr_exec_id"] == "tws-1"
    assert body["rows"][0]["resolution_status"] == "unresolved"


def test_unmatched_returns_empty_list_when_none(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path, with_run=False, with_audit=False, with_queue=False, with_unmatched=False)
    response = client.get("/reconciliation/unmatched-executions")
    assert response.status_code == 200
    assert response.json()["rows"] == []
