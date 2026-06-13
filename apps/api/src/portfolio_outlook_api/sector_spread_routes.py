"""Sector-spread endpoint (V1.2 §AV / CLAUDE.md §7.3).

CLAUDE.md §7.3 turns the sector concentration into *information*
rather than a hard cap — the dashboard shows the operator's current
sector mix so they can decide whether to take a tech-heavy proposal
on top of an already tech-heavy portfolio.

We read the most-recent ``ibkr_position_snapshots`` batch and join
each row's symbol to the latest ``asset_fundamentals_snapshots`` row
for the sector field. Symbols without a fundamentals snapshot roll
into a single ``onbekend`` bucket so the operator immediately sees
how much of the portfolio is unclassified.

Approximate-EUR weighting:
* Quantity × average_cost in the position's local currency.
* No FX conversion is applied here — the doctrine surfaces sector
  *proportions*, not absolute EUR amounts, so a missing FX rate
  doesn't degrade the answer.

Read-only; never raises except on storage-unavailable (503).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from ai_trading_agent_storage import (
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import (
    asset_fundamentals_snapshots,
    ibkr_position_snapshots,
    ibkr_sync_runs,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class SectorRow(BaseModel):
    sector: str
    weight_pct: float
    notional_local_approx: str
    position_count: int


class SectorSpreadResponse(BaseModel):
    title_nl: str
    help_nl: str
    items: list[SectorRow]
    total_positions: int
    has_unclassified: bool


_HELP_NL = (
    "Sector-verdeling van de huidige portefeuille. CLAUDE.md §7.3 "
    "haalt de harde sector-cap weg — de software laat tech-zware "
    "suggesties door, maar je ziet hier direct waar je nu staat. "
    "Gewichten zijn benaderend: quantity × average_cost, zonder "
    "FX-conversie."
)


def _empty() -> SectorSpreadResponse:
    return SectorSpreadResponse(
        title_nl="Sector-verdeling",
        help_nl=_HELP_NL,
        items=[],
        total_positions=0,
        has_unclassified=False,
    )


def _latest_positions(connection: Connection) -> list[tuple[str, Decimal]]:
    """Return ``[(symbol, notional_local), ...]`` for the most recent
    position snapshot. notional_local = ``|quantity| * average_cost``,
    defaulting to ``Decimal(0)`` when either component is null.
    """

    latest_run = (
        connection.execute(
            select(ibkr_sync_runs.c.sync_run_id)
            .order_by(ibkr_sync_runs.c.started_at.desc())
            .limit(1)
        )
        .first()
    )
    if latest_run is None:
        return []
    sync_run_id = str(latest_run[0])
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
    out: list[tuple[str, Decimal]] = []
    for symbol, quantity, average_cost in rows:
        if symbol is None or quantity is None:
            continue
        qty = Decimal(quantity)
        if qty == 0:
            continue
        cost = Decimal(average_cost) if average_cost is not None else Decimal(0)
        out.append((str(symbol), abs(qty) * cost))
    return out


def _sectors_for_symbols(
    connection: Connection, symbols: list[str]
) -> dict[str, str | None]:
    """Return ``{symbol: sector_or_None}`` using the most recent
    fundamentals snapshot per symbol. Symbols with no snapshot get
    a ``None`` entry so the caller can roll them into ``onbekend``.
    """

    if not symbols:
        return {}
    rows = (
        connection.execute(
            select(
                asset_fundamentals_snapshots.c.symbol,
                asset_fundamentals_snapshots.c.sector,
                asset_fundamentals_snapshots.c.fetched_at,
            )
            .where(asset_fundamentals_snapshots.c.symbol.in_(symbols))
            .order_by(asset_fundamentals_snapshots.c.fetched_at.desc())
        )
        .all()
    )
    latest_per_symbol: dict[str, str | None] = {sym: None for sym in symbols}
    seen: set[str] = set()
    for symbol, sector, _fetched_at in rows:
        sym = str(symbol)
        if sym in seen:
            continue
        seen.add(sym)
        latest_per_symbol[sym] = sector
    return latest_per_symbol


@router.get("/portfolio/sector-spread", response_model=SectorSpreadResponse)
def get_sector_spread() -> SectorSpreadResponse:
    """Return current portfolio breakdown by sector, sorted by weight."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            positions = _latest_positions(checked.connection)
            symbols = [sym for sym, _ in positions]
            sector_map = _sectors_for_symbols(checked.connection, symbols)
    except StorageConnectionError as exc:
        logger.warning("sector-spread storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    if not positions:
        return _empty()

    # Aggregate notional + count per sector. Sector label is
    # lower-cased so "Technology" and "technology" don't double-count.
    @dataclass
    class _Bucket:
        label: str
        notional: Decimal
        count: int

    buckets: dict[str, _Bucket] = {}
    for symbol, notional in positions:
        raw_sector = sector_map.get(symbol)
        sector_label = (raw_sector or "").strip()
        key = sector_label.lower() if sector_label else "onbekend"
        bucket = buckets.setdefault(
            key,
            _Bucket(label=key, notional=Decimal(0), count=0),
        )
        bucket.notional += notional
        bucket.count += 1
        if sector_label and bucket.label == "onbekend":
            bucket.label = sector_label

    total = sum((bucket.notional for bucket in buckets.values()), Decimal(0))
    items: list[SectorRow] = []
    if total > 0:
        for bucket in buckets.values():
            weight_pct = float((bucket.notional / total) * Decimal(100))
            items.append(
                SectorRow(
                    sector=bucket.label,
                    weight_pct=round(weight_pct, 2),
                    notional_local_approx=str(
                        bucket.notional.quantize(Decimal("0.01"))
                    ),
                    position_count=bucket.count,
                )
            )
    items.sort(key=lambda r: r.weight_pct, reverse=True)
    return SectorSpreadResponse(
        title_nl="Sector-verdeling",
        help_nl=_HELP_NL,
        items=items,
        total_positions=sum(b.count for b in buckets.values()),
        has_unclassified=any(r.sector.lower() == "onbekend" for r in items),
    )


__all__ = ["router"]
