"""Task 133 — Action Draft repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ActionDraftStateTransitionError,
    SqlAlchemyActionDraftAuditRepository,
    SqlAlchemyActionDraftRepository,
)
from ai_trading_agent_storage.metadata import (
    action_draft_audit,
    action_drafts,
    metadata,
)
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


def _report(allowed: bool = True) -> MigrationReadinessReport:
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


_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


def _draft(
    *,
    draft_id: str = "draft-1",
    decision_package_id: str | None = "dp-1",
    conid: str = "ASML.AS",
    account_id: str = "DU1234567",
    side: str = "BUY",
    quantity: Decimal = Decimal("10"),
    limit_price_local: Decimal = Decimal("638.72000000"),
    status: str = "proposed",
    created_at: datetime | None = None,
    audit_trail_hash: str = "hash-1",
    previous_draft_hash: str | None = None,
    held_quantity_at_creation: Decimal | None = None,
) -> ActionDraftEntry:
    ts = created_at or _BASE_TS
    notional_local = quantity * limit_price_local
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=decision_package_id,
        forecast_run_id="fcst-1" if decision_package_id else None,
        created_at=ts,
        created_by="user",
        ibkr_account_id=account_id,
        conid=conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side=side,
        quantity=quantity,
        order_type="LMT",
        limit_price_local=limit_price_local,
        time_in_force="DAY",
        notional_local=notional_local,
        notional_eur=notional_local,
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000.00000000"),
        held_quantity_at_creation=held_quantity_at_creation,
        status=status,
        last_edited_at=None,
        user_approved_at=None,
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_trail_hash,
        previous_draft_hash=previous_draft_hash,
        safe_for_submission=False,
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


# ---- happy path -------------------------------------------------------


def test_append_and_get_by_id_roundtrips_record() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        record = _draft()
        result = repo.append(record)
        assert result.action_draft_id == "draft-1"

        fetched = repo.get_by_id("draft-1")
        assert fetched is not None
        assert fetched.action_draft_id == "draft-1"
        assert fetched.side == "BUY"
        assert fetched.quantity == Decimal("10")
        assert fetched.limit_price_local == Decimal("638.72000000")
        assert fetched.status == "proposed"
        assert fetched.safe_for_submission is False


def test_get_by_id_returns_none_when_missing() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        assert repo.get_by_id("does-not-exist") is None


def test_append_writes_created_audit_row() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        events = audit_repo.list_for_draft("draft-1")
        assert len(events) == 1
        assert events[0].event_type == "created"
        assert events[0].before_state_json is None
        assert events[0].after_state_json is not None
        assert events[0].after_state_json["status"] == "proposed"
        assert events[0].actor == "user"


def test_list_te_keuren_returns_only_active_drafts() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(
            _draft(draft_id="draft-prop", status="proposed", audit_trail_hash="h1")
        )
        repo.append(
            _draft(draft_id="draft-edit", status="edited", audit_trail_hash="h2")
        )
        repo.append(
            _draft(
                draft_id="draft-appr",
                status="user_approved",
                audit_trail_hash="h3",
            )
        )
        repo.append(
            _draft(
                draft_id="draft-dism",
                status="dismissed",
                audit_trail_hash="h4",
            )
        )
        repo.append(
            _draft(
                draft_id="draft-del", status="deleted", audit_trail_hash="h5"
            )
        )

        result = repo.list_te_keuren_for_account("DU1234567")
        ids = {d.action_draft_id for d in result}
        assert ids == {"draft-prop", "draft-edit", "draft-appr"}


def test_list_te_keuren_filters_by_account() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(draft_id="d1", account_id="A1", audit_trail_hash="h1"))
        repo.append(_draft(draft_id="d2", account_id="A2", audit_trail_hash="h2"))
        assert len(repo.list_te_keuren_for_account("A1")) == 1
        assert len(repo.list_te_keuren_for_account("A2")) == 1


def test_list_pending_for_conid_returns_only_proposed_and_edited() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(
            _draft(draft_id="d-prop", status="proposed", audit_trail_hash="h1")
        )
        repo.append(
            _draft(draft_id="d-edit", status="edited", audit_trail_hash="h2")
        )
        repo.append(
            _draft(
                draft_id="d-appr",
                status="user_approved",
                audit_trail_hash="h3",
            )
        )
        result = repo.list_pending_for_conid(
            ibkr_account_id="DU1234567", conid="ASML.AS"
        )
        ids = {d.action_draft_id for d in result}
        assert ids == {"d-prop", "d-edit"}


# ---- state transitions ------------------------------------------------


def test_update_status_proposed_to_user_approved_writes_audit() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        updated = repo.update_status(
            action_draft_id="draft-1",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=5),
        )
        assert updated.status == "user_approved"
        assert updated.user_approved_at is not None
        events = audit_repo.list_for_draft("draft-1")
        assert len(events) == 2
        assert events[1].event_type == "approved"
        assert events[1].actor == "user"


def test_update_status_to_dismissed_records_reason() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        updated = repo.update_status(
            action_draft_id="draft-1",
            new_status="dismissed",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=10),
            dismissed_reason="Niet de juiste timing",
        )
        assert updated.status == "dismissed"
        assert updated.dismissed_reason == "Niet de juiste timing"


def test_update_status_rejects_invalid_transition() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        # First approve.
        repo.update_status(
            action_draft_id="draft-1",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=5),
        )
        with pytest.raises(ActionDraftStateTransitionError):
            repo.update_status(
                action_draft_id="draft-1",
                new_status="dismissed",
                transition_actor="user",
                transition_at=_BASE_TS + timedelta(minutes=10),
            )


def test_update_status_unknown_draft_raises_lookup_error() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        with pytest.raises(LookupError):
            repo.update_status(
                action_draft_id="missing",
                new_status="dismissed",
                transition_actor="user",
                transition_at=_BASE_TS,
            )


# ---- field edits ------------------------------------------------------


def test_update_fields_flips_proposed_to_edited_and_writes_audit() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        updated = repo.update_fields(
            action_draft_id="draft-1",
            quantity=Decimal("5"),
            limit_price_local=Decimal("640.00000000"),
            notional_local=Decimal("3200.00000000"),
            notional_eur=Decimal("3200.00000000"),
            user_note="kleinere positie",
            actor="user",
            edited_at=_BASE_TS + timedelta(minutes=2),
        )
        assert updated.status == "edited"
        assert updated.quantity == Decimal("5")
        assert updated.limit_price_local == Decimal("640.00000000")
        assert updated.user_note == "kleinere positie"
        events = audit_repo.list_for_draft("draft-1")
        assert len(events) == 2
        assert events[1].event_type == "edited"


def test_update_fields_rejected_after_approval() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        repo.update_status(
            action_draft_id="draft-1",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=1),
        )
        with pytest.raises(ActionDraftStateTransitionError):
            repo.update_fields(
                action_draft_id="draft-1",
                quantity=Decimal("3"),
                actor="user",
                edited_at=_BASE_TS + timedelta(minutes=2),
            )


# ---- mark_superseded ---------------------------------------------------


def test_mark_superseded_only_for_pending_drafts() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        updated = repo.mark_superseded(
            action_draft_id="draft-1",
            by_decision_package_id="dp-newer",
            marked_at=_BASE_TS + timedelta(hours=24),
        )
        assert updated.superseded_by_decision_package_id == "dp-newer"
        assert updated.status == "proposed"  # status unchanged, flag only
        events = audit_repo.list_for_draft("draft-1")
        assert len(events) == 2
        assert events[1].event_type == "superseded"


def test_mark_superseded_rejected_when_already_dismissed() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        repo.update_status(
            action_draft_id="draft-1",
            new_status="dismissed",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=1),
        )
        with pytest.raises(ActionDraftStateTransitionError):
            repo.mark_superseded(
                action_draft_id="draft-1",
                by_decision_package_id="dp-newer",
                marked_at=_BASE_TS + timedelta(minutes=2),
            )


def test_dismiss_clears_superseded_flag() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        repo.mark_superseded(
            action_draft_id="draft-1",
            by_decision_package_id="dp-newer",
            marked_at=_BASE_TS + timedelta(hours=1),
        )
        dismissed = repo.update_status(
            action_draft_id="draft-1",
            new_status="dismissed",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(hours=2),
        )
        assert dismissed.superseded_by_decision_package_id is None


# ---- safety boolean enforcement ---------------------------------------


def test_safe_for_submission_true_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _draft()  # baseline ok
        ActionDraftEntry(
            action_draft_id="x",
            decision_package_id=None,
            forecast_run_id=None,
            created_at=_BASE_TS,
            created_by="user",
            ibkr_account_id="A1",
            conid="ASML.AS",
            symbol="ASML",
            exchange="AEB",
            currency_local="EUR",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LMT",
            limit_price_local=Decimal("100"),
            time_in_force="DAY",
            notional_local=Decimal("100"),
            notional_eur=Decimal("100"),
            fx_rate_at_creation=Decimal("1"),
            usable_cash_eur_at_creation=Decimal("1000"),
            held_quantity_at_creation=None,
            status="proposed",
            last_edited_at=None,
            user_approved_at=None,
            dismissed_at=None,
            deleted_at=None,
            dismissed_reason=None,
            user_note=None,
            superseded_by_decision_package_id=None,
            audit_trail_hash="h",
            previous_draft_hash=None,
            safe_for_submission=True,
        )


def test_safe_for_submission_true_rejected_at_repo_layer() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        record = _draft()
        # Construct an entry with the flag flipped, bypassing the
        # dataclass guard via ``object.__setattr__`` to prove the repo
        # layer also rejects it.
        object.__setattr__(record, "safe_for_submission", True)
        with pytest.raises(ValueError):
            repo.append(record)


# ---- list_by_status ---------------------------------------------------


def test_list_by_status_filters_correctly() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(
            _draft(draft_id="d1", status="proposed", audit_trail_hash="h1")
        )
        repo.append(
            _draft(draft_id="d2", status="dismissed", audit_trail_hash="h2")
        )
        repo.append(
            _draft(draft_id="d3", status="dismissed", audit_trail_hash="h3")
        )
        dismissed = repo.list_by_status("DU1234567", "dismissed")
        assert {d.action_draft_id for d in dismissed} == {"d2", "d3"}


# ---- audit list ordering ----------------------------------------------


def test_audit_list_orders_by_event_at() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        repo.update_fields(
            action_draft_id="draft-1",
            quantity=Decimal("5"),
            actor="user",
            edited_at=_BASE_TS + timedelta(minutes=2),
        )
        repo.update_status(
            action_draft_id="draft-1",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_BASE_TS + timedelta(minutes=4),
        )
        events = audit_repo.list_for_draft("draft-1")
        assert [e.event_type for e in events] == [
            "created",
            "edited",
            "approved",
        ]
