"""End-to-end integration test for the orchestrator scoring CLI.

This test wires the entire V1.2 doctrine against a real in-memory
SQLite connection and asserts that verdicts get written. It's the
"yes the integration works" check that complements the per-module
unit tests.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import SqlAlchemyOrchestratorScoringVerdictRepository
from ai_trading_agent_storage.metadata import (
    metadata,
    orchestrator_scoring_verdicts,
)
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from portfolio_outlook_portfolio import HistoricalBar
from sqlalchemy import create_engine, select

from portfolio_outlook_worker.forecasting.orchestrator_candidate_provider import (
    CandidateProviderInputs,
    ForecastRow,
    FundamentalsRow,
    HeldPositionRow,
    TradingSettingsSnapshot,
)
from portfolio_outlook_worker.forecasting.orchestrator_scoring_cli import (
    format_run_summary,
    run_scoring_pipeline,
)

_TODAY = date(2026, 6, 12)
_GENERATED_AT = datetime(2026, 6, 12, 9, 0, tzinfo=UTC)


def _bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    price = 100.0
    out = []
    for i in range(count):
        noise = math.sin(i * 17) * 0.015
        price *= math.exp(noise)
        out.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return tuple(out)


def _index_bars() -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * 0.5, 4))),
        )
        for i in range(250)
    )


def _settings() -> TradingSettingsSnapshot:
    return TradingSettingsSnapshot(
        target_net_pct=Decimal("4"),
        confidence_threshold_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
        total_budget_eur=Decimal("1000000"),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
        max_sector_pct=Decimal("25"),
        fat_tail_factor=Decimal("1.15"),
        earnings_block_days=5,
        news_buy_bias_max_boost_pct=Decimal("5"),
    )


def _readiness(allowed: bool = True) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0071_orchestrator_scoring_verdicts",
        database_revision_id=(
            "0071_orchestrator_scoring_verdicts" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


def _build_inputs(*, symbols: list[str]) -> CandidateProviderInputs:
    forecasts = tuple(
        ForecastRow(
            forecast_id=f"fc-{sym}",
            symbol=sym,
            ibkr_conid=hash(sym) & 0xFFFFFF,
            current_price=Decimal("100"),
            p50_price=Decimal("115"),
            expected_volatility_annual=Decimal("20"),
            horizon_days=126,
            confidence_score=Decimal("0.85"),
        )
        for sym in symbols
    )
    fundamentals = {
        sym: FundamentalsRow(
            symbol=sym,
            sector="technology",
            market_cap_eur=Decimal("3000000000000"),
        )
        for sym in symbols
    }
    bars = {sym: _bars() for sym in symbols}
    return CandidateProviderInputs(
        ibkr_account_ref="DU1234567",
        today=_TODAY,
        forecasts=forecasts,
        fundamentals_by_symbol=fundamentals,
        candidate_bars_by_symbol=bars,
        held_positions=(
            HeldPositionRow(
                symbol="X",
                sector="healthcare",
                eur_value=Decimal("100000"),
            ),
        ),
        settings=_settings(),
        vix_level=Decimal("15"),
        index_bars=_index_bars(),
    )


# ---- end-to-end ------------------------------------------------------


def test_pipeline_persists_one_verdict_per_candidate() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_all(engine)
    conn = engine.connect()
    try:
        run = run_scoring_pipeline(
            connection=conn,
            readiness_report=_readiness(True),
            inputs=_build_inputs(symbols=["AAPL", "MSFT"]),
            generated_at=_GENERATED_AT,
        )
        assert run.candidates_built == 2
        assert run.skipped_provider_count == 0
        assert run.scoring.succeeded_count == 2
        assert run.scoring.failed_count == 0
        # Cross-check the rows landed in storage.
        rows = conn.execute(select(orchestrator_scoring_verdicts)).mappings().all()
        assert len(rows) == 2
        decisions = {row["decision"] for row in rows}
        assert decisions == {"suggest"}
        symbols = {row["symbol"] for row in rows}
        assert symbols == {"AAPL", "MSFT"}
        summaries = {row["summary_nl"] for row in rows}
        assert all("Koop" in s for s in summaries)
    finally:
        conn.close()


def test_pipeline_persists_skip_verdicts_too() -> None:
    """A bad candidate (small-cap → risk_universe skip) still gets a
    row written so the operator UI can show why we declined."""

    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_all(engine)
    conn = engine.connect()
    try:
        inputs = _build_inputs(symbols=["TINY"])
        # Override the fundamentals to make TINY a small-cap.
        tiny_funds = {
            "TINY": FundamentalsRow(
                symbol="TINY",
                sector="technology",
                market_cap_eur=Decimal("1000000000"),  # 1B < 5B floor
            )
        }
        inputs_adj = CandidateProviderInputs(
            ibkr_account_ref=inputs.ibkr_account_ref,
            today=inputs.today,
            forecasts=inputs.forecasts,
            fundamentals_by_symbol=tiny_funds,
            candidate_bars_by_symbol=inputs.candidate_bars_by_symbol,
            held_positions=inputs.held_positions,
            settings=inputs.settings,
            vix_level=inputs.vix_level,
            index_bars=inputs.index_bars,
        )
        run = run_scoring_pipeline(
            connection=conn,
            readiness_report=_readiness(True),
            inputs=inputs_adj,
            generated_at=_GENERATED_AT,
        )
        assert run.scoring.succeeded_count == 1
        rows = conn.execute(select(orchestrator_scoring_verdicts)).mappings().all()
        assert len(rows) == 1
        assert rows[0]["decision"] == "skip_risk_universe"
        assert rows[0]["blocking_reason"] == "below_min_market_cap"
    finally:
        conn.close()


def test_format_run_summary_produces_human_readable_lines() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_all(engine)
    conn = engine.connect()
    try:
        run = run_scoring_pipeline(
            connection=conn,
            readiness_report=_readiness(True),
            inputs=_build_inputs(symbols=["AAPL"]),
            generated_at=_GENERATED_AT,
        )
        lines = format_run_summary(run)
        assert any("1 candidates" in line for line in lines)
        assert any("succeeded" in line for line in lines)
    finally:
        conn.close()


def test_repo_can_read_back_what_pipeline_wrote() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_all(engine)
    conn = engine.connect()
    try:
        run_scoring_pipeline(
            connection=conn,
            readiness_report=_readiness(True),
            inputs=_build_inputs(symbols=["AAPL"]),
            generated_at=_GENERATED_AT,
        )
        # Read back via the repository's list method.
        repo = SqlAlchemyOrchestratorScoringVerdictRepository(
            conn, _readiness(True)
        )
        listed = repo.list_verdicts_for_account(
            ibkr_account_ref="DU1234567", limit=10
        )
        assert len(listed.records) == 1
        assert listed.records[0].symbol == "AAPL"
        assert listed.records[0].decision == "suggest"
    finally:
        conn.close()
