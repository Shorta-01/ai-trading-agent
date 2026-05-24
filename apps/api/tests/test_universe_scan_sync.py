"""Tests for the universe scan orchestrator (Slice 17)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetFundamentalsSnapshotRecord,
    UniverseScanRunRecord,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdBar,
    EodhdClientError,
    EodhdFundamentals,
)
from portfolio_outlook_api.universe_registry import UniverseEntry
from portfolio_outlook_api.universe_scan_sync import (
    build_universe_fundamentals,
    scan_universe,
)

_NOW = datetime(2026, 6, 3, 6, 30, tzinfo=UTC)


def _entry(symbol: str = "AAPL", eodhd: str = "AAPL.US") -> UniverseEntry:
    return UniverseEntry(
        symbol=symbol, eodhd_symbol=eodhd, index_code="SP100", sector="Technology"
    )


def _fundamentals(symbol: str = "AAPL.US") -> EodhdFundamentals:
    return EodhdFundamentals(
        eodhd_symbol=symbol,
        sector="Technology",
        currency="USD",
        market_cap=Decimal("3000000000000"),
        pe_ratio=Decimal("30.0"),
        pb_ratio=Decimal("50.0"),
        ev_ebitda=Decimal("22.0"),
        roic_pct=Decimal("28.0"),
        gross_margin_pct=Decimal("45.0"),
        dividend_yield_pct=Decimal("0.5"),
        return_6m_pct=None,
        return_12m_pct=None,
        raw_payload_hash="hash",
    )


def _bar(bar_date: date, close: float) -> EodhdBar:
    return EodhdBar(
        bar_date=bar_date,
        open_price=Decimal(str(close)),
        high_price=Decimal(str(close)),
        low_price=Decimal(str(close)),
        close_price=Decimal(str(close)),
        adjusted_close=Decimal(str(close)),
        volume=Decimal("1000000"),
    )


def _bars(count: int = 260, start_price: float = 100.0) -> list[EodhdBar]:
    base = date(2025, 5, 1)
    return [_bar(base + timedelta(days=i), start_price + i * 0.1) for i in range(count)]


class FakeEodhdClient:
    def __init__(
        self,
        *,
        fundamentals: dict[str, EodhdFundamentals] | None = None,
        bars: dict[str, list[EodhdBar]] | None = None,
        raise_on_fundamentals: set[str] | None = None,
        raise_on_bars: set[str] | None = None,
    ) -> None:
        self._fundamentals = fundamentals or {}
        self._bars = bars or {}
        self._raise_fund = raise_on_fundamentals or set()
        self._raise_bars = raise_on_bars or set()
        self.fetched: list[str] = []

    def fetch_fundamentals(self, eodhd_symbol: str) -> EodhdFundamentals:
        self.fetched.append(f"fund:{eodhd_symbol}")
        if eodhd_symbol in self._raise_fund:
            raise EodhdClientError("auth_error")
        return self._fundamentals.get(eodhd_symbol, _fundamentals(eodhd_symbol))

    def fetch_eod_bars(
        self, eodhd_symbol: str, *, from_date: date, to_date: date
    ) -> list[EodhdBar]:
        self.fetched.append(f"bars:{eodhd_symbol}")
        if eodhd_symbol in self._raise_bars:
            raise EodhdClientError("bars_failed")
        return self._bars.get(eodhd_symbol, _bars())


class FakeSnapshotRepo:
    def __init__(self, *, raise_on_save: bool = False) -> None:
        self.saved: list[AssetFundamentalsSnapshotRecord] = []
        self._raise = raise_on_save

    def save_snapshot(self, record: AssetFundamentalsSnapshotRecord) -> object:
        if self._raise:
            raise RuntimeError("storage-fail")
        self.saved.append(record)
        return None


class FakeScanRepo:
    def __init__(self) -> None:
        self.saved: list[UniverseScanRunRecord] = []
        self.updated: list[UniverseScanRunRecord] = []

    def save_run(self, record: UniverseScanRunRecord) -> object:
        self.saved.append(record)
        return None

    def update_run(self, record: UniverseScanRunRecord) -> object:
        self.updated.append(record)
        return None


# ---- happy path -------------------------------------------------------


def test_scan_persists_one_snapshot_per_ticker_and_updates_run() -> None:
    universe = [_entry("AAPL", "AAPL.US"), _entry("MSFT", "MSFT.US")]
    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()

    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )

    assert report.status == "succeeded"
    assert report.scanned_count == 2
    assert report.persisted_count == 2
    assert report.failed_count == 0
    assert report.ranked_count == 2
    assert len(snapshot_repo.saved) == 2
    # The scan_run row is first saved as "running" then updated to a
    # terminal state.
    assert len(scan_repo.saved) == 1
    assert scan_repo.saved[0].status == "running"
    assert len(scan_repo.updated) == 1
    assert scan_repo.updated[0].status == "succeeded"
    assert scan_repo.updated[0].scanned_count == 2


def test_scan_caps_iteration_at_max_tickers() -> None:
    universe = [_entry(f"T{i}", f"T{i}.US") for i in range(10)]
    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=3,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    assert report.scanned_count == 3
    assert report.persisted_count == 3
    assert report.universe_size == 10
    # 3 funds + 3 bars = 6 fetches
    assert len([f for f in client.fetched if f.startswith("fund:")]) == 3


# ---- failures ---------------------------------------------------------


def test_fundamentals_fetch_error_is_recorded_but_does_not_abort_batch() -> None:
    universe = [_entry("AAPL", "AAPL.US"), _entry("MSFT", "MSFT.US")]
    client = FakeEodhdClient(raise_on_fundamentals={"AAPL.US"})
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    assert report.persisted_count == 1
    assert report.failed_count == 1
    assert any(f["reason"] == "fundamentals_fetch_failed" for f in report.failures)
    assert any(f["eodhd_symbol"] == "AAPL.US" for f in report.failures)


def test_bars_fetch_error_records_failure_but_still_persists() -> None:
    universe = [_entry("AAPL", "AAPL.US")]
    client = FakeEodhdClient(raise_on_bars={"AAPL.US"})
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    # The snapshot is still persisted (fundamentals succeeded).
    assert report.persisted_count == 1
    # ...but the bars failure is reported on the failures list.
    assert any(f["reason"] == "bars_fetch_failed" for f in report.failures)


def test_persistence_error_is_classified_as_failure() -> None:
    universe = [_entry("AAPL", "AAPL.US")]
    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepo(raise_on_save=True)
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    assert report.persisted_count == 0
    assert report.failed_count == 1
    assert report.status == "failed"
    assert any(f["reason"] == "persistence_failed" for f in report.failures)


def test_empty_batch_yields_skipped_status() -> None:
    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=0,
        history_lookback_days=400,
        universe=[_entry()],
        now=_NOW,
    )
    assert report.status == "skipped"
    assert report.scanned_count == 0


# ---- derived returns --------------------------------------------------


def test_return_6m_and_12m_are_derived_from_bars_when_fundamentals_omit_them() -> None:
    # Build bars where price doubles over 252 days → 12m return = 100 %.
    bars = []
    base = date(2025, 5, 1)
    for i in range(260):
        # Geometric series: 100 * 2^(i/252)
        price = 100.0 * (2 ** (i / 252))
        bars.append(_bar(base + timedelta(days=i), price))
    fundamentals = EodhdFundamentals(
        eodhd_symbol="AAPL.US",
        sector="Technology",
        currency="USD",
        market_cap=None,
        pe_ratio=None,
        pb_ratio=None,
        ev_ebitda=None,
        roic_pct=None,
        gross_margin_pct=None,
        dividend_yield_pct=None,
        return_6m_pct=None,
        return_12m_pct=None,
        raw_payload_hash="h",
    )
    universe = [_entry()]
    client = FakeEodhdClient(
        fundamentals={"AAPL.US": fundamentals}, bars={"AAPL.US": bars}
    )
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    assert report.persisted_count == 1
    record = snapshot_repo.saved[0]
    # 12m return derived from doubling series ≈ 100 %.
    assert record.return_12m_pct is not None
    assert abs(record.return_12m_pct - Decimal("100")) < Decimal("1.5")
    # 6m return (~126 days) ≈ 41 % (i.e. 2^0.5 - 1).
    assert record.return_6m_pct is not None
    assert abs(record.return_6m_pct - Decimal("41.4")) < Decimal("1.5")


def test_explicit_returns_in_fundamentals_take_precedence() -> None:
    fundamentals = EodhdFundamentals(
        eodhd_symbol="AAPL.US",
        sector=None,
        currency=None,
        market_cap=None,
        pe_ratio=None,
        pb_ratio=None,
        ev_ebitda=None,
        roic_pct=None,
        gross_margin_pct=None,
        dividend_yield_pct=None,
        return_6m_pct=Decimal("7.0"),
        return_12m_pct=Decimal("15.0"),
        raw_payload_hash="h",
    )
    universe = [_entry()]
    client = FakeEodhdClient(fundamentals={"AAPL.US": fundamentals})
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    record = snapshot_repo.saved[0]
    assert record.return_6m_pct == Decimal("7.0")
    assert record.return_12m_pct == Decimal("15.0")


# ---- ranking + universe fundamentals helper ---------------------------


def test_ranked_count_skips_records_with_no_factor_data() -> None:
    rich = _fundamentals("RICH.US")
    bare = EodhdFundamentals(
        eodhd_symbol="BARE.US",
        sector=None,
        currency=None,
        market_cap=None,
        pe_ratio=None,
        pb_ratio=None,
        ev_ebitda=None,
        roic_pct=None,
        gross_margin_pct=None,
        dividend_yield_pct=None,
        return_6m_pct=None,
        return_12m_pct=None,
        raw_payload_hash="h",
    )
    universe = [
        _entry("RICH", "RICH.US"),
        _entry("BARE", "BARE.US"),
    ]
    client = FakeEodhdClient(
        fundamentals={"RICH.US": rich, "BARE.US": bare},
        # No bars for BARE → bare snapshot has no factor data → not ranked
        bars={"RICH.US": _bars(), "BARE.US": []},
    )
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    report = scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    assert report.persisted_count == 2
    assert report.ranked_count == 1


def test_build_universe_fundamentals_translates_snapshots_to_predictor_inputs() -> None:
    universe = [_entry("AAPL", "AAPL.US")]
    client = FakeEodhdClient()
    snapshot_repo = FakeSnapshotRepo()
    scan_repo = FakeScanRepo()
    scan_universe(
        client=client,
        snapshot_repo=snapshot_repo,
        scan_repo=scan_repo,
        max_tickers=10,
        history_lookback_days=400,
        universe=universe,
        now=_NOW,
    )
    fundamentals = build_universe_fundamentals(snapshot_repo.saved)
    assert fundamentals.entries[0].symbol == "AAPL"
    assert fundamentals.entries[0].pe_ratio == Decimal("30.0")
