"""Task 135: IBKR reconciliation passes (Stage 4 of the action flow).

The reconciler is the worker-side self-healing convergence layer that
fires on a recurring tick (Task 135b) and reconciles the local
``ibkr_executions`` + ``action_drafts`` tables against the IBKR-side
truth. Each tick walks three passes in fixed order:

* Pass A (Task 135a) — ``pass_a_orphaned_executions``: backfill IBKR
  fills the worker missed, and flag IBKR fills that have no matching
  draft.
* Pass B (Task 135b) — stale in-flight detection: drafts the worker
  thinks are in-flight that IBKR no longer reports.
* Pass C (Task 135b) — 24h timeout escalation: ``awaiting_reply_timeout``
  drafts that still have no IBKR data after the cut-off become
  ``requires_manual_review``.

The orchestration shell (single-flight lock, run-row bookkeeping,
APScheduler wiring) lives in Task 135b. This module exposes the
per-pass entry points the orchestrator composes.
"""

from portfolio_outlook_worker.ibkr_reconciliation.pass_a_orphaned_executions import (
    IbkrExecutionFetcherProtocol,
    IbkrExecutionForReconciliation,
    PassAOrphanedExecutionsResult,
    run_pass_a_orphaned_executions,
)

__all__ = [
    "IbkrExecutionFetcherProtocol",
    "IbkrExecutionForReconciliation",
    "PassAOrphanedExecutionsResult",
    "run_pass_a_orphaned_executions",
]
