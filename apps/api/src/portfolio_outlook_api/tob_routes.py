"""Belgian TOB year-to-date endpoint (V1.2 §AH).

Surfaces the *realised* Belgische beurstaks for the current calendar
year by iterating over the persisted ``ibkr_executions`` rows and
applying the locked rate table from ``belgian_tax.compute_tob``.

This is the "indicative → realised" upgrade flagged in V1.2 §AG:
the morning dashboard widget no longer guesses from action-draft
estimates, it reads from the actual broker fills.

V1 universe-scope is US equities (``TobSecurityClass.STANDARD_STOCK``),
so every fill is classified as a standard stock at 0,35 %. When the
universe expands to ETFs / bonds, this module gains a join to
``asset_listings.asset_type`` and per-row classification — for now the
class is locked.

The endpoint reports per execution-currency totals so we never invent
an FX rate: if the operator traded both EUR and USD names, both totals
show up side-by-side. The UI surfaces them as "EUR X • USD Y" and lets
the operator see honest currency-split numbers.

Read-only; never raises except on storage-niet-beschikbaar (503).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import ibkr_executions
from fastapi import APIRouter, HTTPException
from portfolio_outlook_portfolio import TobSecurityClass, compute_tob
from pydantic import BaseModel
from sqlalchemy import select

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class TobYearToDateResponse(BaseModel):
    title_nl: str
    help_nl: str
    year: int
    executions_count: int
    by_currency: dict[str, str]
    by_security_class: dict[str, dict[str, str]]
    note_nl: str
    safe_for_orders: bool


_HELP_NL = (
    "Realised Belgische beurstaks (TOB) over de huidige "
    "kalenderjaar-fills uit ``ibkr_executions``. Per uitvoering wordt "
    "de TOB berekend met ``compute_tob`` (locked tariefcatalogus); "
    "totalen worden per fill-valuta gerapporteerd — er wordt geen "
    "wisselkoers verzonnen om alles in EUR samen te smelten."
)

_NOTE_LOCKED_STANDARD = (
    "V1-universe is US equities: alles wordt geclassificeerd als "
    "standard_stock (0,35 %). Bij uitbreiding naar ETFs of obligaties "
    "wordt classificatie per asset_listing toegevoegd."
)

_EMPTY_NOTE = (
    "Nog geen IBKR-fills geregistreerd in {year}. Realised TOB "
    "verschijnt hier zodra het syncen van executions begint."
)


def _empty_response(year: int) -> TobYearToDateResponse:
    return TobYearToDateResponse(
        title_nl=f"Belgische TOB {year} (realised)",
        help_nl=_HELP_NL,
        year=year,
        executions_count=0,
        by_currency={},
        by_security_class={},
        note_nl=_EMPTY_NOTE.format(year=year),
        safe_for_orders=False,
    )


def _resolve_year(year: int | None) -> int:
    if year is not None:
        return year
    return datetime.now(tz=UTC).year


@router.get("/tob/year-to-date", response_model=TobYearToDateResponse)
def get_tob_year_to_date(year: int | None = None) -> TobYearToDateResponse:
    """Return realised TOB for the given (or current) calendar year.

    Aggregates ``compute_tob(fill_price_local * fill_quantity,
    standard_stock)`` over every fill whose ``fill_time`` falls inside
    the calendar year. Both BUY and SELL count — TOB is owed on each
    leg of a round-trip.

    Per-currency totals are reported as decimal strings; the response
    never collapses them into a single EUR figure.
    """

    resolved_year = _resolve_year(year)
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(status_code=400, detail="year moet tussen 2000 en 2100 liggen")

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_response(resolved_year)

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            stmt = select(
                ibkr_executions.c.commission_currency,
                ibkr_executions.c.fill_price_local,
                ibkr_executions.c.fill_quantity,
                ibkr_executions.c.fill_time,
            )
            rows = checked.connection.execute(stmt).mappings().all()
    except StorageConnectionError as exc:
        logger.warning("tob-ytd storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    by_currency: dict[str, Decimal] = {}
    by_class_currency: dict[str, dict[str, Decimal]] = {}
    executions_count = 0
    locked_class = TobSecurityClass.STANDARD_STOCK
    locked_class_key = locked_class.value

    for row in rows:
        fill_time = row["fill_time"]
        if fill_time is None or fill_time.year != resolved_year:
            continue
        currency = (row["commission_currency"] or "").upper() or "UNKNOWN"
        price = row["fill_price_local"]
        quantity = row["fill_quantity"]
        if price is None or quantity is None:
            continue
        transaction_value = Decimal(price) * Decimal(quantity)
        if transaction_value <= 0:
            continue
        tob = compute_tob(
            transaction_value=transaction_value,
            security_class=locked_class,
        )
        by_currency[currency] = by_currency.get(currency, Decimal("0")) + tob
        cls_bucket = by_class_currency.setdefault(locked_class_key, {})
        cls_bucket[currency] = cls_bucket.get(currency, Decimal("0")) + tob
        executions_count += 1

    if executions_count == 0:
        return _empty_response(resolved_year)

    return TobYearToDateResponse(
        title_nl=f"Belgische TOB {resolved_year} (realised)",
        help_nl=_HELP_NL,
        year=resolved_year,
        executions_count=executions_count,
        by_currency={ccy: f"{amount:.2f}" for ccy, amount in by_currency.items()},
        by_security_class={
            cls: {ccy: f"{amount:.2f}" for ccy, amount in totals.items()}
            for cls, totals in by_class_currency.items()
        },
        note_nl=_NOTE_LOCKED_STANDARD,
        safe_for_orders=False,
    )


__all__ = ["router"]
