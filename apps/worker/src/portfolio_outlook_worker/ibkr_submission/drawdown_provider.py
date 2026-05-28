"""Drawdown circuit-breaker provider + NAV recorder (execution layer 3b-ii/5).

Consumes the per-account NAV history persisted in 3b-i to give the submission
sweep a real ``DrawdownContext`` (it was fail-closed before). Two pieces:

* :func:`record_nav_from_account_summary` — writes one NAV point from an IBKR
  account summary (called from the sync path; account id known there).
* :class:`DrawdownProvider` — reads the recent NAV series and computes the
  decline-from-peak over the soft/hard windows.

Drawdown is **peak-based**: ``loss = (latest - peak_in_window) / peak``, a
non-positive percent. A fresh account with a single NAV point reads 0% (peak ==
latest) and is therefore NOT blocked — the breaker only fires once the series
shows a real decline from a prior peak. Genuinely empty history (no NAV at all)
returns ``None``, which the gate treats as fail-closed.

Windows are CALENDAR days, matching every other time window in the gate
(``safety_recheck``); there is no trading-calendar utility in the codebase.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import IbkrNavSnapshotRecord

from portfolio_outlook_worker.ibkr_submission.safety_recheck import DrawdownContext

_NLV_TAG = "NetLiquidationValue"


class _CashRowProtocol(Protocol):
    tag: str
    currency: str
    value: Decimal


class _AccountSummaryProtocol(Protocol):
    rows: tuple[_CashRowProtocol, ...]
    as_of: datetime


class _NavReadRepoProtocol(Protocol):
    def list_ibkr_nav_snapshots_since(
        self, *, ibkr_account_id: str, since: datetime
    ) -> list[IbkrNavSnapshotRecord]: ...


class _NavWriteRepoProtocol(Protocol):
    def save_ibkr_nav_snapshot(self, record: IbkrNavSnapshotRecord) -> None: ...


def compute_drawdown_context(
    *,
    snapshots: list[IbkrNavSnapshotRecord],
    soft_window_days: int,
    hard_window_days: int,
    now: datetime,
) -> DrawdownContext:
    """Peak-based decline over the soft + hard windows (non-positive percent)."""

    points = sorted(
        (
            (s.recorded_at, s.nav_value)
            for s in snapshots
            if s.nav_value is not None and s.nav_value > 0
        ),
        key=lambda p: p[0],
    )
    if not points:
        return DrawdownContext(soft_loss_pct=None, hard_loss_pct=None)
    latest_nav = points[-1][1]

    def _loss(window_days: int) -> Decimal | None:
        cutoff = now - timedelta(days=window_days)
        in_window = [nav for (ts, nav) in points if ts >= cutoff]
        # Always include the latest point so a one-point series reads 0%.
        peak = max([*in_window, latest_nav])
        if peak <= 0:
            return None
        return ((latest_nav - peak) / peak * Decimal("100")).quantize(
            Decimal("0.01")
        )

    return DrawdownContext(
        soft_loss_pct=_loss(soft_window_days),
        hard_loss_pct=_loss(hard_window_days),
    )


class DrawdownProvider:
    """Reads recent NAV history and computes the submission drawdown context."""

    def __init__(
        self,
        *,
        nav_repo: _NavReadRepoProtocol,
        soft_window_days: int,
        hard_window_days: int,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._nav_repo = nav_repo
        self._soft_window_days = soft_window_days
        self._hard_window_days = hard_window_days
        self._now = now_provider or (lambda: datetime.now(UTC))

    def for_account(self, *, ibkr_account_id: str) -> DrawdownContext:
        now = self._now()
        lookback = max(self._soft_window_days, self._hard_window_days)
        snapshots = self._nav_repo.list_ibkr_nav_snapshots_since(
            ibkr_account_id=ibkr_account_id, since=now - timedelta(days=lookback)
        )
        return compute_drawdown_context(
            snapshots=snapshots,
            soft_window_days=self._soft_window_days,
            hard_window_days=self._hard_window_days,
            now=now,
        )


def record_nav_from_account_summary(
    *,
    account_summary: _AccountSummaryProtocol,
    ibkr_account_id: str,
    nav_repo: _NavWriteRepoProtocol,
    now: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> bool:
    """Persist one NAV point from an account summary's NetLiquidationValue.

    Returns ``True`` when a point was written, ``False`` when the summary has no
    usable NetLiquidationValue row (nothing to record)."""

    stored_at = now or datetime.now(UTC)
    make_id = id_factory or (lambda: str(uuid4()))
    nlv = next(
        (
            row
            for row in account_summary.rows
            if row.tag == _NLV_TAG and row.value is not None and row.value > 0
        ),
        None,
    )
    if nlv is None:
        return False
    nav_repo.save_ibkr_nav_snapshot(
        IbkrNavSnapshotRecord(
            snapshot_id=make_id(),
            ibkr_account_id=ibkr_account_id,
            base_currency=nlv.currency or "UNKNOWN",
            nav_value=nlv.value,
            recorded_at=account_summary.as_of,
            stored_at=stored_at,
        )
    )
    return True


__all__ = [
    "DrawdownProvider",
    "compute_drawdown_context",
    "record_nav_from_account_summary",
]
