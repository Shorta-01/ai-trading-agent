"""Maandelijks rapport-engine (V1.2 §AX / CLAUDE.md §13).

De /rapporten pagina vraagt om een live maandoverzicht met:

* Executive summary — netto winst van de maand, vergelijking met de
  termijnrekening-baseline van CLAUDE.md §1, één regel takeaway.
* Maand-activiteit — counts van voorgestelde / goedgekeurde /
  verzonden action drafts en orchestrator-verdicts (suggest / skip).
* Income — capital gains + TOB voor de maand, plus cumulatief
  jaartotaal.
* Software-prestatie — hit-rate +4% en gemiddelde hold-tijd over de
  maand-trades.
* Open posities-snapshot — gewoon de huidige stand zoals de
  dashboard die toont; voor dit rapport leveren we alleen een
  position-count omdat een live snapshot in de live web-pagina al
  beschikbaar is.

Geen IO — pure functies. Caller fetcht data en injecteert.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from portfolio_outlook_api.tax_report import (
    ExecutionRow,
    RealisedTradeRow,
    _match_trades,
)

# CLAUDE.md §1 baseline. Op €50k zou de termijnrekening (2,5 %)
# ongeveer €104/maand netto opleveren — niet de €1.458 in een ouder
# concept; dat veronderstelde een veel hogere termijnrekening. Voor
# transparantie nemen we de actuele €50k-baseline van 2,5 % per jaar /
# 12 maanden.
DEFAULT_BASELINE_MONTHLY_EUR = Decimal("104")


@dataclass(frozen=True)
class ActionDraftActivityRow:
    """Per-status counts in the requested month."""

    proposed: int
    user_approved: int
    submitted: int
    filled: int
    dismissed: int


@dataclass(frozen=True)
class VerdictActivity:
    total: int
    by_decision: dict[str, int]


@dataclass(frozen=True)
class ExecutiveSummary:
    headline_nl: str
    net_local_by_currency: dict[str, str]
    vs_baseline_eur: str | None
    trade_count: int
    hit_rate_pct: float


@dataclass(frozen=True)
class IncomeBreakdown:
    capital_gains_local_by_currency: dict[str, str]
    tob_local_by_currency: dict[str, str]
    net_local_by_currency: dict[str, str]
    ytd_net_local_by_currency: dict[str, str]


@dataclass(frozen=True)
class SoftwarePerformance:
    hit_rate_pct: float
    average_hold_days: int
    confidence_distribution_pct: dict[str, float]
    proposals_vs_approved: tuple[int, int]


@dataclass(frozen=True)
class MonthlyReport:
    year: int
    month: int
    executive_summary: ExecutiveSummary
    open_positions_count: int
    action_draft_activity: ActionDraftActivityRow
    verdict_activity: VerdictActivity
    income: IncomeBreakdown
    software_performance: SoftwarePerformance
    realised_trades: tuple[RealisedTradeRow, ...]
    notes_nl: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ActionDraftSnapshot:
    """Subset of the ``action_drafts`` row needed for the activity tally.

    The created_at / user_approved_at / submission_started_at /
    terminal_state_at columns let us bucket per status without
    re-reading the events table.
    """

    action_draft_id: str
    status: str
    created_at: datetime
    user_approved_at: datetime | None
    submission_started_at: datetime | None
    terminal_state_at: datetime | None
    dismissed_at: datetime | None


@dataclass(frozen=True)
class VerdictSnapshot:
    """Subset of ``orchestrator_scoring_verdicts``."""

    decision: str
    generated_at: datetime
    confidence_score_pct: float | None


def _within_month(value: datetime | None, year: int, month: int) -> bool:
    if value is None:
        return False
    return value.year == year and value.month == month


def _confidence_bucket(pct: float | None) -> str:
    if pct is None:
        return "onbekend"
    if pct >= 90:
        return ">=90%"
    if pct >= 80:
        return "80-90%"
    if pct >= 70:
        return "70-80%"
    if pct >= 60:
        return "60-70%"
    return "<60%"


def _format_currency_dict(d: dict[str, Decimal]) -> dict[str, str]:
    return {ccy: f"{value:.2f}" for ccy, value in d.items()}


def _baseline_comparison_text(
    *,
    net_eur: Decimal | None,
    baseline_eur: Decimal,
) -> str | None:
    if net_eur is None:
        return None
    diff = net_eur - baseline_eur
    if diff >= 0:
        return (
            f"€{diff:.0f} bovenop de termijnrekening-baseline "
            f"(€{baseline_eur:.0f}/maand)."
        )
    return (
        f"€{(-diff):.0f} onder de termijnrekening-baseline "
        f"(€{baseline_eur:.0f}/maand)."
    )


def build_monthly_report(
    *,
    year: int,
    month: int,
    executions: Sequence[ExecutionRow],
    action_drafts: Sequence[ActionDraftSnapshot],
    verdicts: Sequence[VerdictSnapshot],
    open_positions_count: int,
    baseline_monthly_eur: Decimal = DEFAULT_BASELINE_MONTHLY_EUR,
    profit_target_pct: Decimal = Decimal("4"),
) -> MonthlyReport:
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")

    # --- Realised trades (FIFO match across all history, filter to
    # ``sell_date`` in this month / this year for YTD).
    all_matched = _match_trades(executions)
    in_month: list[RealisedTradeRow] = []
    in_year_so_far: list[RealisedTradeRow] = []
    for trade in all_matched:
        if trade.sell_date.year == year:
            in_year_so_far.append(trade)
            if trade.sell_date.month == month:
                in_month.append(trade)

    # --- Income aggregation.
    gains_month: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    tob_month: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    net_month: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    ytd_net: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for trade in in_month:
        gains_month[trade.currency_local] += trade.gross_local
        tob_month[trade.currency_local] += (
            trade.tob_buy_local + trade.tob_sell_local
        )
        net_month[trade.currency_local] += trade.net_local
    for trade in in_year_so_far:
        ytd_net[trade.currency_local] += trade.net_local

    # --- Software performance.
    trade_count = len(in_month)
    average_hold = (
        int(sum(t.hold_days for t in in_month) / trade_count)
        if trade_count
        else 0
    )
    hit_count = sum(
        1 for t in in_month if t.net_pct_on_cost >= profit_target_pct
    )
    hit_rate = (
        round(hit_count / trade_count * 100, 1) if trade_count else 0.0
    )

    # Confidence distribution from verdicts in this month.
    buckets: dict[str, int] = defaultdict(int)
    month_verdicts = [
        v for v in verdicts if _within_month(v.generated_at, year, month)
    ]
    for v in month_verdicts:
        buckets[_confidence_bucket(v.confidence_score_pct)] += 1
    total_verdicts = sum(buckets.values())
    confidence_pct = {
        bucket: round(count / total_verdicts * 100, 1)
        for bucket, count in buckets.items()
    } if total_verdicts else {}

    # --- Action-draft activity by status, filtered to drafts that
    # were ``touched`` (any timestamp landed) in the month.
    activity = {
        "proposed": 0,
        "user_approved": 0,
        "submitted": 0,
        "filled": 0,
        "dismissed": 0,
    }
    for draft in action_drafts:
        if _within_month(draft.created_at, year, month):
            activity["proposed"] += 1
        if _within_month(draft.user_approved_at, year, month):
            activity["user_approved"] += 1
        if _within_month(draft.submission_started_at, year, month):
            activity["submitted"] += 1
        if draft.status == "filled" and _within_month(
            draft.terminal_state_at, year, month
        ):
            activity["filled"] += 1
        if _within_month(draft.dismissed_at, year, month):
            activity["dismissed"] += 1

    # --- Verdict activity grouping.
    by_decision: dict[str, int] = defaultdict(int)
    for v in month_verdicts:
        by_decision[v.decision] += 1

    # --- Executive summary headline.
    # For comparison vs baseline we pick the EUR bucket if present —
    # otherwise we surface the comparison as ``None`` (the UI shows
    # "Baseline-vergelijking niet beschikbaar in deze munt").
    net_eur = net_month.get("EUR")
    baseline_text = _baseline_comparison_text(
        net_eur=net_eur, baseline_eur=baseline_monthly_eur
    )
    if trade_count == 0:
        headline = (
            f"Geen gesloten trades in {year:04d}-{month:02d}. "
            "Software draait, maar er kwamen geen winsten binnen."
        )
    else:
        headline = (
            f"{trade_count} trades gesloten in {year:04d}-{month:02d}; "
            f"hit-rate +4% = {hit_rate:.1f}%."
        )

    return MonthlyReport(
        year=year,
        month=month,
        executive_summary=ExecutiveSummary(
            headline_nl=headline,
            net_local_by_currency=_format_currency_dict(net_month),
            vs_baseline_eur=baseline_text,
            trade_count=trade_count,
            hit_rate_pct=hit_rate,
        ),
        open_positions_count=open_positions_count,
        action_draft_activity=ActionDraftActivityRow(
            proposed=activity["proposed"],
            user_approved=activity["user_approved"],
            submitted=activity["submitted"],
            filled=activity["filled"],
            dismissed=activity["dismissed"],
        ),
        verdict_activity=VerdictActivity(
            total=len(month_verdicts),
            by_decision=dict(by_decision),
        ),
        income=IncomeBreakdown(
            capital_gains_local_by_currency=_format_currency_dict(gains_month),
            tob_local_by_currency=_format_currency_dict(tob_month),
            net_local_by_currency=_format_currency_dict(net_month),
            ytd_net_local_by_currency=_format_currency_dict(ytd_net),
        ),
        software_performance=SoftwarePerformance(
            hit_rate_pct=hit_rate,
            average_hold_days=average_hold,
            confidence_distribution_pct=confidence_pct,
            proposals_vs_approved=(
                activity["proposed"], activity["user_approved"]
            ),
        ),
        realised_trades=tuple(in_month),
        notes_nl=(
            (
                "EUR-conversie via dagkoersen is V1 nog niet beschikbaar — "
                "bedragen blijven in lokale munt."
            ),
            (
                "Dividenden-feed wordt later toegevoegd; de income-sectie "
                "telt nu enkel capital gains."
            ),
        ),
    )


__all__ = [
    "ActionDraftSnapshot",
    "VerdictSnapshot",
    "MonthlyReport",
    "ExecutiveSummary",
    "IncomeBreakdown",
    "SoftwarePerformance",
    "ActionDraftActivityRow",
    "VerdictActivity",
    "build_monthly_report",
    "DEFAULT_BASELINE_MONTHLY_EUR",
]
