"""Belastingjaaroverzicht API (V1.2 §AW / CLAUDE.md §12).

Two endpoints:

* ``GET /belasting/jaaroverzicht?year=N`` returns the full report
  as JSON for the UI.
* ``GET /belasting/jaaroverzicht.csv?year=N`` returns the realised-
  trades table as CSV for the accountant.

PDF export is doctrine-required but lands in a follow-up: V1's
container does not ship a PDF library and the doctrine forbids
silently fabricating one at import time.

Read-only; storage failures bubble up as 503.
"""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    SqlAlchemyDividendEventRepository,
    SqlAlchemyFxRateRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import ibkr_executions
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.fx_conversion import FxConverter
from portfolio_outlook_api.profit_target import get_profit_target_pct
from portfolio_outlook_api.tax_report import (
    ExecutionRow,
    TaxYearReport,
    build_tax_year_report,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ----------------------------------------------------------------------
# Response models.
# ----------------------------------------------------------------------


class TaxRealisedTradeOut(BaseModel):
    symbol: str
    account_id: str
    currency_local: str
    quantity: str
    buy_date: str
    buy_price_local: str
    buy_exec_id: str
    sell_date: str
    sell_price_local: str
    sell_exec_id: str
    gross_local: str
    tob_buy_local: str
    tob_sell_local: str
    net_local: str
    hold_days: int
    net_pct_on_cost: str
    buy_action_draft_id: str | None
    sell_action_draft_id: str | None
    # V1.2 §BB — EUR-velden (None wanneer geen FX-koers gevonden).
    buy_fx_rate_eur: str | None = None
    sell_fx_rate_eur: str | None = None
    gross_eur: str | None = None
    tob_buy_eur: str | None = None
    tob_sell_eur: str | None = None
    net_eur: str | None = None


class TaxYearTotalsOut(BaseModel):
    trade_count: int
    gross_local_by_currency: dict[str, str]
    tob_local_by_currency: dict[str, str]
    net_local_by_currency: dict[str, str]
    average_hold_days: int
    hit_rate_pct: float
    earliest_close: str | None
    latest_close: str | None
    # V1.2 §BB — EUR-totalen.
    gross_eur_total: str | None = None
    tob_eur_total: str | None = None
    net_eur_total: str | None = None
    eur_conversion_coverage_pct: float = 0.0


class TaxMonthlyPointOut(BaseModel):
    month: str
    net_local_by_currency: dict[str, str]
    cumulative_net_local_by_currency: dict[str, str]


class TaxGoodHouseholderOut(BaseModel):
    trades_per_year: int
    average_hold_days: int
    trading_capital_share_pct: float | None
    uses_leverage: bool
    uses_shorts: bool
    summary_nl: str


class TaxYearReportResponse(BaseModel):
    title_nl: str
    help_nl: str
    year: int
    realised_trades: list[TaxRealisedTradeOut]
    year_totals: TaxYearTotalsOut
    monthly_points: list[TaxMonthlyPointOut]
    good_householder: TaxGoodHouseholderOut
    dividends: list[dict[str, object]]
    fx_conversion_available: bool
    notes_nl: list[str]


_HELP_NL = (
    "Belastingjaaroverzicht — alles wat je accountant nodig heeft "
    "voor je aangifte. Gerealiseerde kapitaalwinsten zijn FIFO-"
    "gematched op (account, symbol). Belgische TOB op beide kanten "
    "is meegerekend. Bedragen staan in lokale munt — EUR-conversie "
    "vraagt een dagkoers-bestand dat V1 nog niet bijhoudt."
)


def _resolve_year(year: int | None) -> int:
    if year is not None:
        return year
    return datetime.now(tz=UTC).year


def _empty_report(year: int) -> TaxYearReport:
    return build_tax_year_report(year=year, executions=())


def _to_response(report: TaxYearReport) -> TaxYearReportResponse:
    return TaxYearReportResponse(
        title_nl=f"Belastingoverzicht {report.year}",
        help_nl=_HELP_NL,
        year=report.year,
        realised_trades=[
            TaxRealisedTradeOut(
                symbol=t.symbol,
                account_id=t.account_id,
                currency_local=t.currency_local,
                quantity=str(t.quantity),
                buy_date=t.buy_date.isoformat(),
                buy_price_local=str(t.buy_price_local),
                buy_exec_id=t.buy_exec_id,
                sell_date=t.sell_date.isoformat(),
                sell_price_local=str(t.sell_price_local),
                sell_exec_id=t.sell_exec_id,
                gross_local=str(t.gross_local),
                tob_buy_local=str(t.tob_buy_local),
                tob_sell_local=str(t.tob_sell_local),
                net_local=str(t.net_local),
                hold_days=t.hold_days,
                net_pct_on_cost=str(t.net_pct_on_cost),
                buy_action_draft_id=t.buy_action_draft_id,
                sell_action_draft_id=t.sell_action_draft_id,
                buy_fx_rate_eur=(
                    str(t.buy_fx_rate_eur) if t.buy_fx_rate_eur else None
                ),
                sell_fx_rate_eur=(
                    str(t.sell_fx_rate_eur) if t.sell_fx_rate_eur else None
                ),
                gross_eur=str(t.gross_eur) if t.gross_eur is not None else None,
                tob_buy_eur=str(t.tob_buy_eur) if t.tob_buy_eur else None,
                tob_sell_eur=str(t.tob_sell_eur) if t.tob_sell_eur else None,
                net_eur=str(t.net_eur) if t.net_eur is not None else None,
            )
            for t in report.realised_trades
        ],
        year_totals=TaxYearTotalsOut(
            trade_count=report.year_totals.trade_count,
            gross_local_by_currency=report.year_totals.gross_local_by_currency,
            tob_local_by_currency=report.year_totals.tob_local_by_currency,
            net_local_by_currency=report.year_totals.net_local_by_currency,
            average_hold_days=report.year_totals.average_hold_days,
            hit_rate_pct=report.year_totals.hit_rate_pct,
            earliest_close=report.year_totals.earliest_close,
            latest_close=report.year_totals.latest_close,
            gross_eur_total=report.year_totals.gross_eur_total,
            tob_eur_total=report.year_totals.tob_eur_total,
            net_eur_total=report.year_totals.net_eur_total,
            eur_conversion_coverage_pct=(
                report.year_totals.eur_conversion_coverage_pct
            ),
        ),
        monthly_points=[
            TaxMonthlyPointOut(
                month=p.month,
                net_local_by_currency=p.net_local_by_currency,
                cumulative_net_local_by_currency=(
                    p.cumulative_net_local_by_currency
                ),
            )
            for p in report.monthly_points
        ],
        good_householder=TaxGoodHouseholderOut(
            trades_per_year=report.good_householder.trades_per_year,
            average_hold_days=report.good_householder.average_hold_days,
            trading_capital_share_pct=(
                report.good_householder.trading_capital_share_pct
            ),
            uses_leverage=report.good_householder.uses_leverage,
            uses_shorts=report.good_householder.uses_shorts,
            summary_nl=report.good_householder.summary_nl,
        ),
        dividends=list(report.dividends),
        fx_conversion_available=report.fx_conversion_available,
        notes_nl=list(report.notes_nl),
    )


def _fetch_dividends(year: int) -> list[dict[str, object]]:
    """Return manually-tracked dividenden voor dit jaar als plain
    dicts zodat de tax_report engine puur op data werkt."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return []
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyDividendEventRepository(
                checked.connection, checked.readiness
            )
            listed = repo.list_for_account(
                ibkr_account_ref="default", year=year
            )
    except StorageConnectionError as exc:
        logger.warning("belasting dividend lookup error: %s", exc)
        return []
    return [
        {
            "dividend_event_id": r.dividend_event_id,
            "symbol": r.symbol,
            "isin": r.isin,
            "pay_date": r.pay_date.isoformat(),
            "currency_local": r.currency_local,
            "gross_local": str(r.gross_local),
            "withholding_pct": str(r.withholding_pct),
            "withholding_local": str(r.withholding_local),
            "net_local": str(r.net_local),
            "country_code": r.country_code,
            "note": r.note,
        }
        for r in listed.records
    ]


def _open_fx_converter() -> tuple[FxConverter | None, "Callable[[], None]"]:
    """Return a (converter, close_callback) tuple, or (None, noop).

    De caller moet de close-callback aanroepen na het rapport-build
    zodat de storage-connection vrijkomt.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return None, (lambda: None)
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        ctx = provider.checked_connection(require_writable=False)
        checked = ctx.__enter__()
        repo = SqlAlchemyFxRateRepository(checked.connection, checked.readiness)
        converter = FxConverter(repo)

        def _close() -> None:
            ctx.__exit__(None, None, None)

        return converter, _close
    except StorageConnectionError as exc:
        logger.warning("FX converter open failed: %s", exc)
        return None, (lambda: None)


def _fetch_executions(year: int) -> list[ExecutionRow]:
    """Read every execution from storage. We fetch the full table
    (not just the year) so FIFO matching works for sells that close
    out lots opened in prior years."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return []
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            stmt = select(
                ibkr_executions.c.ibkr_exec_id,
                ibkr_executions.c.account_id,
                ibkr_executions.c.conid,
                ibkr_executions.c.side,
                ibkr_executions.c.fill_price_local,
                ibkr_executions.c.fill_quantity,
                ibkr_executions.c.fill_time,
                ibkr_executions.c.commission,
                ibkr_executions.c.commission_currency,
                ibkr_executions.c.action_draft_id,
            )
            rows = checked.connection.execute(stmt).mappings().all()
    except StorageConnectionError as exc:
        logger.warning("belasting fetch storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    out: list[ExecutionRow] = []
    for row in rows:
        fill_time = row["fill_time"]
        if fill_time is None or fill_time.year > year:
            # SELL fills *after* the requested year don't belong in
            # this year's report. BUYs from any prior year are kept
            # so FIFO can match them.
            continue
        out.append(
            ExecutionRow(
                ibkr_exec_id=str(row["ibkr_exec_id"]),
                account_id=str(row["account_id"]),
                # ``conid`` is the broker-side identifier; the UI
                # benefits more from the ticker, but the ticker isn't
                # in this table. The downstream renderer will join to
                # asset master records to surface a friendly label;
                # for now we surface the conid as ``symbol`` so the
                # FIFO grouping still works correctly per instrument.
                symbol=str(row["conid"]),
                side=str(row["side"]),
                fill_price_local=Decimal(row["fill_price_local"]),
                fill_quantity=Decimal(row["fill_quantity"]),
                fill_time=fill_time,
                commission=Decimal(row["commission"]),
                commission_currency=str(row["commission_currency"]),
                action_draft_id=(
                    str(row["action_draft_id"])
                    if row["action_draft_id"] is not None
                    else None
                ),
            )
        )
    return out


# ----------------------------------------------------------------------
# Routes.
# ----------------------------------------------------------------------


@router.get(
    "/belasting/jaaroverzicht",
    response_model=TaxYearReportResponse,
)
def get_jaaroverzicht(year: int | None = None) -> TaxYearReportResponse:
    resolved_year = _resolve_year(year)
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _to_response(_empty_report(resolved_year))

    executions = _fetch_executions(resolved_year)
    converter, close_converter = _open_fx_converter()
    try:
        report = build_tax_year_report(
            year=resolved_year,
            executions=executions,
            profit_target_pct=get_profit_target_pct(),
            dividends=_fetch_dividends(resolved_year),
            fx_converter=converter,
        )
    finally:
        close_converter()
    return _to_response(report)


@router.get("/belasting/jaaroverzicht.csv")
def get_jaaroverzicht_csv(year: int | None = None) -> Response:
    resolved_year = _resolve_year(year)
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        report = _empty_report(resolved_year)
    else:
        executions = _fetch_executions(resolved_year)
        converter, close_converter = _open_fx_converter()
        try:
            report = build_tax_year_report(
                year=resolved_year,
                executions=executions,
                profit_target_pct=get_profit_target_pct(),
                dividends=_fetch_dividends(resolved_year),
                fx_converter=converter,
            )
        finally:
            close_converter()

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "symbol",
            "account",
            "valuta",
            "aantal",
            "aankoop_datum",
            "aankoop_prijs",
            "aankoop_exec_id",
            "verkoop_datum",
            "verkoop_prijs",
            "verkoop_exec_id",
            "bruto",
            "tob_aankoop",
            "tob_verkoop",
            "netto",
            "hold_dagen",
            "netto_pct_op_kost",
        ]
    )
    for t in report.realised_trades:
        writer.writerow(
            [
                t.symbol,
                t.account_id,
                t.currency_local,
                str(t.quantity),
                t.buy_date.isoformat(),
                str(t.buy_price_local),
                t.buy_exec_id,
                t.sell_date.isoformat(),
                str(t.sell_price_local),
                t.sell_exec_id,
                str(t.gross_local),
                str(t.tob_buy_local),
                str(t.tob_sell_local),
                str(t.net_local),
                t.hold_days,
                str(t.net_pct_on_cost),
            ]
        )
    body = buffer.getvalue()
    filename = f"belasting-{resolved_year}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


__all__ = ["router"]
