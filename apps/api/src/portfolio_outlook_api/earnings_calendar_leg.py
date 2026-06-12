"""Real (non-stub) earnings-calendar refresh leg for the morning
chain (V1.2 §AK).

Promotes the V1.2 §AJ stub in ``morning_chain.py`` to a leg that
actually fetches earnings from EODHD and upserts the
``earnings_events`` table. When the orchestrator-scoring leg fires
next, ``SqlAlchemyEarningsEventRepository.get_next_for_symbols``
returns real dates so the earnings-window gate finally bites.

Pipeline:

1. Open a writable storage connection.
2. Collect candidate symbols from the latest ``ibkr_position_snapshots``
   sync run. The watchlist module is in-memory in V1, so positions
   are the durable source of truth; watchlist refresh is a follow-up.
3. For each position symbol, ask
   :func:`map_ibkr_exchange_to_eodhd` for the EODHD suffix and skip
   any unsupported exchange so we don't burn quota on a malformed
   request.
4. Build an :class:`EodhdClient` with the configured API key.
5. Hand the list to :func:`refresh_earnings_calendar`; the helper
   already swallows provider errors and reports them in the
   summary so a transient EODHD outage doesn't fail the chain.

Doctrine constraints:

- Short-circuits to ``skipped`` whenever the runtime flag is off,
  storage is disabled, or the EODHD key is missing — mirrors every
  other leg's contract.
- Failure path returns ``failed`` with a stable failure code so the
  chain stops and the audit row carries an explanation.
- Read/write of ``earnings_events`` only; no broker pad, no order
  promotion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyEarningsEventRepository,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import (
    ibkr_position_snapshots,
    ibkr_sync_runs,
)
from ai_trading_agent_storage.migration_readiness import MigrationReadinessReport
from sqlalchemy import select

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.earnings_sync import (
    EarningsCalendarProvider,
    refresh_earnings_calendar,
)
from portfolio_outlook_api.eodhd_client import EodhdClient
from portfolio_outlook_api.market_data_sync import map_ibkr_exchange_to_eodhd
from portfolio_outlook_api.morning_chain import (
    LEG_EARNINGS_CALENDAR_SYNC,
    LEG_STATUS_FAILED,
    LEG_STATUS_SKIPPED,
    LEG_STATUS_SUCCEEDED,
    LegCallable,
    MorningChainLegOutcome,
)


def _readiness_from(readiness: Any) -> MigrationReadinessReport:
    # ``checked_connection`` already returns a real report; the cast
    # exists so mypy can see the static type through the ``Any``.
    return readiness  # type: ignore[no-any-return]


def _latest_sync_run_id(connection: Any) -> str | None:
    row = (
        connection.execute(
            select(ibkr_sync_runs.c.sync_run_id)
            .order_by(ibkr_sync_runs.c.started_at.desc())
            .limit(1)
        )
        .first()
    )
    if row is None:
        return None
    return str(row[0])


def _gather_eodhd_symbols(connection: Any) -> tuple[str, ...]:
    """Return de-duplicated EODHD-shaped symbols for the latest
    persisted position snapshot.

    Skips positions whose ``primary_exchange`` doesn't map to an
    EODHD suffix — that's the conservative default so we never
    issue a request EODHD can't answer.
    """

    sync_run_id = _latest_sync_run_id(connection)
    if sync_run_id is None:
        return ()
    rows = (
        connection.execute(
            select(
                ibkr_position_snapshots.c.symbol,
                ibkr_position_snapshots.c.primary_exchange,
                ibkr_position_snapshots.c.quantity,
            ).where(ibkr_position_snapshots.c.sync_run_id == sync_run_id)
        )
        .all()
    )
    seen: set[str] = set()
    out: list[str] = []
    for symbol, primary_exchange, quantity in rows:
        if symbol is None:
            continue
        # Skip closed positions — no point refreshing earnings for
        # a name we no longer hold.
        if quantity is None or quantity == 0:
            continue
        suffix = map_ibkr_exchange_to_eodhd(primary_exchange)
        if suffix is None:
            continue
        candidate = f"{symbol}.{suffix}"
        if candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
    return tuple(out)


def build_real_earnings_calendar_leg(
    api_settings: Settings,
    *,
    provider_factory: (
        type[EodhdClient] | None
    ) = None,
    window_days: int = 21,
) -> LegCallable:
    """Construct the real morning-chain earnings-calendar leg.

    ``provider_factory`` is exposed so tests inject a fake without
    touching the EODHD network or having to monkey-patch a global.
    Defaults to the real :class:`EodhdClient`.
    """

    factory: type[EodhdClient] | type[EarningsCalendarProvider] = (
        provider_factory if provider_factory is not None else EodhdClient
    )

    def _leg() -> MorningChainLegOutcome:
        if not getattr(api_settings, "earnings_calendar_sync_enabled", False):
            return MorningChainLegOutcome(
                leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Earnings-calendar refresh overgeslagen — "
                    "`earnings_calendar_sync_enabled` staat uit."
                ),
            )
        storage = api_settings.storage
        if not storage.enabled or not storage.database_url:
            return MorningChainLegOutcome(
                leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Earnings-calendar refresh overgeslagen — opslag is "
                    "uitgeschakeld of database_url ontbreekt."
                ),
            )
        api_key = getattr(api_settings, "eodhd_api_key", None)
        if not api_key:
            return MorningChainLegOutcome(
                leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                status=LEG_STATUS_SKIPPED,
                failure_code=None,
                detail_nl=(
                    "Earnings-calendar refresh overgeslagen — "
                    "EODHD api-key ontbreekt."
                ),
            )

        provider_conn = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        try:
            with provider_conn.checked_connection(require_writable=True) as checked:
                symbols = _gather_eodhd_symbols(checked.connection)
                if not symbols:
                    return MorningChainLegOutcome(
                        leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                        status=LEG_STATUS_SUCCEEDED,
                        failure_code=None,
                        detail_nl=(
                            "Earnings-calendar refresh: geen posities "
                            "met EODHD-symbol gevonden; niets te "
                            "verversen."
                        ),
                    )
                client: EarningsCalendarProvider = (
                    factory(api_key=api_key)
                    if factory is EodhdClient
                    else factory()  # type: ignore[call-arg]
                )
                repo = SqlAlchemyEarningsEventRepository(
                    checked.connection,
                    _readiness_from(checked.readiness),
                )
                now = datetime.now(tz=UTC)
                summary = refresh_earnings_calendar(
                    provider=client,
                    repository=repo,
                    symbols=symbols,
                    today=now.date(),
                    window_days=window_days,
                    source="eodhd",
                    fetched_at=now,
                )
                checked.connection.commit()
        except Exception as exc:  # noqa: BLE001 — boundary catch
            return MorningChainLegOutcome(
                leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                status=LEG_STATUS_FAILED,
                failure_code="earnings_calendar_sync_failed",
                detail_nl=(
                    f"Earnings-calendar refresh gefaald: {exc}"
                ),
            )

        if summary.error_text:
            return MorningChainLegOutcome(
                leg_name=LEG_EARNINGS_CALENDAR_SYNC,
                status=LEG_STATUS_FAILED,
                failure_code="earnings_calendar_provider_error",
                detail_nl=(
                    f"Earnings-calendar refresh — provider-fout: "
                    f"{summary.error_text} "
                    f"(symbolen aangevraagd: "
                    f"{summary.symbols_requested})."
                ),
            )

        return MorningChainLegOutcome(
            leg_name=LEG_EARNINGS_CALENDAR_SYNC,
            status=LEG_STATUS_SUCCEEDED,
            failure_code=None,
            detail_nl=(
                f"Earnings-calendar refresh uitgevoerd: "
                f"{summary.symbols_requested} symbolen aangevraagd, "
                f"{summary.fetched_count} events opgehaald, "
                f"{summary.upserted_count} weggeschreven."
            ),
        )

    return _leg


__all__ = ["build_real_earnings_calendar_leg"]
