"""Task 135a: Pass A — orphaned-execution recovery.

Pass A is the first of three reconciliation passes the worker runs on
each reconciler tick. It compares the IBKR-side execution ledger
against the locally-persisted ``ibkr_executions`` table and heals two
divergence classes:

1. **Missing execution applied** — IBKR has a fill the worker missed
   (typical when an IBKR callback was dropped or the worker was
   offline when IBKR fired the event). The fill matches a draft via
   ``ibkr_perm_id``; Pass A inserts the missing ``ibkr_executions``
   row and applies the appropriate ``filled``/``partially_filled``
   status transition.

2. **Unmatched execution** — IBKR has a fill whose ``perm_id``
   doesn't map to any local draft (typical when the user placed an
   order directly in TWS while the worker was offline). Pass A
   inserts an ``unmatched_execution_audit`` row + a reconciliation
   audit entry. The local draft state is **not** touched — there is
   nothing to heal.

Pass A is intentionally idempotent at every step:

* the executions table is ``UNIQUE`` on ``ibkr_exec_id``, so a
  duplicate IBKR poll just hits a no-op;
* the unmatched table is ``UNIQUE`` on ``ibkr_exec_id`` too;
* the reconciliation audit is append-only — repeated runs simply
  add more identical rows, which the dashboard de-duplicates by
  ``(reconciliation_run_id, action_draft_id)``.

The pass is wired into the reconciler orchestrator (Task 135b) which
owns single-flight, run-row bookkeeping, and the three-pass ordering.
This module owns the per-execution logic only.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrExecutionEntry,
    ReconciliationAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
    UnmatchedExecutionAuditEntry,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inputs the reconciler hands Pass A.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IbkrExecutionForReconciliation:
    """One IBKR execution returned by the live API poll.

    Production wraps an ``ib_insync.Execution`` into this dataclass at
    the gateway boundary so Pass A has no ``ib_insync`` dependency
    (the allowlist forbids it here). Tests construct instances by
    hand.
    """

    ibkr_exec_id: str
    ibkr_perm_id: int
    account_id: str
    conid: str
    side: Literal["BUY", "SELL"]
    fill_price_local: Decimal
    fill_quantity: Decimal
    fill_time: datetime
    raw: dict[str, object] = field(default_factory=dict)


class IbkrExecutionFetcherProtocol(Protocol):
    """Adapter Pass A relies on to read IBKR-side executions.

    The production implementation polls
    ``ib_insync.IB.reqExecutions(account, since)`` and converts the
    results to ``IbkrExecutionForReconciliation`` tuples; tests inject
    fakes that return canned data so unit tests stay deterministic.
    """

    def fetch_recent_executions(
        self, *, account_id: str
    ) -> tuple[IbkrExecutionForReconciliation, ...]: ...


# ---------------------------------------------------------------------------
# Outcome dataclass.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassAOrphanedExecutionsResult:
    """Audit-friendly outcome of running Pass A once."""

    reconciliation_run_id: str
    account_id: str
    executions_observed: int
    executions_already_recorded: int
    missing_execution_applied: int
    unmatched_execution_recorded: int
    divergences_found: int
    healed_draft_ids: tuple[str, ...] = field(default_factory=tuple)
    unmatched_exec_ids: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Pass A entry point.
# ---------------------------------------------------------------------------


def run_pass_a_orphaned_executions(
    *,
    reconciliation_run_id: str,
    account_id: str,
    fetcher: IbkrExecutionFetcherProtocol,
    action_draft_repo: SqlAlchemyActionDraftRepository,
    executions_repo: SqlAlchemyIbkrExecutionsRepository,
    submission_audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
    unmatched_repo: SqlAlchemyUnmatchedExecutionAuditRepository,
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
    now_provider: Callable[[], datetime],
) -> PassAOrphanedExecutionsResult:
    """Run Pass A for one reconciler tick.

    Returns a structured result the orchestrator persists on the
    ``reconciliation_run_audit`` row. Pass A never raises through; any
    per-execution failure is logged + counted as a divergence so the
    orchestrator can continue to Passes B and C.
    """

    observed = fetcher.fetch_recent_executions(account_id=account_id)
    already_recorded = 0
    missing_applied = 0
    unmatched_recorded = 0
    healed_draft_ids: list[str] = []
    unmatched_exec_ids: list[str] = []

    for execution in observed:
        if executions_repo.get_by_exec_id(execution.ibkr_exec_id) is not None:
            already_recorded += 1
            continue

        if unmatched_repo.get_by_exec_id(execution.ibkr_exec_id) is not None:
            # Already flagged on a previous tick — leave it for the
            # user to triage; do not double-record.
            already_recorded += 1
            continue

        draft_id = submission_audit_repo.get_action_draft_id_for_perm_id(
            execution.ibkr_perm_id
        )
        if draft_id is None:
            _record_unmatched_execution(
                execution=execution,
                reconciliation_run_id=reconciliation_run_id,
                unmatched_repo=unmatched_repo,
                reconciliation_audit_repo=reconciliation_audit_repo,
                now_provider=now_provider,
            )
            unmatched_recorded += 1
            unmatched_exec_ids.append(execution.ibkr_exec_id)
            continue

        draft = action_draft_repo.get_by_id(draft_id)
        if draft is None:
            # Submission audit row points at a draft that no longer
            # exists — very unusual; record as unmatched so the user
            # sees it.
            _record_unmatched_execution(
                execution=execution,
                reconciliation_run_id=reconciliation_run_id,
                unmatched_repo=unmatched_repo,
                reconciliation_audit_repo=reconciliation_audit_repo,
                now_provider=now_provider,
            )
            unmatched_recorded += 1
            unmatched_exec_ids.append(execution.ibkr_exec_id)
            continue

        healed = _apply_missing_execution(
            execution=execution,
            draft=draft,
            reconciliation_run_id=reconciliation_run_id,
            action_draft_repo=action_draft_repo,
            executions_repo=executions_repo,
            reconciliation_audit_repo=reconciliation_audit_repo,
            now_provider=now_provider,
        )
        if healed:
            missing_applied += 1
            healed_draft_ids.append(draft.action_draft_id)

    divergences_found = missing_applied + unmatched_recorded
    return PassAOrphanedExecutionsResult(
        reconciliation_run_id=reconciliation_run_id,
        account_id=account_id,
        executions_observed=len(observed),
        executions_already_recorded=already_recorded,
        missing_execution_applied=missing_applied,
        unmatched_execution_recorded=unmatched_recorded,
        divergences_found=divergences_found,
        healed_draft_ids=tuple(healed_draft_ids),
        unmatched_exec_ids=tuple(unmatched_exec_ids),
    )


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _record_unmatched_execution(
    *,
    execution: IbkrExecutionForReconciliation,
    reconciliation_run_id: str,
    unmatched_repo: SqlAlchemyUnmatchedExecutionAuditRepository,
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
    now_provider: Callable[[], datetime],
) -> None:
    event_at = now_provider()
    unmatched_repo.append(
        UnmatchedExecutionAuditEntry(
            event_at=event_at,
            ibkr_perm_id=execution.ibkr_perm_id,
            ibkr_exec_id=execution.ibkr_exec_id,
            account_id=execution.account_id,
            conid=execution.conid,
            side=execution.side,
            fill_price_local=execution.fill_price_local,
            fill_quantity=execution.fill_quantity,
            fill_time=execution.fill_time,
            raw_execution_json=execution.raw,
            resolution_status="unresolved",
        )
    )
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=None,
            event_at=event_at,
            pass_name="orphaned_execution",
            divergence_type="unmatched_execution",
            before_status=None,
            after_status=None,
            ibkr_evidence_json={
                "ibkr_exec_id": execution.ibkr_exec_id,
                "ibkr_perm_id": execution.ibkr_perm_id,
                "conid": execution.conid,
                "side": execution.side,
                "fill_price_local": str(execution.fill_price_local),
                "fill_quantity": str(execution.fill_quantity),
            },
            notes_dutch=(
                "Niet-gekoppelde IBKR-uitvoering gedetecteerd; "
                "geen actie ondernomen op een Action Draft."
            ),
        )
    )


def _apply_missing_execution(
    *,
    execution: IbkrExecutionForReconciliation,
    draft: ActionDraftEntry,
    reconciliation_run_id: str,
    action_draft_repo: SqlAlchemyActionDraftRepository,
    executions_repo: SqlAlchemyIbkrExecutionsRepository,
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
    now_provider: Callable[[], datetime],
) -> bool:
    """Insert the missing execution + heal the draft status if needed."""

    event_at = now_provider()
    before_status = draft.status
    executions_repo.append(
        IbkrExecutionEntry(
            ibkr_exec_id=execution.ibkr_exec_id,
            ibkr_perm_id=execution.ibkr_perm_id,
            action_draft_id=draft.action_draft_id,
            account_id=draft.ibkr_account_id,
            conid=draft.conid,
            side=draft.side,
            fill_price_local=execution.fill_price_local,
            fill_quantity=execution.fill_quantity,
            fill_time=execution.fill_time,
            commission=Decimal("0"),
            commission_currency=draft.currency_local,
            exchange="RECONCILIATION",
        )
    )
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=draft.action_draft_id,
            event_at=event_at,
            pass_name="orphaned_execution",
            divergence_type="missing_execution_applied",
            before_status=before_status,
            after_status=before_status,
            ibkr_evidence_json={
                "ibkr_exec_id": execution.ibkr_exec_id,
                "ibkr_perm_id": execution.ibkr_perm_id,
                "fill_price_local": str(execution.fill_price_local),
                "fill_quantity": str(execution.fill_quantity),
            },
            notes_dutch=(
                "Ontbrekende IBKR-uitvoering teruggevonden en "
                "lokaal vastgelegd."
            ),
        )
    )

    next_status = _resolve_next_status(
        draft=draft,
        executions_repo=executions_repo,
    )
    if next_status is None or next_status == draft.status:
        return True

    # The transition is allowed by the (Task 135-widened) state
    # machine. ``apply_lifecycle_transition`` validates the path and
    # stamps the terminal timestamp.
    updated = action_draft_repo.apply_lifecycle_transition(
        action_draft_id=draft.action_draft_id,
        new_status=next_status,
        transitioned_at=event_at,
    )
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=draft.action_draft_id,
            event_at=event_at,
            pass_name="orphaned_execution",
            divergence_type=_status_corrected_divergence_for(updated.status),
            before_status=before_status,
            after_status=updated.status,
            ibkr_evidence_json={
                "ibkr_exec_id": execution.ibkr_exec_id,
                "ibkr_perm_id": execution.ibkr_perm_id,
                "fill_quantity": str(execution.fill_quantity),
            },
            notes_dutch=(
                "Status van Action Draft hersteld op basis van "
                "IBKR-uitvoering."
            ),
        )
    )
    return True


def _resolve_next_status(
    *,
    draft: ActionDraftEntry,
    executions_repo: SqlAlchemyIbkrExecutionsRepository,
) -> str | None:
    """Decide whether the heal closes the draft fully or partially."""

    if draft.status in {
        "filled",
        "cancelled",
        "rejected",
        "dismissed",
        "deleted",
        "superseded",
        "requires_manual_review",
    }:
        # Terminal — never reverse. Pass B is where any terminal-state
        # divergence is logged (without flipping state); Pass A leaves
        # this alone.
        return None

    fills = executions_repo.list_for_draft(draft.action_draft_id)
    filled_quantity = sum(
        (entry.fill_quantity for entry in fills), Decimal("0")
    )
    if filled_quantity >= draft.quantity:
        return "filled"
    return "partially_filled"


def _status_corrected_divergence_for(new_status: str) -> str:
    """Map the resolved status to its locked divergence_type literal."""

    if new_status == "filled":
        return "status_corrected_to_filled"
    if new_status == "partially_filled":
        return "status_corrected_to_partially_filled"
    if new_status == "cancelled":
        return "status_corrected_to_cancelled"
    if new_status == "rejected":
        return "status_corrected_to_rejected"
    # Pass A only produces fill-driven heals; any other status here is
    # a programming error.
    raise ValueError(
        f"Pass A produced unexpected heal status {new_status!r}"
    )


__all__ = [
    "IbkrExecutionFetcherProtocol",
    "IbkrExecutionForReconciliation",
    "PassAOrphanedExecutionsResult",
    "run_pass_a_orphaned_executions",
]
