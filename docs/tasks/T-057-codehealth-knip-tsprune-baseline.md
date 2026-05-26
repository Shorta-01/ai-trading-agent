```yaml
id: T-057
title: Run `knip` + `ts-prune` baseline (unused TS exports) and emit FIND entries
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

Run `knip` and `ts-prune` against `apps/web` (combining unused-files, unused-exports, unused-dependencies findings) and triage results into FIND-XXX entries or `_dismissed.md` rows.

## Context

`depends_on:` —. Both tools are install-then-run (not yet in `package.json` devDependencies — the workflow installs them ephemerally with `--no-save`). Expect overlap between the two tools' findings; deduplicate during triage.

## Touch scope

Create / append to:
- `docs/code-health/01-dead-code.md`
- `docs/code-health/_dismissed.md`

Run:
- `cd apps/web && npm install --legacy-peer-deps`
- `cd apps/web && npm install --no-save --legacy-peer-deps knip ts-prune`
- `cd apps/web && npx knip --reporter json | tee /tmp/knip-baseline.json`
- `cd apps/web && npx knip | tee /tmp/knip-baseline.txt`
- `cd apps/web && npx ts-prune | tee /tmp/ts-prune-baseline.txt`

## Acceptance criteria

- [ ] Raw outputs captured (all three).
- [ ] Every distinct finding becomes a FIND-XXX or `_dismissed.md` row.
- [ ] Duplicates between knip and ts-prune merged: the FIND cites both tools in `tool` field.
- [ ] FIND ID convention: `FIND-KNIP-NNN` for knip-only, `FIND-TSPRUNE-NNN` for ts-prune-only, `FIND-UNUSED-NNN` for entries observed by both.
- [ ] Common dismissals: route-handler exports that Next.js consumes by file convention (page.tsx default export, etc.) — note pattern.
- [ ] No source modification.

## Out of scope

- Removing any export.
- Adding either tool to `package.json` permanently — that decision goes through Phase 4 brainstorming.

## Verification

- All three raw outputs present.
- Every distinct finding appears exactly once in either FIND or dismissed.

## Notes

Next.js conventions (page.tsx default exports, route.ts handlers, layout.tsx defaults) are framework-driven entry points — dismiss these wholesale with one pattern note rather than per-file rows.
