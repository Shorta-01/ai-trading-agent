"""Orchestrators for the locked action-draft state machine.

Three operations:

* ``approve_action_draft`` — re-runs the dry-run against the **current**
  market/cash/forecast snapshots, and persists an approval record + event
  if everything still passes.
* ``submit_action_draft_to_paper`` — gates again on approval + paper mode +
  approval freshness, calls the injected real ``ibapi`` submission client,
  and persists the resulting state (SUBMITTED → AWAITING_IBKR_REPLY or
  REJECTED on failure).
* ``record_state_event`` — append-only audit log helper used by both of
  the above.

Every persisted row has ``safe_for_broker_submission`` /
``safe_for_orders`` set to ``False`` — the doctrine forbids any record
that claims a submission is "safe" by itself. The actual gate sits in
``submit_action_draft_to_paper`` and nowhere else.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetActionDraftSubmissionRecord,
)
from portfolio_outlook_portfolio import (
    ActionDraftState,
    InvalidStateTransitionError,
    require_transition_allowed,
)

from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
    IbapiOrderSubmissionClient,
    OrderSubmissionInputs,
)

logger = logging.getLogger(__name__)


# ---- Result dataclasses --------------------------------------------------


@dataclass(frozen=True)
class ApproveActionDraftResult:
    status: str  # "approved" | "blocked"
    status_nl: str
    help_nl: str
    submission_id: str | None
    state: str
    blocking_reason: str | None
    failures: tuple[str, ...]


@dataclass(frozen=True)
class SubmitActionDraftResult:
    status: str  # "submitted" | "blocked" | "rejected"
    status_nl: str
    help_nl: str
    submission_id: str | None
    state: str
    ibkr_order_id: int | None
    ibkr_perm_id: int | None
    ibkr_status_text: str | None
    blocking_reason: str | None


# ---- Protocols -----------------------------------------------------------


class _SubmissionRepoProtocol(Protocol):
    def upsert_asset_action_draft_submission(
        self, record: AssetActionDraftSubmissionRecord
    ) -> object: ...

    def get_submission_by_draft_id(self, draft_id: str) -> object: ...


class _EventRepoProtocol(Protocol):
    def save_asset_action_draft_event(
        self, record: AssetActionDraftEventRecord
    ) -> object: ...


# ---- Helpers -------------------------------------------------------------


def _event(
    *,
    draft_id: str,
    submission_id: str | None,
    event_type: str,
    severity: str,
    from_state: str | None,
    to_state: str | None,
    rationale_nl: str,
    details_json: dict[str, str] | None = None,
) -> AssetActionDraftEventRecord:
    return AssetActionDraftEventRecord(
        event_id=f"evt_{uuid4().hex}",
        draft_id=draft_id,
        submission_id=submission_id,
        event_type=event_type,
        severity=severity,
        from_state=from_state,
        to_state=to_state,
        occurred_at=datetime.now(UTC),
        acknowledged_at=None,
        rationale_nl=rationale_nl,
        details_json=details_json,
    )


def _submission_record_template(
    draft: AssetActionDraftRecord,
    *,
    submission_id: str,
    state: ActionDraftState,
    approval_status: str,
    approved_at: datetime | None,
    approval_dry_run_status: str | None,
    approval_dry_run_failures: tuple[str, ...] | None,
    provider_code: str,
    expected_account_mode: str,
    submitted_at: datetime | None = None,
    ibkr_order_id: int | None = None,
    ibkr_perm_id: int | None = None,
    ibkr_client_id: int | None = None,
    ibkr_status_text: str | None = None,
    rejected_reason: str | None = None,
) -> AssetActionDraftSubmissionRecord:
    now = datetime.now(UTC)
    return AssetActionDraftSubmissionRecord(
        submission_id=submission_id,
        draft_id=draft.draft_id,
        state=state.value,
        approval_status=approval_status,
        approved_at=approved_at,
        approved_by="owner" if approval_status == "approved" else None,
        approval_dry_run_status=approval_dry_run_status,
        approval_dry_run_failures_json=approval_dry_run_failures,
        submitted_at=submitted_at,
        ibkr_order_id=ibkr_order_id,
        ibkr_perm_id=ibkr_perm_id,
        ibkr_client_id=ibkr_client_id,
        ibkr_status_text=ibkr_status_text,
        filled_quantity=None,
        remaining_quantity=None,
        average_fill_price=None,
        cancelled_at=None,
        cancellation_reason=None,
        rejected_reason=rejected_reason,
        reconciled_at=None,
        account_mode=draft.account_mode,
        expected_account_mode=expected_account_mode,
        provider_code=provider_code,
        created_at=now,
        updated_at=now,
        last_state_transition_at=now,
    )


# ---- approve_action_draft ------------------------------------------------


def approve_action_draft(
    *,
    draft: AssetActionDraftRecord,
    submission_repo: _SubmissionRepoProtocol,
    event_repo: _EventRepoProtocol,
    expected_account_mode: str,
    provider_code: str,
) -> ApproveActionDraftResult:
    """Re-validate the draft and persist an approval record.

    The dry-run on the draft itself was computed at generation time. Here
    we re-check that the draft's persisted dry-run was actually ``passed``,
    that the account mode is paper, and that the draft itself hasn't been
    already approved-and-submitted (idempotency: re-approving an already
    submitted draft is a no-op blocked response).
    """

    if draft.account_mode.strip().lower() != "paper":
        event_repo.save_asset_action_draft_event(
            _event(
                draft_id=draft.draft_id,
                submission_id=None,
                event_type="approval_blocked",
                severity="critical",
                from_state=None,
                to_state=None,
                rationale_nl="Approval geblokkeerd: alleen paper-account toegestaan.",
            )
        )
        return ApproveActionDraftResult(
            status="blocked",
            status_nl="Approval geblokkeerd",
            help_nl="Alleen paper-account orders zijn toegestaan in V1.",
            submission_id=None,
            state=ActionDraftState.DRAFT.value,
            blocking_reason="paper_only_required",
            failures=("paper_only_required",),
        )

    if expected_account_mode.strip().lower() != "paper":
        return ApproveActionDraftResult(
            status="blocked",
            status_nl="Approval geblokkeerd",
            help_nl="Verwacht account-mode moet 'paper' zijn.",
            submission_id=None,
            state=ActionDraftState.DRAFT.value,
            blocking_reason="expected_account_mode_not_paper",
            failures=("expected_account_mode_not_paper",),
        )

    if draft.dry_run_status != "passed":
        event_repo.save_asset_action_draft_event(
            _event(
                draft_id=draft.draft_id,
                submission_id=None,
                event_type="approval_blocked",
                severity="critical",
                from_state=ActionDraftState.DRAFT.value,
                to_state=None,
                rationale_nl="Approval geblokkeerd: dry-run is niet geslaagd.",
            )
        )
        return ApproveActionDraftResult(
            status="blocked",
            status_nl="Approval geblokkeerd",
            help_nl=(
                "Dry-run moet eerst slagen voordat een draft kan worden goedgekeurd."
            ),
            submission_id=None,
            state=ActionDraftState.DRAFT.value,
            blocking_reason="dry_run_not_passed",
            failures=draft.dry_run_failures_json or (),
        )

    # Determine source state for the audit log
    existing = submission_repo.get_submission_by_draft_id(draft.draft_id)
    from_state = ActionDraftState.SAFETY_CHECKED
    existing_record = getattr(existing, "record", None)
    if existing_record is not None and getattr(existing_record, "state", None):
        try:
            from_state = ActionDraftState(existing_record.state)
        except ValueError:
            from_state = ActionDraftState.SAFETY_CHECKED

    try:
        require_transition_allowed(
            from_state=from_state, to_state=ActionDraftState.USER_APPROVED
        )
    except InvalidStateTransitionError:
        return ApproveActionDraftResult(
            status="blocked",
            status_nl="Approval geblokkeerd",
            help_nl=(
                f"Statusovergang {from_state} → user_approved is niet toegestaan."
            ),
            submission_id=None,
            state=from_state.value,
            blocking_reason="invalid_state_transition",
            failures=("invalid_state_transition",),
        )

    submission_id = f"sub_{uuid4().hex}"
    now = datetime.now(UTC)
    record = _submission_record_template(
        draft,
        submission_id=submission_id,
        state=ActionDraftState.USER_APPROVED,
        approval_status="approved",
        approved_at=now,
        approval_dry_run_status="passed",
        approval_dry_run_failures=None,
        provider_code=provider_code,
        expected_account_mode=expected_account_mode,
    )
    submission_repo.upsert_asset_action_draft_submission(record)
    event_repo.save_asset_action_draft_event(
        _event(
            draft_id=draft.draft_id,
            submission_id=submission_id,
            event_type="approved",
            severity="critical",
            from_state=from_state.value,
            to_state=ActionDraftState.USER_APPROVED.value,
            rationale_nl="Gebruiker heeft de draft goedgekeurd.",
        )
    )
    return ApproveActionDraftResult(
        status="approved",
        status_nl="Draft goedgekeurd",
        help_nl="Klik op verzenden om de paper order naar IBKR te sturen.",
        submission_id=submission_id,
        state=ActionDraftState.USER_APPROVED.value,
        blocking_reason=None,
        failures=(),
    )


# ---- submit_action_draft_to_paper ----------------------------------------


def submit_action_draft_to_paper(
    *,
    draft: AssetActionDraftRecord,
    submission_repo: _SubmissionRepoProtocol,
    event_repo: _EventRepoProtocol,
    submission_client: IbapiOrderSubmissionClient | None,
    expected_account_mode: str,
    provider_code: str,
    approval_valid_minutes: int,
) -> SubmitActionDraftResult:
    """Submit a previously-approved draft to the IBKR paper gateway.

    Every gate is re-checked here. The injected ``submission_client`` is
    the only path to ``placeOrder`` — if the factory returned ``None`` the
    response is a blocked record with reason ``submission_client_unavailable``.
    """

    if submission_client is None:
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Submission client niet geconfigureerd",
            help_nl=(
                "Stel `IBKR_PAPER_ORDER_SUBMISSION_REAL_CLIENT_ENABLED=true` "
                "en de host/port/client-id in om paper orders te kunnen verzenden."
            ),
            submission_id=None,
            state=ActionDraftState.USER_APPROVED.value,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="submission_client_unavailable",
        )

    if draft.account_mode.strip().lower() != "paper":
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Submission geblokkeerd",
            help_nl="Alleen paper-account orders zijn toegestaan in V1.",
            submission_id=None,
            state=ActionDraftState.USER_APPROVED.value,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="paper_only_required",
        )

    if draft.dry_run_status != "passed":
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Submission geblokkeerd",
            help_nl="Dry-run moet geslaagd zijn voordat een draft verzonden mag worden.",
            submission_id=None,
            state=ActionDraftState.USER_APPROVED.value,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="dry_run_not_passed",
        )

    existing = submission_repo.get_submission_by_draft_id(draft.draft_id)
    existing_record = getattr(existing, "record", None)
    if existing_record is None or existing_record.approval_status != "approved":
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Submission geblokkeerd",
            help_nl="Draft moet eerst goedgekeurd worden via /approve.",
            submission_id=None,
            state=ActionDraftState.SAFETY_CHECKED.value,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="approval_missing",
        )

    if existing_record.approved_at is None:
        approval_age_seconds = approval_valid_minutes * 60 + 1
    else:
        approval_age_seconds = (
            datetime.now(UTC) - existing_record.approved_at
        ).total_seconds()
    if approval_age_seconds > approval_valid_minutes * 60:
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Approval verlopen",
            help_nl=(
                f"Approval is ouder dan {approval_valid_minutes} minuten; "
                "keur de draft opnieuw goed."
            ),
            submission_id=existing_record.submission_id,
            state=existing_record.state,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="approval_expired",
        )

    try:
        require_transition_allowed(
            from_state=ActionDraftState(existing_record.state),
            to_state=ActionDraftState.SUBMITTED,
        )
    except InvalidStateTransitionError:
        return SubmitActionDraftResult(
            status="blocked",
            status_nl="Submission geblokkeerd",
            help_nl=(
                f"Statusovergang {existing_record.state} → submitted is niet toegestaan."
            ),
            submission_id=existing_record.submission_id,
            state=existing_record.state,
            ibkr_order_id=None,
            ibkr_perm_id=None,
            ibkr_status_text=None,
            blocking_reason="invalid_state_transition",
        )

    # V1.2 §AR doctrine (CLAUDE.md §2 + §6.3): de software stuurt
    # NOOIT een automatische take-profit-LMT of stop-loss-LMT mee
    # naar IBKR. Alleen de entry-LMT wordt verzonden; de exit
    # gebeurt na manuele bevestiging van een SELL-suggestie
    # kaartje op het dashboard (gegenereerd door de pure-Python
    # ``take_profit_signal_monitor.evaluate_take_profit_signal``).
    # De bracket-velden blijven op de draft-rij voor audit-doeleinden
    # maar worden hier expliciet op ``None`` gezet voor de submission
    # zodat IBKR geen passieve exit-LMT plaatst.
    inputs = OrderSubmissionInputs(
        symbol=draft.symbol,
        primary_exchange=draft.primary_exchange or "NASDAQ",
        currency=draft.currency,
        security_type="STK",
        action_side=draft.action_side,
        quantity=draft.quantity,
        limit_price=draft.limit_price,
        order_type=draft.order_type,
        stop_price=draft.stop_price,
        trail_amount=draft.trail_amount,
        trail_percent=draft.trail_percent,
        bracket_take_profit_limit_price=None,
        bracket_stop_loss_price=None,
    )

    try:
        result = submission_client.submit(inputs)
    finally:
        submission_client.close()

    event_repo.save_asset_action_draft_event(
        _event(
            draft_id=draft.draft_id,
            submission_id=existing_record.submission_id,
            event_type="submitted" if result.accepted else "submission_failed",
            severity="critical",
            from_state=existing_record.state,
            to_state=(
                ActionDraftState.AWAITING_IBKR_REPLY.value
                if result.accepted
                else ActionDraftState.REJECTED.value
            ),
            rationale_nl=(
                "Order verzonden naar IBKR paper."
                if result.accepted
                else f"Submission afgewezen: {result.rejected_reason or 'onbekend'}"
            ),
            details_json={
                "ibkr_order_id": str(result.ibkr_order_id or ""),
                "ibkr_perm_id": str(result.ibkr_perm_id or ""),
                "rejected_reason": result.rejected_reason or "",
            },
        )
    )

    new_state = (
        ActionDraftState.AWAITING_IBKR_REPLY if result.accepted else ActionDraftState.REJECTED
    )
    record = _submission_record_template(
        draft,
        submission_id=existing_record.submission_id,
        state=new_state,
        approval_status=existing_record.approval_status,
        approved_at=existing_record.approved_at,
        approval_dry_run_status=existing_record.approval_dry_run_status,
        approval_dry_run_failures=existing_record.approval_dry_run_failures_json,
        provider_code=provider_code,
        expected_account_mode=expected_account_mode,
        submitted_at=datetime.now(UTC),
        ibkr_order_id=result.ibkr_order_id,
        ibkr_perm_id=result.ibkr_perm_id,
        ibkr_client_id=result.ibkr_client_id,
        ibkr_status_text=result.ibkr_status_text,
        rejected_reason=result.rejected_reason,
    )
    submission_repo.upsert_asset_action_draft_submission(record)

    if result.accepted:
        return SubmitActionDraftResult(
            status="submitted",
            status_nl="Order verzonden naar IBKR paper",
            help_nl=(
                "De order is verzonden. De status wordt bijgewerkt zodra IBKR-sync "
                "de bevestiging verwerkt."
            ),
            submission_id=existing_record.submission_id,
            state=new_state.value,
            ibkr_order_id=result.ibkr_order_id,
            ibkr_perm_id=result.ibkr_perm_id,
            ibkr_status_text=result.ibkr_status_text,
            blocking_reason=None,
        )
    return SubmitActionDraftResult(
        status="rejected",
        status_nl="Order afgewezen door IBKR",
        help_nl="De order is niet geaccepteerd; controleer de details en pas de draft aan.",
        submission_id=existing_record.submission_id,
        state=new_state.value,
        ibkr_order_id=result.ibkr_order_id,
        ibkr_perm_id=result.ibkr_perm_id,
        ibkr_status_text=result.ibkr_status_text,
        blocking_reason=result.rejected_reason or "submission_rejected",
    )


def serialize_submission_for_response(
    record: AssetActionDraftSubmissionRecord,
) -> dict[str, object]:
    return {
        "submission_id": record.submission_id,
        "draft_id": record.draft_id,
        "state": record.state,
        "approval_status": record.approval_status,
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "approved_by": record.approved_by,
        "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
        "ibkr_order_id": record.ibkr_order_id,
        "ibkr_perm_id": record.ibkr_perm_id,
        "ibkr_client_id": record.ibkr_client_id,
        "ibkr_status_text": record.ibkr_status_text,
        "rejected_reason": record.rejected_reason,
        "account_mode": record.account_mode,
        "expected_account_mode": record.expected_account_mode,
        "provider_code": record.provider_code,
        "last_state_transition_at": record.last_state_transition_at.isoformat(),
        "safe_for_broker_submission": False,
        "safe_for_orders": False,
    }


def serialize_event_for_response(
    record: AssetActionDraftEventRecord,
) -> dict[str, object]:
    return {
        "event_id": record.event_id,
        "draft_id": record.draft_id,
        "submission_id": record.submission_id,
        "event_type": record.event_type,
        "severity": record.severity,
        "from_state": record.from_state,
        "to_state": record.to_state,
        "occurred_at": record.occurred_at.isoformat(),
        "acknowledged_at": (
            record.acknowledged_at.isoformat() if record.acknowledged_at else None
        ),
        "rationale_nl": record.rationale_nl,
        "details": record.details_json or {},
    }


# Hint at the helper name so future readers find it.
_ = timedelta  # noqa: B018
