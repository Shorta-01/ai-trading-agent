"""Task 134: pure-function submission gate evaluator.

The submission sweep calls ``evaluate_submission_gates`` for every
``user_approved`` draft on every minute tick. This function is the
single source of truth for the locked Tier 1 safety re-check
(account-mode + connection + account-ID + cash + position + market-
hours + duplicate-in-flight + behavioural guardrails) defined in
Task 134 product lock §3 and §4.

It returns a frozen ``SubmissionGateResult`` — either ``ok=True`` or
``ok=False`` with a locked ``block_reason`` enum and a Dutch
``explanation_nl`` string the UI can surface verbatim. It never
mutates any draft, never opens an IBKR socket, never reads from
storage directly; everything it needs is passed in as inputs.

Tier 2 (the per-submit account-ID re-read right before
``placeOrder()``) lives in ``submitter.py`` (Task 134b) — it cannot
be expressed as a pure function because it must observe live session
state at the exact moment of the network call.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    BehaviouralGuardrailSettings,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
)

SubmissionBlockReason = Literal[
    "cash_insufficient",
    "mode_mismatch",
    "connection_down",
    "account_id_mismatch",
    "duplicate_in_flight",
    "market_closed",
    "cooldown",
    "daily_limit",
    "soft_drawdown",
    "hard_drawdown",
    "fomo",
    "tick_size_invalid",
    "unknown",
]


# ---------------------------------------------------------------------------
# Gate inputs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GatewaySnapshot:
    """Minimal cross-section of the IBKR gateway state the gates need.

    The real ``IbkrGateway`` (Task 126) exposes a much wider surface;
    we keep this dataclass narrow so the gate function stays pure +
    testable. The caller is responsible for taking the snapshot
    immediately before evaluating gates so the state doesn't drift.
    """

    connected: bool
    account_id: str | None
    account_mode: Literal["paper", "live", "unknown"]


@dataclass(frozen=True)
class RecentSubmissionRecord:
    """Compact view of a row in ``ibkr_submission_audit``.

    Used by the cool-down + daily-limit gates. Only the fields the
    gates inspect are surfaced — full audit rows stay in the repo.
    """

    submitted_at: datetime
    result: str  # "placed" | "rejected_at_send" | "connection_lost"
    sent_to_account_id: str


@dataclass(frozen=True)
class DrawdownContext:
    """Soft + hard drawdown inputs.

    ``soft_loss_pct`` is the realised + unrealised return over the last
    ``soft_drawdown_window_days`` trading days as a *negative* Decimal
    (a 6% loss is ``Decimal("-6")``). ``None`` means "unavailable" —
    the gate is conservative: unavailable drawdown data → block.

    Same convention for ``hard_loss_pct``.
    """

    soft_loss_pct: Decimal | None
    hard_loss_pct: Decimal | None


class MarketHoursProviderProtocol(Protocol):
    """Minimal protocol the gate calls to ask whether an exchange is open.

    The real implementation (Task 134b) will use a Brussels-aware
    calendar; for V1 the gate stays oblivious to the holiday rules and
    just calls ``is_open(exchange, now)``.
    """

    def is_open(self, *, exchange: str, now: datetime) -> bool: ...


@dataclass(frozen=True)
class FomoContext:
    """Inputs for the FOMO (price-drift) gate.

    ``current_price_local`` is the latest observed market price for the
    asset, in the draft's local currency. ``None`` means unavailable —
    we err on the side of letting the user submit (no drift signal).
    """

    current_price_local: Decimal | None


# ---------------------------------------------------------------------------
# Gate result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubmissionGateResult:
    """Outcome of ``evaluate_submission_gates``.

    Frozen + tiny so tests can compare results with ``==``. The
    explanation is Dutch and surfaced verbatim in the Te keuren UI
    badge per Task 134 lock §3.
    """

    ok: bool
    block_reason: SubmissionBlockReason | None = None
    explanation_nl: str = ""
    failed_gates: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def ok_result(cls) -> SubmissionGateResult:
        return cls(ok=True, block_reason=None, explanation_nl="")

    @classmethod
    def blocked(
        cls,
        *,
        reason: SubmissionBlockReason,
        explanation_nl: str,
        gate_name: str,
    ) -> SubmissionGateResult:
        return cls(
            ok=False,
            block_reason=reason,
            explanation_nl=explanation_nl,
            failed_gates=(gate_name,),
        )


# ---------------------------------------------------------------------------
# Locked Dutch explanations per block reason.
# ---------------------------------------------------------------------------


_DUTCH_EXPLANATIONS: dict[SubmissionBlockReason, str] = {
    "cash_insufficient": (
        "Onvoldoende beschikbare cash om deze order te plaatsen. "
        "Verlaag het aantal of wacht tot er meer cash beschikbaar is."
    ),
    "mode_mismatch": (
        "De huidige IBKR-verbinding staat in een andere accountmodus "
        "dan toen je de draft goedkeurde."
    ),
    "connection_down": (
        "Geen actieve IBKR-verbinding. Verbinding opzetten of "
        "wachten tot de session weer beschikbaar is."
    ),
    "account_id_mismatch": (
        "Het IBKR-account dat nu verbonden is, komt niet overeen met "
        "het account waarop je de draft hebt goedgekeurd."
    ),
    "duplicate_in_flight": (
        "Er is al een lopende order voor ditzelfde asset op dit "
        "account. Wacht tot die afgerond is voordat je een nieuwe "
        "indient."
    ),
    "market_closed": (
        "De beurs voor dit asset is op dit moment gesloten. De order "
        "wordt automatisch geprobeerd zodra de markt opent."
    ),
    "cooldown": (
        "Cooldown actief: er is recent al een order verstuurd voor "
        "dit account. Wacht totdat de cooldown verloopt."
    ),
    "daily_limit": (
        "Dagelijks limiet bereikt. Verdere orders worden pas morgen "
        "weer toegelaten."
    ),
    "soft_drawdown": (
        "Soft drawdown: de portefeuille staat in de afgelopen "
        "vijf handelsdagen meer dan vijf procent in de min. "
        "Aankooporders worden tijdelijk geblokkeerd; verkopen blijft "
        "toegestaan."
    ),
    "hard_drawdown": (
        "Hard drawdown: de portefeuille staat in de afgelopen twintig "
        "handelsdagen meer dan tien procent in de min. Alle orders "
        "worden geblokkeerd tot je dit expliciet bevestigt in "
        "Instellingen."
    ),
    "fomo": (
        "De huidige marktprijs ligt te ver van je goedgekeurde "
        "limietprijs. Bekijk de draft opnieuw en bevestig de prijs "
        "voordat je hem opnieuw goedkeurt."
    ),
    "tick_size_invalid": (
        "De limietprijs voldoet niet aan de IBKR tick-size voor dit "
        "contract. Pas de prijs aan en keur opnieuw goed."
    ),
    "unknown": (
        "Onbekende blokkering. Bekijk de audit-log voor details."
    ),
}


def dutch_explanation_for(reason: SubmissionBlockReason) -> str:
    return _DUTCH_EXPLANATIONS[reason]


# ---------------------------------------------------------------------------
# Main entry point — Tier 1 gate evaluation (Task 134 lock §3 + §4).
# ---------------------------------------------------------------------------


def evaluate_submission_gates(
    *,
    draft: ActionDraftEntry,
    gateway: GatewaySnapshot,
    cash_snapshot: IbkrAccountCashSnapshotRecord | None,
    position_snapshot: IbkrPositionSnapshotRecord | None,
    guardrail_settings: BehaviouralGuardrailSettings,
    recent_submissions: Sequence[RecentSubmissionRecord],
    in_flight_drafts_for_conid: Iterable[ActionDraftEntry] = (),
    drawdown: DrawdownContext | None = None,
    fomo: FomoContext | None = None,
    market_hours: MarketHoursProviderProtocol | None = None,
    now: datetime,
) -> SubmissionGateResult:
    """Evaluate every Tier 1 gate in the locked order.

    Returns on the **first** failure; the order matters so the UI
    surfaces the most-actionable Dutch message. Order:

    1. Connection (``connection_down``)
    2. Account-mode match (``mode_mismatch``)
    3. Account-ID match (``account_id_mismatch``)
    4. Market hours (``market_closed``) — only when provider is supplied
    5. Duplicate-in-flight (``duplicate_in_flight``)
    6. Hard drawdown (``hard_drawdown``)
    7. Soft drawdown (``soft_drawdown`` — BUY only)
    8. Daily approval limit (``daily_limit``)
    9. Cool-down (``cooldown``)
    10. Cash sufficiency for BUY (``cash_insufficient``)
    11. Position sufficiency for SELL (``cash_insufficient`` reused —
        same reason code per lock §3)
    12. FOMO drift (``fomo``)
    """

    if draft.status != "user_approved":
        return SubmissionGateResult.blocked(
            reason="unknown",
            explanation_nl="Draft is niet in user_approved status.",
            gate_name="draft_status",
        )

    if not gateway.connected:
        return _block("connection_down", "gateway_connected")

    if (
        gateway.account_mode == "paper"
        and draft.ibkr_account_id.startswith(("DU", "DF"))
    ) or (
        gateway.account_mode == "live"
        and not draft.ibkr_account_id.startswith(("DU", "DF"))
    ):
        pass
    else:
        return _block("mode_mismatch", "account_mode_match")

    if gateway.account_id is None or gateway.account_id != draft.ibkr_account_id:
        return _block("account_id_mismatch", "account_id_match")

    if market_hours is not None:
        if not market_hours.is_open(exchange=draft.exchange, now=now):
            return _block("market_closed", "market_hours")

    for other in in_flight_drafts_for_conid:
        if other.action_draft_id == draft.action_draft_id:
            continue
        if other.status in _IN_FLIGHT_STATUSES:
            return _block("duplicate_in_flight", "duplicate_in_flight")

    if drawdown is not None:
        if drawdown.hard_loss_pct is None:
            return _block("hard_drawdown", "hard_drawdown_unknown")
        if (
            -drawdown.hard_loss_pct  # convert loss to positive magnitude
            >= guardrail_settings.hard_drawdown_pct
        ):
            return _block("hard_drawdown", "hard_drawdown")
        if draft.side == "BUY":
            if drawdown.soft_loss_pct is None:
                return _block("soft_drawdown", "soft_drawdown_unknown")
            if (
                -drawdown.soft_loss_pct
                >= guardrail_settings.soft_drawdown_pct
            ):
                return _block("soft_drawdown", "soft_drawdown")

    daily_window_start = now - timedelta(hours=24)
    daily_placed = [
        r
        for r in recent_submissions
        if r.sent_to_account_id == draft.ibkr_account_id
        and r.result == "placed"
        and r.submitted_at >= daily_window_start
    ]
    if len(daily_placed) >= guardrail_settings.daily_max_approvals:
        return _block("daily_limit", "daily_limit")

    if guardrail_settings.cooldown_seconds > 0:
        cooldown_start = now - timedelta(
            seconds=guardrail_settings.cooldown_seconds
        )
        if any(
            r.submitted_at >= cooldown_start
            and r.sent_to_account_id == draft.ibkr_account_id
            and r.result == "placed"
            for r in recent_submissions
        ):
            return _block("cooldown", "cooldown")

    if draft.side == "BUY":
        if cash_snapshot is None or cash_snapshot.available_funds is None:
            return _block("cash_insufficient", "cash_snapshot_missing")
        if cash_snapshot.available_funds < draft.notional_eur:
            return _block("cash_insufficient", "cash_sufficient")

    if draft.side == "SELL":
        if position_snapshot is None or position_snapshot.quantity is None:
            return _block("cash_insufficient", "position_snapshot_missing")
        if position_snapshot.quantity < draft.quantity:
            return _block("cash_insufficient", "position_sufficient")

    if fomo is not None and fomo.current_price_local is not None:
        if draft.limit_price_local <= 0:
            return _block("fomo", "fomo_price_invalid")
        drift_pct = (
            abs(fomo.current_price_local - draft.limit_price_local)
            / draft.limit_price_local
        ) * Decimal("100")
        if drift_pct > guardrail_settings.fomo_drift_pct:
            return _block("fomo", "fomo_drift")

    return SubmissionGateResult.ok_result()


def _block(
    reason: SubmissionBlockReason, gate_name: str
) -> SubmissionGateResult:
    return SubmissionGateResult.blocked(
        reason=reason,
        explanation_nl=dutch_explanation_for(reason),
        gate_name=gate_name,
    )


# Statuses we treat as "in flight" for the duplicate-detection gate.
_IN_FLIGHT_STATUSES = frozenset(
    {
        "submitted",
        "accepted",
        "working",
        "partially_filled",
        "pending_cancellation",
    }
)
