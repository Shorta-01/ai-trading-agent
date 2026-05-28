"""Tests for the gateway-snapshot + FOMO-price submission providers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Literal

from portfolio_outlook_worker.ibkr_submission.ibkr_submission_providers import (
    FomoPriceProvider,
    GatewaySnapshotProvider,
)


class _FakeGateway:
    def __init__(
        self,
        *,
        connected: bool,
        account_id: str | None,
        mode: Literal["paper", "live", "unknown"],
    ) -> None:
        self._connected = connected
        self._account_id = account_id
        self._mode = mode

    def is_connected(self) -> bool:
        return self._connected

    def get_account_mode(self) -> Literal["paper", "live", "unknown"]:
        return self._mode

    @property
    def account_id(self) -> str | None:
        return self._account_id


@dataclass
class _ReadResult:
    record: object | None


class _FakeMarketRepo:
    def __init__(self, record: object | None) -> None:
        self._record = record
        self.queried: list[str] = []

    def get_latest_market_data_snapshot_by_conid(self, ibkr_conid: str) -> _ReadResult:
        self.queried.append(ibkr_conid)
        return _ReadResult(record=self._record)


@dataclass
class _Draft:
    conid: str
    currency_local: str = "EUR"


def _price_record(last_price: Decimal | None) -> object:
    # Duck-typed: the provider only reads ``.last_price``.
    return SimpleNamespace(last_price=last_price)


# ---- gateway snapshot ---------------------------------------------------


def test_gateway_snapshot_connected() -> None:
    provider = GatewaySnapshotProvider(
        gateway=_FakeGateway(connected=True, account_id="DU1234567", mode="paper")
    )
    snap = provider.snapshot()
    assert snap.connected is True
    assert snap.account_id == "DU1234567"
    assert snap.account_mode == "paper"


def test_gateway_snapshot_disconnected_nulls_account_id() -> None:
    provider = GatewaySnapshotProvider(
        gateway=_FakeGateway(connected=False, account_id="DU1234567", mode="unknown")
    )
    snap = provider.snapshot()
    assert snap.connected is False
    assert snap.account_id is None


# ---- fomo price ---------------------------------------------------------


def test_fomo_returns_latest_price() -> None:
    repo = _FakeMarketRepo(_price_record(Decimal("123.45")))
    ctx = FomoPriceProvider(market_repo=repo).for_draft(draft=_Draft(conid="265598"))
    assert ctx.current_price_local == Decimal("123.45")
    assert repo.queried == ["265598"]


def test_fomo_none_when_no_record() -> None:
    ctx = FomoPriceProvider(market_repo=_FakeMarketRepo(None)).for_draft(
        draft=_Draft(conid="265598")
    )
    assert ctx.current_price_local is None


def test_fomo_none_when_price_non_positive() -> None:
    ctx = FomoPriceProvider(
        market_repo=_FakeMarketRepo(_price_record(Decimal("0")))
    ).for_draft(draft=_Draft(conid="265598"))
    assert ctx.current_price_local is None


def test_fomo_none_when_conid_blank() -> None:
    repo = _FakeMarketRepo(_price_record(Decimal("10")))
    ctx = FomoPriceProvider(market_repo=repo).for_draft(draft=_Draft(conid="  "))
    assert ctx.current_price_local is None
    assert repo.queried == []  # no lookup attempted
