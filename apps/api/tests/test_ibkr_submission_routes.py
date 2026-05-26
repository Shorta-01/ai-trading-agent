"""Task 134c — IBKR submission read API tests.

Drives all five GET routes against a real SQLite database seeded with
draft + audit + lifecycle + executions rows. Covers happy paths, 404
fallback semantics, and the 503 storage-unavailable path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrExecutionEntry,
    IbkrSubmissionAuditEntry,
    IbkrSubmissionLifecycleEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
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
_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


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


def _draft(
    *,
    draft_id: str,
    status: str,
    audit_trail_hash: str | None = None,
    conid: str = "12345",
    submission_started_at: datetime | None = None,
    terminal_state_at: datetime | None = None,
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id="DU1234567",
        conid=conid,
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
        status=status,
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_trail_hash or f"h-{draft_id}",
        previous_draft_hash=None,
        safe_for_submission=False,
        submission_started_at=submission_started_at,
        terminal_state_at=terminal_state_at,
    )


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "ibkr-sub.sqlite"
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
                f"INSERT INTO alembic_version (version_num) VALUES ('{_LATEST}')"
            )
        )
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        )
        lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        executions_repo = SqlAlchemyIbkrExecutionsRepository(
            conn, _report()
        )

        # Active draft (working).
        draft_repo.append(
            _draft(
                draft_id="d-active",
                status="working",
                submission_started_at=_NOW - timedelta(minutes=2),
            )
        )
        audit_repo.append(
            IbkrSubmissionAuditEntry(
                action_draft_id="d-active",
                submitted_at=_NOW - timedelta(minutes=2),
                sent_to_account_id="DU1234567",
                sent_account_mode="paper",
                ibkr_perm_id=100100,
                ibkr_order_id=1,
                contract_json={"symbol": "ASML"},
                order_json={"action": "BUY"},
                gateway_session_id="sess-1",
                result="placed",
                error_class=None,
                error_message_dutch=None,
            )
        )
        lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id="d-active",
                event_at=_NOW - timedelta(minutes=2),
                ibkr_perm_id=100100,
                event_type="status_change",
                from_status="submitted",
                to_status="accepted",
                ibkr_raw_status="Submitted",
                fill_price_local=None,
                fill_quantity=None,
                commission=None,
                commission_currency=None,
                raw_callback_json={"status": "Submitted"},
            )
        )

        # Terminal draft (filled).
        draft_repo.append(
            _draft(
                draft_id="d-filled",
                status="filled",
                audit_trail_hash="h-filled",
                terminal_state_at=_NOW - timedelta(hours=1),
            )
        )
        executions_repo.append(
            IbkrExecutionEntry(
                ibkr_exec_id="exec-A",
                ibkr_perm_id=99999,
                action_draft_id="d-filled",
                account_id="DU1234567",
                conid="12345",
                side="BUY",
                fill_price_local=Decimal("638.72"),
                fill_quantity=Decimal("6"),
                fill_time=_NOW - timedelta(hours=1),
                commission=Decimal("1.50"),
                commission_currency="EUR",
                exchange="AEB",
            )
        )
    return db_url


# ---- /ibkr-submission/audit -----------------------------------------


def test_audit_route_returns_rows_for_account(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/audit?account_id=DU1234567")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ibkr_account_id"] == "DU1234567"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["result"] == "placed"
    assert body["rows"][0]["ibkr_perm_id"] == 100100
    assert body["rows"][0]["sent_account_mode"] == "paper"


def test_audit_route_uses_account_hint_when_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    api_settings.ibkr_account_id_hint = "DU1234567"
    r = client.get("/ibkr-submission/audit")
    assert r.status_code == 200, r.text
    assert len(r.json()["rows"]) == 1


def test_audit_route_returns_404_without_account_hint(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/audit")
    assert r.status_code == 404


def test_audit_route_returns_503_when_storage_off() -> None:
    r = client.get("/ibkr-submission/audit?account_id=DU1234567")
    assert r.status_code == 503


# ---- /ibkr-submission/lifecycle/{action_draft_id} -------------------


def test_lifecycle_route_returns_events_for_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/lifecycle/d-active")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action_draft_id"] == "d-active"
    assert len(body["events"]) == 1
    assert body["events"][0]["event_type"] == "status_change"
    assert body["events"][0]["ibkr_raw_status"] == "Submitted"


def test_lifecycle_route_empty_for_unknown_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/lifecycle/d-nope")
    assert r.status_code == 200
    assert r.json()["events"] == []


# ---- /ibkr-submission/active ----------------------------------------


def test_active_route_returns_in_flight_drafts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/active?account_id=DU1234567")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["drafts"]) == 1
    assert body["drafts"][0]["action_draft_id"] == "d-active"
    assert body["drafts"][0]["status"] == "working"


# ---- /ibkr-submission/historiek -------------------------------------


def test_historiek_route_returns_terminal_drafts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get("/ibkr-submission/historiek?account_id=DU1234567")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["drafts"]) == 1
    assert body["drafts"][0]["action_draft_id"] == "d-filled"
    assert body["drafts"][0]["status"] == "filled"


# ---- /ibkr-executions ------------------------------------------------


def test_executions_route_returns_per_asset_history(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get(
        "/ibkr-executions?account_id=DU1234567&conid=12345"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["conid"] == "12345"
    assert len(body["executions"]) == 1
    ex = body["executions"][0]
    assert ex["side"] == "BUY"
    assert Decimal(ex["fill_price_local"]) == Decimal("638.72")
    assert Decimal(ex["fill_quantity"]) == Decimal("6")
    assert Decimal(ex["commission"]) == Decimal("1.50")
    assert ex["commission_currency"] == "EUR"


def test_executions_route_returns_empty_for_unknown_conid(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path)
    r = client.get(
        "/ibkr-executions?account_id=DU1234567&conid=99999"
    )
    assert r.status_code == 200
    assert r.json()["executions"] == []
