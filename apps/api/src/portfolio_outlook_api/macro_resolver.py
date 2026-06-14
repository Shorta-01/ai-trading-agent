"""Macro-regime data resolver (V1.2 §BE).

CLAUDE.md §7.2: de macro-gate moet de échte VIX + S&P-trend zien om
zinvol te zijn. Vóór deze module las de orchestrator-scoring-leg
``vix_level=Decimal("15")`` en een synthetische uptrend — de gate
zag dus altijd "rustig" en miste elke marktdaling. Niet veilig genoeg
voor een €1M trading-budget.

Deze resolver:

* Probeert de meest recente VIX-close uit ``macro_index_snapshots``.
* Probeert de laatste ~252 S&P-500 closes (genoeg voor de 200-day
  MA) als ``HistoricalBar`` reeks.
* Valt netjes terug op (None, synthetische uptrend) wanneer de
  feed niet geseed is — exact het gedrag dat de orchestrator vóór
  §BE had, zodat een verse install identiek werkt.

Pure storage-IO; geen netwerkcalls hier. Een aparte
``macro_feed_sync.py`` leg vult de tabel via EODHD.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    MACRO_SERIES_SPX,
    MACRO_SERIES_VIX,
    SqlAlchemyMacroIndexSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from portfolio_outlook_portfolio import HistoricalBar

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)


# Hoeveel bars de macro-regime gate wil zien voor de 50/200-day MA-
# crossover. We pakken een ruime buffer zodat een paar gemiste dagen
# (feestdagen, weekend) niet onmiddellijk onder de threshold duiken.
_SPX_BARS_LIMIT = 300


@dataclass(frozen=True)
class MacroDataResolution:
    """Resultaat van één macro-snapshot-lookup.

    De ``vix_source`` en ``index_source`` strings documenteren
    waar de waarden vandaan kwamen zodat de scoring-leg detail_nl
    kan loggen of de gate op echte data of op fallbacks draaide.
    """

    vix_level: Decimal | None
    index_bars: tuple[HistoricalBar, ...]
    vix_source: str
    index_source: str


def _synthetic_index_bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    """Backward-compat synthetic uptrend (zelfde reeks als de
    orchestrator vóór §BE gebruikte). Wordt alleen geretourneerd
    wanneer de feed leeg is — de gate kan dan toch evalueren in
    plaats van schop-tussen-de-benen te krijgen op een verse
    install."""

    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * 0.5, 4))),
        )
        for i in range(count)
    )


def resolve_macro_data(*, on_date: date | None = None) -> MacroDataResolution:
    """Lees de meest recente VIX + S&P-bars uit de macro-snapshot
    tabel.

    Wanneer storage uit staat, een tabel leeg is, of een lookup faalt,
    valt het netjes terug op (None / synthetic_uptrend) — bestaand
    gedrag blijft behouden voor verse installs zonder feed.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return MacroDataResolution(
            vix_level=None,
            index_bars=_synthetic_index_bars(),
            vix_source="storage-unavailable",
            index_source="synthetic-fallback",
        )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMacroIndexSnapshotRepository(
                checked.connection, checked.readiness
            )
            vix_record = repo.get_latest_value(
                series_code=MACRO_SERIES_VIX, on_or_before=on_date
            )
            spx_listing = repo.list_bars(
                series_code=MACRO_SERIES_SPX,
                to_date=on_date,
                limit=_SPX_BARS_LIMIT,
            )
    except StorageConnectionError as exc:
        logger.warning("macro-resolver storage error: %s", exc)
        return MacroDataResolution(
            vix_level=None,
            index_bars=_synthetic_index_bars(),
            vix_source="storage-error",
            index_source="synthetic-fallback",
        )

    vix_level = vix_record.close_value if vix_record is not None else None
    vix_source = "feed" if vix_record is not None else "missing"
    if spx_listing.records:
        index_bars = tuple(
            HistoricalBar(
                bar_date=row.bar_date,
                close_price=row.close_value,
            )
            for row in spx_listing.records
        )
        index_source = f"feed:{len(spx_listing.records)}-bars"
    else:
        index_bars = _synthetic_index_bars()
        index_source = "synthetic-fallback"
    return MacroDataResolution(
        vix_level=vix_level,
        index_bars=index_bars,
        vix_source=vix_source,
        index_source=index_source,
    )


__all__ = ["MacroDataResolution", "resolve_macro_data"]
