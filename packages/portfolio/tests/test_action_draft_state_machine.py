"""Tests for the action-draft state machine."""

from __future__ import annotations

import pytest

from portfolio_outlook_portfolio.action_draft_state_machine import (
    ALLOWED_TRANSITIONS,
    LIVE_AT_BROKER_STATES,
    TERMINAL_STATES,
    ActionDraftState,
    InvalidStateTransitionError,
    coerce_state,
    is_transition_allowed,
    require_transition_allowed,
)


def test_locked_path_draft_to_reconciled_is_allowed_via_documented_steps() -> None:
    path = [
        ActionDraftState.DRAFT,
        ActionDraftState.SAFETY_CHECKED,
        ActionDraftState.USER_APPROVED,
        ActionDraftState.SUBMITTED,
        ActionDraftState.AWAITING_IBKR_REPLY,
        ActionDraftState.WORKING,
        ActionDraftState.FILLED,
        ActionDraftState.RECONCILED,
    ]
    for from_state, to_state in zip(path[:-1], path[1:], strict=True):
        assert is_transition_allowed(from_state=from_state, to_state=to_state), (
            f"locked path step {from_state} → {to_state} must be allowed"
        )


def test_edit_revokes_approval_by_transitioning_back_to_draft() -> None:
    assert is_transition_allowed(
        from_state=ActionDraftState.USER_APPROVED, to_state=ActionDraftState.DRAFT
    )
    assert is_transition_allowed(
        from_state=ActionDraftState.SAFETY_CHECKED, to_state=ActionDraftState.DRAFT
    )


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        # Cannot skip approval
        (ActionDraftState.SAFETY_CHECKED, ActionDraftState.SUBMITTED),
        # Cannot skip safety check
        (ActionDraftState.DRAFT, ActionDraftState.USER_APPROVED),
        # Cannot un-submit
        (ActionDraftState.SUBMITTED, ActionDraftState.DRAFT),
        (ActionDraftState.AWAITING_IBKR_REPLY, ActionDraftState.DRAFT),
        # Cannot resurrect terminals
        (ActionDraftState.RECONCILED, ActionDraftState.DRAFT),
        (ActionDraftState.EXPIRED, ActionDraftState.DRAFT),
        (ActionDraftState.FAILED, ActionDraftState.DRAFT),
        # Cannot jump straight to filled
        (ActionDraftState.SUBMITTED, ActionDraftState.FILLED),
    ],
)
def test_forbidden_transitions_raise(
    from_state: ActionDraftState, to_state: ActionDraftState
) -> None:
    assert not is_transition_allowed(from_state=from_state, to_state=to_state)
    with pytest.raises(InvalidStateTransitionError):
        require_transition_allowed(from_state=from_state, to_state=to_state)


def test_every_listed_state_appears_in_allowed_transitions_map() -> None:
    for state in ActionDraftState:
        assert state in ALLOWED_TRANSITIONS, f"state {state} missing from map"


def test_terminal_states_have_empty_outgoing_edges() -> None:
    for terminal in TERMINAL_STATES:
        assert ALLOWED_TRANSITIONS[terminal] == frozenset(), (
            f"terminal {terminal} must have no outgoing edges"
        )


def test_live_at_broker_states_cover_the_expected_window() -> None:
    # §CB.2 audit-cleanup 2026-06-16: PENDING_CANCELLATION is óók
    # "live at broker" — de cancel-sweep wacht op IBKR's antwoord.
    assert LIVE_AT_BROKER_STATES == frozenset(
        {
            ActionDraftState.SUBMITTED,
            ActionDraftState.AWAITING_IBKR_REPLY,
            ActionDraftState.REPLY_CONFIRMED,
            ActionDraftState.WORKING,
            ActionDraftState.PENDING_CANCELLATION,
        }
    )


def test_pending_cancellation_can_be_reached_from_all_in_flight_states() -> None:
    """§CB.2 audit-cleanup 2026-06-16: de cancel-flow stuurt elke
    in-flight state naar PENDING_CANCELLATION. Bevestig dat de state
    machine dit toelaat vanuit alle 4 in-flight states."""

    for from_state in (
        ActionDraftState.SUBMITTED,
        ActionDraftState.AWAITING_IBKR_REPLY,
        ActionDraftState.REPLY_CONFIRMED,
        ActionDraftState.WORKING,
    ):
        require_transition_allowed(
            from_state=from_state,
            to_state=ActionDraftState.PENDING_CANCELLATION,
        )


def test_pending_cancellation_resolves_to_terminal_states() -> None:
    """De cancel kan worden geraced door een fill — daarom mag
    PENDING_CANCELLATION zowel naar CANCELLED, FILLED, REJECTED als
    FAILED gaan."""

    for to_state in (
        ActionDraftState.CANCELLED,
        ActionDraftState.FILLED,
        ActionDraftState.REJECTED,
        ActionDraftState.FAILED,
    ):
        require_transition_allowed(
            from_state=ActionDraftState.PENDING_CANCELLATION,
            to_state=to_state,
        )


def test_requires_manual_review_can_be_reached_from_awaiting_reply() -> None:
    """§CB.2: Pass C 24h timeout-escalation transitioneert naar
    REQUIRES_MANUAL_REVIEW vanuit AWAITING_IBKR_REPLY."""

    require_transition_allowed(
        from_state=ActionDraftState.AWAITING_IBKR_REPLY,
        to_state=ActionDraftState.REQUIRES_MANUAL_REVIEW,
    )


def test_requires_manual_review_is_terminal() -> None:
    """REQUIRES_MANUAL_REVIEW is een terminal-state in V1.2; de
    operator heeft (nog) geen UI-route om hem manueel naar een
    terminal-state te schrijven."""

    assert ActionDraftState.REQUIRES_MANUAL_REVIEW in TERMINAL_STATES
    assert ALLOWED_TRANSITIONS[ActionDraftState.REQUIRES_MANUAL_REVIEW] == frozenset()


def test_coerce_state_round_trips_known_values() -> None:
    for state in ActionDraftState:
        assert coerce_state(state.value) is state


def test_coerce_state_rejects_unknown_values() -> None:
    with pytest.raises(InvalidStateTransitionError):
        coerce_state("teleporting")


def test_failure_and_expiry_can_short_circuit_from_any_pre_terminal_state() -> None:
    pre_terminals = (
        ActionDraftState.DRAFT,
        ActionDraftState.SAFETY_CHECKED,
        ActionDraftState.USER_APPROVED,
    )
    for state in pre_terminals:
        assert is_transition_allowed(from_state=state, to_state=ActionDraftState.FAILED)
        assert is_transition_allowed(from_state=state, to_state=ActionDraftState.EXPIRED)
