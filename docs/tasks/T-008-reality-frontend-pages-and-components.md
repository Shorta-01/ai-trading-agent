```yaml
id: T-008
title: Write reality docs for the frontend (pages + components)
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

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
