"""Reconciliation orchestrator: match submitted action drafts to IBKR sync.

Pulls every action-draft submission still in ``AWAITING_IBKR_REPLY`` /
``REPLY_CONFIRMED`` / ``WORKING``, matches it by ``ibkr_order_id`` /
``ibkr_perm_id`` against the latest IBKR open-orders and execution
snapshots, and transitions the state to ``FILLED`` / ``CANCELLED`` /
``REJECTED`` followed by ``RECONCILED`` (terminal local state). Every
transition writes a critical-severity ``asset_action_draft_events`` row.

This module is the only place where the state machine's downstream half
(SUBMITTED → terminal) is driven. Combined with Slice 7's approval +
submission orchestrators, it closes the locked V1 reply-handshake loop.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftSubmissionRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
)
from portfolio_outlook_portfolio import (
    ActionDraftState,
    InvalidStateTransitionError,
    coerce_state,
    require_transition_allowed,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReconciliationReport:
    requested_at: datetime
    completed_at: datetime
    submissions_total: int
    submissions_filled: int
    submissions_cancelled: int
    submissions_rejected: int
    submissions_still_working: int
    submissions_unchanged: int
    submissions_failed: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _SubmissionRepoProtocol(Protocol):
    def upsert_asset_action_draft_submission(
        self, record: AssetActionDraftSubmissionRecord
    ) -> object: ...


class _EventRepoProtocol(Protocol):
    def save_asset_action_draft_event(
        self, record: AssetActionDraftEventRecord
    ) -> object: ...


def _critical_event(
    *,
    draft_id: str,
    submission_id: str,
    from_state: str,
    to_state: str,
    rationale_nl: str,
    details_json: dict[str, str] | None = None,
) -> AssetActionDraftEventRecord:
    return AssetActionDraftEventRecord(
        event_id=f"evt_{uuid4().hex}",
        draft_id=draft_id,
        submission_id=submission_id,
        event_type=f"reconciled_to_{to_state}",
        severity="critical",
        from_state=from_state,
        to_state=to_state,
        occurred_at=datetime.now(UTC),
        acknowledged_at=None,
        rationale_nl=rationale_nl,
        details_json=details_json,
    )


def _classify(
    *,
    submission: AssetActionDraftSubmissionRecord,
    open_orders_by_order_id: dict[int, IbkrOpenOrderSnapshotRecord],
    executions_by_order_id: dict[int, list[IbkrExecutionSnapshotRecord]],
    submitted_quantity: Decimal,
) -> tuple[ActionDraftState | None, dict[str, str]]:
    """Decide the next state for one submission given the IBKR sync data.

    Returns ``(next_state, details)`` where ``next_state is None`` means
    "still working / nothing changed".
    """

    if submission.ibkr_order_id is None:
        return None, {"reason": "missing_ibkr_order_id"}
    executions = executions_by_order_id.get(submission.ibkr_order_id, [])
    open_order = open_orders_by_order_id.get(submission.ibkr_order_id)

    filled_qty = sum((exec_record.quantity for exec_record in executions), Decimal("0"))
    if filled_qty > 0 and filled_qty >= submitted_quantity:
        notional = sum(
            (exec_record.quantity * exec_record.price for exec_record in executions),
            Decimal("0"),
        )
        avg_price = (notional / filled_qty) if filled_qty > 0 else None
        return ActionDraftState.FILLED, {
            "filled_quantity": str(filled_qty),
            "average_fill_price": str(avg_price) if avg_price is not None else "",
            "execution_count": str(len(executions)),
        }

    if open_order is None:
        # Not in open_orders and no (or insufficient) fills → cancelled
        # (this assumes IBKR sync ran after the submission; partial fills
        # would surface as filled_qty > 0 < submitted_quantity which we
        # still treat as still-working until a full fill or cancel arrives)
        if filled_qty > 0:
            return None, {
                "filled_quantity": str(filled_qty),
                "reason": "partial_fill_still_working",
            }
        return ActionDraftState.CANCELLED, {"reason": "absent_from_open_orders"}

    status_text = (open_order.status or "").strip().lower()
    if status_text in {"cancelled", "apicancelled", "inactive"}:
        return ActionDraftState.CANCELLED, {
            "ibkr_status_text": open_order.status or "",
        }
    if status_text in {"submitted", "presubmitted", "working"}:
        return None, {"reason": "still_working", "ibkr_status_text": open_order.status or ""}
    # Default: still working but unrecognised status; persist a non-state-changing event
    return None, {
        "reason": "unrecognised_open_order_status",
        "ibkr_status_text": open_order.status or "",
    }


def _persist_state_transition(
    *,
    submission: AssetActionDraftSubmissionRecord,
    next_state: ActionDraftState,
    submission_repo: _SubmissionRepoProtocol,
    event_repo: _EventRepoProtocol,
    details: dict[str, str],
) -> AssetActionDraftSubmissionRecord:
    """Transition submission to ``next_state`` and append the audit event.

    Terminal IBKR states (FILLED / CANCELLED / REJECTED) immediately get a
    second transition to ``RECONCILED`` so the doctrine's locked end-state
    is honoured in one pass.
    """

    now = datetime.now(UTC)
    fields = dict(submission.__dict__)
    fields["state"] = next_state.value
    fields["last_state_transition_at"] = now
    fields["updated_at"] = now
    if next_state is ActionDraftState.FILLED:
        if "filled_quantity" in details and details["filled_quantity"]:
            fields["filled_quantity"] = Decimal(details["filled_quantity"])
            fields["remaining_quantity"] = Decimal("0")
        if "average_fill_price" in details and details["average_fill_price"]:
            fields["average_fill_price"] = Decimal(details["average_fill_price"])
    if next_state is ActionDraftState.CANCELLED:
        fields["cancelled_at"] = now
        fields["cancellation_reason"] = details.get("reason") or details.get(
            "ibkr_status_text"
        )
    if next_state is ActionDraftState.REJECTED:
        fields["rejected_reason"] = details.get("reason") or details.get(
            "ibkr_status_text"
        )

    intermediate = AssetActionDraftSubmissionRecord(**fields)
    submission_repo.upsert_asset_action_draft_submission(intermediate)
    event_repo.save_asset_action_draft_event(
        _critical_event(
            draft_id=submission.draft_id,
            submission_id=submission.submission_id,
            from_state=submission.state,
            to_state=next_state.value,
            rationale_nl=f"IBKR-sync reconciliatie → {next_state.value}.",
            details_json={k: str(v) for k, v in details.items()},
        )
    )

    # Auto-advance terminal IBKR states to RECONCILED.
    if next_state in {
        ActionDraftState.FILLED,
        ActionDraftState.CANCELLED,
        ActionDraftState.REJECTED,
    }:
        reconciled_now = datetime.now(UTC)
        next_fields = dict(intermediate.__dict__)
        next_fields["state"] = ActionDraftState.RECONCILED.value
        next_fields["last_state_transition_at"] = reconciled_now
        next_fields["updated_at"] = reconciled_now
        next_fields["reconciled_at"] = reconciled_now
        reconciled = AssetActionDraftSubmissionRecord(**next_fields)
        submission_repo.upsert_asset_action_draft_submission(reconciled)
        event_repo.save_asset_action_draft_event(
            _critical_event(
                draft_id=submission.draft_id,
                submission_id=submission.submission_id,
                from_state=next_state.value,
                to_state=ActionDraftState.RECONCILED.value,
                rationale_nl="IBKR-sync reconciliatie afgesloten.",
            )
        )
        return reconciled
    return intermediate


def reconcile_submissions(
    *,
    submissions: Iterable[AssetActionDraftSubmissionRecord],
    open_orders: Iterable[IbkrOpenOrderSnapshotRecord],
    executions: Iterable[IbkrExecutionSnapshotRecord],
    submitted_quantity_by_draft_id: dict[str, Decimal],
    submission_repo: _SubmissionRepoProtocol,
    event_repo: _EventRepoProtocol,
) -> ReconciliationReport:
    """Drive every reconcilable submission to its terminal local state."""

    requested_at = datetime.now(UTC)
    open_by_order_id: dict[int, IbkrOpenOrderSnapshotRecord] = {
        order.ibkr_order_id: order for order in open_orders if order.ibkr_order_id
    }
    exec_by_order_id: dict[int, list[IbkrExecutionSnapshotRecord]] = {}
    for execution in executions:
        order_id = execution.ibkr_order_id
        if order_id is None:
            continue
        exec_by_order_id.setdefault(order_id, []).append(execution)

    submission_total = 0
    filled = 0
    cancelled = 0
    rejected = 0
    still_working = 0
    unchanged = 0
    failed = 0
    failures: list[dict[str, str]] = []

    reconcilable_states = {
        ActionDraftState.SUBMITTED.value,
        ActionDraftState.AWAITING_IBKR_REPLY.value,
        ActionDraftState.REPLY_CONFIRMED.value,
        ActionDraftState.WORKING.value,
    }

    for submission in submissions:
        if submission.state not in reconcilable_states:
            continue
        submission_total += 1
        try:
            current_state = coerce_state(submission.state)
        except InvalidStateTransitionError:
            failed += 1
            failures.append(
                {
                    "draft_id": submission.draft_id,
                    "reason": "unknown_current_state",
                    "state": submission.state,
                }
            )
            continue

        submitted_quantity = submitted_quantity_by_draft_id.get(submission.draft_id)
        if submitted_quantity is None or submitted_quantity <= 0:
            failed += 1
            failures.append(
                {
                    "draft_id": submission.draft_id,
                    "reason": "missing_submitted_quantity",
                }
            )
            continue

        next_state, details = _classify(
            submission=submission,
            open_orders_by_order_id=open_by_order_id,
            executions_by_order_id=exec_by_order_id,
            submitted_quantity=submitted_quantity,
        )
        if next_state is None:
            if details.get("reason") in {"missing_ibkr_order_id", "partial_fill_still_working"}:
                still_working += 1
            else:
                unchanged += 1
            continue

        try:
            require_transition_allowed(from_state=current_state, to_state=next_state)
        except InvalidStateTransitionError:
            failed += 1
            failures.append(
                {
                    "draft_id": submission.draft_id,
                    "reason": "invalid_state_transition",
                    "from_state": current_state.value,
                    "to_state": next_state.value,
                }
            )
            continue

        _persist_state_transition(
            submission=submission,
            next_state=next_state,
            submission_repo=submission_repo,
            event_repo=event_repo,
            details=details,
        )
        if next_state is ActionDraftState.FILLED:
            filled += 1
        elif next_state is ActionDraftState.CANCELLED:
            cancelled += 1
        elif next_state is ActionDraftState.REJECTED:
            rejected += 1

    completed_at = datetime.now(UTC)
    if submission_total == 0:
        status_nl = "Geen submissions om te reconciliëren"
        help_nl = "Submission-pool is leeg of staat al in een terminale toestand."
    elif filled + cancelled + rejected == 0 and failed == 0:
        status_nl = "Reconciliatie zonder terminale wijziging"
        help_nl = "Submissions blijven werkend bij IBKR."
    elif failed > 0:
        status_nl = "Reconciliatie deels mislukt"
        help_nl = "Sommige submissions konden niet worden afgesloten; zie failures."
    else:
        status_nl = "Reconciliatie voltooid"
        help_nl = "Alle terminale states zijn opgeslagen en in events gelogd."

    return ReconciliationReport(
        requested_at=requested_at,
        completed_at=completed_at,
        submissions_total=submission_total,
        submissions_filled=filled,
        submissions_cancelled=cancelled,
        submissions_rejected=rejected,
        submissions_still_working=still_working,
        submissions_unchanged=unchanged,
        submissions_failed=failed,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )
