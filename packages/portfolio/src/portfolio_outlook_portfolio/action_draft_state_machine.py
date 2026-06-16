"""Action-draft submission state machine.

Locked V1 state graph from
``docs/product/locked-decisions.md`` (IBKR reply-handshake lock) and the
release-1 blueprint §11:

    DRAFT
      ↳ SAFETY_CHECKED   (auto, when dry-run passes)
      ↳ USER_APPROVED    (via approve endpoint)
      ↳ SUBMITTED        (via submit-to-ibkr-paper endpoint, after IBKR
                          ``placeOrder`` returns synchronously)
      ↳ AWAITING_IBKR_REPLY  (immediately after SUBMITTED, until openOrder
                              callback or reconciliation arrives)
      ↳ REPLY_CONFIRMED   (after openOrder confirms the order live)
      ↳ WORKING           (alias for REPLY_CONFIRMED used by downstream
                          views; same semantics — IBKR has accepted)
      ↳ PENDING_CANCELLATION (operator clicked cancel on an in-flight
                              order; cancel-sweep will pick this up
                              and send the cancel to IBKR)
      ↳ FILLED / CANCELLED / REJECTED   (terminal at the IBKR side; await
                                          reconciliation)
      ↳ RECONCILED        (terminal local; sync confirmed terminal IBKR
                           state)

Plus drie safety-side terminals/escalations:
* ``EXPIRED`` — dry-run validity-window verlopen vóór submission
* ``FAILED`` — orchestrator-fout vóór de order is geplaatst
* ``REQUIRES_MANUAL_REVIEW`` — reconciliation Pass C 24h-timeout
  escalation; de operator moet manueel uitzoeken of de order live
  is bij IBKR (geen automatische actie meer)

Every transition is one-way except DRAFT⇆SAFETY_CHECKED⇆USER_APPROVED: an
edit can downgrade an approved draft back to DRAFT so a fresh dry-run
must re-pass before the next approval.

Audit-correctie §CB.2 (2026-06-16): ``PENDING_CANCELLATION`` en
``REQUIRES_MANUAL_REVIEW`` waren in V1.0 niet in deze map opgenomen;
``action_draft.py``'s cancel-route en ``pass_c_timeout_recovery.py``'s
escalation schreven hun status rechtstreeks naar het storage-layer
zonder ``require_transition_allowed`` te raadplegen. Nu opgenomen
zodat de transitie-validatie ÉCHT de waarheid van de state-machine
weerspiegelt.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class ActionDraftState(StrEnum):
    DRAFT = "draft"
    SAFETY_CHECKED = "safety_checked"
    USER_APPROVED = "user_approved"
    SUBMITTED = "submitted"
    AWAITING_IBKR_REPLY = "awaiting_ibkr_reply"
    REPLY_CONFIRMED = "reply_confirmed"
    WORKING = "working"
    PENDING_CANCELLATION = "pending_cancellation"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RECONCILED = "reconciled"
    EXPIRED = "expired"
    FAILED = "failed"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"


# Allowed transitions. Anything not in this map is **forbidden**.
ALLOWED_TRANSITIONS: Final[dict[ActionDraftState, frozenset[ActionDraftState]]] = {
    ActionDraftState.DRAFT: frozenset(
        {
            ActionDraftState.SAFETY_CHECKED,
            ActionDraftState.EXPIRED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.SAFETY_CHECKED: frozenset(
        {
            ActionDraftState.DRAFT,  # edit → must re-pass dry-run
            ActionDraftState.USER_APPROVED,
            ActionDraftState.EXPIRED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.USER_APPROVED: frozenset(
        {
            ActionDraftState.DRAFT,  # edit revokes approval
            ActionDraftState.SUBMITTED,
            ActionDraftState.EXPIRED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.SUBMITTED: frozenset(
        {
            ActionDraftState.AWAITING_IBKR_REPLY,
            ActionDraftState.PENDING_CANCELLATION,
            ActionDraftState.REJECTED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.AWAITING_IBKR_REPLY: frozenset(
        {
            ActionDraftState.REPLY_CONFIRMED,
            ActionDraftState.WORKING,
            ActionDraftState.PENDING_CANCELLATION,
            ActionDraftState.REJECTED,
            ActionDraftState.CANCELLED,
            ActionDraftState.FAILED,
            ActionDraftState.REQUIRES_MANUAL_REVIEW,
        }
    ),
    ActionDraftState.REPLY_CONFIRMED: frozenset(
        {
            ActionDraftState.WORKING,
            ActionDraftState.PENDING_CANCELLATION,
            ActionDraftState.FILLED,
            ActionDraftState.CANCELLED,
            ActionDraftState.REJECTED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.WORKING: frozenset(
        {
            ActionDraftState.PENDING_CANCELLATION,
            ActionDraftState.FILLED,
            ActionDraftState.CANCELLED,
            ActionDraftState.REJECTED,
            ActionDraftState.FAILED,
        }
    ),
    # PENDING_CANCELLATION — cancel-sweep stuurt cancel; outcome
    # bepaalt of de order alsnog gefilld werd (race tussen cancel en
    # fill) of netjes geannuleerd. Beide terminal-paden mogelijk.
    ActionDraftState.PENDING_CANCELLATION: frozenset(
        {
            ActionDraftState.CANCELLED,
            ActionDraftState.FILLED,
            ActionDraftState.REJECTED,
            ActionDraftState.FAILED,
        }
    ),
    ActionDraftState.FILLED: frozenset({ActionDraftState.RECONCILED}),
    ActionDraftState.CANCELLED: frozenset({ActionDraftState.RECONCILED}),
    ActionDraftState.REJECTED: frozenset({ActionDraftState.RECONCILED}),
    ActionDraftState.RECONCILED: frozenset(),  # terminal
    ActionDraftState.EXPIRED: frozenset(),  # terminal
    ActionDraftState.FAILED: frozenset(),  # terminal
    # REQUIRES_MANUAL_REVIEW — Pass C 24h escalation; geen
    # auto-transitie meer. Operator moet manueel uitzoeken (zou
    # vervolgens via een dedicated audit-tool naar een terminal
    # state gezet kunnen worden, V1.3+).
    ActionDraftState.REQUIRES_MANUAL_REVIEW: frozenset(),  # terminal for now
}


TERMINAL_STATES: Final[frozenset[ActionDraftState]] = frozenset(
    {
        ActionDraftState.RECONCILED,
        ActionDraftState.EXPIRED,
        ActionDraftState.FAILED,
        ActionDraftState.REQUIRES_MANUAL_REVIEW,
    }
)

# States that confirm the order is live at IBKR (used by downstream views).
LIVE_AT_BROKER_STATES: Final[frozenset[ActionDraftState]] = frozenset(
    {
        ActionDraftState.SUBMITTED,
        ActionDraftState.AWAITING_IBKR_REPLY,
        ActionDraftState.REPLY_CONFIRMED,
        ActionDraftState.WORKING,
        ActionDraftState.PENDING_CANCELLATION,
    }
)


class InvalidStateTransitionError(ValueError):
    """Raised when a caller asks for a state transition the doctrine forbids."""


def is_transition_allowed(
    *, from_state: ActionDraftState, to_state: ActionDraftState
) -> bool:
    """Return whether the transition ``from_state → to_state`` is allowed."""

    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())


def require_transition_allowed(
    *, from_state: ActionDraftState, to_state: ActionDraftState
) -> None:
    """Raise :class:`InvalidStateTransitionError` if the transition is not
    in the allowed map."""

    if not is_transition_allowed(from_state=from_state, to_state=to_state):
        raise InvalidStateTransitionError(
            f"transition {from_state} → {to_state} is not permitted"
        )


def coerce_state(value: str) -> ActionDraftState:
    """Convert a string from storage / API input into the typed enum.

    Unknown values raise :class:`InvalidStateTransitionError` to keep the
    code path honest: every accepted state must be listed here.
    """

    try:
        return ActionDraftState(value)
    except ValueError as exc:
        raise InvalidStateTransitionError(f"unknown state {value!r}") from exc
