"""Task 134b: IBKR reply-handshake state machine.

The lifecycle handler is what listens for the four IBKR callback
event families (``Trade.statusEvent``, ``Trade.fillEvent``,
``Trade.commissionReportEvent``, ``Trade.cancelledEvent``) and
translates them into:

* a draft status transition via
  ``SqlAlchemyActionDraftRepository.apply_lifecycle_transition`` —
  the Task 134 product lock §6 state machine,
* one append-only row in ``ibkr_submission_lifecycle``,
* on fills: one row in ``ibkr_executions``.

The handler is fully synchronous + stateless — every method takes the
data it needs as inputs. The production wiring (registering the
callbacks on the ``ib_insync.Trade`` object returned by
``placeOrder()``) lives in the submitter / sweep adapter layer; tests
exercise the handler directly with hand-built event dataclasses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrExecutionEntry,
    IbkrSubmissionLifecycleEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event dataclasses — the handler's input contract.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderStatusEvent:
    """Triggered by ``ib_insync.Trade.statusEvent``.

    ``ibkr_raw_status`` is the verbatim IBKR string
    (``Submitted``/``PreSubmitted``/``Filled``/``Cancelled``/
    ``Inactive``/``Rejected``/...) — the handler maps it to the
    locked Task 134 draft statuses.
    """

    perm_id: int
    event_at: datetime
    ibkr_raw_status: str
    remaining_quantity: Decimal
    raw_callback_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FillEvent:
    """Triggered by ``ib_insync.Trade.fillEvent``.

    One event per partial or full fill. ``ibkr_exec_id`` is IBKR's
    natural unique key on the execution and powers the
    ``ibkr_executions.ibkr_exec_id`` UNIQUE constraint so duplicate
    callbacks land as ``IntegrityError`` rather than double-counting.
    """

    perm_id: int
    event_at: datetime
    ibkr_exec_id: str
    fill_price_local: Decimal
    fill_quantity: Decimal
    fill_time: datetime
    exchange: str
    raw_callback_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CommissionReportEvent:
    """Triggered by ``ib_insync.Trade.commissionReportEvent``.

    IBKR commission reports arrive separately from fills, sometimes
    seconds later. They reference the same ``ibkr_exec_id`` so the
    handler can attach the commission to the matching execution row.
    """

    perm_id: int
    event_at: datetime
    ibkr_exec_id: str
    commission: Decimal
    commission_currency: str
    raw_callback_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RejectionEvent:
    """Triggered by ``ib_insync.Trade.statusEvent`` when status==Rejected.

    The IBKR ``errorString`` is captured verbatim in
    ``raw_callback_json["error_string"]`` for the audit chain.
    """

    perm_id: int
    event_at: datetime
    reject_reason: str
    raw_callback_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CancellationEvent:
    """User-initiated cancellation request.

    Distinct from ``OrderStatusEvent(status='Cancelled')`` — that one
    is IBKR confirming the cancel; this one is the user clicking
    Cancel in the UI, which transitions to ``pending_cancellation``
    until IBKR confirms.
    """

    perm_id: int
    event_at: datetime
    raw_callback_json: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# IBKR raw status → Task 134 locked draft status mapping.
# ---------------------------------------------------------------------------


# IBKR's raw status enum is documented at
# https://interactivebrokers.github.io/tws-api/order_submission.html#order_status
# Only the values relevant to LMT × DAY × STK orders are mapped here;
# anything else returns None and the handler keeps the draft at its
# current status (logged for diagnosis).
_RAW_STATUS_MAP: dict[str, str] = {
    "Submitted": "accepted",  # IBKR has accepted the order
    "PreSubmitted": "working",  # IBKR has activated the order
    "Filled": "filled",  # mapped further below by remaining_quantity
    "Cancelled": "cancelled",
    "ApiCancelled": "cancelled",
    "Inactive": "rejected",
    "Rejected": "rejected",
}


def map_raw_status_to_lifecycle_status(
    *, ibkr_raw_status: str, remaining_quantity: Decimal
) -> str | None:
    """Pure helper: translate IBKR raw status to a Task 134 draft status.

    For ``Filled`` the choice between ``filled`` and ``partially_filled``
    depends on remaining quantity — IBKR fires multiple Fill events
    on a partial fill, so the handler distinguishes the terminal fill
    from the in-flight partial.
    """

    base = _RAW_STATUS_MAP.get(ibkr_raw_status)
    if base is None:
        return None
    if base == "filled":
        return "filled" if remaining_quantity <= 0 else "partially_filled"
    return base


# ---------------------------------------------------------------------------
# Handler.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleHandlerResult:
    """Outcome of one event-handler call.

    ``draft_status_after`` is None when the event didn't trigger a
    status change (e.g. an OrderStatus update from ``working`` →
    ``working``). ``execution_id_written`` is set only for FillEvents.
    """

    draft_status_after: str | None
    lifecycle_row_id: int | None
    execution_id_written: str | None


class LifecycleHandler:
    """Stateless dispatcher for the four IBKR callback families."""

    def __init__(
        self,
        *,
        action_draft_repo: SqlAlchemyActionDraftRepository,
        lifecycle_repo: SqlAlchemyIbkrSubmissionLifecycleRepository,
        executions_repo: SqlAlchemyIbkrExecutionsRepository,
    ) -> None:
        self._action_draft_repo = action_draft_repo
        self._lifecycle_repo = lifecycle_repo
        self._executions_repo = executions_repo

    # ----- OrderStatus -------------------------------------------------

    def handle_status_event(
        self,
        *,
        draft: ActionDraftEntry,
        event: OrderStatusEvent,
    ) -> LifecycleHandlerResult:
        next_status = map_raw_status_to_lifecycle_status(
            ibkr_raw_status=event.ibkr_raw_status,
            remaining_quantity=event.remaining_quantity,
        )
        if next_status is None:
            logger.info(
                "OrderStatus %r (perm=%s) not mapped; keeping draft "
                "in status %r",
                event.ibkr_raw_status,
                event.perm_id,
                draft.status,
            )
            written = self._lifecycle_repo.append(
                IbkrSubmissionLifecycleEntry(
                    action_draft_id=draft.action_draft_id,
                    event_at=event.event_at,
                    ibkr_perm_id=event.perm_id,
                    event_type="status_change",
                    from_status=draft.status,
                    to_status=None,
                    ibkr_raw_status=event.ibkr_raw_status,
                    fill_price_local=None,
                    fill_quantity=None,
                    commission=None,
                    commission_currency=None,
                    raw_callback_json=event.raw_callback_json,
                )
            )
            return LifecycleHandlerResult(
                draft_status_after=None,
                lifecycle_row_id=written.id,
                execution_id_written=None,
            )

        if next_status == draft.status:
            # Idempotent re-delivery of the same callback — record the
            # event for the audit chain but skip the (no-op) transition.
            written = self._lifecycle_repo.append(
                IbkrSubmissionLifecycleEntry(
                    action_draft_id=draft.action_draft_id,
                    event_at=event.event_at,
                    ibkr_perm_id=event.perm_id,
                    event_type="status_change",
                    from_status=draft.status,
                    to_status=next_status,
                    ibkr_raw_status=event.ibkr_raw_status,
                    fill_price_local=None,
                    fill_quantity=None,
                    commission=None,
                    commission_currency=None,
                    raw_callback_json=event.raw_callback_json,
                )
            )
            return LifecycleHandlerResult(
                draft_status_after=None,
                lifecycle_row_id=written.id,
                execution_id_written=None,
            )

        updated = self._action_draft_repo.apply_lifecycle_transition(
            action_draft_id=draft.action_draft_id,
            new_status=next_status,
            transitioned_at=event.event_at,
        )
        written = self._lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id=draft.action_draft_id,
                event_at=event.event_at,
                ibkr_perm_id=event.perm_id,
                event_type="status_change",
                from_status=draft.status,
                to_status=updated.status,
                ibkr_raw_status=event.ibkr_raw_status,
                fill_price_local=None,
                fill_quantity=None,
                commission=None,
                commission_currency=None,
                raw_callback_json=event.raw_callback_json,
            )
        )
        return LifecycleHandlerResult(
            draft_status_after=updated.status,
            lifecycle_row_id=written.id,
            execution_id_written=None,
        )

    # ----- Fill --------------------------------------------------------

    def handle_fill_event(
        self,
        *,
        draft: ActionDraftEntry,
        event: FillEvent,
        remaining_quantity_after: Decimal,
    ) -> LifecycleHandlerResult:
        """Record a fill + transition to filled / partially_filled.

        ``remaining_quantity_after`` is the live ``Trade.remaining()``
        after this fill has been applied — the handler can't infer it
        from the event alone because IBKR fires fills incrementally.
        """

        terminal = remaining_quantity_after <= 0
        next_status = "filled" if terminal else "partially_filled"

        execution_entry = self._executions_repo.append(
            IbkrExecutionEntry(
                ibkr_exec_id=event.ibkr_exec_id,
                ibkr_perm_id=event.perm_id,
                action_draft_id=draft.action_draft_id,
                account_id=draft.ibkr_account_id,
                conid=draft.conid,
                side=draft.side,
                fill_price_local=event.fill_price_local,
                fill_quantity=event.fill_quantity,
                fill_time=event.fill_time,
                commission=Decimal("0"),
                commission_currency=draft.currency_local,
                exchange=event.exchange,
            )
        )

        if next_status != draft.status:
            updated = self._action_draft_repo.apply_lifecycle_transition(
                action_draft_id=draft.action_draft_id,
                new_status=next_status,
                transitioned_at=event.event_at,
            )
            applied_status: str | None = updated.status
        else:
            applied_status = None

        written = self._lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id=draft.action_draft_id,
                event_at=event.event_at,
                ibkr_perm_id=event.perm_id,
                event_type="fill",
                from_status=draft.status,
                to_status=next_status,
                ibkr_raw_status=None,
                fill_price_local=event.fill_price_local,
                fill_quantity=event.fill_quantity,
                commission=None,
                commission_currency=None,
                raw_callback_json=event.raw_callback_json,
            )
        )
        return LifecycleHandlerResult(
            draft_status_after=applied_status,
            lifecycle_row_id=written.id,
            execution_id_written=execution_entry.ibkr_exec_id,
        )

    # ----- Commission report ------------------------------------------

    def handle_commission_report_event(
        self,
        *,
        draft: ActionDraftEntry,
        event: CommissionReportEvent,
    ) -> LifecycleHandlerResult:
        """Record commission. Does not change draft status."""

        written = self._lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id=draft.action_draft_id,
                event_at=event.event_at,
                ibkr_perm_id=event.perm_id,
                event_type="commission_report",
                from_status=None,
                to_status=None,
                ibkr_raw_status=None,
                fill_price_local=None,
                fill_quantity=None,
                commission=event.commission,
                commission_currency=event.commission_currency,
                raw_callback_json=event.raw_callback_json,
            )
        )
        return LifecycleHandlerResult(
            draft_status_after=None,
            lifecycle_row_id=written.id,
            execution_id_written=None,
        )

    # ----- Rejection ---------------------------------------------------

    def handle_rejection_event(
        self,
        *,
        draft: ActionDraftEntry,
        event: RejectionEvent,
    ) -> LifecycleHandlerResult:
        """Transition to ``rejected`` and record the IBKR reason."""

        from_status = draft.status
        if from_status not in ("submitted", "accepted", "working"):
            # Re-delivery or out-of-order callback — log + record but
            # don't try to retransition.
            written = self._lifecycle_repo.append(
                IbkrSubmissionLifecycleEntry(
                    action_draft_id=draft.action_draft_id,
                    event_at=event.event_at,
                    ibkr_perm_id=event.perm_id,
                    event_type="status_change",
                    from_status=from_status,
                    to_status=None,
                    ibkr_raw_status="Rejected",
                    fill_price_local=None,
                    fill_quantity=None,
                    commission=None,
                    commission_currency=None,
                    raw_callback_json={
                        **event.raw_callback_json,
                        "reject_reason": event.reject_reason,
                    },
                )
            )
            return LifecycleHandlerResult(
                draft_status_after=None,
                lifecycle_row_id=written.id,
                execution_id_written=None,
            )
        updated = self._action_draft_repo.apply_lifecycle_transition(
            action_draft_id=draft.action_draft_id,
            new_status="rejected",
            transitioned_at=event.event_at,
        )
        written = self._lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id=draft.action_draft_id,
                event_at=event.event_at,
                ibkr_perm_id=event.perm_id,
                event_type="status_change",
                from_status=from_status,
                to_status=updated.status,
                ibkr_raw_status="Rejected",
                fill_price_local=None,
                fill_quantity=None,
                commission=None,
                commission_currency=None,
                raw_callback_json={
                    **event.raw_callback_json,
                    "reject_reason": event.reject_reason,
                },
            )
        )
        return LifecycleHandlerResult(
            draft_status_after=updated.status,
            lifecycle_row_id=written.id,
            execution_id_written=None,
        )

    # ----- User-initiated cancellation -------------------------------

    def handle_cancellation_request_event(
        self,
        *,
        draft: ActionDraftEntry,
        event: CancellationEvent,
    ) -> LifecycleHandlerResult:
        """Transition from in-flight to ``pending_cancellation``.

        The actual ``cancelled`` status comes from IBKR's confirmation
        callback (handled by ``handle_status_event``).
        """

        from_status = draft.status
        updated = self._action_draft_repo.apply_lifecycle_transition(
            action_draft_id=draft.action_draft_id,
            new_status="pending_cancellation",
            transitioned_at=event.event_at,
        )
        written = self._lifecycle_repo.append(
            IbkrSubmissionLifecycleEntry(
                action_draft_id=draft.action_draft_id,
                event_at=event.event_at,
                ibkr_perm_id=event.perm_id,
                event_type="cancellation_request",
                from_status=from_status,
                to_status=updated.status,
                ibkr_raw_status=None,
                fill_price_local=None,
                fill_quantity=None,
                commission=None,
                commission_currency=None,
                raw_callback_json=event.raw_callback_json,
            )
        )
        return LifecycleHandlerResult(
            draft_status_after=updated.status,
            lifecycle_row_id=written.id,
            execution_id_written=None,
        )


# Convenience union typing for callers that want to dispatch
# generically. Not used by the production wiring (which calls the
# specific ``handle_*`` methods directly) but handy in tests.
LifecycleEvent = (
    OrderStatusEvent
    | FillEvent
    | CommissionReportEvent
    | RejectionEvent
    | CancellationEvent
)


__all__ = [
    "CancellationEvent",
    "CommissionReportEvent",
    "FillEvent",
    "LifecycleEvent",
    "LifecycleHandler",
    "LifecycleHandlerResult",
    "OrderStatusEvent",
    "RejectionEvent",
    "map_raw_status_to_lifecycle_status",
]


_ = Literal  # silence unused-import warning in case future widening removes Literal usage
