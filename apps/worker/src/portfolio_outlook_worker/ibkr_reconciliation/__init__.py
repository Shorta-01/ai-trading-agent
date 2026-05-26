"""Task 135: IBKR reconciliation passes (Stage 4 of the action flow).

The reconciler is the worker-side self-healing convergence layer that
fires on a recurring tick (orchestrator + APScheduler wiring shipped
in Task 135b) and reconciles the local ``ibkr_executions`` +
``action_drafts`` tables against the IBKR-side truth. Each tick walks
three passes in fixed order:

* Pass A (Task 135a) — ``pass_a_orphaned_executions``: backfill IBKR
  fills the worker missed, and flag IBKR fills that have no matching
  draft.
* Pass B (Task 135b) — ``pass_b_stale_in_flight``: drafts the worker
  thinks are in-flight that IBKR reports as terminal (heal) or no
  longer reports at all (log divergence).
* Pass C (Task 135b) — ``pass_c_timeout_recovery``: drafts in
  ``awaiting_reply_timeout`` for >24h escalate to
  ``requires_manual_review`` and land in the manual-review queue.

The ``IbkrReconciler`` orchestrator composes the three passes inside
a single-flight lock with run-row bookkeeping and exception capture.
"""

from portfolio_outlook_worker.ibkr_reconciliation.pass_a_orphaned_executions import (
    IbkrExecutionFetcherProtocol,
    IbkrExecutionForReconciliation,
    PassAOrphanedExecutionsResult,
    run_pass_a_orphaned_executions,
)
from portfolio_outlook_worker.ibkr_reconciliation.pass_b_stale_in_flight import (
    IbkrOrderStatusFetcherProtocol,
    IbkrOrderStatusForReconciliation,
    PassBStaleInFlightResult,
    run_pass_b_stale_in_flight,
)
from portfolio_outlook_worker.ibkr_reconciliation.pass_c_timeout_recovery import (
    TIMEOUT_CUTOFF,
    PassCTimeoutRecoveryResult,
    run_pass_c_timeout_recovery,
)
from portfolio_outlook_worker.ibkr_reconciliation.reconciler import (
    IbkrReconciler,
    IbkrReconcilerGatewayProtocol,
    IbkrReconcilerResult,
    ReconcilerMode,
)

__all__ = [
    "IbkrExecutionFetcherProtocol",
    "IbkrExecutionForReconciliation",
    "IbkrOrderStatusFetcherProtocol",
    "IbkrOrderStatusForReconciliation",
    "IbkrReconciler",
    "IbkrReconcilerGatewayProtocol",
    "IbkrReconcilerResult",
    "PassAOrphanedExecutionsResult",
    "PassBStaleInFlightResult",
    "PassCTimeoutRecoveryResult",
    "ReconcilerMode",
    "TIMEOUT_CUTOFF",
    "run_pass_a_orphaned_executions",
    "run_pass_b_stale_in_flight",
    "run_pass_c_timeout_recovery",
]
