"""Tests for the drawdown provider + NAV recorder (execution layer 3b-ii)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import IbkrNavSnapshotRecord

from portfolio_outlook_worker.ibkr_submission.drawdown_provider import (
    DrawdownProvider,
    compute_drawdown_context,
    record_nav_from_account_summary,
)

_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _nav(value: str, days_ago: int) -> IbkrNavSnapshotRecord:
    return IbkrNavSnapshotRecord(
        snapshot_id=f"nav-{days_ago}",
        ibkr_account_id="DU1",
        base_currency="EUR",
        nav_value=Decimal(value),
        recorded_at=_NOW - timedelta(days=days_ago),
        stored_at=_NOW - timedelta(days=days_ago),
    )


# ---- compute_drawdown_context ------------------------------------------


def test_no_history_returns_none_none() -> None:
    ctx = compute_drawdown_context(
        snapshots=[], soft_window_days=5, hard_window_days=20, now=_NOW
    )
    assert ctx.soft_loss_pct is None
    assert ctx.hard_loss_pct is None


def test_single_point_reads_zero_drawdown() -> None:
    ctx = compute_drawdown_context(
        snapshots=[_nav("50000", 0)],
        soft_window_days=5,
        hard_window_days=20,
        now=_NOW,
    )
    assert ctx.soft_loss_pct == Decimal("0.00")
    assert ctx.hard_loss_pct == Decimal("0.00")


def test_decline_from_peak_is_negative() -> None:
    # Peak 50000 two days ago, now 45000 -> -10%.
    ctx = compute_drawdown_context(
        snapshots=[_nav("50000", 2), _nav("45000", 0)],
        soft_window_days=5,
        hard_window_days=20,
        now=_NOW,
    )
    assert ctx.soft_loss_pct == Decimal("-10.00")
    assert ctx.hard_loss_pct == Decimal("-10.00")


def test_hard_window_sees_older_peak_than_soft() -> None:
    # Peak 60000 was 10 days ago (inside hard=20, outside soft=5).
    # Within soft window the peak is 50000 (2 days ago). Now 48000.
    snaps = [_nav("60000", 10), _nav("50000", 2), _nav("48000", 0)]
    ctx = compute_drawdown_context(
        snapshots=snaps, soft_window_days=5, hard_window_days=20, now=_NOW
    )
    assert ctx.soft_loss_pct == Decimal("-4.00")  # (48000-50000)/50000
    assert ctx.hard_loss_pct == Decimal("-20.00")  # (48000-60000)/60000


# ---- DrawdownProvider ---------------------------------------------------


class _FakeNavRepo:
    def __init__(self, snaps: list[IbkrNavSnapshotRecord]) -> None:
        self._snaps = snaps
        self.since: datetime | None = None

    def list_ibkr_nav_snapshots_since(
        self, *, ibkr_account_id: str, since: datetime
    ) -> list[IbkrNavSnapshotRecord]:
        self.since = since
        return self._snaps


def test_provider_queries_hard_window_and_computes() -> None:
    repo = _FakeNavRepo([_nav("50000", 2), _nav("45000", 0)])
    provider = DrawdownProvider(
        nav_repo=repo,
        soft_window_days=5,
        hard_window_days=20,
        now_provider=lambda: _NOW,
    )
    ctx = provider.for_account(ibkr_account_id="DU1")
    assert ctx.hard_loss_pct == Decimal("-10.00")
    # Looks back over the larger (hard) window.
    assert repo.since == _NOW - timedelta(days=20)


# ---- record_nav_from_account_summary -----------------------------------


@dataclass
class _Row:
    tag: str
    currency: str
    value: Decimal | None


@dataclass
class _Summary:
    rows: tuple[_Row, ...]
    as_of: datetime


class _WriteRepo:
    def __init__(self) -> None:
        self.saved: list[IbkrNavSnapshotRecord] = []

    def save_ibkr_nav_snapshot(self, record: IbkrNavSnapshotRecord) -> None:
        self.saved.append(record)


def test_recorder_writes_nlv_point() -> None:
    repo = _WriteRepo()
    summary = _Summary(
        rows=(
            _Row("AvailableFunds", "EUR", Decimal("40000")),
            _Row("NetLiquidationValue", "EUR", Decimal("52000")),
        ),
        as_of=_NOW,
    )
    written = record_nav_from_account_summary(
        account_summary=summary,
        ibkr_account_id="DU1",
        nav_repo=repo,
        now=_NOW,
        id_factory=lambda: "nav-1",
    )
    assert written is True
    assert len(repo.saved) == 1
    rec = repo.saved[0]
    assert rec.nav_value == Decimal("52000")
    assert rec.ibkr_account_id == "DU1"
    assert rec.recorded_at == _NOW


def test_recorder_skips_when_no_nlv_row() -> None:
    repo = _WriteRepo()
    summary = _Summary(
        rows=(_Row("AvailableFunds", "EUR", Decimal("40000")),), as_of=_NOW
    )
    written = record_nav_from_account_summary(
        account_summary=summary,
        ibkr_account_id="DU1",
        nav_repo=repo,
        now=_NOW,
    )
    assert written is False
    assert repo.saved == []
