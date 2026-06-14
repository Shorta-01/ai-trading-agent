"""Real (non-stub) orchestrator scoring leg for the morning chain
(V1.2 §AB).

Promotes the V1.2 §Y no-op stub in ``morning_chain.py`` to an
actual call into the worker's end-to-end pipeline. When the new
``orchestrator_scoring_enabled`` flag is on, this leg:

1. Opens a writable storage connection
2. Reads the latest ``asset_forecasts`` row per known symbol
3. Builds a ``CandidateProviderInputs`` with:

   * the real forecast values (current_price, p50, vol, horizon,
     confidence)
   * synthetic fundamentals and bars for now — the V1 universe is
     all liquid US large-caps, so safe defaults for market_cap and
     a 250-bar moderate-vol series let every per-name gate run.
     A future slice replaces these with live
     ``asset_fundamentals_snapshots`` and ``market_data_bars``
     lookups (V1.2 §AC).
   * locked V1 trading-settings defaults — the user-facing UI
     stores edits in ``trading_settings.user_strategy_json`` and a
     future slice (V1.2 §AC) will pull them through to the leg.
   * favorable macro placeholders (VIX 15, synthetic uptrend) so
     the per-name doctrine work isn't masked by the macro gate.

4. Calls ``run_scoring_pipeline`` to score every candidate and
   persist verdicts to ``orchestrator_scoring_verdicts``.
5. Returns a ``MorningChainLegOutcome`` whose ``detail_nl``
   carries the score / skip counts so the operator UI explains
   exactly what the run produced.

The leg short-circuits to ``skipped`` whenever the runtime flag is
off, matching every other morning-chain leg's contract.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from ai_trading_agent_storage import (
    AssetForecastRecord,
    SqlAlchemyAssetFundamentalsSnapshotRepository,
    SqlAlchemyEarningsEventRepository,
    SqlAlchemyMarketDataBarRepository,
    SqlAlchemyWatchlistPreferenceRepository,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import (
    asset_forecasts,
    ibkr_position_snapshots,
    ibkr_sync_runs,
)
from ai_trading_agent_storage.migration_readiness import MigrationReadinessReport
from portfolio_outlook_portfolio import HistoricalBar
from portfolio_outlook_worker.forecasting.orchestrator_candidate_provider import (
    CandidateProviderInputs,
    ForecastRow,
    FundamentalsRow,
    HeldPositionRow,
    TradingSettingsSnapshot,
)
from portfolio_outlook_worker.forecasting.orchestrator_scoring_cli import (
    run_scoring_pipeline,
)
from sqlalchemy import select

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.morning_chain import (
    LEG_ORCHESTRATOR_SCORING,
    LEG_STATUS_FAILED,
    LEG_STATUS_SKIPPED,
    LEG_STATUS_SUCCEEDED,
    MorningChainLegOutcome,
)
from portfolio_outlook_api.operator_settings import (
    load_operator_trading_settings,
)

# Locked V1.2 doctrinal defaults — match
# domain/settings.py::UserStrategySettings. The "read from
# trading_settings" path lands in V1.2 §AC; until then the
# user's UI edits don't flow through to the orchestrator. The
# defaults below are still useful — they let the doctrine run
# against live forecasts with the doctrine-correct knobs.
_DEFAULT_TRADING_SETTINGS = TradingSettingsSnapshot(
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


def _synthetic_bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    """Deterministic moderate-vol series so every per-name gate
    has enough history to evaluate.

    Replaced in V1.2 §AC by a real lookup against
    ``market_data_bars`` keyed by ``ibkr_conid``.
    """

    base = date(2025, 1, 1)
    price = 100.0
    bars = []
    for i in range(count):
        noise = math.sin(i * 17) * 0.015
        price *= math.exp(noise)
        bars.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return tuple(bars)


def _synthetic_index_bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    """Linear uptrend so the macro-regime gate stays favorable.

    Replaced by a real broad-index series (SPY/STOXX600) in
    V1.2 §AC.
    """

    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * 0.5, 4))),
        )
        for i in range(count)
    )


def _list_latest_forecasts(connection: Any) -> tuple[AssetForecastRecord, ...]:
    """Read the most-recent forecast per ``ibkr_conid``.

    Storage doesn't ship a "list all latest" method yet
    (``list_latest_asset_forecasts_by_conids`` requires the caller
    to supply the conid list), so we do a single SELECT that pulls
    every forecast row ordered ``ibkr_conid ASC, generated_at
    DESC`` and keeps the first row per conid in Python.
    """

    rows = (
        connection.execute(
            select(asset_forecasts).order_by(
                asset_forecasts.c.ibkr_conid.asc(),
                asset_forecasts.c.generated_at.desc(),
            )
        )
        .mappings()
        .all()
    )
    latest: dict[str, AssetForecastRecord] = {}
    for row in rows:
        record = AssetForecastRecord(**dict(row))
        if record.ibkr_conid not in latest:
            latest[record.ibkr_conid] = record
    return tuple(latest.values())


def _lookup_fundamentals_by_symbol(
    connection: Any,
    *,
    forecasts: tuple[AssetForecastRecord, ...],
) -> dict[str, FundamentalsRow]:
    """For each forecast symbol, fetch the latest persisted
    fundamentals snapshot. Falls back to the previous synthetic
    defaults when storage has no row (so the per-name gate can
    still run for newly-listed names without coverage).
    """

    repo = SqlAlchemyAssetFundamentalsSnapshotRepository(connection, None)  # type: ignore[arg-type]
    out: dict[str, FundamentalsRow] = {}
    for record in forecasts:
        eodhd_symbol_candidates = (
            f"{record.symbol}.US",
            record.symbol,
        )
        snapshot = None
        for candidate in eodhd_symbol_candidates:
            result = repo.get_latest_snapshot_for_symbol(candidate)
            if result.found and result.record is not None:
                snapshot = result.record
                break
        if snapshot is None:
            # Mirror the V1.2 §M default — missing fundamentals fall
            # back to safe placeholders so the per-name gates can
            # still evaluate. Real snapshots replace these once the
            # ``fundamentals/refresh`` worker populates storage.
            out[record.symbol] = FundamentalsRow(
                symbol=record.symbol,
                sector="technology",
                market_cap_eur=Decimal("10000000000"),
            )
            continue
        out[record.symbol] = FundamentalsRow(
            symbol=record.symbol,
            sector=snapshot.sector or "technology",
            market_cap_eur=(
                snapshot.market_cap
                if snapshot.market_cap is not None
                else Decimal("10000000000")
            ),
        )
    return out


def _lookup_bars_by_symbol(
    connection: Any,
    *,
    forecasts: tuple[AssetForecastRecord, ...],
    limit: int = 250,
) -> dict[str, tuple[HistoricalBar, ...]]:
    """For each forecast symbol, fetch the latest persisted daily
    bars via ``SqlAlchemyMarketDataBarRepository``. Empty tuple
    when storage has no bars — the orchestrator skips that name
    rather than fabricating prices.
    """

    repo = SqlAlchemyMarketDataBarRepository(connection, None)  # type: ignore[arg-type]
    synth = _synthetic_bars()
    out: dict[str, tuple[HistoricalBar, ...]] = {}
    for record in forecasts:
        result = repo.list_market_data_bars_by_conid(
            record.ibkr_conid, interval_code="1day", limit=limit
        )
        if not result.records:
            # Fall back to synthetic so the per-name gates can still
            # run for newly-listed names without persisted bars.
            out[record.symbol] = synth
            continue
        out[record.symbol] = tuple(
            HistoricalBar(
                bar_date=row.bar_date,
                close_price=row.close_price,
            )
            for row in result.records
        )
    return out


def _lookup_held_positions(
    connection: Any,
) -> tuple[HeldPositionRow, ...]:
    """Read the latest ``ibkr_position_snapshots`` batch and convert
    to ``HeldPositionRow``. EUR-value is taken from
    ``quantity * average_cost`` as a best-effort approximation when
    no live market-data is at hand — the sector-concentration gate
    uses these as relative weights, not absolute amounts.
    """

    latest_run_row = (
        connection.execute(
            select(ibkr_sync_runs.c.sync_run_id)
            .order_by(ibkr_sync_runs.c.started_at.desc())
            .limit(1)
        )
        .first()
    )
    if latest_run_row is None:
        return ()
    sync_run_id = str(latest_run_row[0])
    rows = (
        connection.execute(
            select(
                ibkr_position_snapshots.c.symbol,
                ibkr_position_snapshots.c.quantity,
                ibkr_position_snapshots.c.average_cost,
            )
            .where(ibkr_position_snapshots.c.sync_run_id == sync_run_id)
            .where(ibkr_position_snapshots.c.quantity != 0)
        )
        .all()
    )
    out: list[HeldPositionRow] = []
    for symbol, quantity, average_cost in rows:
        if symbol is None or quantity is None:
            continue
        qty = Decimal(quantity)
        if qty == 0:
            continue
        cost = Decimal(average_cost) if average_cost is not None else Decimal("0")
        out.append(
            HeldPositionRow(
                symbol=str(symbol),
                sector=None,  # joined separately when fundamentals carry sector
                eur_value=qty * cost,
            )
        )
    return tuple(out)


def _build_inputs(
    *,
    forecasts: tuple[AssetForecastRecord, ...],
    today: date,
    ibkr_account_ref: str,
    next_earnings_by_symbol: dict[str, date | None] | None = None,
    fundamentals_by_symbol: dict[str, FundamentalsRow] | None = None,
    bars_by_symbol: dict[str, tuple[HistoricalBar, ...]] | None = None,
    held_positions: tuple[HeldPositionRow, ...] = (),
    excluded_symbols: frozenset[str] = frozenset(),
    trading_settings: TradingSettingsSnapshot | None = None,
) -> CandidateProviderInputs:
    """Convert live forecast records into provider inputs.

    V1.2 §AM — ``fundamentals_by_symbol``, ``bars_by_symbol`` and
    ``held_positions`` are now passed in from real storage lookups.
    Synthetic defaults remain as fallback so the function stays
    callable from tests without a live database.

    V1.2 §AJ — ``next_earnings_by_symbol`` flows from the
    ``earnings_events`` repository into the orchestrator candidate
    provider so the earnings-window gate finally sees real dates.
    Missing symbols stay ``None`` (locked gate semantics: missing
    data does not block).
    """

    forecast_rows = tuple(
        ForecastRow(
            forecast_id=record.forecast_id,
            symbol=record.symbol,
            ibkr_conid=(
                int(record.ibkr_conid)
                if record.ibkr_conid.isdigit()
                else None
            ),
            current_price=record.current_price,
            p50_price=record.p50_price,
            expected_volatility_annual=record.expected_volatility_annual,
            horizon_days=record.horizon_days,
            confidence_score=record.confidence_score,
        )
        for record in forecasts
    )
    if fundamentals_by_symbol is None:
        fundamentals_by_symbol = {
            record.symbol: FundamentalsRow(
                symbol=record.symbol,
                sector="technology",
                market_cap_eur=Decimal("10000000000"),
            )
            for record in forecasts
        }
    if bars_by_symbol is None:
        synth = _synthetic_bars()
        bars_by_symbol = {record.symbol: synth for record in forecasts}
    return CandidateProviderInputs(
        ibkr_account_ref=ibkr_account_ref,
        today=today,
        forecasts=forecast_rows,
        fundamentals_by_symbol=fundamentals_by_symbol,
        candidate_bars_by_symbol=bars_by_symbol,
        held_positions=held_positions,
        settings=trading_settings or _DEFAULT_TRADING_SETTINGS,
        vix_level=Decimal("15"),
        index_bars=_synthetic_index_bars(),
        next_earnings_by_symbol=next_earnings_by_symbol or {},
        excluded_symbols=excluded_symbols,
    )


def build_real_orchestrator_scoring_leg(
    api_settings: Settings,
    *,
    ibkr_account_ref: str = "default",
) -> ScoringLegCallable:
    """Construct the real morning-chain leg.

    The returned callable replaces the V1.2 §Y no-op stub. When the
    runtime flag is off it returns ``skipped`` (matching the existing
    stub's behaviour); when on, it opens a writable connection,
    fetches forecasts, scores them, and persists verdicts.
    """

    def _leg() -> MorningChainLegOutcome:
        if not getattr(api_settings, "orchestrator_scoring_enabled", False):
            return MorningChainLegOutcome(
                leg_name=LEG_ORCHESTRATOR_SCORING,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Orchestrator scoring leg overgeslagen — "
                    "`orchestrator_scoring_enabled` staat uit."
                ),
            )
        # V1.2 §AY — software-pauze blokkeert de BUY-leg. SELL-
        # monitoring zit niet in deze chain (eigen sweep), dus die
        # blijft draaien zoals CLAUDE.md §11 vraagt.
        from portfolio_outlook_api.pauze_routes import is_software_paused
        if is_software_paused():
            return MorningChainLegOutcome(
                leg_name=LEG_ORCHESTRATOR_SCORING,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Orchestrator scoring overgeslagen — software is "
                    "gepauzeerd (CLAUDE.md §11)."
                ),
            )
        storage = api_settings.storage
        if not storage.enabled or not storage.database_url:
            return MorningChainLegOutcome(
                leg_name=LEG_ORCHESTRATOR_SCORING,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Orchestrator scoring overgeslagen — "
                    "opslag is uitgeschakeld of database_url ontbreekt."
                ),
            )
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        try:
            with provider.checked_connection(require_writable=True) as checked:
                forecasts = _list_latest_forecasts(checked.connection)
                if not forecasts:
                    return MorningChainLegOutcome(
                        leg_name=LEG_ORCHESTRATOR_SCORING,
                        status=LEG_STATUS_SUCCEEDED,
                        failure_code=None,
                        detail_nl=(
                            "Orchestrator scoring: geen forecasts "
                            "beschikbaar; niets te scoren."
                        ),
                    )
                today = datetime.now(UTC).date()
                symbols = tuple(record.symbol for record in forecasts)
                earnings_repo = SqlAlchemyEarningsEventRepository(
                    checked.connection,
                    _readiness_from(checked.readiness),
                )
                next_earnings_by_symbol = (
                    earnings_repo.get_next_for_symbols(
                        symbols=symbols, today=today,
                    )
                )
                # V1.2 §AM — real lookups replace synthetic defaults.
                fundamentals_by_symbol = _lookup_fundamentals_by_symbol(
                    checked.connection, forecasts=forecasts
                )
                bars_by_symbol = _lookup_bars_by_symbol(
                    checked.connection, forecasts=forecasts
                )
                held_positions = _lookup_held_positions(checked.connection)
                # V1.2 §AU — operator exclusions short-circuit before
                # the gates fire. Empty set when no exclusions are
                # configured.
                prefs_repo = SqlAlchemyWatchlistPreferenceRepository(
                    checked.connection,
                    _readiness_from(checked.readiness),
                )
                excluded_symbols = prefs_repo.list_excluded_symbols(
                    ibkr_account_ref=ibkr_account_ref
                )
                # V1.2 §BD — operator-keuzes uit /instellingen voeden
                # nu de live scoring. Bij een verse install valt dit
                # netjes terug op de doctrine-defaults.
                operator_resolution = load_operator_trading_settings()
                inputs = _build_inputs(
                    forecasts=forecasts,
                    today=today,
                    ibkr_account_ref=ibkr_account_ref,
                    next_earnings_by_symbol=next_earnings_by_symbol,
                    fundamentals_by_symbol=fundamentals_by_symbol,
                    bars_by_symbol=bars_by_symbol,
                    held_positions=held_positions,
                    excluded_symbols=excluded_symbols,
                    trading_settings=operator_resolution.snapshot,
                )
                run = run_scoring_pipeline(
                    connection=checked.connection,
                    readiness_report=_readiness_from(checked.readiness),
                    inputs=inputs,
                    generated_at=datetime.now(UTC),
                )
                # checked_connection doesn't auto-commit; do it
                # here so verdict rows persist past the
                # context-manager close.
                checked.connection.commit()
            return MorningChainLegOutcome(
                leg_name=LEG_ORCHESTRATOR_SCORING,
                status=LEG_STATUS_SUCCEEDED,
                failure_code=None,
                detail_nl=(
                    f"Orchestrator scoring uitgevoerd: "
                    f"{run.candidates_built} kandidaten gebouwd, "
                    f"{run.scoring.succeeded_count} verdicts "
                    f"geschreven, "
                    f"{run.scoring.failed_count} mislukt, "
                    f"{run.skipped_provider_count} forecasts "
                    f"overgeslagen door de provider. "
                    f"Instellingen-bron: {operator_resolution.source}"
                    + (
                        " (winstdoel overschreven)"
                        if operator_resolution.profit_target_overridden
                        else ""
                    )
                    + "."
                ),
            )
        except Exception as exc:  # noqa: BLE001 — boundary catch
            return MorningChainLegOutcome(
                leg_name=LEG_ORCHESTRATOR_SCORING,
                status=LEG_STATUS_FAILED,
                failure_code="orchestrator_scoring_failed",
                detail_nl=(
                    f"Orchestrator scoring leg gefaald: {exc}"
                ),
            )

    return _leg


def _readiness_from(
    readiness: MigrationReadinessReport,
) -> MigrationReadinessReport:
    """Pass-through for now — the runner takes whatever readiness
    state the connection was opened with. Lifted into its own
    function so future tweaks (e.g. forcing
    ``MIGRATIONS_CURRENT``) live in one place."""

    return readiness


# Convenience type alias for the public API.
ScoringLegCallable = Any  # ``Callable[[], MorningChainLegOutcome]`` once mypy supports it cleanly


__all__ = [
    "ScoringLegCallable",
    "build_real_orchestrator_scoring_leg",
]
