"""Task 134b: Action Draft → IBKR placeOrder submission.

The submitter is the single code path that calls ``placeOrder()`` in
the production runtime. It owns the Tier 2 safety re-check (per-submit
account-ID re-read) that the brainstorm-locked two-tier model
demands; the actual network write happens through an
``IbkrSubmitProtocol`` adapter, so tests can inject fakes without
pulling in ``ib_insync``.

Every submission attempt writes one row to ``ibkr_submission_audit``
with ``result`` ∈ ``{placed, rejected_at_send, connection_lost}``
(Task 134 product lock §5). On ``placed`` the draft's status
transitions to ``submitted`` and the lifecycle_handler picks up the
callbacks from there. On ``rejected_at_send`` or ``connection_lost``
the draft stays at ``user_approved`` with a ``submission_block_reason``
set so the UI surfaces the Dutch badge; the sweep retries on the next
tick.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrSubmissionAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
)

from portfolio_outlook_worker.ibkr_submission.order_builder import (
    LimitPriceNotOnTickSizeError,
    TickSize,
    build_ib_order,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubmittedTrade:
    """Compact snapshot of an ``ib_insync.Trade`` after placeOrder().

    Tests pass a hand-built instance through a fake adapter; production
    callers wrap the real ``Trade`` object. ``contract_dict`` and
    ``order_dict`` are the canonical JSON representations the audit
    row persists.
    """

    perm_id: int
    order_id: int
    contract_dict: dict[str, object]
    order_dict: dict[str, object]


class IbkrSubmitProtocol(Protocol):
    """Narrow adapter the submitter relies on.

    The production implementation (wiring lives outside this PR) wraps
    ``ib_insync.IB`` and the ``IbkrGateway`` session manager. Tests
    inject fakes that record calls + return canned data.
    """

    @property
    def gateway_session_id(self) -> str: ...

    @property
    def account_mode(self) -> Literal["paper", "live"]: ...

    def fetch_managed_account_id(self) -> str: ...

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize: ...

    def place_order(
        self, contract: Any, order: Any
    ) -> SubmittedTrade: ...

    def cancel_order(self, perm_id: int) -> None: ...


class IbkrConnectionLostError(RuntimeError):
    """Raised by the adapter when the gateway session dropped mid-call."""


class IbkrTickSizeFetchError(RuntimeError):
    """Raised by the adapter when ``reqContractDetails`` fails."""


@dataclass(frozen=True)
class SubmissionResult:
    """Outcome of one ``IbkrSubmitter.submit(...)`` call.

    ``ok=True`` means the audit row was written with
    ``result="placed"`` and the draft is now in ``submitted`` status.
    ``ok=False`` carries a ``block_reason`` from the Task 134 locked
    enum + a Dutch ``error_message_dutch`` the UI surfaces verbatim.
    """

    ok: bool
    perm_id: int | None
    audit_id: int | None
    block_reason: str | None
    error_class: str | None
    error_message_dutch: str | None


@dataclass(frozen=True)
class CancelResult:
    """Outcome of one ``IbkrSubmitter.cancel(...)`` call.

    Cancels are fire-and-forget: ``ok=True`` means the cancel was sent to
    IBKR (the reconciler's Pass B converges the draft to ``cancelled`` once
    IBKR confirms). ``ok=False`` carries a Dutch message for the UI."""

    ok: bool
    perm_id: int | None
    error_class: str | None
    error_message_dutch: str | None


_CANCEL_DUTCH_MESSAGES: dict[str, str] = {
    "missing_perm_id": (
        "Geen IBKR order-id bekend voor deze draft; er is niets om te "
        "annuleren. De reconciler ruimt verweesde drafts op."
    ),
    "connection_down": (
        "Verbinding met IBKR verbroken tijdens annuleren. De annulering "
        "wordt op de volgende sweep opnieuw geprobeerd."
    ),
}


# Locked Dutch messages per submitter-side failure path. The Tier 1
# safety_recheck reasons live in safety_recheck._DUTCH_EXPLANATIONS;
# the submitter has its own set because Tier 2 is a different
# observation moment with its own user-facing context.
_DUTCH_MESSAGES: dict[str, str] = {
    "account_id_mismatch": (
        "Het IBKR-account dat IBKR rapporteert komt niet overeen met de "
        "draft op het moment van versturen. Submission afgebroken; "
        "controleer de IBKR-sessie."
    ),
    "tick_size_invalid": (
        "De limietprijs voldoet niet aan de IBKR tick-size voor dit "
        "contract. Pas de prijs aan en keur opnieuw goed."
    ),
    "connection_down": (
        "Verbinding met IBKR verbroken tijdens versturen. Submission "
        "wordt op de volgende sweep opnieuw geprobeerd."
    ),
    "unknown": (
        "Onverwachte fout tijdens IBKR-submission. Bekijk de audit-log "
        "voor details."
    ),
}


class IbkrSubmitter:
    """Submits one Action Draft to IBKR via the injected adapter.

    Constructor takes the storage repos + the IBKR adapter; ``submit``
    is the single public method. The submitter never starts its own
    transaction — the sweep wraps each tick in a checked connection
    and commits on its way out.
    """

    def __init__(
        self,
        *,
        submit_adapter: IbkrSubmitProtocol,
        action_draft_repo: SqlAlchemyActionDraftRepository,
        audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._submit_adapter = submit_adapter
        self._action_draft_repo = action_draft_repo
        self._audit_repo = audit_repo
        self._now_provider = now_provider

    def submit(self, draft: ActionDraftEntry) -> SubmissionResult:
        if draft.status != "user_approved":
            raise ValueError(
                f"IbkrSubmitter expects user_approved drafts; "
                f"got {draft.status!r}"
            )
        now = self._now()

        # Tier 2 safety: re-read the account ID at the exact submit
        # moment so a mid-session account swap can't slip an order
        # through. Tier 1 (cached gateway snapshot) was checked earlier
        # in the sweep; Tier 2 observes the live socket reply.
        live_account = self._submit_adapter.fetch_managed_account_id()
        if live_account != draft.ibkr_account_id:
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="rejected_at_send",
                reason="account_id_mismatch",
                error_class="AccountIdMismatchError",
            )

        try:
            tick = self._submit_adapter.fetch_tick_size(
                symbol=draft.symbol,
                exchange=draft.exchange,
                currency=draft.currency_local,
                conid=_safe_int(draft.conid),
            )
        except IbkrConnectionLostError as exc:
            logger.warning(
                "fetch_tick_size connection lost for draft %s: %s",
                draft.action_draft_id,
                exc,
            )
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="connection_lost",
                reason="connection_down",
                error_class=type(exc).__name__,
            )
        except IbkrTickSizeFetchError as exc:
            logger.warning(
                "fetch_tick_size failed for draft %s: %s",
                draft.action_draft_id,
                exc,
            )
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="rejected_at_send",
                reason="tick_size_invalid",
                error_class=type(exc).__name__,
            )

        try:
            contract, order = build_ib_order(
                draft=draft, tick=tick, conid=_safe_int(draft.conid)
            )
        except LimitPriceNotOnTickSizeError as exc:
            logger.warning(
                "tick_size align failed for draft %s: %s",
                draft.action_draft_id,
                exc,
            )
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="rejected_at_send",
                reason="tick_size_invalid",
                error_class=type(exc).__name__,
            )

        try:
            trade = self._submit_adapter.place_order(contract, order)
        except IbkrConnectionLostError as exc:
            logger.warning(
                "place_order connection lost for draft %s: %s",
                draft.action_draft_id,
                exc,
            )
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="connection_lost",
                reason="connection_down",
                error_class=type(exc).__name__,
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "place_order unexpected error for draft %s",
                draft.action_draft_id,
            )
            return self._record_block_and_mark_draft(
                draft=draft,
                now=now,
                result="rejected_at_send",
                reason="unknown",
                error_class=type(exc).__name__,
            )

        # Success path: write the audit row, transition the draft to
        # ``submitted``. The lifecycle_handler takes over from here.
        audit_entry = self._audit_repo.append(
            IbkrSubmissionAuditEntry(
                action_draft_id=draft.action_draft_id,
                submitted_at=now,
                sent_to_account_id=live_account,
                sent_account_mode=self._submit_adapter.account_mode,
                ibkr_perm_id=trade.perm_id,
                ibkr_order_id=trade.order_id,
                contract_json=trade.contract_dict,
                order_json=trade.order_dict,
                gateway_session_id=self._submit_adapter.gateway_session_id,
                result="placed",
                error_class=None,
                error_message_dutch=None,
            )
        )
        self._action_draft_repo.apply_lifecycle_transition(
            action_draft_id=draft.action_draft_id,
            new_status="submitted",
            transitioned_at=now,
        )
        return SubmissionResult(
            ok=True,
            perm_id=trade.perm_id,
            audit_id=audit_entry.id,
            block_reason=None,
            error_class=None,
            error_message_dutch=None,
        )

    def cancel(self, draft: ActionDraftEntry) -> CancelResult:
        """Send a fire-and-forget cancel for a ``pending_cancellation`` draft.

        The cancel is routed through the submitter so the IBKR adapter stays
        the single broker-write path. Status convergence to ``cancelled`` is
        the reconciler's job (Pass B); this method only sends the request."""

        if draft.status != "pending_cancellation":
            raise ValueError(
                f"IbkrSubmitter.cancel expects pending_cancellation drafts; "
                f"got {draft.status!r}"
            )
        # The draft → live perm_id mapping lives in the submission audit
        # (latest ``placed`` row), same resolution Pass B uses.
        perm_id = self._resolve_perm_id(draft.action_draft_id)
        if perm_id is None:
            return CancelResult(
                ok=False,
                perm_id=None,
                error_class="MissingPermId",
                error_message_dutch=_CANCEL_DUTCH_MESSAGES["missing_perm_id"],
            )
        try:
            self._submit_adapter.cancel_order(perm_id)
        except IbkrConnectionLostError as exc:
            logger.warning(
                "cancel_order connection lost for draft %s: %s",
                draft.action_draft_id,
                exc,
            )
            return CancelResult(
                ok=False,
                perm_id=perm_id,
                error_class=type(exc).__name__,
                error_message_dutch=_CANCEL_DUTCH_MESSAGES["connection_down"],
            )
        return CancelResult(
            ok=True, perm_id=perm_id, error_class=None, error_message_dutch=None
        )

    def _resolve_perm_id(self, action_draft_id: str) -> int | None:
        """Latest ``placed`` perm_id for the draft from the submission audit."""

        rows = self._audit_repo.list_for_draft(action_draft_id)
        for row in reversed(rows):
            if row.result == "placed" and row.ibkr_perm_id is not None:
                return int(row.ibkr_perm_id)
        return None

    def _record_block_and_mark_draft(
        self,
        *,
        draft: ActionDraftEntry,
        now: datetime,
        result: Literal["rejected_at_send", "connection_lost"],
        reason: str,
        error_class: str,
    ) -> SubmissionResult:
        message_nl = _DUTCH_MESSAGES.get(reason, _DUTCH_MESSAGES["unknown"])
        audit_entry = self._audit_repo.append(
            IbkrSubmissionAuditEntry(
                action_draft_id=draft.action_draft_id,
                submitted_at=now,
                sent_to_account_id=draft.ibkr_account_id,
                sent_account_mode=self._submit_adapter.account_mode,
                ibkr_perm_id=None,
                ibkr_order_id=None,
                contract_json={
                    "symbol": draft.symbol,
                    "exchange": draft.exchange,
                    "currency": draft.currency_local,
                },
                order_json={
                    "side": draft.side,
                    "quantity": str(draft.quantity),
                    "limit_price_local": str(draft.limit_price_local),
                    "order_type": draft.order_type,
                    "time_in_force": draft.time_in_force,
                },
                gateway_session_id=self._submit_adapter.gateway_session_id,
                result=result,
                error_class=error_class,
                error_message_dutch=message_nl,
            )
        )
        try:
            self._action_draft_repo.set_submission_block_reason(
                action_draft_id=draft.action_draft_id,
                reason=reason,
                set_at=now,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "set_submission_block_reason failed for draft %s",
                draft.action_draft_id,
            )
        return SubmissionResult(
            ok=False,
            perm_id=None,
            audit_id=audit_entry.id,
            block_reason=reason,
            error_class=error_class,
            error_message_dutch=message_nl,
        )

    def _now(self) -> datetime:
        if self._now_provider is not None:
            return self._now_provider()
        from datetime import UTC

        return datetime.now(UTC)


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
