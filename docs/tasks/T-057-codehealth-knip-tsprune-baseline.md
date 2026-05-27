```yaml
id: T-057
title: Run `knip` + `ts-prune` baseline (unused TS exports) and emit FIND entries
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/01-dead-code.md` (T-052 contents) and `docs/code-health/_dismissed.md` (T-050…T-056 sections) read pre-edit. `npm install --legacy-peer-deps` ran cleanly in `apps/web`; `npm install --no-save --legacy-peer-deps knip ts-prune` installed both tools ephemerally. Three raw outputs captured: `/tmp/knip-baseline.json` (1 line JSON), `/tmp/knip-baseline.txt` (46 lines), `/tmp/ts-prune-baseline.txt` (93 lines).
- **Step 2 (one-line per touched file):**
  - `docs/code-health/01-dead-code.md` — pre-edit: `FIND-VULTURE-001`; post-edit: seven new FINDs appended (3 dual-source `FIND-UNUSED-001..003` + 4 knip-only `FIND-KNIP-001..004`).
  - `docs/code-health/_dismissed.md` — pre-edit: T-050…T-056 sections; post-edit: T-057 section appended (3 dismissal categories — Next.js framework defaults, config file defaults, ts-prune `(used in module)` over-reporting).
- **Step 3 (one-line change):** run knip + ts-prune, file 7 umbrella FINDs covering 41 knip-reportable items (3 files + 2 devDeps + 10 exports + 25 types + 1 duplicate), dismiss the framework + config + over-reporting categories.
- **Step 4 (criteria measurable):** yes — three raw outputs present; **knip accounting**: 41 reportables = 3 (FIND-UNUSED-001) + 7 (FIND-UNUSED-002) + 2 (FIND-UNUSED-003) + 2 (FIND-KNIP-001) + 1 (FIND-KNIP-002) + 1 (FIND-KNIP-003) + 24 (FIND-KNIP-004) + 1 (the duplicate-export `missingLinksLabel` counted once in FIND-KNIP-003) = 41 ✓; **ts-prune accounting**: 93 total = 18 Next.js framework + 3 config files + 60 "(used in module)" over-reports + 12 real findings (all 12 overlap with the 3 dual-source FINDs above); ID convention honoured (`FIND-UNUSED-*` for dual-source, `FIND-KNIP-*` for knip-only).
- **Step 5 (out-of-scope does not block goal):** confirmed — no export removed, no `package.json` modification (both tools installed `--no-save`), no source / config modification.

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
