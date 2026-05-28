"""Tests for the cancel sweep + submitter.cancel (execution layer 4/5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage import ActionDraftEntry

from portfolio_outlook_worker.ibkr_submission.cancel_sweep import CancelSweep
from portfolio_outlook_worker.ibkr_submission.submitter import (
    CancelResult,
    IbkrConnectionLostError,
    IbkrSubmitter,
)

_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _draft(
    *, draft_id: str = "draft-1", status: str = "pending_cancellation"
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id="DU1234567",
        conid="12345",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=Decimal("6"),
        order_type="LMT",
        limit_price_local=Decimal("638.72"),
        time_in_force="DAY",
        notional_local=Decimal("3832.32"),
        notional_eur=Decimal("3832.32"),
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status=status,
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


# ---- submitter.cancel ---------------------------------------------------


class _FakeAdapter:
    def __init__(self, *, raise_conn: bool = False) -> None:
        self.cancelled: list[int] = []
        self._raise_conn = raise_conn

    def cancel_order(self, perm_id: int) -> None:
        if self._raise_conn:
            raise IbkrConnectionLostError("session dropped")
        self.cancelled.append(perm_id)


class _AuditRow:
    def __init__(self, result: str, ibkr_perm_id: int | None) -> None:
        self.result = result
        self.ibkr_perm_id = ibkr_perm_id


class _FakeAuditRepo:
    def __init__(self, rows: list[_AuditRow]) -> None:
        self._rows = rows

    def list_for_draft(self, action_draft_id: str) -> list[_AuditRow]:
        return self._rows


def _submitter(adapter: _FakeAdapter, *, perm_id: int | None = 555) -> IbkrSubmitter:
    rows = [_AuditRow("placed", perm_id)] if perm_id is not None else []
    return IbkrSubmitter(
        submit_adapter=adapter,  # type: ignore[arg-type]
        action_draft_repo=None,  # type: ignore[arg-type]
        audit_repo=_FakeAuditRepo(rows),  # type: ignore[arg-type]
    )


def test_submitter_cancel_sends_to_adapter() -> None:
    adapter = _FakeAdapter()
    result = _submitter(adapter, perm_id=555).cancel(_draft())
    assert result.ok is True
    assert result.perm_id == 555
    assert adapter.cancelled == [555]


def test_submitter_cancel_missing_perm_id() -> None:
    adapter = _FakeAdapter()
    result = _submitter(adapter, perm_id=None).cancel(_draft())
    assert result.ok is False
    assert result.error_class == "MissingPermId"
    assert adapter.cancelled == []


def test_submitter_cancel_connection_lost() -> None:
    adapter = _FakeAdapter(raise_conn=True)
    result = _submitter(adapter, perm_id=555).cancel(_draft())
    assert result.ok is False
    assert result.error_class == "IbkrConnectionLostError"


def test_submitter_cancel_rejects_wrong_status() -> None:
    with pytest.raises(ValueError):
        _submitter(_FakeAdapter()).cancel(_draft(status="user_approved"))


# ---- CancelSweep --------------------------------------------------------


class _FakeLock:
    def __init__(self, *, acquired: bool = True) -> None:
        self._acquired = acquired
        self.released = False

    def try_acquire(self) -> bool:
        return self._acquired

    def release(self) -> None:
        self.released = True


class _FakeRepo:
    def __init__(self, drafts: tuple[ActionDraftEntry, ...]) -> None:
        self._drafts = drafts

    def list_pending_cancellation(
        self, *, ibkr_account_id: str
    ) -> tuple[ActionDraftEntry, ...]:
        return self._drafts


class _FakeSubmitter:
    def __init__(self, results: dict[str, CancelResult]) -> None:
        self._results = results
        self.calls: list[str] = []

    def cancel(self, draft: ActionDraftEntry) -> CancelResult:
        self.calls.append(draft.action_draft_id)
        return self._results[draft.action_draft_id]


def _sweep(lock: _FakeLock, repo: _FakeRepo, submitter: _FakeSubmitter) -> CancelSweep:
    return CancelSweep(
        ibkr_account_id="DU1234567",
        lock=lock,  # type: ignore[arg-type]
        action_draft_repo=repo,  # type: ignore[arg-type]
        submitter=submitter,  # type: ignore[arg-type]
        now_provider=lambda: _NOW,
    )


def test_cancel_sweep_cancels_all_pending() -> None:
    drafts = (_draft(draft_id="d1"), _draft(draft_id="d2"))
    submitter = _FakeSubmitter(
        {
            "d1": CancelResult(ok=True, perm_id=1, error_class=None, error_message_dutch=None),
            "d2": CancelResult(ok=True, perm_id=2, error_class=None, error_message_dutch=None),
        }
    )
    lock = _FakeLock()
    result = _sweep(lock, _FakeRepo(drafts), submitter).tick()
    assert result.mode == "completed"
    assert result.evaluated_count == 2
    assert {r.action_draft_id for r in result.cancelled} == {"d1", "d2"}
    assert result.failed == ()
    assert lock.released is True


def test_cancel_sweep_records_failures() -> None:
    drafts = (_draft(draft_id="d1"),)
    submitter = _FakeSubmitter(
        {
            "d1": CancelResult(
                ok=False, perm_id=None, error_class="MissingPermId", error_message_dutch="x"
            )
        }
    )
    result = _sweep(_FakeLock(), _FakeRepo(drafts), submitter).tick()
    assert result.mode == "completed"
    assert result.cancelled == ()
    assert len(result.failed) == 1
    assert result.failed[0].action_draft_id == "d1"


def test_cancel_sweep_skipped_when_locked() -> None:
    result = _sweep(
        _FakeLock(acquired=False), _FakeRepo(()), _FakeSubmitter({})
    ).tick()
    assert result.mode == "skipped_locked"


def test_cancel_sweep_no_drafts() -> None:
    result = _sweep(_FakeLock(), _FakeRepo(()), _FakeSubmitter({})).tick()
    assert result.mode == "no_drafts"
