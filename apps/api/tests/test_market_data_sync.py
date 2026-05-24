"""Tests for the market-data + FX sync orchestrator.

We inject a fake EODHD provider and fake storage repos, so these tests cover
the exchange mapping, the FX-pair derivation, error handling, partial-batch
behaviour, and the safety contract of the persisted records.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ai_trading_agent_storage import (
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    MarketDataLatestSnapshotRecord,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdFxRate,
    EodhdNotFoundError,
    EodhdQuote,
)
from portfolio_outlook_api.market_data_sync import (
    derive_required_fx_pairs,
    map_ibkr_exchange_to_eodhd,
    sync_market_data_and_fx,
)

# ---- Fixtures ---------------------------------------------------------------

_NOW = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)


def _position(
    *,
    conid: str,
    symbol: str,
    primary_exchange: str | None,
    currency: str = "USD",
    quantity: str = "10",
    average_cost: str | None = "150.00",
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos_{conid}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU12345",
        conid=conid,
        symbol=symbol,
        security_type="STK",
        currency=currency,
        exchange="SMART",
        primary_exchange=primary_exchange,
        quantity=Decimal(quantity),
        average_cost=Decimal(average_cost) if average_cost is not None else None,
        received_at=_NOW,
        stored_at=_NOW,
    )


def _cash(currency: str, amount: str) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id=f"cash_{currency}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU12345",
        base_currency=currency,
        cash=Decimal(amount),
        available_funds=Decimal(amount),
        buying_power=Decimal(amount),
        received_at=_NOW,
        stored_at=_NOW,
    )


class FakeMarketRepo:
    def __init__(self) -> None:
        self.saved: list[MarketDataLatestSnapshotRecord] = []

    def save_latest_market_data_snapshot(
        self, record: MarketDataLatestSnapshotRecord
    ) -> object:
        self.saved.append(record)
        return None


class FakeFxRepo:
    def __init__(self) -> None:
        self.saved: list[FxRateSnapshotRecord] = []

    def save_fx_rate_snapshot(self, record: FxRateSnapshotRecord) -> None:
        self.saved.append(record)


class FakeProvider:
    def __init__(
        self,
        *,
        quotes: dict[str, EodhdQuote] | None = None,
        fx: dict[tuple[str, str], EodhdFxRate] | None = None,
        quote_errors: dict[str, Exception] | None = None,
        fx_errors: dict[tuple[str, str], Exception] | None = None,
    ) -> None:
        self.quotes = quotes or {}
        self.fx = fx or {}
        self.quote_errors = quote_errors or {}
        self.fx_errors = fx_errors or {}
        self.quote_calls: list[str] = []
        self.fx_calls: list[tuple[str, str]] = []

    def fetch_quote(self, eodhd_symbol: str) -> EodhdQuote:
        self.quote_calls.append(eodhd_symbol)
        if eodhd_symbol in self.quote_errors:
            raise self.quote_errors[eodhd_symbol]
        if eodhd_symbol not in self.quotes:
            raise EodhdNotFoundError(eodhd_symbol)
        return self.quotes[eodhd_symbol]

    def fetch_fx_rate(self, base_currency: str, quote_currency: str) -> EodhdFxRate:
        pair = (base_currency, quote_currency)
        self.fx_calls.append(pair)
        if pair in self.fx_errors:
            raise self.fx_errors[pair]
        if pair not in self.fx:
            raise EodhdNotFoundError(f"{base_currency}{quote_currency}.FOREX")
        return self.fx[pair]


def _quote(
    code: str,
    *,
    close: str = "200.00",
    previous_close: str = "198.00",
    change_pct: str = "1.01",
) -> EodhdQuote:
    return EodhdQuote(
        code=code,
        last_price=Decimal(close),
        open_price=None,
        high_price=None,
        low_price=None,
        previous_close=Decimal(previous_close),
        day_change_percent=Decimal(change_pct),
        volume=None,
        provider_as_of=_NOW,
    )


def _fx(base: str, quote: str, rate: str = "0.92") -> EodhdFxRate:
    return EodhdFxRate(
        pair_code=f"{base}{quote}.FOREX",
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        previous_close=Decimal(rate),
        provider_as_of=_NOW,
    )


# ---- Exchange mapping -------------------------------------------------------


@pytest.mark.parametrize(
    "ibkr_exchange,expected",
    [
        ("NYSE", "US"),
        ("NASDAQ", "US"),
        ("NMS", "US"),
        ("AEB", "AS"),
        ("SBF", "PA"),
        ("EBR", "BR"),
        ("IBIS", "XETRA"),
        ("LSE", "LSE"),
        ("nasdaq", "US"),
        ("  NYSE  ", "US"),
    ],
)
def test_map_ibkr_exchange_returns_eodhd_suffix(ibkr_exchange: str, expected: str) -> None:
    assert map_ibkr_exchange_to_eodhd(ibkr_exchange) == expected


@pytest.mark.parametrize("ibkr_exchange", [None, "", "  ", "OTC", "UNKNOWN_EX"])
def test_map_ibkr_exchange_returns_none_for_unknown(ibkr_exchange: str | None) -> None:
    assert map_ibkr_exchange_to_eodhd(ibkr_exchange) is None


# ---- FX pair derivation -----------------------------------------------------


def test_derive_required_fx_pairs_returns_empty_when_single_currency() -> None:
    positions = [_position(conid="1", symbol="AAPL", primary_exchange="NASDAQ", currency="USD")]
    cash = [_cash("USD", "1000")]
    pairs, base = derive_required_fx_pairs(positions=positions, cash_snapshots=cash)
    assert base == "USD"
    assert pairs == []


def test_derive_required_fx_pairs_creates_pair_per_non_base_currency() -> None:
    positions = [
        _position(conid="1", symbol="AAPL", primary_exchange="NASDAQ", currency="USD"),
        _position(conid="2", symbol="ASML", primary_exchange="AEB", currency="EUR"),
        _position(conid="3", symbol="SAP", primary_exchange="IBIS", currency="EUR"),
    ]
    cash = [_cash("EUR", "5000")]
    pairs, base = derive_required_fx_pairs(positions=positions, cash_snapshots=cash)
    assert base == "EUR"
    assert pairs == [("USD", "EUR")]


def test_derive_required_fx_pairs_returns_none_base_when_multi_currency_cash() -> None:
    positions = [_position(conid="1", symbol="AAPL", primary_exchange="NASDAQ", currency="USD")]
    cash = [_cash("USD", "1000"), _cash("EUR", "1000")]
    pairs, base = derive_required_fx_pairs(positions=positions, cash_snapshots=cash)
    assert base is None
    assert pairs == []


# ---- End-to-end sync orchestration -----------------------------------------


def test_sync_happy_path_persists_quotes_and_fx_with_safe_flags_false() -> None:
    positions = [
        _position(conid="265598", symbol="AAPL", primary_exchange="NASDAQ", currency="USD"),
        _position(conid="100001", symbol="ASML", primary_exchange="AEB", currency="EUR"),
    ]
    cash = [_cash("EUR", "10000")]
    provider = FakeProvider(
        quotes={
            "AAPL.US": _quote("AAPL.US", close="181.40"),
            "ASML.AS": _quote("ASML.AS", close="780.50"),
        },
        fx={("USD", "EUR"): _fx("USD", "EUR", rate="0.9234")},
    )
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=cash,
        max_assets=50,
    )

    assert report.asset_total == 2
    assert report.asset_success == 2
    assert report.asset_failed == 0
    assert report.fx_total == 1
    assert report.fx_success == 1
    assert report.market_snapshots_persisted == 2
    assert report.fx_snapshots_persisted == 1
    assert report.base_currency == "EUR"
    assert report.failures == ()
    assert provider.quote_calls == ["AAPL.US", "ASML.AS"]
    assert provider.fx_calls == [("USD", "EUR")]
    # Safety contract on persisted records.
    for record in market_repo.saved:
        assert record.safe_for_analysis is False
        assert record.safe_for_suggestions is False
        assert record.safe_for_action_drafts is False
        assert record.provider_code == "eodhd"
    for fx in fx_repo.saved:
        assert fx.provider == "eodhd"
        assert fx.validation_status == "valid"
        assert fx.freshness_status == "fresh"
        assert fx.pair == "USD/EUR"


def test_sync_skips_positions_with_unknown_exchange() -> None:
    positions = [
        _position(conid="1", symbol="AAPL", primary_exchange="NASDAQ", currency="USD"),
        _position(conid="2", symbol="MYSTERY", primary_exchange="OTC", currency="USD"),
    ]
    provider = FakeProvider(quotes={"AAPL.US": _quote("AAPL.US")})
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=[_cash("USD", "100")],
        max_assets=10,
    )

    assert report.asset_success == 1
    assert report.asset_skipped_unknown_exchange == 1
    assert provider.quote_calls == ["AAPL.US"]
    assert any(
        f["reason"] == "unknown_exchange" and f["symbol"] == "MYSTERY"
        for f in report.failures
    )


def test_sync_deduplicates_positions_by_conid_and_respects_max_assets() -> None:
    positions = [
        _position(conid="1", symbol="AAPL", primary_exchange="NASDAQ"),
        _position(conid="1", symbol="AAPL", primary_exchange="NASDAQ"),  # duplicate
        _position(conid="2", symbol="MSFT", primary_exchange="NASDAQ"),
        _position(conid="3", symbol="GOOG", primary_exchange="NASDAQ"),
    ]
    provider = FakeProvider(
        quotes={
            "AAPL.US": _quote("AAPL.US"),
            "MSFT.US": _quote("MSFT.US"),
        },
    )
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=[_cash("USD", "100")],
        max_assets=2,
    )

    assert report.asset_total == 2
    assert provider.quote_calls == ["AAPL.US", "MSFT.US"]


def test_sync_stops_calling_quote_after_auth_error() -> None:
    positions = [
        _position(conid="1", symbol="AAPL", primary_exchange="NASDAQ"),
        _position(conid="2", symbol="MSFT", primary_exchange="NASDAQ"),
    ]
    provider = FakeProvider(
        quote_errors={"AAPL.US": EodhdAuthError("bad key")},
        quotes={"MSFT.US": _quote("MSFT.US")},  # should never be called
    )
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=[_cash("USD", "100")],
        max_assets=10,
    )

    assert provider.quote_calls == ["AAPL.US"]
    assert report.market_snapshots_persisted == 0
    assert any(f["reason"] == "auth_error" for f in report.failures)


def test_sync_handles_missing_price_quote() -> None:
    positions = [_position(conid="1", symbol="AAPL", primary_exchange="NASDAQ")]
    provider = FakeProvider(
        quotes={
            "AAPL.US": EodhdQuote(
                code="AAPL.US",
                last_price=None,
                open_price=None,
                high_price=None,
                low_price=None,
                previous_close=None,
                day_change_percent=None,
                volume=None,
                provider_as_of=_NOW,
            ),
        },
    )
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=[_cash("USD", "100")],
        max_assets=10,
    )

    assert report.asset_success == 0
    assert report.asset_failed == 1
    assert market_repo.saved == []
    assert any(f["reason"] == "missing_price" for f in report.failures)


def test_sync_persists_fx_with_invalid_status_when_rate_is_zero() -> None:
    positions = [_position(conid="1", symbol="ASML", primary_exchange="AEB", currency="EUR")]
    cash = [_cash("USD", "1000")]
    provider = FakeProvider(
        quotes={"ASML.AS": _quote("ASML.AS")},
        fx={("EUR", "USD"): _fx("EUR", "USD", rate="0")},
    )
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=cash,
        max_assets=10,
    )

    assert report.fx_total == 1
    assert report.fx_failed == 1
    assert report.fx_snapshots_persisted == 1
    persisted_fx = fx_repo.saved[0]
    assert persisted_fx.validation_status == "invalid"
    assert persisted_fx.reason_code == "non_positive_rate"


def test_sync_skips_fx_when_no_base_currency_resolvable() -> None:
    positions = [_position(conid="1", symbol="AAPL", primary_exchange="NASDAQ")]
    cash = [_cash("USD", "1000"), _cash("EUR", "1000")]  # two cash currencies, no base
    provider = FakeProvider(quotes={"AAPL.US": _quote("AAPL.US")})
    market_repo = FakeMarketRepo()
    fx_repo = FakeFxRepo()

    report = sync_market_data_and_fx(
        provider=provider,
        market_repo=market_repo,
        fx_repo=fx_repo,
        positions=positions,
        cash_snapshots=cash,
        max_assets=10,
    )

    assert report.base_currency is None
    assert report.fx_total == 0
    assert provider.fx_calls == []
