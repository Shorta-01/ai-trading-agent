"""One-tick IBKR cancel sweep (execution layer 4/5).

Mirror of the submission sweep for the cancellation path: every tick it pulls
``pending_cancellation`` drafts and sends a cancel to IBKR for each (via the
submitter, the single broker-write path). Cancels are fire-and-forget — the
reconciler's Pass B converges each draft to ``cancelled`` once IBKR confirms,
so this sweep does not mutate draft status.

Differences from the submission sweep:
* No market-hours gate — a user may cancel a resting order at any time.
* All pending cancels are sent per tick (not one-per-tick); the adapter's
  cancel_order is idempotent (a no-op once the order is gone), so re-sending in
  the brief window before the reconciler converges is safe.
* Single-flight via its own lock so it never overlaps with itself.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from ai_trading_agent_storage import SqlAlchemyActionDraftRepository

from portfolio_outlook_worker.ibkr_submission.submitter import IbkrSubmitter
from portfolio_outlook_worker.single_flight_lock import SingleFlightLockProtocol

logger = logging.getLogger(__name__)


CancelSweepMode = Literal["completed", "skipped_locked", "no_drafts", "error"]


@dataclass(frozen=True)
class CancelledDraftRecord:
    action_draft_id: str
    perm_id: int | None


@dataclass(frozen=True)
class FailedCancelRecord:
    action_draft_id: str
    error_message: str


@dataclass(frozen=True)
class CancelSweepResult:
    mode: CancelSweepMode
    started_at: datetime
    completed_at: datetime
    evaluated_count: int = 0
    cancelled: tuple[CancelledDraftRecord, ...] = field(default_factory=tuple)
    failed: tuple[FailedCancelRecord, ...] = field(default_factory=tuple)
    error_message: str | None = None


class CancelSweep:
    """One cancel-sweep tick — pull ``pending_cancellation`` → send cancels."""

    def __init__(
        self,
        *,
        ibkr_account_id: str,
        lock: SingleFlightLockProtocol,
        action_draft_repo: SqlAlchemyActionDraftRepository,
        submitter: IbkrSubmitter,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._ibkr_account_id = ibkr_account_id
        self._lock = lock
        self._action_draft_repo = action_draft_repo
        self._submitter = submitter
        self._now_provider = now_provider

    def tick(self) -> CancelSweepResult:
        started = self._now()
        if not self._lock.try_acquire():
            return CancelSweepResult(
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
                logger.exception("cancel sweep lock release failed")

    def _run_locked(self, *, started: datetime) -> CancelSweepResult:
        try:
            drafts = self._action_draft_repo.list_pending_cancellation(
                ibkr_account_id=self._ibkr_account_id
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception("cancel sweep list_pending_cancellation failed")
            return CancelSweepResult(
                mode="error",
                started_at=started,
                completed_at=self._now(),
                error_message=str(exc),
            )

        if not drafts:
            return CancelSweepResult(
                mode="no_drafts",
                started_at=started,
                completed_at=self._now(),
            )

        cancelled: list[CancelledDraftRecord] = []
        failed: list[FailedCancelRecord] = []
        for draft in drafts:
            try:
                result = self._submitter.cancel(draft)
            except Exception as exc:  # noqa: BLE001 — boundary
                logger.exception(
                    "submitter.cancel raised for draft %s",
                    draft.action_draft_id,
                )
                failed.append(
                    FailedCancelRecord(
                        action_draft_id=draft.action_draft_id,
                        error_message=str(exc),
                    )
                )
                continue
            if result.ok:
                cancelled.append(
                    CancelledDraftRecord(
                        action_draft_id=draft.action_draft_id,
                        perm_id=result.perm_id,
                    )
                )
            else:
                failed.append(
                    FailedCancelRecord(
                        action_draft_id=draft.action_draft_id,
                        error_message=result.error_message_dutch or "",
                    )
                )

        return CancelSweepResult(
            mode="completed",
            started_at=started,
            completed_at=self._now(),
            evaluated_count=len(drafts),
            cancelled=tuple(cancelled),
            failed=tuple(failed),
        )

    def _now(self) -> datetime:
        if self._now_provider is not None:
            return self._now_provider()
        return datetime.now(UTC)


__all__ = [
    "CancelSweep",
    "CancelSweepResult",
    "CancelledDraftRecord",
    "CancelSweepMode",
    "FailedCancelRecord",
]
