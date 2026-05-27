```yaml
id: T-008
title: Write reality docs for the frontend (pages + components)
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/448
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** all three target files under `docs/reality/components/` do not exist (verified). The 16 page/layout files (~2528 LoC) + 30 non-test components (~3965 LoC, total ~6493 LoC) plus intent refs (`docs/ui-principles.md` 68 lines + AGENTS.md "UI Dutch" lines at `:33-34`) are read in parallel by three subagents.
  - Agent A — pages cluster: all 17 `page.tsx` + `layout.tsx` files (16 routes, includes nested `[id]` dynamic routes under `decision-package/` and `audit/`), plus `docs/ui-principles.md` + AGENTS.md Dutch-UI rule.
  - Agent B — status + shared components (19 of 30): `AccountModeBadge`, `ApiUnavailableNotice`, `CalibrationCoverageBadge`, `ChartPlaceholder`, `ColdStartBanner`, `DashboardPanel`, `EmptyState`, `HelpText`, `HelpTooltip`, `IconButtonWithTooltip`, `MetricCard`, `PriceFreshnessBadge`, `ReconciliationStatusWidget`, `SchedulerStatusBadge`, `SectionHeader`, `StatusBadge`, `StatusCard`, `SyncStatusBadge`, `SystemEventsIndicator`.
  - Agent C — feature-grid components (11 of 30): `ActionDraftEditForm`, `ActionDraftGrid`, `DecisionPackageDetail`, `ForecastDaySummaryWidget`, `ForecastExplanationPanel`, `IbkrSubmissionGrids`, `PortefeuilleRealtimeSection`, `PositionPlTraceDetails`, `SubmissionLifecycleDrawer`, `ValuationTraceDetails`, `VolglijstColdStartFlow`.
- **Step 2 (one-line per touched file):** the three target files do not exist; each holds one sub-cluster reality doc.
  - `web-pages.md` — page catalogue (route → page file → top-level component refs) for 16 routes; layout + root page + nested dynamic routes; `apiClient` consumption pattern.
  - `web-components-status-and-shared.md` — 19 status/shared components: per-component props + Dutch microcopy + server/client component split.
  - `web-components-feature-grids.md` — 11 feature-specific grids/forms: per-component data flow + state machine touchpoints + Dutch microcopy.
- **Step 3 (one-line change):** write three cited reality docs covering the entire `apps/web/app/**/page.tsx` + `apps/web/components/*.tsx` (non-test) tree, no source modified.
- **Step 4 (criteria measurable):** yes — six acceptance criteria: three files exist; page catalogue (route → page file → top-level component refs); each non-test `.tsx` appears in exactly one of the two component files (sum = 30; 19 + 11 = 30 ✓); Dutch microcopy invariant documented with ≥ 3 example refs; `"use client"` split documented; `apiClient` consumption pattern documented (not the client itself); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — `apiClient.ts`, `uiText.ts`, build/test config are T-009; backend API routes are T-004/T-005/T-006; vitest / playwright test files read for behaviour confirmation only.

## Goal

Produce three reality docs covering the Next.js frontend: pages, shared/status components, and feature-specific grids.

## Context

`apps/web` is a Next.js 15 app with 16 pages and 41 components plus the `app/admin/` and `app/audit/` route trees. `depends_on:` —. Intent inputs: `docs/ui-principles.md`, AGENTS.md (Dutch UI requirement).

## Touch scope

Create:
- `docs/reality/components/web-pages.md`
- `docs/reality/components/web-components-status-and-shared.md`
- `docs/reality/components/web-components-feature-grids.md`

Read: `apps/web/app/**/page.tsx` + `layout.tsx`, all files in `apps/web/components/` (excluding `.test.tsx`), `docs/ui-principles.md`, AGENTS.md.

## Acceptance criteria

- [ ] Three output files at the locked filenames.
- [ ] Page catalogue: route → page file → top-level component refs.
- [ ] Component catalogue: each non-test `.tsx` file appears in exactly one of the two component files; no file uncategorised.
- [ ] Dutch microcopy invariant documented with at least three example refs (locked Dutch text in components).
- [ ] Server / client component split documented (`"use client"` directives noted).
- [ ] `apiClient` consumption pattern documented (not the client itself; that's T-009).
- [ ] No source modification.

## Out of scope

- `apiClient.ts`, `uiText.ts`, build/test config (T-009).
- Backend API routes that the frontend consumes (T-004, T-005, T-006).
- Vitest / Playwright test files (read for behaviour confirmation only).

## Verification

- All three files exist.
- `find apps/web/components -name '*.tsx' -not -name '*.test.tsx'` → every file is referenced exactly once across the two component files.

## Notes

Component split heuristic (refine during execution):
- `web-components-status-and-shared.md`: `StatusCard`, `EmptyState`, `HelpText`, `HelpTooltip`, `IconButtonWithTooltip`, `SyncStatusBadge`, `AccountModeBadge`, `SchedulerStatusBadge`, `ReconciliationStatusWidget`, `ColdStartBanner`, and similar generic/shared UI.
- `web-components-feature-grids.md`: domain-specific grids and forms: `ActionDraftGrid`, `IbkrSubmissionGrids`, `PortefeuilleRealtimeSection`, `ValuationTraceDetails`, `ForecastExplanationPanel`, `ForecastDaySummaryWidget`, `DecisionPackageDetail`, `SubmissionLifecycleDrawer`, `VolglijstColdStartFlow`, etc.
