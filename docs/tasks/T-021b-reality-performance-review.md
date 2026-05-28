```yaml
id: T-021b
title: Write reality doc for performance-review functionality
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/dashboard-and-order-flow.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/499
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/functionality/performance-review.md` does not exist (verified). Investigated the screen's status:
  - Frontend: zero pages/components match `performance` / `review` (grep proof).
  - Backend: `packages/portfolio/src/portfolio_outlook_portfolio/performance.py` (230 LOC) exists with `build_portfolio_performance_summary` (`:177`) + `PortfolioPerformanceSummary` (basic metrics: starting capital, deposits, withdrawals, current value, gross/net result, return-since-start). **NO** TWR / benchmark / drawdown / volatility / sharpe / exposure.
  - No API route consumes `build_portfolio_performance_summary` (grep returns zero non-test consumers).
  - Intent §8 of `dashboard-and-order-flow.md` specifies the screen.
  - T-044 §1 already recorded the performance review screen as a Must missing feature; T-011c §3.1 documented charts belong here.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the performance-review-screen functionality reality doc.
  - `performance-review.md` — documents the intent §8 screen spec (TWR vs benchmark + drawdown + volatility/risk-budget + exposure breakdown by asset-class/sector/currency + portfolio chart + weekly/monthly views) vs implementation status: screen ABSENT; backend `performance.py` computes only BASIC metrics (return-since-start, cash flow, costs) — NOT the intent §8 sophisticated metrics; even the basic summary is not API-exposed; the most-absent of the functional-review screens.
- **Step 3 (one-line change):** write one functionality-level reality doc documenting the performance-review screen spec + implementation status.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; intent §8 screen spec documented (6 metric groups); implementation status documented (screen absent; backend partial; not API-exposed); the `performance.py` basic-vs-intent-§8-sophisticated gap surfaced; cross-references to T-044 §1 + T-011c §3.1 + Phase 1c; closes-Phase-1 note; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — this is the LAST functional-review addition; closes Phase 1.

## Goal

Produce one functionality-level reality doc documenting the performance-review screen spec (intent §8) + implementation status. Per queue.md T-021b: "Documents the performance review screen spec (time-weighted return vs benchmark, drawdown, volatility / risk-budget usage, exposure breakdown, portfolio chart, weekly/monthly views) and current implementation status." Answer: screen absent; backend `performance.py` computes only basic return-since-start, not the intent §8 metrics; not API-exposed. The most-absent functional-review screen.

## Context

`depends_on:` T-008 (frontend pages), T-021 (portfolio valuation). T-021 documented valuation; T-021b documents the absent performance-review screen built on top of it. Intent §8 of `dashboard-and-order-flow.md` is the binding spec. T-044 §1 already recorded it as a Must missing feature.

## Touch scope

Create:
- `docs/reality/functionality/performance-review.md`

Read: T-008 + T-021 reality docs + `performance.py` + frontend page inventory + intent §8.

## Acceptance criteria

- [ ] Output file exists at `docs/reality/functionality/performance-review.md`.
- [ ] Intent §8 screen spec documented (6 metric groups: TWR-vs-benchmark, drawdown, volatility/risk-budget, exposure breakdown, portfolio chart, weekly/monthly views).
- [ ] Implementation status documented (screen absent; backend partial; not API-exposed).
- [ ] `performance.py` basic-vs-intent-§8 gap surfaced.
- [ ] Cross-references to T-044 §1 + T-011c §3.1 + Phase 1c.
- [ ] Closes-Phase-1 note.
- [ ] No source modification.

## Out of scope

- T-021 valuation deep dive (merged sibling).
- T-044 §1 performance-review missing-feature entry (merged — this is the functional-review counterpart).
- T-011c dashboard charts-forbidden finding (merged).
- Audit trail screen (intent §9 — separate; not a functional-review addition).

## Verification

- File exists.
- Intent §8 6 metric groups documented.
- Screen absence proven.
- performance.py partial-backend gap surfaced.

## Notes

T-021b is the 5th + LAST of the functional-review additions — it closes Phase 1 entirely. The finding is the most-absent of the functional-review screens: the screen doesn't exist (like T-016b), AND the backend computes only basic metrics not the sophisticated intent §8 ones, AND even the basic metrics aren't API-exposed. This is T-044 §1's Must missing feature documented from the functional-review angle. With T-021b merged, all Phase 1 audit tasks are complete.
