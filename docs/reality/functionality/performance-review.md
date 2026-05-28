# Performance Review Screen — Specification vs Implementation Status

**Scope.** Functionality-level reality doc documenting the performance-review-screen specification (intent §8 of `dashboard-and-order-flow.md`) + current implementation status. Per queue.md T-021b: "Documents the performance review screen spec (time-weighted return vs benchmark, drawdown, volatility / risk-budget usage, exposure breakdown, portfolio chart, weekly/monthly views) and current implementation status."

**Answer**: the screen **does not exist**, AND the backend is only partially capable. `performance.py` computes BASIC metrics (return-since-start, cash flow, costs) but NONE of the intent §8 sophisticated metrics (TWR vs benchmark, drawdown, volatility/risk-budget, exposure breakdown). Even the basic metrics it does compute are **not API-exposed**. This is the most-absent of the functional-review screens — and the T-044 §1 Must missing feature documented from the functional-review angle.

**The LAST functional-review addition — closes Phase 1.**

## 0. TL;DR

| Layer | Status |
|-------|--------|
| Frontend performance-review screen | **Absent** — zero pages/components match `performance`/`review` |
| Backend basic metrics (return-since-start, cash flow, costs) | **Present** — `performance.py:177` `build_portfolio_performance_summary` |
| Backend intent §8 metrics (TWR/benchmark/drawdown/volatility/exposure) | **Absent** — `performance.py` has none |
| API exposure of even the basic summary | **Absent** — no route consumes `build_portfolio_performance_summary` |
| Portfolio chart | **Absent** — and would have lived on the dashboard wrongly (T-011c §3.1 charts-forbidden) |

**Net**: the most-absent functional-review screen. Frontend not built, backend partial, basic backend not even API-exposed.

## 1. The intent §8 screen specification

`docs/intent/dashboard-and-order-flow.md` §8 ("Performance review (separate screen)"):

> "A separate screen, not the dashboard. The user visits it when they choose to. (doctrine §11)"

Shows (6 metric groups):
1. **Time-weighted return vs benchmark** — TWR removes the distortion of deposit/withdrawal timing; compared against a benchmark index.
2. **Drawdown from peak** — peak-to-trough decline.
3. **Volatility / risk-budget usage** — realised volatility + how much of the risk budget is consumed.
4. **Exposure breakdown** — by asset class, sector, currency.
5. **Portfolio chart** — value evolution over time.
6. **Weekly and monthly views** — time-window aggregation.

The intent's design rationale (§8):
> "Deliberately not on the dashboard. The intent is to support deliberate weekly/monthly review, not encourage daily emotional reactions."

This is why T-011c §3.1 flagged the dashboard's chart placeholder as a violation — the portfolio chart belongs HERE, on the performance review screen, not on the dashboard.

## 2. The backend that exists — `performance.py`

`packages/portfolio/src/portfolio_outlook_portfolio/performance.py` (230 LOC):

### 2.1 `PortfolioPerformanceSummary` (`:35-48`)

```python
@dataclass(frozen=True)
class PortfolioPerformanceSummary:
    portfolio_id: PortfolioId
    starting_capital: Money
    deposits: Money
    withdrawals: Money
    current_cash: Money
    current_positions_value: Money
    current_total_value: Money
    gross_result_since_start: Money
    fees: Money
    estimated_taxes: Money
    net_result_since_start: Money
    return_since_start: Percentage | None
```

The summary computes **simple-return-since-inception accounting**: starting capital + net cash flow → current value → gross/net result → `return_since_start`.

### 2.2 What `performance.py` does NOT compute

Compared with the intent §8 spec:

| Intent §8 metric | In `performance.py`? |
|-------------------|----------------------|
| Time-weighted return | **No** — only simple `return_since_start` |
| Benchmark comparison | **No** |
| Drawdown from peak | **No** |
| Volatility / risk-budget usage | **No** |
| Exposure breakdown (asset class / sector / currency) | **No** |
| Portfolio chart (time-series) | **No** — only point-in-time summary |
| Weekly / monthly views | **No** — only since-start |

**`performance.py` implements 0 of the 6 intent §8 metric groups.** It implements a 7th metric (simple return-since-start) that the intent §8 spec doesn't even list — because intent §8 deliberately prefers TWR over simple return (TWR removes cash-flow-timing distortion). The basic simple-return metric is arguably the WRONG metric per intent (which prefers TWR for exactly this reason).

### 2.3 The basic summary is not API-exposed

Grep proof: no API route consumes `build_portfolio_performance_summary` (`:177`) — zero non-test references outside `performance.py` itself. The basic summary exists as a pure function with no caller. The frontend has nothing to fetch even if a screen were built.

## 3. The frontend — entirely absent

Grep proof: zero pages in `apps/web/app/` and zero components in `apps/web/components/` match `performance` or `review`. The 12 routed pages (admin, audit, decision-package, historiek, ibkr-acties, instellingen, onderzoek, portefeuille, research-sources, suggesties, systeemmeldingen, volglijst) include no performance-review screen.

The dashboard's "Dagresultaat" + "Totaal resultaat" metric cards (T-011c §2.4) are hard-coded "Niet beschikbaar" — and per intent §2 ("No daily P&L on the dashboard. No daily change colouring."), they shouldn't even be on the dashboard. Daily P&L is "deliberately not surfaced anywhere as a headline metric" (intent §2.24).

## 4. The three-layer absence

