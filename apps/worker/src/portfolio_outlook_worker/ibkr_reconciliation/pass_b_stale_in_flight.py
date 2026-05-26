"""Task 135b: Pass B — stale in-flight detection.

Pass B compares the worker's view of in-flight drafts (``submitted`` /
``accepted`` / ``working`` / ``partially_filled`` / ``pending_cancellation``)
against IBKR's order-status truth. For each in-flight draft it asks
the gateway for the live status of the draft's ``ibkr_perm_id`` and
acts on the result:

* **IBKR says the order is terminal but we think it's in-flight** —
  heal the draft to the matching terminal status (``filled`` /
  ``cancelled`` / ``rejected``) and write one ``status_corrected_to_*``
  audit row. Fills detected via this path are *not* re-recorded here
  (Pass A owns ``ibkr_executions`` writes); Pass B's job is solely to
  reconcile the draft status when Pass A's execution polling missed
  an order-status callback.

* **IBKR doesn't know the perm_id at all** — log one
  ``terminal_state_divergence_logged`` reconciliation_audit row with
  the IBKR response in ``ibkr_evidence_json`` and leave the draft
  alone. The user resolves this through the manual-review queue
  surface (added later in 135b).

* **IBKR reports a status that's still in-flight** (the worker is in
  sync) — no-op.

Pass B never touches the executions table and never reverses a
terminal status. It is purely additive on the audit chain.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ReconciliationAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyReconciliationAuditRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IBKR-side adapter contract.
# ---------------------------------------------------------------------------


# Locked IBKR raw status set that Pass B understands. Anything outside
# this set is treated as ``unknown`` and the draft is not touched.
_IBKR_RAW_TO_DRAFT_STATUS: dict[str, str] = {
    "Submitted": "accepted",
    "PreSubmitted": "working",
    "Filled": "filled",
    "Cancelled": "cancelled",
    "ApiCancelled": "cancelled",
    "Inactive": "rejected",
    "Rejected": "rejected",
}

# Subset that closes the draft into a terminal status. Pass B will
# attempt a heal only when IBKR reports one of these.
_IBKR_TERMINAL_STATUSES = frozenset({"filled", "cancelled", "rejected"})


@dataclass(frozen=True)
class IbkrOrderStatusForReconciliation:
    """One IBKR-side order status snapshot used by Pass B.

    Production wraps an ``ib_insync`` ``orderStatus`` callback or a
    ``reqOpenOrders``/``reqAllOpenOrders`` snapshot into this
    dataclass; tests construct instances by hand.

    ``found_in_ibkr`` distinguishes the *unknown perm_id* case (the
    worker thinks the order is in-flight but IBKR has no record of
    it) from the *known with status* case.
    """

    ibkr_perm_id: int
    found_in_ibkr: bool
    ibkr_raw_status: str | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)


class IbkrOrderStatusFetcherProtocol(Protocol):
    """Adapter Pass B relies on to read live IBKR-side order status.

    Production wraps ``ib_insync.IB.reqOpenOrders()`` + a perm_id
    lookup; tests inject fakes that return canned data so unit tests
    stay deterministic.
    """

    def fetch_order_status(
        self, *, ibkr_perm_id: int, account_id: str
    ) -> IbkrOrderStatusForReconciliation: ...


# ---------------------------------------------------------------------------
# Outcome dataclass.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassBStaleInFlightResult:
    """Audit-friendly outcome of running Pass B once."""

    reconciliation_run_id: str
    account_id: str
    drafts_evaluated: int
    drafts_skipped_no_perm_id: int
    status_corrections_applied: int
    terminal_divergence_logged: int
    in_sync_count: int
    divergences_found: int
    healed_draft_ids: tuple[str, ...] = field(default_factory=tuple)
    divergent_draft_ids: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Pass B entry point.
# ---------------------------------------------------------------------------


def run_pass_b_stale_in_flight(
    *,
    reconciliation_run_id: str,
    account_id: str,
    fetcher: IbkrOrderStatusFetcherProtocol,
    action_draft_repo: SqlAlchemyActionDraftRepository,
    submission_audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
    now_provider: Callable[[], datetime],
) -> PassBStaleInFlightResult:
    """Run Pass B for one reconciler tick.

    Pass B never raises through; per-draft failures are logged and
    counted as ``terminal_divergence_logged`` so the orchestrator can
    continue to Pass C.
    """

    drafts = action_draft_repo.list_active_for_account(
        ibkr_account_id=account_id
    )
    skipped = 0
    healed = 0
    divergent = 0
    in_sync = 0
    healed_ids: list[str] = []
    divergent_ids: list[str] = []

    for draft in drafts:
        # The submission audit table has both action_draft_id and
        # ibkr_perm_id; we walk that repo's per-draft history to find
        # the latest ``placed`` perm_id (a draft may have a
        # ``rejected_at_send`` followed by a successful retry).
        perm_id_value = _resolve_perm_id_for_draft(
            action_draft_id=draft.action_draft_id,
            submission_audit_repo=submission_audit_repo,
        )
        if perm_id_value is None:
            skipped += 1
            continue

        try:
            status = fetcher.fetch_order_status(
                ibkr_perm_id=perm_id_value,
                account_id=account_id,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Pass B fetch_order_status raised for draft %s perm %s",
                draft.action_draft_id,
                perm_id_value,
            )
            skipped += 1
            continue

        event_at = now_provider()

        if not status.found_in_ibkr:
            _log_terminal_divergence_unknown_to_ibkr(
                draft=draft,
                perm_id=perm_id_value,
                reconciliation_run_id=reconciliation_run_id,
                event_at=event_at,
                payload=status.raw_payload,
                reconciliation_audit_repo=reconciliation_audit_repo,
            )
            divergent += 1
            divergent_ids.append(draft.action_draft_id)
            continue

        mapped = _IBKR_RAW_TO_DRAFT_STATUS.get(status.ibkr_raw_status or "")
        if mapped is None:
            # Unknown raw status — record as divergence but don't touch
            # the draft; mode is intentionally conservative.
            _log_terminal_divergence_unknown_status(
                draft=draft,
                perm_id=perm_id_value,
                ibkr_raw_status=status.ibkr_raw_status,
                reconciliation_run_id=reconciliation_run_id,
                event_at=event_at,
                payload=status.raw_payload,
                reconciliation_audit_repo=reconciliation_audit_repo,
            )
            divergent += 1
            divergent_ids.append(draft.action_draft_id)
            continue

        if mapped not in _IBKR_TERMINAL_STATUSES:
            # IBKR also thinks the order is in-flight; nothing to heal.
            in_sync += 1
            continue

        if mapped == draft.status:
            # Both sides agree it's terminal (shouldn't normally happen
            # since Pass B iterates non-terminal drafts only, but be
            # robust against in-flight terminal races).
            in_sync += 1
            continue

        before_status = draft.status
        try:
            updated = action_draft_repo.apply_lifecycle_transition(
                action_draft_id=draft.action_draft_id,
                new_status=mapped,
                transitioned_at=event_at,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Pass B apply_lifecycle_transition failed for draft %s "
                "(%s -> %s)",
                draft.action_draft_id,
                before_status,
                mapped,
            )
            _log_terminal_divergence_transition_failed(
                draft=draft,
                perm_id=perm_id_value,
                attempted_status=mapped,
                reconciliation_run_id=reconciliation_run_id,
                event_at=event_at,
                payload=status.raw_payload,
                reconciliation_audit_repo=reconciliation_audit_repo,
            )
            divergent += 1
            divergent_ids.append(draft.action_draft_id)
            continue

        reconciliation_audit_repo.append(
            ReconciliationAuditEntry(
                reconciliation_run_id=reconciliation_run_id,
                action_draft_id=draft.action_draft_id,
                event_at=event_at,
                pass_name="stale_in_flight",
                divergence_type=_corrected_divergence_for(updated.status),
                before_status=before_status,
                after_status=updated.status,
                ibkr_evidence_json={
                    "ibkr_perm_id": perm_id_value,
                    "ibkr_raw_status": status.ibkr_raw_status,
                    **status.raw_payload,
                },
                notes_dutch=(
                    "Status van Action Draft hersteld op basis van "
                    "IBKR-orderstatus."
                ),
            )
        )
        healed += 1
        healed_ids.append(draft.action_draft_id)

    return PassBStaleInFlightResult(
        reconciliation_run_id=reconciliation_run_id,
        account_id=account_id,
        drafts_evaluated=len(drafts),
        drafts_skipped_no_perm_id=skipped,
        status_corrections_applied=healed,
        terminal_divergence_logged=divergent,
        in_sync_count=in_sync,
        divergences_found=healed + divergent,
        healed_draft_ids=tuple(healed_ids),
        divergent_draft_ids=tuple(divergent_ids),
    )


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _resolve_perm_id_for_draft(
    *,
    action_draft_id: str,
    submission_audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
) -> int | None:
    """Return the latest ``placed`` perm_id for the draft, or None.

    A draft can have multiple submission audit rows (e.g. a
    ``rejected_at_send`` followed by a successful retry); Pass B
    needs the most recent ``placed`` perm_id since that's the live
    IBKR order ID. ``list_for_draft`` returns chronological order
    (oldest first), so we walk in reverse.
    """

    rows = submission_audit_repo.list_for_draft(action_draft_id)
    for row in reversed(rows):
        if row.result == "placed" and row.ibkr_perm_id is not None:
            return row.ibkr_perm_id
    return None


def _log_terminal_divergence_unknown_to_ibkr(
    *,
    draft: ActionDraftEntry,
    perm_id: int,
    reconciliation_run_id: str,
    event_at: datetime,
    payload: dict[str, object],
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
) -> None:
    action_draft_id = draft.action_draft_id
    status = draft.status
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=action_draft_id,
            event_at=event_at,
            pass_name="stale_in_flight",
            divergence_type="terminal_state_divergence_logged",
            before_status=status,
            after_status=status,
            ibkr_evidence_json={
                "ibkr_perm_id": perm_id,
                "ibkr_found": False,
                **payload,
            },
            notes_dutch=(
                "IBKR rapporteert deze order niet meer; lokale status "
                "ongewijzigd."
            ),
        )
    )


def _log_terminal_divergence_unknown_status(
    *,
    draft: ActionDraftEntry,
    perm_id: int,
    ibkr_raw_status: str | None,
    reconciliation_run_id: str,
    event_at: datetime,
    payload: dict[str, object],
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
) -> None:
    action_draft_id = draft.action_draft_id
    status = draft.status
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=action_draft_id,
            event_at=event_at,
            pass_name="stale_in_flight",
            divergence_type="terminal_state_divergence_logged",
            before_status=status,
            after_status=status,
            ibkr_evidence_json={
                "ibkr_perm_id": perm_id,
                "ibkr_raw_status": ibkr_raw_status,
                "ibkr_status_unknown_to_reconciler": True,
                **payload,
            },
            notes_dutch=(
                "IBKR rapporteert een onbekende status; "
                "lokale status ongewijzigd."
            ),
        )
    )


def _log_terminal_divergence_transition_failed(
    *,
    draft: ActionDraftEntry,
    perm_id: int,
    attempted_status: str,
    reconciliation_run_id: str,
    event_at: datetime,
    payload: dict[str, object],
    reconciliation_audit_repo: SqlAlchemyReconciliationAuditRepository,
) -> None:
    action_draft_id = draft.action_draft_id
    status = draft.status
    reconciliation_audit_repo.append(
        ReconciliationAuditEntry(
            reconciliation_run_id=reconciliation_run_id,
            action_draft_id=action_draft_id,
            event_at=event_at,
            pass_name="stale_in_flight",
            divergence_type="terminal_state_divergence_logged",
            before_status=status,
            after_status=status,
            ibkr_evidence_json={
                "ibkr_perm_id": perm_id,
                "attempted_status": attempted_status,
                "transition_failed": True,
                **payload,
            },
            notes_dutch=(
                "Statusovergang geweigerd door de state-machine; "
                "menselijke review nodig."
            ),
        )
    )


def _corrected_divergence_for(new_status: str) -> str:
    if new_status == "filled":
        return "status_corrected_to_filled"
    if new_status == "partially_filled":
        return "status_corrected_to_partially_filled"
    if new_status == "cancelled":
        return "status_corrected_to_cancelled"
    if new_status == "rejected":
        return "status_corrected_to_rejected"
    raise ValueError(
        f"Pass B produced unexpected heal status {new_status!r}"
    )


__all__ = [
    "IbkrOrderStatusFetcherProtocol",
    "IbkrOrderStatusForReconciliation",
    "PassBStaleInFlightResult",
    "run_pass_b_stale_in_flight",
]


_ = Literal  # silence unused-import warning
