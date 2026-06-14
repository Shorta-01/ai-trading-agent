"""Belgian tax-year overview engine (V1.2 §AW / CLAUDE.md §12).

The /belasting page needs a full breakdown of one tax year for the
operator's accountant. This module is the pure-Python core that
takes ``ibkr_executions`` rows and produces:

* Realised capital gains using FIFO lot matching per (account,
  symbol). Each closed-out lot becomes one ``RealisedTradeRow`` with
  buy/sell sides, Belgian TOB on both legs, and net result.
* Year totals (gross, TOB total, net, trade count, average hold,
  hit-rate at the +4 % doctrine target).
* Monthly cumulative net so the UI can draw a simple line graph.
* "Goed huisvader"-style metrics that the doctrine surfaces as
  evidence the operator is not day-trading.

Out of scope for V1 (CLAUDE.md §16 grouping):
* FX-to-EUR conversion using the historical day's rate — the system
  does not yet persist a daily FX history we can join against. The
  rows report local-currency amounts and a "FX conversion = niet
  beschikbaar" flag so the accountant has full transparency.
* Dividend tracking — depends on a dividend feed that V1 does not
  yet ingest. The module exposes an empty list there so the UI can
  still render the section.

Pure functions, no I/O. The API layer fetches rows and passes them
in.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from portfolio_outlook_portfolio import TobSecurityClass, compute_tob

# Doctrine target — CLAUDE.md §6.1: +4% gross per trade. The hit-
# rate metric counts closed lots that hit at least this net-of-TOB
# percentage gain on the local-currency cost basis.
HIT_RATE_TARGET_PCT = Decimal("4")
TOB_ROUND_TRIP_PCT = Decimal("0.70")
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class ExecutionRow:
    """A raw IBKR execution row, scoped to the columns the report uses."""

    ibkr_exec_id: str
    account_id: str
    symbol: str
    side: str  # "BUY" | "SELL"
    fill_price_local: Decimal
    fill_quantity: Decimal
    fill_time: datetime
    commission: Decimal
    commission_currency: str
    action_draft_id: str | None
    security_class: TobSecurityClass = TobSecurityClass.STANDARD_STOCK


@dataclass(frozen=True)
class RealisedTradeRow:
    """One FIFO-matched closed lot.

    Money values are local-currency; EUR conversion is a follow-up
    that needs historical FX data.
    """

    symbol: str
    account_id: str
    currency_local: str
    quantity: Decimal
    buy_date: date
    buy_price_local: Decimal
    buy_exec_id: str
    sell_date: date
    sell_price_local: Decimal
    sell_exec_id: str
    gross_local: Decimal
    tob_buy_local: Decimal
    tob_sell_local: Decimal
    net_local: Decimal
    hold_days: int
    net_pct_on_cost: Decimal
    # The pair of action_draft_ids — useful for the audit pane.
    buy_action_draft_id: str | None
    sell_action_draft_id: str | None


@dataclass(frozen=True)
class YearTotals:
    trade_count: int
    gross_local_by_currency: dict[str, str]
    tob_local_by_currency: dict[str, str]
    net_local_by_currency: dict[str, str]
    average_hold_days: int
    hit_rate_pct: float
    earliest_close: str | None
    latest_close: str | None


@dataclass(frozen=True)
class MonthlyPoint:
    month: str  # "YYYY-MM"
    net_local_by_currency: dict[str, str]
    cumulative_net_local_by_currency: dict[str, str]


@dataclass(frozen=True)
class GoodHouseholderMetrics:
    """CLAUDE.md §12 "goed huisvader"-bewijs.

    Trades-per-year + average hold days + leverage flag is the
    doctrine's evidence package that the operator is investing, not
    day-trading. The accountant can include this verbatim in the
    aangifte commentary.
    """

    trades_per_year: int
    average_hold_days: int
    trading_capital_share_pct: float | None
    uses_leverage: bool
    uses_shorts: bool
    summary_nl: str


@dataclass(frozen=True)
class TaxYearReport:
    year: int
    realised_trades: tuple[RealisedTradeRow, ...]
    year_totals: YearTotals
    monthly_points: tuple[MonthlyPoint, ...]
    good_householder: GoodHouseholderMetrics
    dividends: tuple[dict[str, object], ...] = field(default_factory=tuple)
    fx_conversion_available: bool = False
    notes_nl: tuple[str, ...] = field(default_factory=tuple)


def _quant2(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass
class _BuyLot:
    exec_id: str
    quantity: Decimal
    price: Decimal
    fill_time: datetime
    commission_currency: str
    action_draft_id: str | None
    security_class: TobSecurityClass


def _match_trades(
    executions: Sequence[ExecutionRow],
) -> list[RealisedTradeRow]:
    """FIFO match BUYs against SELLs per (account, symbol)."""

    # Group by (account, symbol) and sort each group by fill_time.
    groups: dict[tuple[str, str], list[ExecutionRow]] = defaultdict(list)
    for ex in executions:
        groups[(ex.account_id, ex.symbol)].append(ex)
    out: list[RealisedTradeRow] = []
    for (account_id, symbol), rows in groups.items():
        rows_sorted = sorted(rows, key=lambda r: r.fill_time)
        buy_queue: deque[_BuyLot] = deque()
        for ex in rows_sorted:
            if ex.side == "BUY":
                buy_queue.append(
                    _BuyLot(
                        exec_id=ex.ibkr_exec_id,
                        quantity=ex.fill_quantity,
                        price=ex.fill_price_local,
                        fill_time=ex.fill_time,
                        commission_currency=ex.commission_currency,
                        action_draft_id=ex.action_draft_id,
                        security_class=ex.security_class,
                    )
                )
                continue
            # SELL path: match against oldest BUY lots first.
            sell_qty_remaining = ex.fill_quantity
            while sell_qty_remaining > 0 and buy_queue:
                lot = buy_queue[0]
                matched = min(sell_qty_remaining, lot.quantity)
                gross = matched * (ex.fill_price_local - lot.price)
                buy_notional = matched * lot.price
                sell_notional = matched * ex.fill_price_local
                tob_buy = compute_tob(
                    transaction_value=buy_notional,
                    security_class=lot.security_class,
                )
                tob_sell = compute_tob(
                    transaction_value=sell_notional,
                    security_class=ex.security_class,
                )
                net = gross - tob_buy - tob_sell
                hold_days = max(
                    0, (ex.fill_time.date() - lot.fill_time.date()).days
                )
                cost_basis = buy_notional
                net_pct = (
                    (net / cost_basis * Decimal(100)).quantize(_CENT)
                    if cost_basis > 0
                    else Decimal(0)
                )
                out.append(
                    RealisedTradeRow(
                        symbol=symbol,
                        account_id=account_id,
                        currency_local=ex.commission_currency,
                        quantity=matched,
                        buy_date=lot.fill_time.date(),
                        buy_price_local=lot.price,
                        buy_exec_id=lot.exec_id,
                        sell_date=ex.fill_time.date(),
                        sell_price_local=ex.fill_price_local,
                        sell_exec_id=ex.ibkr_exec_id,
                        gross_local=_quant2(gross),
                        tob_buy_local=_quant2(tob_buy),
                        tob_sell_local=_quant2(tob_sell),
                        net_local=_quant2(net),
                        hold_days=hold_days,
                        net_pct_on_cost=net_pct,
                        buy_action_draft_id=lot.action_draft_id,
                        sell_action_draft_id=ex.action_draft_id,
                    )
                )
                # Reduce the BUY lot — if fully consumed, drop it.
                if matched >= lot.quantity:
                    buy_queue.popleft()
                else:
                    buy_queue[0] = _BuyLot(
                        exec_id=lot.exec_id,
                        quantity=lot.quantity - matched,
                        price=lot.price,
                        fill_time=lot.fill_time,
                        commission_currency=lot.commission_currency,
                        action_draft_id=lot.action_draft_id,
                        security_class=lot.security_class,
                    )
                sell_qty_remaining -= matched
            # If buy_queue is exhausted before sell is filled, the
            # operator sold short — V1 paper doctrine forbids that, so
            # ignore the leftover (an audit upstream will surface it).
    # Stable order: sell date asc.
    out.sort(key=lambda r: (r.sell_date, r.symbol))
    return out


def _aggregate_year(
    trades: Sequence[RealisedTradeRow],
    *,
    hit_target_pct: Decimal = HIT_RATE_TARGET_PCT,
) -> YearTotals:
    by_currency: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"gross": Decimal(0), "tob": Decimal(0), "net": Decimal(0)}
    )
    hit = 0
    total_hold = 0
    earliest: date | None = None
    latest: date | None = None
    for trade in trades:
        bucket = by_currency[trade.currency_local]
        bucket["gross"] += trade.gross_local
        bucket["tob"] += trade.tob_buy_local + trade.tob_sell_local
        bucket["net"] += trade.net_local
        if trade.net_pct_on_cost >= hit_target_pct:
            hit += 1
        total_hold += trade.hold_days
        if earliest is None or trade.sell_date < earliest:
            earliest = trade.sell_date
        if latest is None or trade.sell_date > latest:
            latest = trade.sell_date
    trade_count = len(trades)
    average_hold = int(total_hold / trade_count) if trade_count else 0
    hit_rate = (
        round(hit / trade_count * 100, 1) if trade_count else 0.0
    )
    return YearTotals(
        trade_count=trade_count,
        gross_local_by_currency={
            ccy: f"{_quant2(v['gross'])}" for ccy, v in by_currency.items()
        },
        tob_local_by_currency={
            ccy: f"{_quant2(v['tob'])}" for ccy, v in by_currency.items()
        },
        net_local_by_currency={
            ccy: f"{_quant2(v['net'])}" for ccy, v in by_currency.items()
        },
        average_hold_days=average_hold,
        hit_rate_pct=hit_rate,
        earliest_close=earliest.isoformat() if earliest else None,
        latest_close=latest.isoformat() if latest else None,
    )


def _monthly_breakdown(
    year: int,
    trades: Sequence[RealisedTradeRow],
) -> list[MonthlyPoint]:
    """One point per month in the year, with running cumulative."""

    per_month: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal(0))
    )
    for trade in trades:
        if trade.sell_date.year != year:
            continue
        per_month[trade.sell_date.month][trade.currency_local] += trade.net_local

    points: list[MonthlyPoint] = []
    cumulative: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for month_num in range(1, 13):
        monthly = per_month.get(month_num, {})
        for ccy, amount in monthly.items():
            cumulative[ccy] += amount
        points.append(
            MonthlyPoint(
                month=f"{year:04d}-{month_num:02d}",
                net_local_by_currency={
                    ccy: f"{_quant2(amount)}" for ccy, amount in monthly.items()
                },
                cumulative_net_local_by_currency={
                    ccy: f"{_quant2(amount)}" for ccy, amount in cumulative.items()
                },
            )
        )
    return points


def _good_householder_metrics(
    trades: Sequence[RealisedTradeRow],
    *,
    trading_capital_eur: Decimal | None,
    total_wealth_eur: Decimal | None,
) -> GoodHouseholderMetrics:
    """Compose the §12 evidence package.

    The leverage / shorts flags are always False under the doctrine
    (paper-only, no margin, no shorting); the explicit booleans are
    here so the audit-trail surfaces "the software refused leverage"
    rather than the accountant having to read the absence as proof.
    """

    trade_count = len(trades)
    average_hold = (
        int(sum(t.hold_days for t in trades) / trade_count)
        if trade_count
        else 0
    )
    share: float | None = None
    if (
        trading_capital_eur is not None
        and total_wealth_eur is not None
        and total_wealth_eur > 0
    ):
        share = round(
            float(trading_capital_eur / total_wealth_eur * Decimal(100)), 1
        )
    bits: list[str] = [
        f"{trade_count} trade{'s' if trade_count != 1 else ''} per jaar",
        f"gemiddelde hold {average_hold} dagen",
        "geen hefboom",
        "geen short-posities",
    ]
    if share is not None:
        bits.insert(
            2, f"trading-kapitaal {share}% van totaal vermogen"
        )
    summary = ", ".join(bits) + "."
    return GoodHouseholderMetrics(
        trades_per_year=trade_count,
        average_hold_days=average_hold,
        trading_capital_share_pct=share,
        uses_leverage=False,
        uses_shorts=False,
        summary_nl=summary,
    )


def build_tax_year_report(
    *,
    year: int,
    executions: Sequence[ExecutionRow],
    trading_capital_eur: Decimal | None = None,
    total_wealth_eur: Decimal | None = None,
    fx_conversion_available: bool = False,
    profit_target_pct: Decimal = HIT_RATE_TARGET_PCT,
) -> TaxYearReport:
    """End-to-end report builder. Pure function — call from the API
    layer after fetching rows."""

    # Include cross-year BUYs so a sell in ``year`` can match a buy
    # from a previous year. Filter trades to those that *closed* in
    # ``year`` post-match.
    matched = _match_trades(executions)
    in_year = tuple(t for t in matched if t.sell_date.year == year)
    totals = _aggregate_year(in_year, hit_target_pct=profit_target_pct)
    monthly = _monthly_breakdown(year, in_year)
    householder = _good_householder_metrics(
        in_year,
        trading_capital_eur=trading_capital_eur,
        total_wealth_eur=total_wealth_eur,
    )
    notes: list[str] = []
    if not fx_conversion_available:
        notes.append(
            "EUR-conversie nog niet beschikbaar — bedragen zijn in "
            "lokale munt. De accountant past zelf de FX-koers van de "
            "transactiedag toe."
        )
    notes.append(
        "Dividenden zijn nog niet opgenomen — V1 heeft geen "
        "dividend-feed; opvolgsessie voegt dit toe."
    )
    return TaxYearReport(
        year=year,
        realised_trades=in_year,
        year_totals=totals,
        monthly_points=tuple(monthly),
        good_householder=householder,
        dividends=(),
        fx_conversion_available=fx_conversion_available,
        notes_nl=tuple(notes),
    )


__all__ = [
    "ExecutionRow",
    "RealisedTradeRow",
    "YearTotals",
    "MonthlyPoint",
    "GoodHouseholderMetrics",
    "TaxYearReport",
    "build_tax_year_report",
    "HIT_RATE_TARGET_PCT",
    "TOB_ROUND_TRIP_PCT",
]
