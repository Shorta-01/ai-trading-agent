"""Task 135b: Pass C — 24h awaiting_reply_timeout escalation.

Pass C is the last of the three reconciliation passes. It walks all
drafts in ``awaiting_reply_timeout`` and, for each one whose
``terminal_state_at`` is older than the 24-hour cut-off (Task 135
product lock §4), escalates it to ``requires_manual_review``:

1. Transition the draft to ``requires_manual_review`` via
   ``apply_lifecycle_transition`` (the state machine widened by
   Task 135a allows this transition).
2. Insert one ``manual_review_queue`` row with
   ``reason='timeout_24h_no_data'`` so the user sees the queue item
   on the admin surface (Task 135b API + frontend).
3. Append one ``timeout_flagged_manual_review`` reconciliation_audit
   row capturing the timestamp of the original timeout + the
   reconciler tick that escalated it.

Pass C runs after Pass A. If Pass A produced an execution-driven heal
on the same draft earlier in the tick, the draft is no longer in
``awaiting_reply_timeout`` and Pass C skips it automatically.

Drafts that have been in ``awaiting_reply_timeout`` for less than 24h
stay there — the next reconciler tick re-evaluates them. There is no
partial-credit "almost 24h" mode; the cut-off is hard.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ai_trading_agent_storage import (
    ManualReviewQueueEntry,
    ReconciliationAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
)

logger = logging.getLogger(__name__)


# Task 135 product lock §4 — 24h cut-off, not configurable.
TIMEOUT_CUTOFF = timedelta(hours=24)


# ---------------------------------------------------------------------------
# Outcome dataclass.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassCTimeoutRecoveryResult:
    """Audit-friendly outcome of running Pass C once."""

    reconciliation_run_id: str
    account_id: str
    timeouts_evaluated: int
    escalated_to_manual_review: int
    skipped_within_cutoff: int
    skipped_missing_terminal_at: int
    divergences_found: int
    escalated_draft_ids: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Pass C entry point.
# ---------------------------------------------------------------------------


def run_pass_c_timeout_recovery(
    *,
    reconciliation_run_id: str,
    account_id: str,
    action_draft_repo: SqlAlchemyActionDraftRepository,
    manual_review_repo: SqlAlchemyManualReviewQueueRepository,
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
    now_provider: Callable[[], datetime],
) -> PassCTimeoutRecoveryResult:
    """Run Pass C for one reconciler tick."""

    timeouts = action_draft_repo.list_by_status(
        account_id, "awaiting_reply_timeout"
    )
    escalated = 0
    within_cutoff = 0
    missing_ts = 0
    escalated_ids: list[str] = []
    now = now_provider()

    for draft in timeouts:
        if draft.terminal_state_at is None:
            missing_ts += 1
            continue
        # SQLite's pysqlite driver drops tzinfo on round-trip even when
        # the column is declared with timezone=True. Compare in a
        # tz-agnostic way: if one side is naive we strip the other so
        # the subtraction never blows up at the production boundary.
        left = now if now.tzinfo is None else now.replace(tzinfo=None)
        right = (
            draft.terminal_state_at
            if draft.terminal_state_at.tzinfo is None
            else draft.terminal_state_at.replace(tzinfo=None)
        )
        age = left - right
        if age < TIMEOUT_CUTOFF:
            within_cutoff += 1
            continue

        before_status = draft.status
        try:
            updated = action_draft_repo.apply_lifecycle_transition(
                action_draft_id=draft.action_draft_id,
                new_status="requires_manual_review",
                transitioned_at=now,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Pass C apply_lifecycle_transition failed for draft %s",
                draft.action_draft_id,
            )
            continue

        manual_review_repo.append(
            ManualReviewQueueEntry(
                flagged_at=now,
                action_draft_id=draft.action_draft_id,
                reason="timeout_24h_no_data",
                details_dutch=(
                    "Action Draft is langer dan 24 uur in "
                    "awaiting_reply_timeout zonder dat IBKR een "
                    "uitvoering, status-update of annulering heeft "
                    "teruggemeld. Handmatige beoordeling vereist."
                ),
                resolution_status="pending",
            )
        )
        reconciliation_audit_repo.append(
            ReconciliationAuditEntry(
                reconciliation_run_id=reconciliation_run_id,
                action_draft_id=draft.action_draft_id,
                event_at=now,
                pass_name="timeout_recovery",
                divergence_type="timeout_flagged_manual_review",
                before_status=before_status,
                after_status=updated.status,
                ibkr_evidence_json={
                    "awaited_since": draft.terminal_state_at.isoformat(),
                    "elapsed_seconds": int(age.total_seconds()),
                    "cutoff_seconds": int(TIMEOUT_CUTOFF.total_seconds()),
                },
                notes_dutch=(
                    "Timeout van 24 uur overschreden zonder IBKR-data; "
                    "doorgezet naar handmatige beoordeling."
                ),
            )
        )
        escalated += 1
        escalated_ids.append(draft.action_draft_id)

    return PassCTimeoutRecoveryResult(
        reconciliation_run_id=reconciliation_run_id,
        account_id=account_id,
        timeouts_evaluated=len(timeouts),
        escalated_to_manual_review=escalated,
        skipped_within_cutoff=within_cutoff,
        skipped_missing_terminal_at=missing_ts,
        divergences_found=escalated,
        escalated_draft_ids=tuple(escalated_ids),
    )


__all__ = [
    "PassCTimeoutRecoveryResult",
    "TIMEOUT_CUTOFF",
    "run_pass_c_timeout_recovery",
]
