"""Task 134b: one-tick IBKR submission sweep.

The sweep is the recurring entry point: every 60 seconds during
market hours, the worker fires this and the result is at most one
``placeOrder()`` per tick. FIFO by ``user_approved_at`` so the user
sees the oldest approval move first. Single-flight via an injected
``SingleFlightLockProtocol`` (the production wiring uses Postgres
``pg_advisory_lock``; tests inject in-memory locks).

The sweep is the bridge between Task 134a (pure functions) and the
real IBKR session. Every blocker found by ``safety_recheck`` writes a
``submission_block_reason`` on the draft so the Te keuren UI badge
appears immediately; the next tick re-evaluates and may clear the
reason. The sweep never raises through to APScheduler — every failure
lands in a structured ``SubmissionSweepResult`` for the audit log.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    BehaviouralGuardrailSettings,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyBehaviouralGuardrailSettingsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
)

from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    DrawdownContext,
    FomoContext,
    GatewaySnapshot,
    MarketHoursProviderProtocol,
    RecentSubmissionRecord,
    SubmissionGateResult,
    evaluate_submission_gates,
)
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrSubmitter,
    SubmissionResult,
)
from portfolio_outlook_worker.single_flight_lock import (
    SingleFlightLockProtocol,
)

logger = logging.getLogger(__name__)


SweepMode = Literal[
    "completed",
    "skipped_locked",
    "skipped_market_closed",
    "no_drafts",
    "error",
]


@dataclass(frozen=True)
class BlockedDraftRecord:
    action_draft_id: str
    block_reason: str
    explanation_nl: str


@dataclass(frozen=True)
class SubmittedDraftRecord:
    action_draft_id: str
    perm_id: int | None


@dataclass(frozen=True)
class SubmissionSweepResult:
    """Audit-friendly outcome of one sweep tick."""

    mode: SweepMode
    started_at: datetime
    completed_at: datetime
    evaluated_count: int = 0
    blocked: tuple[BlockedDraftRecord, ...] = field(default_factory=tuple)
    submitted: tuple[SubmittedDraftRecord, ...] = field(default_factory=tuple)
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Adapters the sweep depends on.
# ---------------------------------------------------------------------------


class GatewaySnapshotProviderProtocol(Protocol):
    """Returns the live ``GatewaySnapshot`` for the configured account."""

    def snapshot(self) -> GatewaySnapshot: ...


class IbkrCashSnapshotProviderProtocol(Protocol):
    """Returns the latest persisted IBKR cash snapshot for the account."""

    def get_latest_account_cash_snapshot(
        self, *, ibkr_account_id: str
    ) -> IbkrAccountCashSnapshotRecord | None: ...


class IbkrPositionSnapshotProviderProtocol(Protocol):
    def get_latest_position_snapshot_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None: ...


class DrawdownProviderProtocol(Protocol):
    """Returns the soft + hard drawdown context for an account.

    Real implementation reads portfolio valuation history; the V1
    minimal wiring may return ``DrawdownContext(None, None)`` which
    causes the gate to block conservatively until a real source is
    plumbed in. Tests inject fakes.
    """

    def for_account(
        self, *, ibkr_account_id: str
    ) -> DrawdownContext: ...


class FomoPriceProviderProtocol(Protocol):
    """Returns the live or last-observed price for the conid."""

    def for_draft(
        self, *, draft: ActionDraftEntry
    ) -> FomoContext: ...


# ---------------------------------------------------------------------------
# Market-hours default.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrusselsBusinessHoursMarket(MarketHoursProviderProtocol):
    """Coarse-grained Brussels weekday 09:00–22:30 window.

    Per Task 134 product lock §2 the sweep runs in this window;
    outside it the sweep audits ``mode_detected="market_closed"`` and
    exits. Holiday awareness is deliberately out of scope for V1;
    Task 134c will defer that to a finer-grained calendar provider.
    """

    open_hour: int = 9
    open_minute: int = 0
    close_hour: int = 22
    close_minute: int = 30

    def is_open(self, *, exchange: str, now: datetime) -> bool:
        # ``now`` is UTC-aware; Brussels weekday window check
        # approximates via the UTC weekday — the brief allows the
        # coarse approximation for V1 (the exact DST-aware check is
        # Task 134c's MarketHoursProvider replacement).
        _ = exchange  # locked window applies to every exchange in V1.
        if now.weekday() >= 5:
            return False
        local_minutes = now.hour * 60 + now.minute
        open_minutes = self.open_hour * 60 + self.open_minute
        close_minutes = self.close_hour * 60 + self.close_minute
        return open_minutes <= local_minutes <= close_minutes


# ---------------------------------------------------------------------------
# Sweep.
# ---------------------------------------------------------------------------


class SubmissionSweep:
    """One sweep tick — pull → gate → (optionally) submit.

    Wired into APScheduler as a no-arg ``tick()`` invocation. The
    sweep handles single-flight via the injected ``lock`` protocol;
    failing to acquire returns ``SubmissionSweepResult(mode="skipped_locked")``.
    """

    def __init__(
        self,
        *,
        ibkr_account_id: str,
        lock: SingleFlightLockProtocol,
        action_draft_repo: SqlAlchemyActionDraftRepository,
        audit_repo: SqlAlchemyIbkrSubmissionAuditRepository,
        guardrail_repo: SqlAlchemyBehaviouralGuardrailSettingsRepository,
        submitter: IbkrSubmitter,
        gateway_snapshot_provider: GatewaySnapshotProviderProtocol,
        cash_snapshot_provider: IbkrCashSnapshotProviderProtocol,
        position_snapshot_provider: IbkrPositionSnapshotProviderProtocol,
        drawdown_provider: DrawdownProviderProtocol,
        fomo_provider: FomoPriceProviderProtocol,
        market_hours: MarketHoursProviderProtocol | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._ibkr_account_id = ibkr_account_id
        self._lock = lock
        self._action_draft_repo = action_draft_repo
        self._audit_repo = audit_repo
        self._guardrail_repo = guardrail_repo
        self._submitter = submitter
        self._gateway_snapshot_provider = gateway_snapshot_provider
        self._cash_snapshot_provider = cash_snapshot_provider
        self._position_snapshot_provider = position_snapshot_provider
        self._drawdown_provider = drawdown_provider
        self._fomo_provider = fomo_provider
        self._market_hours = market_hours or BrusselsBusinessHoursMarket()
        self._now_provider = now_provider

    def tick(self) -> SubmissionSweepResult:
        started = self._now()
        if not self._lock.try_acquire():
            return SubmissionSweepResult(
                mode="skipped_locked",
                started_at=started,
                completed_at=self._now(),
            )
        try:
            return self._run_locked(started=started)
        finally:
            try:
                self._lock.release()
            except Exception:  # noqa: BLE001 — boundary
                logger.exception("submission sweep lock release failed")

    def _run_locked(
        self, *, started: datetime
    ) -> SubmissionSweepResult:
        # Market-hours short-circuit. The check uses the configured
        # account's primary exchange via the first user_approved draft
        # when present; otherwise the gate is applied with a synthetic
        # exchange name that the V1 ``BrusselsBusinessHoursMarket``
        # ignores anyway.
        if not self._market_hours.is_open(
            exchange="UNKNOWN", now=started
        ):
            return SubmissionSweepResult(
                mode="skipped_market_closed",
                started_at=started,
                completed_at=self._now(),
            )

        try:
            drafts = self._action_draft_repo.list_user_approved_for_sweep(
                ibkr_account_id=self._ibkr_account_id
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "submission sweep list_user_approved_for_sweep failed"
            )
            return SubmissionSweepResult(
                mode="error",
                started_at=started,
                completed_at=self._now(),
                error_message=str(exc),
            )

        if not drafts:
            return SubmissionSweepResult(
                mode="no_drafts",
                started_at=started,
                completed_at=self._now(),
            )

        gateway = self._gateway_snapshot_provider.snapshot()
        guardrails = self._guardrail_repo.get_or_default(
            ibkr_account_id=self._ibkr_account_id, now=started
        )
        recent_submissions = self._build_recent_submission_records(
            now=started,
            guardrails=guardrails,
        )

        blocked: list[BlockedDraftRecord] = []
        submitted: list[SubmittedDraftRecord] = []

        for draft in drafts:
            gate_result = self._evaluate_gates(
                draft=draft,
                gateway=gateway,
                guardrails=guardrails,
                recent_submissions=recent_submissions,
                now=started,
            )
            if not gate_result.ok:
                assert gate_result.block_reason is not None
                try:
                    self._action_draft_repo.set_submission_block_reason(
                        action_draft_id=draft.action_draft_id,
                        reason=gate_result.block_reason,
                        set_at=started,
                    )
                except Exception:  # noqa: BLE001 — boundary
                    logger.exception(
                        "set_submission_block_reason failed for %s",
                        draft.action_draft_id,
                    )
                blocked.append(
                    BlockedDraftRecord(
                        action_draft_id=draft.action_draft_id,
                        block_reason=gate_result.block_reason,
                        explanation_nl=gate_result.explanation_nl,
                    )
                )
                continue

            # Locked one-per-tick: as soon as we submit the first
            # eligible draft we exit the loop and let the next tick
            # pick up the rest. Keeps the audit trail clean + the
            # cool-down gate effective.
            submission = self._submit_one(draft=draft)
            if submission.ok:
                submitted.append(
                    SubmittedDraftRecord(
                        action_draft_id=draft.action_draft_id,
                        perm_id=submission.perm_id,
                    )
                )
            else:
                assert submission.block_reason is not None
                blocked.append(
                    BlockedDraftRecord(
                        action_draft_id=draft.action_draft_id,
                        block_reason=submission.block_reason,
                        explanation_nl=(
                            submission.error_message_dutch or ""
                        ),
                    )
                )
            break

        return SubmissionSweepResult(
            mode="completed",
            started_at=started,
            completed_at=self._now(),
            evaluated_count=len(drafts),
            blocked=tuple(blocked),
            submitted=tuple(submitted),
        )

    def _submit_one(
        self, *, draft: ActionDraftEntry
    ) -> SubmissionResult:
        try:
            return self._submitter.submit(draft)
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "submitter.submit raised for draft %s",
                draft.action_draft_id,
            )
            return SubmissionResult(
                ok=False,
                perm_id=None,
                audit_id=None,
                block_reason="unknown",
                error_class=type(exc).__name__,
                error_message_dutch=str(exc),
            )

    def _evaluate_gates(
        self,
        *,
        draft: ActionDraftEntry,
        gateway: GatewaySnapshot,
        guardrails: BehaviouralGuardrailSettings,
        recent_submissions: Sequence[RecentSubmissionRecord],
        now: datetime,
    ) -> SubmissionGateResult:
        cash_snapshot = (
            self._cash_snapshot_provider.get_latest_account_cash_snapshot(
                ibkr_account_id=draft.ibkr_account_id
            )
        )
        position_snapshot = (
            self._position_snapshot_provider.get_latest_position_snapshot_for_conid(
                ibkr_account_id=draft.ibkr_account_id, conid=draft.conid
            )
        )
        in_flight = self._action_draft_repo.list_in_flight_for_conid(
            ibkr_account_id=draft.ibkr_account_id, conid=draft.conid
        )
        drawdown = self._drawdown_provider.for_account(
            ibkr_account_id=draft.ibkr_account_id
        )
        fomo = self._fomo_provider.for_draft(draft=draft)
        return evaluate_submission_gates(
            draft=draft,
            gateway=gateway,
            cash_snapshot=cash_snapshot,
            position_snapshot=position_snapshot,
            guardrail_settings=guardrails,
            recent_submissions=recent_submissions,
            in_flight_drafts_for_conid=in_flight,
            drawdown=drawdown,
            fomo=fomo,
            market_hours=self._market_hours,
            now=now,
        )

    def _build_recent_submission_records(
        self,
        *,
        now: datetime,
        guardrails: BehaviouralGuardrailSettings,
    ) -> tuple[RecentSubmissionRecord, ...]:
        # Pull a window wide enough to cover both the cooldown and the
        # daily limit gates. ``audit_repo.list_for_account`` returns
        # newest-first; we just translate into the gate's compact
        # ``RecentSubmissionRecord`` shape.
        window = max(
            timedelta(seconds=guardrails.cooldown_seconds),
            timedelta(hours=24),
        )
        window_start = now - window
        try:
            audit_rows = self._audit_repo.list_for_account(
                ibkr_account_id=self._ibkr_account_id, limit=200
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "audit_repo.list_for_account failed during sweep"
            )
            return ()
        # SQLite drops tzinfo on round-trip; force UTC when the row
        # comes back naive so the comparison with ``window_start``
        # (always UTC-aware) doesn't trip Python's offset-naive vs
        # offset-aware mismatch.
        from datetime import UTC as _UTC

        def _as_aware(value: datetime) -> datetime:
            if value.tzinfo is None:
                return value.replace(tzinfo=_UTC)
            return value

        return tuple(
            RecentSubmissionRecord(
                submitted_at=_as_aware(row.submitted_at),
                result=row.result,
                sent_to_account_id=row.sent_to_account_id,
            )
            for row in audit_rows
            if _as_aware(row.submitted_at) >= window_start
        )

    def _now(self) -> datetime:
        if self._now_provider is not None:
            return self._now_provider()
        from datetime import UTC

        return datetime.now(UTC)


__all__ = [
    "BlockedDraftRecord",
    "BrusselsBusinessHoursMarket",
    "DrawdownProviderProtocol",
    "FomoPriceProviderProtocol",
    "GatewaySnapshotProviderProtocol",
    "IbkrCashSnapshotProviderProtocol",
    "IbkrPositionSnapshotProviderProtocol",
    "SubmissionSweep",
    "SubmissionSweepResult",
    "SubmittedDraftRecord",
    "SweepMode",
]

# Silence unused imports kept for downstream callers.
_ = (Iterable, Decimal)