The performance review screen is absent at all three layers:

1. **Frontend**: no screen (§3).
2. **API**: no route exposes any performance data (§2.3).
3. **Computation**: `performance.py` computes only basic metrics, none of the intent §8 sophisticated ones (§2.2).

This is the most-complete absence of the functional-review screens. T-016b (prediction track record) had a fully-present backend (`/prediction-diary`); T-021b's backend is itself only partial.

## 5. Why the gap exists + the metric-correctness concern

The performance accounting module (`performance.py`) was built early as part of the domain/portfolio package (T-002 documented the portfolio package). It implements basic return accounting suitable for a cash-flow ledger. The intent §8 sophistication (TWR, drawdown, volatility, exposure, charting) was never built — neither the computation, the API, nor the screen.

**Metric-correctness concern**: intent §8 specifies **time-weighted return** precisely because simple return-since-start is distorted by deposit/withdrawal timing. The backend computes the distorted simple metric (`return_since_start`). If a future screen surfaces `return_since_start` as "your performance", it would surface the metric intent explicitly chose to avoid. The TWR computation must be added, not just the screen. §6.

## 6. Phase 1c gap entry

This finding is T-044 §1's Must missing feature, documented from the functional-review angle. The full gap:

- **Name**: Performance review screen (TWR vs benchmark + drawdown + volatility/risk-budget + exposure breakdown + portfolio chart + weekly/monthly views).
- **Why it matters**: The user has no way to evaluate "how is my system doing over time?". The dashboard deliberately omits performance (intent §2 — discourage daily emotional reactions); the performance screen is where deliberate weekly/monthly review happens. Without it, the user trades order-by-order with no historical context. T-044 §1 rated this **Must** — the user cannot evaluate the system without it.
- **Where it would live**: New page `apps/web/app/performance/page.tsx` + `apps/web/components/PerformanceReview*.tsx` + a new API surface + TWR/drawdown/volatility/exposure computation extending `performance.py`. Portfolio chart needs a charting library (T-011c §3.1 — charts belong here, not on the dashboard).
- **Effort**: **Large** — three-layer build: (a) extend `performance.py` with TWR + drawdown + volatility + exposure (the hard quant part), (b) new API routes, (c) new frontend screen + charting library adoption.
- **Dependency**: T-021 valuation (the position-value source). Currency exposure (T-044 §2 — companion). Per-lot storage (T-045 §5) would enable lot-level attribution. `fx_rate_at_fill` (T-045 §7) for accurate realised-gain over time.
- **MoSCoW**: **Must** (per T-044 §1).
- **Originating reality**: T-021b (this doc) + T-021 §10.5 + T-044 §1.

## 7. Closes Phase 1

T-021b is the 5th + LAST functional-review addition. With it merged, all Phase 1 audit tasks are complete:

| Track | Docs | Status |
|-------|------|--------|
| 1a Reality (components + functionality + workflows) | 24 + 4 functional-review | Complete |
| 1b Architecture Review | 8 | Complete |
| 1c Gap Analysis | 6 | Complete |
| 1d Code Health | 11 | Complete |

Plus this doc + the other 4 functional-review additions (T-011b, T-011c, T-012b, T-016b).

**Phase 1 audit total: ~54 docs.** The audit answered:
- **Track 1a**: what IS the system?
- **Track 1b**: is what IS good?
- **Track 1c**: what do we fix? (19 Must items, 5 sprints, ~one quarter — the "category transition" per T-049 §4.)
- **Functional-review additions**: closing the gaps the 2026-05-26 functional review surfaced.

Phase 2 backlog inherits the 19 Must items + the functional-review screens (performance review = T-044 §1 Must, prediction track record = T-016b companion to T-044 §4) as its initial scope.

## 8. Out of scope

- T-021 valuation deep dive (merged sibling — the position-value source).
- T-044 §1 performance-review missing-feature entry (merged — this is its functional-review counterpart).
- T-011c dashboard charts-forbidden finding (merged — charts belong here).
- Audit trail screen (intent §9 — separate; not a functional-review addition).
- Currency exposure dimension (T-044 §2 — companion missing feature).

## 9. References

- `packages/portfolio/src/portfolio_outlook_portfolio/performance.py:35-48` (`PortfolioPerformanceSummary` — basic metrics), `:177` (`build_portfolio_performance_summary` — uncalled)
- `apps/web/app/` (12 pages; no performance-review screen)
- `docs/intent/dashboard-and-order-flow.md` §8 (the screen spec — 6 metric groups), §2 (no daily P&L on dashboard), §11 (deliberate weekly/monthly review)
- T-002 `portfolio-money-and-accounting.md` (the portfolio accounting package incl. `performance.py`)
- T-008 `web-pages.md` (frontend page inventory — confirms screen absent)
- T-011c `dashboard-composition.md` §3.1 (charts forbidden on dashboard; belong here) + §2.4 (Dagresultaat/Totaal-resultaat dashboard cards)
- T-016b `prediction-track-record-screen.md` (the other absent functional-review screen — a different screen)
- T-021 `portfolio-valuation-and-cost-basis.md` §10.5 (performance review screen gap originating)
- T-044 `01-missing-features.md` §1 (performance review screen as Must missing feature) + §2 (currency exposure companion)
- T-045 §5 (per-lot storage), §7 (`fx_rate_at_fill`) — dependencies for accurate over-time performance
- T-049 `00-summary.md` §4 (category transition — performance review in Sprint 5)
