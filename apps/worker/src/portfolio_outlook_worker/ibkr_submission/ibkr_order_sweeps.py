"""Wiring for the IBKR submission + cancel sweeps (execution layer 5/5).

Builds the full object graph the scheduler runs each tick: repos (bound to the
per-tick checked connection) + providers + submitter + sweep. The writable
order adapter is opened once at worker start (gated, paper-only) and reused.

Everything here is **default-off** and gated upstream — merging changes nothing
until ``IBKR_SUBMISSION_SWEEP_ENABLED`` / ``IBKR_CANCEL_SWEEP_ENABLED`` are set
AND a writable order session has been opened (which itself fails closed unless
the account looks like paper). UNVERIFIED end-to-end: the builders + gating are
unit-tested, but the live submit/cancel loop needs an IBKR paper account.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyActionDraftRepository,
    SqlAlchemyBehaviouralGuardrailSettingsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyMarketDataSnapshotRepository,
)

from portfolio_outlook_worker.ibkr_submission.cancel_sweep import CancelSweep
from portfolio_outlook_worker.ibkr_submission.drawdown_provider import (
    DrawdownProvider,
)
from portfolio_outlook_worker.ibkr_submission.ibkr_submission_providers import (
    FomoPriceProvider,
    GatewaySnapshotProvider,
)
from portfolio_outlook_worker.ibkr_submission.submission_sweep import (
    SubmissionSweep,
)
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrSubmitProtocol,
    IbkrSubmitter,
)
from portfolio_outlook_worker.single_flight_lock import SingleFlightLockProtocol


def _utcnow() -> datetime:
    return datetime.now(UTC)


def build_submission_sweep(
    *,
    connection: Any,
    readiness: Any,
    gateway: Any,
    order_adapter: IbkrSubmitProtocol,
    ibkr_account_id: str,
    lock: SingleFlightLockProtocol,
    now_provider: Callable[[], datetime] | None = None,
) -> SubmissionSweep:
    """Wire a :class:`SubmissionSweep` against a per-tick connection."""

    now = now_provider or _utcnow
    action_draft_repo = SqlAlchemyActionDraftRepository(connection, readiness)
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(connection, readiness)
    guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
        connection, readiness
    )
    # One repo serves the cash, position AND nav reads (it owns all three).
    sync_repo = SqlAlchemyIbkrSyncSnapshotRepository(connection, readiness)
    market_repo = SqlAlchemyMarketDataSnapshotRepository(connection, readiness)

    submitter = IbkrSubmitter(
        submit_adapter=order_adapter,
        action_draft_repo=action_draft_repo,
        audit_repo=audit_repo,
        now_provider=now_provider,
    )
    guardrails = guardrail_repo.get_or_default(
        ibkr_account_id=ibkr_account_id, now=now()
    )
    drawdown_provider = DrawdownProvider(
        nav_repo=sync_repo,
        soft_window_days=guardrails.soft_drawdown_window_days,
        hard_window_days=guardrails.hard_drawdown_window_days,
        now_provider=now_provider,
    )
    return SubmissionSweep(
        ibkr_account_id=ibkr_account_id,
        lock=lock,
        action_draft_repo=action_draft_repo,
        audit_repo=audit_repo,
        guardrail_repo=guardrail_repo,
        submitter=submitter,
        gateway_snapshot_provider=GatewaySnapshotProvider(gateway=gateway),
        cash_snapshot_provider=sync_repo,
        position_snapshot_provider=sync_repo,
        drawdown_provider=drawdown_provider,
        fomo_provider=FomoPriceProvider(market_repo=market_repo),
        now_provider=now_provider,
    )


def build_cancel_sweep(
    *,
    connection: Any,
    readiness: Any,
    order_adapter: IbkrSubmitProtocol,
    ibkr_account_id: str,
    lock: SingleFlightLockProtocol,
    now_provider: Callable[[], datetime] | None = None,
) -> CancelSweep:
    """Wire a :class:`CancelSweep` against a per-tick connection."""

    action_draft_repo = SqlAlchemyActionDraftRepository(connection, readiness)
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(connection, readiness)
    submitter = IbkrSubmitter(
        submit_adapter=order_adapter,
        action_draft_repo=action_draft_repo,
        audit_repo=audit_repo,
        now_provider=now_provider,
    )
    return CancelSweep(
        ibkr_account_id=ibkr_account_id,
        lock=lock,
        action_draft_repo=action_draft_repo,
        submitter=submitter,
        now_provider=now_provider,
    )


__all__ = ["build_cancel_sweep", "build_submission_sweep"]
