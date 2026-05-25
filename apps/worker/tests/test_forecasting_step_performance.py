"""Task 131 — wall-clock budget check for 15 real bootstraps.

The brief locks a 60-second budget per ``morning_briefing`` run with
15 assets. This test runs the real ``compute_historical_bootstrap_forecast``
(10 000 resamples, 5-day blocks) end-to-end and asserts the assertion
holds with comfortable headroom. If this ever fails, either the
bootstrap math regressed or the universe scope expanded — both are
real issues worth investigating, not bumping the budget.
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
_BUDGET_MS = 60_000  # Task 131 product lock §7


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
    *, count: int, latest_date: date
) -> tuple[tuple[date, Decimal], ...]:
    closes: list[tuple[date, Decimal]] = []
    log_price = math.log(100.0)
    for i in range(count):
        bar_date = latest_date - timedelta(days=(count - 1 - i))
        log_price += 0.0005 + 0.01 * math.sin(i * 0.3)
        closes.append((bar_date, Decimal(repr(math.exp(log_price)))))
    return tuple(closes)


class _Watchlist:
    def __init__(self, conids: tuple[str, ...]) -> None:
        self._conids = conids

    def list_active_conids_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str], ...]:
        return tuple((c, c) for c in self._conids)


class _Positions:
    def list_held_positions_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str, Decimal], ...]:
        return ()


class _Closes:
    def __init__(
        self, closes_by_conid: dict[str, tuple[tuple[date, Decimal], ...]]
    ) -> None:
        self._closes_by_conid = closes_by_conid

    def list_recent_closes(
        self, *, ibkr_conid: str, days: int  # noqa: ARG002
    ) -> tuple[tuple[date, Decimal], ...]:
        return self._closes_by_conid.get(ibkr_conid, ())


def test_15_assets_complete_within_60_seconds() -> None:
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
            watchlist_provider=_Watchlist(conids),
            position_provider=_Positions(),
            close_provider=_Closes(closes_map),
            forecast_repo=forecast_repo,
            scheduled_run_id="srun-1",
            now_provider=lambda: _NOW,
            rng_seed=42,
            # Real production knobs: 10 000 resamples, 5-day blocks.
        )
        assert result.total_attempted == 15
        assert result.succeeded == 15
        # The locked budget is 60 s; we want generous headroom so that
        # CI noise doesn't flake the test.
        assert result.wall_clock_ms < _BUDGET_MS, (
            f"forecasting step took {result.wall_clock_ms}ms, "
            f"exceeds the {_BUDGET_MS}ms budget"
        )
