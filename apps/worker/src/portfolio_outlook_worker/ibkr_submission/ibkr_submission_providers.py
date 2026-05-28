"""Production submission-sweep context providers (execution layer 3/5).

The SubmissionSweep evaluates per-submit safety gates from injected context
providers. Two of the five already have real sources:
* cash + position snapshots — the existing ``SqlAlchemyIbkrSyncSnapshotRepository``
  satisfies their protocols verbatim (no adapter needed).
This module supplies two more:
* ``GatewaySnapshotProvider`` — wraps the live TWS gateway (connected /
  account id / paper-or-live mode) for the connection + mode-match gates.
* ``FomoPriceProvider`` — reads the latest persisted market price for the
  draft's instrument for the price-drift (FOMO) gate. A missing price yields
  ``current_price_local=None``, which the gate treats leniently (no drift
  signal → allow), so this never blocks on absent data.

The drawdown provider is intentionally NOT here: it needs a portfolio
net-liquidation history that doesn't exist yet (component 3b adds it). Until
then the drawdown gate fails closed by design.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Protocol

from ai_trading_agent_storage import MarketDataLatestSnapshotRecord

from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    FomoContext,
    GatewaySnapshot,
)


class _GatewayProtocol(Protocol):
    def is_connected(self) -> bool: ...

    def get_account_mode(self) -> Literal["paper", "live", "unknown"]: ...

    @property
    def account_id(self) -> str | None: ...


class _DraftProtocol(Protocol):
    conid: str
    currency_local: str


class _MarketReadResultProtocol(Protocol):
    record: MarketDataLatestSnapshotRecord | None


class _LatestPriceRepoProtocol(Protocol):
    def get_latest_market_data_snapshot_by_conid(
        self, ibkr_conid: str
    ) -> _MarketReadResultProtocol: ...


class GatewaySnapshotProvider:
    """Live connection + account-mode snapshot from the TWS gateway."""

    def __init__(self, *, gateway: _GatewayProtocol) -> None:
        self._gateway = gateway

    def snapshot(self) -> GatewaySnapshot:
        connected = self._gateway.is_connected()
        return GatewaySnapshot(
            connected=connected,
            account_id=self._gateway.account_id if connected else None,
            account_mode=self._gateway.get_account_mode(),
        )


class FomoPriceProvider:
    """Latest observed market price for a draft's instrument (FOMO gate).

    Reads the persisted latest market-data snapshot; ``None`` when no price is
    available (the gate then applies no drift block)."""

    def __init__(self, *, market_repo: _LatestPriceRepoProtocol) -> None:
        self._market_repo = market_repo

    def for_draft(self, *, draft: _DraftProtocol) -> FomoContext:
        conid = (draft.conid or "").strip()
        if not conid:
            return FomoContext(current_price_local=None)
        result = self._market_repo.get_latest_market_data_snapshot_by_conid(conid)
        record = result.record
        price: Decimal | None = record.last_price if record is not None else None
        if price is not None and price <= 0:
            price = None
        return FomoContext(current_price_local=price)


__all__ = ["FomoPriceProvider", "GatewaySnapshotProvider"]
