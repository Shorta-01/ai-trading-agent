"""Task 134c — ``POST /action-draft/{id}/cancel-submitted`` tests.

Valid only for in-flight statuses (submitted/accepted/working/
partially_filled). The route transitions the draft to
``pending_cancellation`` and writes one ``ibkr_submission_lifecycle``
row tagged ``event_type='cancellation_request'``. It does NOT call
IBKR — the worker picks the row up on its next sweep tick.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrSubmissionAuditEntry,
    SqlAlchemyActionDraftRepository,
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


def _draft(status: str) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
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
        status=status,
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


def _seed_db(tmp_path, *, status: str = "submitted") -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "cancel.sqlite"
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
        draft_repo.append(_draft(status))
        # Also seed an audit row so the route can look up the perm_id.
        audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        )
        audit_repo.append(
            IbkrSubmissionAuditEntry(
                action_draft_id="draft-1",
                submitted_at=_NOW - timedelta(seconds=10),
                sent_to_account_id="DU1234567",
                sent_account_mode="paper",
                ibkr_perm_id=42424242,
                ibkr_order_id=1,
                contract_json={"symbol": "ASML"},
                order_json={"action": "BUY"},
                gateway_session_id="sess-1",
                result="placed",
                error_class=None,
                error_message_dutch=None,
            )
        )
    return db_url


def test_cancel_in_flight_draft_transitions_to_pending_cancellation(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path, status="working")
    r = client.post("/action-draft/draft-1/cancel-submitted")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending_cancellation"

    # The lifecycle row is written; verify by querying the DB.
    engine = create_engine(db_url)
    with engine.connect() as conn:
        lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        events = lifecycle_repo.list_for_draft("draft-1")
        assert len(events) == 1
        assert events[0].event_type == "cancellation_request"
        assert events[0].from_status == "working"
        assert events[0].to_status == "pending_cancellation"
        # The perm_id was looked up from the audit row we seeded.
        assert events[0].ibkr_perm_id == 42424242


def test_cancel_returns_422_for_non_in_flight_status(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path, status="user_approved")
    r = client.post("/action-draft/draft-1/cancel-submitted")
    assert r.status_code == 422
    assert "actief IBKR-status" in r.json()["detail"]


def test_cancel_returns_422_for_terminal_status(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path, status="filled")
    r = client.post("/action-draft/draft-1/cancel-submitted")
    assert r.status_code == 422


def test_cancel_returns_404_for_unknown_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db(tmp_path, status="submitted")
    r = client.post("/action-draft/nope/cancel-submitted")
    assert r.status_code == 404


def test_cancel_returns_503_when_storage_off() -> None:
    r = client.post("/action-draft/draft-1/cancel-submitted")
    assert r.status_code == 503
    assert r.json()["detail"] == "Opslag is niet beschikbaar."


def test_cancel_accepts_submitted_accepted_working_partially_filled(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    """Sanity check: each of the four cancellable statuses is accepted."""
    for status in ("submitted", "accepted", "working", "partially_filled"):
        _reset()
        sub_tmp = tmp_path / status
        sub_tmp.mkdir()
        _seed_db(sub_tmp, status=status)
        r = client.post("/action-draft/draft-1/cancel-submitted")
        assert r.status_code == 200, (
            f"status={status} got {r.status_code}: {r.text}"
        )
        assert r.json()["status"] == "pending_cancellation"
