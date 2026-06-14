"""Task 135b: ``IbkrReconciler`` orchestrator.

The orchestrator is the single entry point an APScheduler tick wires
into. It owns:

* single-flight via the injected ``SingleFlightLockProtocol``;
* one ``reconciliation_run_audit`` row per tick (insert at start,
  ``complete_run`` at the end);
* fixed pass ordering — Pass A → Pass B → Pass C;
* connection / IBKR-gateway disconnect detection — when the gateway
  isn't reachable the tick exits with ``mode_detected="skipped_disconnected"``;
* fatal-exception capture — any pass that raises through is folded
  into a single ``mode_detected="error"`` run row with the exception
  details serialised into ``error_details_json``.

The orchestrator never raises through to APScheduler; every outcome
lands in the structured ``IbkrReconcilerResult`` and the
``reconciliation_run_audit`` row.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol

from ai_trading_agent_storage import (
    ReconciliationRunAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyReconciliationRunAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
)

from portfolio_outlook_worker.ibkr_reconciliation.pass_a_orphaned_executions import (
    IbkrExecutionFetcherProtocol,
    PassAOrphanedExecutionsResult,
    run_pass_a_orphaned_executions,
)
from portfolio_outlook_worker.ibkr_reconciliation.pass_b_stale_in_flight import (
    IbkrOrderStatusFetcherProtocol,
    PassBStaleInFlightResult,
    run_pass_b_stale_in_flight,
)
from portfolio_outlook_worker.ibkr_reconciliation.pass_c_timeout_recovery import (
    PassCTimeoutRecoveryResult,
    run_pass_c_timeout_recovery,
)
from portfolio_outlook_worker.single_flight_lock import (
    SingleFlightLockProtocol,
)

logger = logging.getLogger(__name__)


ReconcilerMode = Literal[
    "completed",
    "skipped_locked",
    "skipped_disconnected",
    "error",
]


# ---------------------------------------------------------------------------
# Gateway-readiness adapter.
# ---------------------------------------------------------------------------


class IbkrReconcilerGatewayProtocol(Protocol):
    """Reads the live IBKR session state Pass A and Pass B depend on.

    Production wraps the worker's persistent ``IbkrGateway`` (the same
    one the submission_sweep uses); tests inject a fake.
    """

    def is_connected(self) -> bool: ...


# ---------------------------------------------------------------------------
# Result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IbkrReconcilerResult:
    """Audit-friendly outcome of one reconciler tick.

    The orchestrator persists a matching ``reconciliation_run_audit``
    row; the dataclass is the in-memory mirror tests assert against.
    """

    reconciliation_run_id: str
    account_id: str
    started_at: datetime
    completed_at: datetime
    mode_detected: ReconcilerMode
    pass_a_result: PassAOrphanedExecutionsResult | None = None
    pass_b_result: PassBStaleInFlightResult | None = None
    pass_c_result: PassCTimeoutRecoveryResult | None = None
    divergences_found: int = 0
    error_details_json: dict[str, object] | None = None

    @property
    def pass_a_orphaned_count(self) -> int:
        return (
            0
            if self.pass_a_result is None
            else self.pass_a_result.divergences_found
        )

    @property
    def pass_b_stale_count(self) -> int:
        return (
            0
            if self.pass_b_result is None
            else self.pass_b_result.divergences_found
        )

    @property
    def pass_c_timeout_count(self) -> int:
        return (
            0
            if self.pass_c_result is None
            else self.pass_c_result.divergences_found
        )


# ---------------------------------------------------------------------------
# Orchestrator.
# ---------------------------------------------------------------------------


class IbkrReconciler:
    """One reconciler tick — Pass A → Pass B → Pass C with audit + lock.

    Wired into APScheduler as a no-arg ``tick()`` invocation. The
    orchestrator handles single-flight via the injected ``lock``
    protocol; failing to acquire returns
    ``IbkrReconcilerResult(mode_detected="skipped_locked")``.
    """

    def __init__(
        self,
        *,
        ibkr_account_id: str,
        lock: SingleFlightLockProtocol,
        gateway: IbkrReconcilerGatewayProtocol,
        execution_fetcher: IbkrExecutionFetcherProtocol,
        order_status_fetcher: IbkrOrderStatusFetcherProtocol,
        action_draft_repo: SqlAlchemyActionDraftRepository,
        executions_repo: SqlAlchemyIbkrExecutionsRepository,
        submission_audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
        unmatched_repo: SqlAlchemyUnmatchedExecutionAuditRepository,
        manual_review_repo: SqlAlchemyManualReviewQueueRepository,
        reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
        run_audit_repo: SqlAlchemyReconciliationRunAuditRepository,
        now_provider: Callable[[], datetime],
        run_id_factory: Callable[[], str] | None = None,
        pass_c_timeout_cutoff: timedelta | None = None,
    ) -> None:
        self._ibkr_account_id = ibkr_account_id
        self._lock = lock
        self._gateway = gateway
        self._execution_fetcher = execution_fetcher
        self._order_status_fetcher = order_status_fetcher
        self._action_draft_repo = action_draft_repo
        self._executions_repo = executions_repo
        self._submission_audit_repo = submission_audit_repo
        self._unmatched_repo = unmatched_repo
        self._manual_review_repo = manual_review_repo
        self._reconciliation_audit_repo = reconciliation_audit_repo
        self._run_audit_repo = run_audit_repo
        self._now_provider = now_provider
        self._run_id_factory = run_id_factory or _default_run_id_factory
        # V1.2 §CC / GAPS.md P2-4 — Pass C cut-off configureerbaar.
        # ``None`` valt terug op de doctrine-default (24u).
        from portfolio_outlook_worker.ibkr_reconciliation.pass_c_timeout_recovery import (
            DEFAULT_TIMEOUT_CUTOFF,
        )

        self._pass_c_timeout_cutoff = (
            pass_c_timeout_cutoff
            if pass_c_timeout_cutoff is not None
            else DEFAULT_TIMEOUT_CUTOFF
        )

    def tick(self) -> IbkrReconcilerResult:
        started = self._now_provider()
        run_id = self._run_id_factory()

        if not self._lock.try_acquire():
            return _empty_run_result(
                run_id=run_id,
                account_id=self._ibkr_account_id,
                started_at=started,
                completed_at=self._now_provider(),
                mode="skipped_locked",
            )

        try:
            return self._run_locked(run_id=run_id, started=started)
        finally:
            try:
                self._lock.release()
            except Exception:  # noqa: BLE001 — boundary
                logger.exception(
                    "reconciler lock release failed"
                )

    def _run_locked(
        self, *, run_id: str, started: datetime
    ) -> IbkrReconcilerResult:
        # Insert the open run-audit row first so an in-flight crash is
        # still visible in the audit table (completed_at stays NULL
        # until ``complete_run`` flips it).
        self._run_audit_repo.append(
            ReconciliationRunAuditEntry(
                reconciliation_run_id=run_id,
                started_at=started,
                completed_at=None,
                account_id=self._ibkr_account_id,
                pass_a_orphaned_count=0,
                pass_b_stale_count=0,
                pass_c_timeout_count=0,
                divergences_found=0,
                mode_detected="completed",  # tentative — finalised below
                error_details_json=None,
            )
        )

        if not self._gateway.is_connected():
            completed = self._now_provider()
            self._run_audit_repo.complete_run(
                reconciliation_run_id=run_id,
                completed_at=completed,
                pass_a_orphaned_count=0,
                pass_b_stale_count=0,
                pass_c_timeout_count=0,
                divergences_found=0,
                mode_detected="skipped_disconnected",
            )
            return _empty_run_result(
                run_id=run_id,
                account_id=self._ibkr_account_id,
                started_at=started,
                completed_at=completed,
                mode="skipped_disconnected",
            )

        pass_a: PassAOrphanedExecutionsResult | None = None
        pass_b: PassBStaleInFlightResult | None = None
        pass_c: PassCTimeoutRecoveryResult | None = None

        try:
            pass_a = run_pass_a_orphaned_executions(
                reconciliation_run_id=run_id,
                account_id=self._ibkr_account_id,
                fetcher=self._execution_fetcher,
                action_draft_repo=self._action_draft_repo,
                executions_repo=self._executions_repo,
                submission_audit_repo=self._submission_audit_repo,
                unmatched_repo=self._unmatched_repo,
                reconciliation_audit_repo=self._reconciliation_audit_repo,
                now_provider=self._now_provider,
            )
            pass_b = run_pass_b_stale_in_flight(
                reconciliation_run_id=run_id,
                account_id=self._ibkr_account_id,
                fetcher=self._order_status_fetcher,
                action_draft_repo=self._action_draft_repo,
                submission_audit_repo=self._submission_audit_repo,
                reconciliation_audit_repo=self._reconciliation_audit_repo,
                now_provider=self._now_provider,
            )
            pass_c = run_pass_c_timeout_recovery(
                reconciliation_run_id=run_id,
                account_id=self._ibkr_account_id,
                action_draft_repo=self._action_draft_repo,
                manual_review_repo=self._manual_review_repo,
                reconciliation_audit_repo=self._reconciliation_audit_repo,
                now_provider=self._now_provider,
                timeout_cutoff=self._pass_c_timeout_cutoff,
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception("reconciler tick raised through a pass")
            completed = self._now_provider()
            divergences = sum(
                result.divergences_found
                for result in (pass_a, pass_b, pass_c)
                if result is not None
            )
            error_details: dict[str, object] = {
                "class": type(exc).__name__,
                "message": str(exc),
                "pass_a_completed": pass_a is not None,
                "pass_b_completed": pass_b is not None,
                "pass_c_completed": pass_c is not None,
            }
            self._run_audit_repo.complete_run(
                reconciliation_run_id=run_id,
                completed_at=completed,
                pass_a_orphaned_count=(
                    pass_a.divergences_found if pass_a else 0
                ),
                pass_b_stale_count=(
                    pass_b.divergences_found if pass_b else 0
                ),
                pass_c_timeout_count=(
                    pass_c.divergences_found if pass_c else 0
                ),
                divergences_found=divergences,
                mode_detected="error",
                error_details_json=error_details,
            )
            return IbkrReconcilerResult(
                reconciliation_run_id=run_id,
                account_id=self._ibkr_account_id,
                started_at=started,
                completed_at=completed,
                mode_detected="error",
                pass_a_result=pass_a,
                pass_b_result=pass_b,
                pass_c_result=pass_c,
                divergences_found=divergences,
                error_details_json=error_details,
            )

        completed = self._now_provider()
        divergences = (
            pass_a.divergences_found
            + pass_b.divergences_found
            + pass_c.divergences_found
        )
        self._run_audit_repo.complete_run(
            reconciliation_run_id=run_id,
            completed_at=completed,
            pass_a_orphaned_count=pass_a.divergences_found,
            pass_b_stale_count=pass_b.divergences_found,
            pass_c_timeout_count=pass_c.divergences_found,
            divergences_found=divergences,
            mode_detected="completed",
        )
        return IbkrReconcilerResult(
            reconciliation_run_id=run_id,
            account_id=self._ibkr_account_id,
            started_at=started,
            completed_at=completed,
            mode_detected="completed",
            pass_a_result=pass_a,
            pass_b_result=pass_b,
            pass_c_result=pass_c,
            divergences_found=divergences,
        )


def _empty_run_result(
    *,
    run_id: str,
    account_id: str,
    started_at: datetime,
    completed_at: datetime,
    mode: ReconcilerMode,
) -> IbkrReconcilerResult:
    return IbkrReconcilerResult(
        reconciliation_run_id=run_id,
        account_id=account_id,
        started_at=started_at,
        completed_at=completed_at,
        mode_detected=mode,
    )


def _default_run_id_factory() -> str:
    return f"recon-{uuid.uuid4().hex[:16]}"


__all__ = [
    "IbkrReconciler",
    "IbkrReconcilerGatewayProtocol",
    "IbkrReconcilerResult",
    "ReconcilerMode",
]


_ = field  # silence unused-import warning
