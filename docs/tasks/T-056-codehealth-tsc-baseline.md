```yaml
id: T-056
title: Run `tsc --noEmit` baseline and emit FIND entries
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/447
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/02-anti-patterns.md` (T-053/T-055 contents) and `docs/code-health/_dismissed.md` (T-050…T-055 sections) read pre-edit. `npm install --legacy-peer-deps` ran cleanly in `apps/web`. `npx tsc --noEmit` produced 1 error line and exit code 1; raw log captured at `/tmp/tsc-baseline.log`. `04-bugs.md` not touched (the single error is test-fixture drift, not a production bug).
- **Step 2 (one-line per touched file):**
  - `docs/code-health/02-anti-patterns.md` — pre-edit: `FIND-BANDIT-001`+`FIND-RADON-001..004`; post-edit: `FIND-TSC-001` appended for the test-fixture drift.
  - `docs/code-health/_dismissed.md` — pre-edit: T-050…T-055 sections; post-edit: T-056 section appended (no dismissals — the single error is a real FIND, not a false positive).
- **Step 3 (one-line change):** run `tsc --noEmit` in `apps/web`, file 1 FIND for the test-fixture drift, no dismissals.
- **Step 4 (criteria measurable):** yes — raw log at `/tmp/tsc-baseline.log` (1 error line, TS2739 at `components/ActionDraftGrid.test.tsx:14`); FIND severity = **low** per task spec ("Errors in `*.test.tsx` and `*.spec.ts` files marked severity `low` by default"); FIND count (1) = total distinct error lines (1).
- **Step 5 (out-of-scope does not block goal):** confirmed — no `tsconfig.json strict` flag tuning, no `@ts-expect-error` insertion, no source / config modification.

## Goal

Run an explicit `tsc --noEmit` against `apps/web` and triage every type error into a FIND-XXX entry or `_dismissed.md` row.

## Context

`depends_on:` —. CI today runs `next build` which invokes tsc, but only emits errors that block the build. An explicit `--noEmit` run is stricter and catches drift between the production build and a clean type-check.

## Touch scope

Create / append to:
- `docs/code-health/02-anti-patterns.md`
- `docs/code-health/04-bugs.md` (where the type error indicates a real bug)
- `docs/code-health/_dismissed.md`

Run:
- `cd apps/web && npm install --legacy-peer-deps`
- `cd apps/web && npx tsc --noEmit | tee /tmp/tsc-baseline.log`

## Acceptance criteria

- [ ] Raw output captured.
- [ ] Every distinct file:line type error becomes a FIND-XXX or `_dismissed.md` row.
- [ ] FIND schema honoured. ID convention: `FIND-TSC-NNN`.
- [ ] Errors in `*.test.tsx` and `*.spec.ts` files marked severity `low` by default (test code).
- [ ] No source / config modification.

## Out of scope

- Adjusting `tsconfig.json` `strict` flags.
- Adding `// @ts-expect-error` comments.

## Verification

- Raw log present.
- Sum of FIND-TSC-* + dismissed rows = total distinct error lines.

## Notes

If `tsc --noEmit` exits 0 (no errors), file zero FIND entries and add a single "baseline clean" note in `_dismissed.md` referencing the run.
