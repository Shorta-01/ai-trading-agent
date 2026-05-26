```yaml
id: T-056
title: Run `tsc --noEmit` baseline and emit FIND entries
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
