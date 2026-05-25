"""Task 129 — market-data step idempotency + partial-failure tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    SqlAlchemyFxRateRepository,
    SqlAlchemyMarketDataEodSnapshotRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.market_data_step import (
    AssetForFetch,
    fetch_market_data_for_account,
)
from portfolio_outlook_worker.providers.eodhd import (
    EodResponse,
    FxResponse,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0048_market_data_eod_and_fx_runtime",
        database_revision_id=(
            "0048_market_data_eod_and_fx_runtime" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_TARGET_DATE = date(2026, 5, 24)
_NOW = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _StubUniverse:
    def __init__(self, assets: tuple[AssetForFetch, ...]) -> None:
        self._assets = assets

    def list_assets_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[AssetForFetch, ...]:
        return self._assets


class _StubEodhdClient:
    """Predictable EodhdClient stand-in.

    Returns canned :class:`EodResponse` / :class:`FxResponse` per
    `(symbol, exchange)` or `(base, quote)`, or raises a stored
    exception for the matching key.
    """

    def __init__(
        self,
        *,
        eod_responses: dict[tuple[str, str], EodResponse | Exception] | None = None,
        fx_responses: dict[tuple[str, str], FxResponse | Exception] | None = None,
    ) -> None:
        self._eod = eod_responses or {}
        self._fx = fx_responses or {}
        self.eod_calls: list[tuple[str, str, date]] = []
        self.fx_calls: list[tuple[str, str, date]] = []

    def fetch_eod(
        self, *, symbol: str, exchange: str, as_of_date: date
    ) -> EodResponse:
        self.eod_calls.append((symbol, exchange, as_of_date))
        result = self._eod.get((symbol, exchange))
        if result is None:
            raise RuntimeError(f"no fixture for {symbol}.{exchange}")
        if isinstance(result, Exception):
            raise result
        return result

    def fetch_fx(
        self, *, base: str, quote: str, as_of_date: date
    ) -> FxResponse:
        self.fx_calls.append((base, quote, as_of_date))
        result = self._fx.get((base, quote))
        if result is None:
            raise RuntimeError(f"no fixture for {base}{quote}")
        if isinstance(result, Exception):
            raise result
        return result


def _eod(close: str) -> EodResponse:
    return EodResponse(
        symbol="X",
        exchange="X",
        as_of_date=_TARGET_DATE,
        open=Decimal("1.0"),
        high=Decimal("1.0"),
        low=Decimal("1.0"),
        close=Decimal(close),
        adjusted_close=Decimal(close),
        volume=100,
        raw_hash="hash-" + close,
    )


def _fx(rate: str) -> FxResponse:
    return FxResponse(
        base="USD",
        quote="EUR",
        as_of_date=_TARGET_DATE,
        rate=Decimal(rate),
        raw_hash="fxhash",
    )


# ---- idempotency -------------------------------------------------


def test_step_skips_fetch_when_snapshot_already_exists() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        fx_repo = SqlAlchemyFxRateRepository(conn, _report(True))
        eodhd = _StubEodhdClient(
            eod_responses={("ASML", "AEB"): _eod("640.0")},
        )
        universe = _StubUniverse(
            assets=(
                AssetForFetch(
                    ibkr_conid="111",
                    symbol="ASML",
                    exchange="AEB",
                    currency_local="EUR",
                ),
            )
        )

        first = fetch_market_data_for_account(
            ibkr_account_id="DU1234567",
            asset_universe=universe,
            snapshot_repo=snap_repo,
            fx_rate_repo=fx_repo,
            eodhd_client=eodhd,  # type: ignore[arg-type]
            target_date=_TARGET_DATE,
            now_provider=lambda: _NOW,
        )
        assert first.snapshots_attempted == 1
        assert first.snapshots_succeeded == 1

        second = fetch_market_data_for_account(
            ibkr_account_id="DU1234567",
            asset_universe=universe,
            snapshot_repo=snap_repo,
            fx_rate_repo=fx_repo,
            eodhd_client=eodhd,  # type: ignore[arg-type]
            target_date=_TARGET_DATE,
            now_provider=lambda: _NOW,
        )
        # No fetch attempted on the second call because the snapshot
        # already exists for (conid, date, provider).
        assert second.snapshots_attempted == 0
        assert second.snapshots_succeeded == 0
        # And the stub recorded only one EOD call across both runs.
        assert len(eodhd.eod_calls) == 1


# ---- partial failure ---------------------------------------------


def test_step_continues_after_one_failed_fetch() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        fx_repo = SqlAlchemyFxRateRepository(conn, _report(True))
        eodhd = _StubEodhdClient(
            eod_responses={
                ("ASML", "AEB"): _eod("640.0"),
                ("VWCE", "XETRA"): ConnectionError("upstream"),
                ("SAP", "XETRA"): _eod("180.0"),
            },
        )
        universe = _StubUniverse(
            assets=(
                AssetForFetch(
                    ibkr_conid="111",
                    symbol="ASML",
                    exchange="AEB",
                    currency_local="EUR",
                ),
                AssetForFetch(
                    ibkr_conid="222",
                    symbol="VWCE",
                    exchange="XETRA",
                    currency_local="EUR",
                ),
                AssetForFetch(
                    ibkr_conid="333",
                    symbol="SAP",
                    exchange="XETRA",
                    currency_local="EUR",
                ),
            )
        )
        result = fetch_market_data_for_account(
            ibkr_account_id="DU1234567",
            asset_universe=universe,
            snapshot_repo=snap_repo,
            fx_rate_repo=fx_repo,
            eodhd_client=eodhd,  # type: ignore[arg-type]
            target_date=_TARGET_DATE,
            now_provider=lambda: _NOW,
        )
        assert result.snapshots_attempted == 3
        assert result.snapshots_succeeded == 2
        assert len(result.snapshots_failed) == 1
        assert result.snapshots_failed[0].symbol == "VWCE"
        assert result.snapshots_failed[0].error_class == "ConnectionError"
        # The two surviving rows landed in storage.
        assert snap_repo.get_for_date(
            ibkr_conid="111", as_of_date=_TARGET_DATE
        ) is not None
        assert snap_repo.get_for_date(
            ibkr_conid="333", as_of_date=_TARGET_DATE
        ) is not None


# ---- FX fan-out --------------------------------------------------


def test_step_fetches_one_fx_per_non_base_currency() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        fx_repo = SqlAlchemyFxRateRepository(conn, _report(True))
        eodhd = _StubEodhdClient(
            eod_responses={
                ("SHEL", "LSE"): _eod("28.5"),
                ("NVDA", "NASDAQ"): _eod("900.0"),
            },
            fx_responses={
                ("GBP", "EUR"): FxResponse(
                    base="GBP",
                    quote="EUR",
                    as_of_date=_TARGET_DATE,
                    rate=Decimal("1.18"),
                    raw_hash="gbp-eur",
                ),
                ("USD", "EUR"): FxResponse(
                    base="USD",
                    quote="EUR",
                    as_of_date=_TARGET_DATE,
                    rate=Decimal("0.91"),
                    raw_hash="usd-eur",
                ),
            },
        )
        universe = _StubUniverse(
            assets=(
                AssetForFetch(
                    ibkr_conid="111",
                    symbol="SHEL",
                    exchange="LSE",
                    currency_local="GBP",
                ),
                AssetForFetch(
                    ibkr_conid="222",
                    symbol="NVDA",
                    exchange="NASDAQ",
                    currency_local="USD",
                ),
                AssetForFetch(
                    ibkr_conid="333",
                    symbol="NVDA-DUP",
                    exchange="NASDAQ",
                    currency_local="USD",
                ),
            )
        )
        result = fetch_market_data_for_account(
            ibkr_account_id="DU1234567",
            asset_universe=universe,
            snapshot_repo=snap_repo,
            fx_rate_repo=fx_repo,
            eodhd_client=eodhd,  # type: ignore[arg-type]
            target_date=_TARGET_DATE,
            now_provider=lambda: _NOW,
        )
        # Two unique currencies (GBP + USD) → two FX fetches.
        assert result.fx_rates_attempted == 2
        assert result.fx_rates_succeeded == 2
        # USD fetched once even though two assets are USD.
        assert {pair[:2] for pair in eodhd.fx_calls} == {
            ("GBP", "EUR"),
            ("USD", "EUR"),
        }


def test_step_returns_zero_counts_for_empty_universe() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        fx_repo = SqlAlchemyFxRateRepository(conn, _report(True))
        eodhd = _StubEodhdClient()
        universe = _StubUniverse(assets=tuple())
        result = fetch_market_data_for_account(
            ibkr_account_id="DU1234567",
            asset_universe=universe,
            snapshot_repo=snap_repo,
            fx_rate_repo=fx_repo,
            eodhd_client=eodhd,  # type: ignore[arg-type]
            target_date=_TARGET_DATE,
            now_provider=lambda: _NOW,
        )
        assert result.snapshots_attempted == 0
        assert result.fx_rates_attempted == 0
