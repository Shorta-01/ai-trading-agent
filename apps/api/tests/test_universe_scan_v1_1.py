"""Tests for the V1.1 Slice 31 universe-scan behavior changes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from ai_trading_agent_storage import (
    AssetFundamentalsSnapshotRecord,
    UniverseScanRunRecord,
)

from portfolio_outlook_api.universe_registry import (
    UNIVERSE_SET_EU600,
    UNIVERSE_SET_SP500,
    UniverseEntry,
)
from portfolio_outlook_api.universe_scan_sync import scan_universe


@dataclass
class _FakeFundamentals:
    eodhd_symbol: str
    symbol: str = "X"
    sector: str | None = "Industrials"
    currency: str | None = "EUR"
    market_cap: Decimal | None = Decimal("10000")
    pe_ratio: Decimal | None = Decimal("12.0")
    pb_ratio: Decimal | None = Decimal("2.0")
    ev_ebitda: Decimal | None = Decimal("8.0")
    roic_pct: Decimal | None = Decimal("15.0")
    gross_margin_pct: Decimal | None = Decimal("30.0")
    dividend_yield_pct: Decimal | None = Decimal("2.0")
    return_6m_pct: Decimal | None = Decimal("5.0")
    return_12m_pct: Decimal | None = Decimal("10.0")
    raw_payload_hash: str = "hash-abc"


@dataclass
class _FakeBar:
    bar_date: Any
    close_price: Decimal


class FakeEodhdClient:
    def __init__(self, *, bars_count: int = 260) -> None:
        self._bars_count = bars_count
        self.fundamentals_calls: list[str] = []

    def fetch_fundamentals(self, eodhd_symbol: str) -> _FakeFundamentals:
        self.fundamentals_calls.append(eodhd_symbol)
        return _FakeFundamentals(
            eodhd_symbol=eodhd_symbol, symbol=eodhd_symbol.split(".")[0]
        )

    def fetch_eod_bars(self, eodhd_symbol: str, *, from_date, to_date):  # type: ignore[no-untyped-def]
        bars = []
        from datetime import date as _date

        base = _date(2024, 1, 1)
        for i in range(self._bars_count):
            bars.append(
                _FakeBar(
                    bar_date=base + timedelta(days=i),
                    close_price=Decimal(f"{100.0 + 0.1 * i:.4f}"),
                )
            )
        return bars


@dataclass
class _CachedResult:
    record: AssetFundamentalsSnapshotRecord | None
    found: bool


class FakeSnapshotRepoWithCache:
    def __init__(
        self, *, cached: dict[str, AssetFundamentalsSnapshotRecord] | None = None
    ) -> None:
        self.saved: list[AssetFundamentalsSnapshotRecord] = []
        self._cached = cached or {}

    def save_snapshot(self, record: AssetFundamentalsSnapshotRecord) -> object:
        self.saved.append(record)
        return None

    def get_latest_snapshot_for_symbol(self, eodhd_symbol: str) -> _CachedResult:
        if eodhd_symbol in self._cached:
            return _CachedResult(record=self._cached[eodhd_symbol], found=True)
        return _CachedResult(record=None, found=False)


class FakeScanRepo:
    def __init__(self) -> None:
        self.saved: list[UniverseScanRunRecord] = []
        self.updated: list[UniverseScanRunRecord] = []

    def save_run(self, record):  # type: ignore[no-untyped-def]
        self.saved.append(record)

    def update_run(self, record):  # type: ignore[no-untyped-def]
        self.updated.append(record)


def _entries() -> tuple[UniverseEntry, ...]:
    return (
        UniverseEntry("ABI", "ABI.BR", "BEL20", "Consumer Staples", "BE"),
        UniverseEntry("ASML", "ASML.AS", "AEX", "Technology", "NL"),
    )


def _snapshot(eodhd_symbol: str, *, fetched_at: datetime) -> AssetFundamentalsSnapshotRecord:
    return AssetFundamentalsSnapshotRecord(
        snapshot_id=f"s-{eodhd_symbol}",
        ibkr_conid=None,
        eodhd_symbol=eodhd_symbol,
        symbol=eodhd_symbol.split(".")[0],
        sector="Industrials",
        currency="EUR",
        market_cap=Decimal("10000"),
        pe_ratio=Decimal("12.0"),
        pb_ratio=Decimal("2.0"),
        ev_ebitda=Decimal("8.0"),
        roic_pct=Decimal("15.0"),
        gross_margin_pct=Decimal("30.0"),
        dividend_yield_pct=Decimal("2.0"),
        return_6m_pct=Decimal("5.0"),
        return_12m_pct=Decimal("10.0"),
        raw_payload_hash="hash-cached",
        provider_code="eodhd",
        fetched_at=fetched_at,
        stored_at=fetched_at,
    )


# ---- cache TTL ----------------------------------------------------------


def test_scan_skips_fetch_when_cache_is_within_ttl() -> None:
    now = datetime(2026, 6, 17, 7, 0, tzinfo=UTC)
    # Recent snapshot (1h ago) within a 24h TTL → should be reused.
    cached = {
        "ABI.BR": _snapshot("ABI.BR", fetched_at=now - timedelta(hours=1)),
    }
    snapshot_repo = FakeSnapshotRepoWithCache(cached=cached)
    client = FakeEodhdClient()
    scan_repo = FakeScanRepo()

    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=_entries(),
        cache_ttl_hours=24,
        now=now,
    )
    # ABI.BR was cached; ASML.AS was not.
    assert "ABI.BR" not in client.fundamentals_calls
    assert "ASML.AS" in client.fundamentals_calls
    # ABI.BR's row counts as persisted (it came from the cache) so the
    # final report should include both.
    assert report.scanned_count == 2
    assert report.persisted_count == 2


def test_scan_fetches_when_cache_is_older_than_ttl() -> None:
    now = datetime(2026, 6, 17, 7, 0, tzinfo=UTC)
    # Stale snapshot (48h ago) outside a 24h TTL → should re-fetch.
    cached = {
        "ABI.BR": _snapshot("ABI.BR", fetched_at=now - timedelta(hours=48)),
    }
    snapshot_repo = FakeSnapshotRepoWithCache(cached=cached)
    client = FakeEodhdClient()
    scan_repo = FakeScanRepo()

    scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=_entries(),
        cache_ttl_hours=24,
        now=now,
    )
    # ABI.BR was stale; should be re-fetched.
    assert "ABI.BR" in client.fundamentals_calls


def test_scan_with_zero_ttl_disables_cache_skip() -> None:
    """cache_ttl_hours=0 (the default) means every fire fetches fresh,
    even when a fresh snapshot exists."""

    now = datetime(2026, 6, 17, 7, 0, tzinfo=UTC)
    cached = {
        "ABI.BR": _snapshot("ABI.BR", fetched_at=now - timedelta(minutes=5)),
    }
    snapshot_repo = FakeSnapshotRepoWithCache(cached=cached)
    client = FakeEodhdClient()
    scan_repo = FakeScanRepo()

    scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=_entries(),
        cache_ttl_hours=0,
        now=now,
    )
    # Cache disabled → both symbols fetched.
    assert set(client.fundamentals_calls) == {"ABI.BR", "ASML.AS"}


# ---- universe_set selection --------------------------------------------


def test_scan_universe_with_set_code_picks_eu600() -> None:
    """When `universe_set=EU600` is passed and no explicit `universe`,
    the scan should iterate over the EU600 set rather than the V1
    SP500 set."""

    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepoWithCache()
    scan_repo = FakeScanRepo()

    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=5,  # cap small so the test is fast
        history_lookback_days=400,
        universe_set=UNIVERSE_SET_EU600,
        cache_ttl_hours=0,
    )
    # The universe_size on the audit row should reflect the EU600 set
    # (strictly larger than SP500).
    sp500_size = report.universe_size
    # Now run with SP500 for comparison.
    report_sp = scan_universe(
        client=FakeEodhdClient(),
        snapshot_repo=FakeSnapshotRepoWithCache(),
        scan_repo=FakeScanRepo(),
        max_tickers=5,
        history_lookback_days=400,
        universe_set=UNIVERSE_SET_SP500,
        cache_ttl_hours=0,
    )
    assert sp500_size > report_sp.universe_size
