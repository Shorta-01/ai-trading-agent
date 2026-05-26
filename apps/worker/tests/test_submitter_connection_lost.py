"""Task 134b — submitter connection-lost path.

When the IBKR adapter raises ``IbkrConnectionLostError`` mid-submit,
the submitter must:

* write one ``ibkr_submission_audit`` row with ``result="connection_lost"``,
* leave the draft in ``user_approved`` (no transition to ``submitted``),
* stamp ``submission_block_reason="connection_down"`` so the UI badge
  appears,
* return ``SubmissionResult(ok=False, block_reason="connection_down")``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_submission.order_builder import TickSize
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrConnectionLostError,
    IbkrSubmitter,
    IbkrTickSizeFetchError,
    SubmittedTrade,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
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


def _draft() -> ActionDraftEntry:
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
        status="user_approved",
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


class _PlaceOrderDropsAdapter:
    """Adapter where ``place_order`` raises ``IbkrConnectionLostError``."""

    gateway_session_id = "sess-1"
    account_mode: Literal["paper", "live"] = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize:
        return TickSize(tick_size_local=Decimal("0.005"))

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        raise IbkrConnectionLostError("socket reset by peer")

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


class _TickSizeDropsAdapter:
    """Adapter where ``fetch_tick_size`` raises ``IbkrConnectionLostError``."""

    gateway_session_id = "sess-1"
    account_mode: Literal["paper", "live"] = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize:
        raise IbkrConnectionLostError("reqContractDetails timed out")

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:  # pragma: no cover
        raise NotImplementedError

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


class _TickSizeRejectsAdapter:
    """Adapter where ``fetch_tick_size`` raises ``IbkrTickSizeFetchError``.

    Different from connection_lost: this is a contract-side problem
    (e.g. unknown conid) and maps to ``tick_size_invalid`` /
    ``rejected_at_send``.
    """

    gateway_session_id = "sess-1"
    account_mode: Literal["paper", "live"] = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize:
        raise IbkrTickSizeFetchError("unknown conid")

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:  # pragma: no cover
        raise NotImplementedError

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def _seed_user_approved(conn):  # type: ignore[no-untyped-def]
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    draft_repo.append(_draft())  # already user_approved
    return draft_repo, audit_repo


def test_place_order_connection_lost_records_audit_and_stays_user_approved() -> None:
    with _conn() as conn:
        draft_repo, audit_repo = _seed_user_approved(conn)
        submitter = IbkrSubmitter(
            submit_adapter=_PlaceOrderDropsAdapter(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        result = submitter.submit(draft)

        assert result.ok is False
        assert result.block_reason == "connection_down"
        assert result.error_class == "IbkrConnectionLostError"
        assert result.perm_id is None

        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.status == "user_approved"
        assert after.submission_block_reason == "connection_down"
        assert after.submission_started_at is None

        rows = audit_repo.list_for_account(ibkr_account_id="DU1234567")
        assert len(rows) == 1
        assert rows[0].result == "connection_lost"
        assert rows[0].ibkr_perm_id is None
        assert rows[0].error_message_dutch is not None
        assert "IBKR" in rows[0].error_message_dutch


def test_tick_size_connection_lost_records_audit() -> None:
    with _conn() as conn:
        draft_repo, audit_repo = _seed_user_approved(conn)
        submitter = IbkrSubmitter(
            submit_adapter=_TickSizeDropsAdapter(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        result = submitter.submit(draft)
        assert result.ok is False
        assert result.block_reason == "connection_down"
        # No place_order attempt happened.
        rows = audit_repo.list_for_account(ibkr_account_id="DU1234567")
        assert rows[0].result == "connection_lost"


def test_tick_size_rejection_records_rejected_at_send() -> None:
    with _conn() as conn:
        draft_repo, audit_repo = _seed_user_approved(conn)
        submitter = IbkrSubmitter(
            submit_adapter=_TickSizeRejectsAdapter(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        result = submitter.submit(draft)
        assert result.ok is False
        assert result.block_reason == "tick_size_invalid"
        rows = audit_repo.list_for_account(ibkr_account_id="DU1234567")
        assert rows[0].result == "rejected_at_send"
