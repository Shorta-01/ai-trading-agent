```yaml
id: T-011c
title: Write reality doc for dashboard-composition functionality
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/dashboard-and-order-flow.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/496
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/functionality/dashboard-composition.md` does not exist (verified). `apps/web/app/page.tsx` (the dashboard homepage, ~135 LOC) read inline. Component-level reality already in T-008 (`web-pages.md` + `web-components-status-and-shared.md`). Intent `docs/intent/dashboard-and-order-flow.md` §1 (dashboard composition) read.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the dashboard-contract functionality reality doc.
  - `dashboard-composition.md` — documents what the dashboard at `apps/web/app/page.tsx` assembles (top badges + 3 widgets + 6 metric cards + 4 panels) vs intent §1's locked 3-area contract (portfolio + watchlist + actions + single system-health line + PAPER/REAL badge); surfaces the intent-vs-reality violations: charts forbidden-but-present, no actions area (out-of-date "runtime bestaat nog niet" placeholders), no watchlist area (lives on /volglijst), no single system-health line (multiple badges instead), PAPER/REAL badge correctly present.
- **Step 3 (one-line change):** write one functionality-level reality doc tracing the dashboard-as-a-whole contract.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; intent §1 3-area + system-health-line + PAPER/REAL badge contract documented; reality composition (page.tsx widgets + cards + panels) documented; intent-vs-reality violations enumerated (charts present, actions/watchlist areas absent, system-health line absent); out-of-date placeholder cards surfaced; cross-references to T-008 + T-028 + T-021 + Phase 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — T-008 component-level deep dive (merged sibling); T-012b / T-016b / T-021b remaining functional-review additions.

## Goal

Produce one functionality-level reality doc documenting the dashboard contract as a whole — distinct from T-008's per-component reality. The dominant finding: the reality dashboard violates intent §1's locked 3-area contract in multiple ways (charts present despite explicit forbid; no actions area; no watchlist area; no single system-health line). The one intent §1 element fully honored is the PAPER/REAL badge.

## Context

`depends_on:` T-008 (frontend pages + components). T-008 documented each dashboard component; T-011c documents the dashboard as an assembled contract against intent §1. Intent `dashboard-and-order-flow.md` §1 is the binding spec.

## Touch scope

Create:
- `docs/reality/functionality/dashboard-composition.md`

Read: T-008 reality docs + `apps/web/app/page.tsx` + `apps/web/app/layout.tsx` + intent §1.

## Acceptance criteria

- [ ] Output file exists at `docs/reality/functionality/dashboard-composition.md`.
- [ ] Intent §1 contract documented (3 areas + system-health line + PAPER/REAL badge + forbidden-items list).
- [ ] Reality composition documented (top badges + 3 widgets + 6 metric cards + 4 panels).
- [ ] Intent-vs-reality violations enumerated.
- [ ] Out-of-date placeholder cards surfaced ("Action-draft runtime bestaat nog niet" despite T-018 reality).
- [ ] Cross-references to T-008 + T-028 + T-021 + Phase 1c.
- [ ] No source modification.

## Out of scope

- T-008 per-component reality (merged sibling).
- Order-flow lifecycle (intent §4-§6 — covered by T-018/T-019/T-026).
- Performance review screen (T-021b — separate functional-review addition).
- T-012b / T-016b remaining additions.

## Verification

- File exists.
- Intent §1 contract documented.
- Violations enumerated.
- Charts-forbidden-but-present surfaced.

## Notes

T-011c is the 2nd of 5 functional-review additions. The dashboard is the user's primary surface; the intent §1 contract is one of the most prescriptive intent sections ("Three areas only", "single system-health line", "Forbidden: charts"). The reality dashboard diverges meaningfully — most notably the ChartPlaceholder for "Portefeuille-evolutie" sitting on a dashboard where intent §1 explicitly forbids charts. This is a clear intent-vs-reality divergence worth surfacing for Phase 1c.
