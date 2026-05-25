"""Task 131 — multi-asset forecasting step integration tests.

Covers the universe-resolver + per-asset error handling. The single-asset
Task 130 cases are subsumed here; per-asset failures must surface as
``Geblokkeerd`` rows with the locked block_reason without crashing the
run.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import SqlAlchemyForecastRepository
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.forecasting.forecasting_step import (
    run_forecasting_step,
)

_NOW = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


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
        latest_expected_revision_id="0049_forecasts_and_calibration_diary",
        database_revision_id=(
            "0049_forecasts_and_calibration_diary" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


def _make_history(
    *, count: int, latest_date: date, drift: float = 0.0005, vol: float = 0.01
) -> tuple[tuple[date, Decimal], ...]:
    """Deterministic synthetic price series.

    Generates ``count`` daily closes ending on ``latest_date`` with
    geometric drift + alternating sinusoidal noise so that p10/p50/p90
    spread out cleanly under the bootstrap.
    """

    closes: list[tuple[date, Decimal]] = []
    log_price = math.log(100.0)
    for i in range(count):
        bar_date = latest_date - timedelta(days=(count - 1 - i))
        # Sinusoid alternating sign gives mean-zero noise with finite vol.
        log_price += drift + vol * math.sin(i * 0.3)
        closes.append((bar_date, Decimal(repr(math.exp(log_price)))))
    return tuple(closes)


class _StubWatchlist:
    def __init__(self, conids: tuple[str, ...]) -> None:
        self._conids = conids

    def list_active_conids_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str], ...]:
        return tuple((c, c) for c in self._conids)


class _StubPositions:
    def list_held_positions_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str, Decimal], ...]:
        return ()


class _StubCloseProvider:
    def __init__(
        self,
        *,
        closes_by_conid: dict[str, tuple[tuple[date, Decimal], ...]],
        raises_for: set[str] | None = None,
    ) -> None:
        self._closes_by_conid = closes_by_conid
        self._raises_for = raises_for or set()

    def list_recent_closes(
        self, *, ibkr_conid: str, days: int  # noqa: ARG002
    ) -> tuple[tuple[date, Decimal], ...]:
        if ibkr_conid in self._raises_for:
            raise RuntimeError(f"simulated outage for {ibkr_conid}")
        return self._closes_by_conid.get(ibkr_conid, ())


# ---- happy path -------------------------------------------------


def test_multi_asset_run_writes_one_row_per_conid() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        conids = tuple(f"asset-{i:02d}" for i in range(15))
        closes_map = {
            c: _make_history(count=252, latest_date=_NOW.date()) for c in conids
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(conids),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=500,
        )
        assert result.total_attempted == 15
        assert result.succeeded == 15
        assert result.total_blocked == 0
        assert result.blocked_by_reason == {}


# ---- per-asset failure modes ------------------------------------


def test_insufficient_history_blocks_only_affected_assets() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        good_conids = tuple(f"good-{i:02d}" for i in range(13))
        short_conids = ("short-A", "short-B")
        closes_map: dict[str, tuple[tuple[date, Decimal], ...]] = {}
        for c in good_conids:
            closes_map[c] = _make_history(count=252, latest_date=_NOW.date())
        for c in short_conids:
            closes_map[c] = _make_history(count=100, latest_date=_NOW.date())
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(good_conids + short_conids),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        assert result.total_attempted == 15
        assert result.succeeded == 13
        assert result.total_blocked == 2
        assert result.blocked_by_reason == {"insufficient_history": 2}


def test_stale_market_data_blocks_only_affected_assets() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        fresh_conids = tuple(f"fresh-{i:02d}" for i in range(14))
        stale_conid = "stale-X"
        closes_map: dict[str, tuple[tuple[date, Decimal], ...]] = {}
        for c in fresh_conids:
            closes_map[c] = _make_history(count=252, latest_date=_NOW.date())
        # Stale = latest snapshot 10 days old (threshold is 3).
        stale_latest = _NOW.date() - timedelta(days=10)
        closes_map[stale_conid] = _make_history(count=252, latest_date=stale_latest)
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(fresh_conids + (stale_conid,)),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        assert result.succeeded == 14
        assert result.blocked_by_reason == {"stale_market_data": 1}


def test_missing_asset_listing_blocks_only_affected_assets() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        good_conids = tuple(f"good-{i:02d}" for i in range(14))
        missing_conid = "missing-X"
        closes_map: dict[str, tuple[tuple[date, Decimal], ...]] = {
            c: _make_history(count=252, latest_date=_NOW.date())
            for c in good_conids
        }
        # missing_conid → empty list returned by provider.
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(good_conids + (missing_conid,)),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        assert result.succeeded == 14
        assert result.blocked_by_reason == {"missing_asset_listing": 1}


def test_computation_error_blocks_only_affected_assets() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        good_conids = tuple(f"good-{i:02d}" for i in range(14))
        boom_conid = "boom-X"
        closes_map: dict[str, tuple[tuple[date, Decimal], ...]] = {
            c: _make_history(count=252, latest_date=_NOW.date())
            for c in good_conids
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(good_conids + (boom_conid,)),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(
                closes_by_conid=closes_map,
                raises_for={boom_conid},
            ),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        # Provider exception → missing_asset_listing (boundary).
        assert result.succeeded == 14
        assert result.blocked_by_reason == {"missing_asset_listing": 1}


# ---- override + empty-universe edge cases ----------------------


def test_empty_universe_returns_empty_result() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(()),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid={}),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
        )
        assert result.total_attempted == 0
        assert result.succeeded == 0


def test_override_conids_bypass_universe_resolver() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        closes_map = {
            "OVERRIDE-A": _make_history(count=252, latest_date=_NOW.date()),
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(("WL-1", "WL-2")),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
            override_conids=("OVERRIDE-A",),
        )
        assert result.total_attempted == 1
        # WL-1, WL-2 were not consulted.
        assert result.per_conid[0].conid == "OVERRIDE-A"


def test_persistence_failures_are_NOT_counted_as_succeeded() -> None:
    """Regression: PR #410 review (P1) — `succeeded` previously incremented on
    label alone, so an asset whose forecast computed cleanly but whose
    ``forecast_repo.append`` raised was reported as a success even though
    the row was never persisted. Make the audit row surface the failure.
    """

    class _AppendFailsRepo:
        """Tiny seam: every append raises, but `_report` thinks writes OK."""

        def __init__(
            self, real_repo: SqlAlchemyForecastRepository
        ) -> None:
            self._real = real_repo
            self.append_calls = 0

        def append(self, record):  # type: ignore[no-untyped-def]  # noqa: ANN001
            self.append_calls += 1
            raise RuntimeError("simulated DB unavailable")

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        real_repo = SqlAlchemyForecastRepository(conn, _report(True))
        failing_repo = _AppendFailsRepo(real_repo)
        closes_map = {
            "X": _make_history(count=252, latest_date=_NOW.date()),
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(("X",)),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=failing_repo,  # type: ignore[arg-type]
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        assert result.total_attempted == 1
        # Audit must NOT report this as a success.
        assert result.succeeded == 0
        # Audit must NOT report this as a block (block row also failed).
        assert result.total_blocked == 0
        # Persistence failure is visibly counted.
        assert result.persistence_failures == 1
        # Audit dict reflects the same.
        audit = result.as_audit_dict()
        assert audit["succeeded"] == 0
        assert audit["persistence_failures"] == 1


def test_persistence_failure_on_block_row_is_NOT_counted_as_blocked() -> None:
    """Parallel regression: when the block-row append fails the audit
    must report a persistence_failure, not a phantom block. Without this,
    `total_blocked` overstates how many block rows actually landed.
    """

    class _AppendFailsRepo:
        def append(self, record):  # type: ignore[no-untyped-def]  # noqa: ANN001
            raise RuntimeError("simulated DB unavailable")

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        # Asset has insufficient history → goes down the block path.
        closes_map = {
            "X": _make_history(count=100, latest_date=_NOW.date()),
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(("X",)),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=_AppendFailsRepo(),  # type: ignore[arg-type]
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        assert result.succeeded == 0
        assert result.total_blocked == 0
        assert result.persistence_failures == 1


def test_audit_dict_shape_for_orchestrator_folding() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        forecast_repo = SqlAlchemyForecastRepository(conn, _report(True))
        closes_map = {
            "A": _make_history(count=252, latest_date=_NOW.date()),
            "B": _make_history(count=100, latest_date=_NOW.date()),
        }
        result = run_forecasting_step(
            ibkr_account_id="DU1234567",
            watchlist_provider=_StubWatchlist(("A", "B")),
            position_provider=_StubPositions(),
            close_provider=_StubCloseProvider(closes_by_conid=closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            num_resamples=200,
        )
        audit = result.as_audit_dict()
        assert audit["total_attempted"] == 2
        assert audit["succeeded"] == 1
        assert audit["total_blocked"] == 1
        assert audit["blocked_by_reason"] == {"insufficient_history": 1}
        assert audit["persistence_failures"] == 0
        assert "wall_clock_ms" in audit
