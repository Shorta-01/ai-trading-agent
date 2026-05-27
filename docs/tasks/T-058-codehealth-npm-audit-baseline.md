```yaml
id: T-058
title: Run `npm audit` baseline (JS dependency CVEs) and emit FIND entries
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

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/04-bugs.md` (T-054 `FIND-PIPAUDIT-001` only) and `docs/code-health/_dismissed.md` (T-050…T-057 sections) read pre-edit. `npm install --legacy-peer-deps` ran cleanly in `apps/web`. All four raw outputs captured: `/tmp/npm-audit-prod.json` (434 lines), `/tmp/npm-audit-prod.txt` (42 lines, exit 1), `/tmp/npm-audit-full.json` (621 lines), `/tmp/npm-audit-full.txt` (73 lines, exit 1). JSON parsed via `python3 json.load` to confirm 9 vulnerable packages (2 prod + 7 dev-only); 22 distinct GHSA advisories rolled up under `next`.
- **Step 2 (one-line per touched file):**
  - `docs/code-health/04-bugs.md` — pre-edit: `FIND-PIPAUDIT-001` only; post-edit: 4 `FIND-NPMAUDIT-001..004` umbrella entries appended (2 prod + 2 dev-only).
  - `docs/code-health/_dismissed.md` — pre-edit: T-050…T-057 sections; post-edit: T-058 section appended with the dismissal accounting (no dismissals required — every reported package is in a FIND; transitive-chain explanation included for the 5 dev-only siblings).
- **Step 3 (one-line change):** run npm audit prod-only + full, file 4 umbrella FINDs covering all 9 vulnerable packages and 23 distinct advisories per the locked severity mapping (prod follows npm-audit; dev-only downgraded one rank).
- **Step 4 (criteria measurable):** yes — four raw outputs captured; severity mapping applied: `next` prod-high → **HIGH** (`FIND-NPMAUDIT-001`), `postcss` prod-moderate → **MEDIUM** (`FIND-NPMAUDIT-002`), `@eslint/plugin-kit` + `eslint` dev-low → **LOW** (`FIND-NPMAUDIT-003`), `esbuild` + `vite` + `@vitest/mocker` + `vite-node` + `vitest` dev-moderate → **LOW** (`FIND-NPMAUDIT-004`, downgraded one rank); FIND evidence carries package + installed range + fixed range + advisory URL + prod/dev flag; **accounting**: 9 packages = 2 prod (FIND-001 + FIND-002) + 2 dev clusters (FIND-003 covering 2 packages, FIND-004 covering 5 packages); 23 distinct GHSAs = 22 (FIND-001) + 1 (FIND-002) + 1 (FIND-003) + 1 (FIND-004 plus 4 transitive packages with no own advisory).
- **Step 5 (out-of-scope does not block goal):** confirmed — no `npm audit fix`, no `package.json` / `package-lock.json` modification, no version pinning.

## Goal

Run `npm audit --omit=dev` and `npm audit` separately against `apps/web` and triage CVEs into FIND-XXX entries or `_dismissed.md` rows.

## Context

`depends_on:` —. Two runs: production-only (`--omit=dev`) and full. Production CVEs default to higher severity than dev-only.

## Touch scope

Create / append to:
- `docs/code-health/04-bugs.md`
- `docs/code-health/_dismissed.md`

Run:
- `cd apps/web && npm install --legacy-peer-deps`
- `cd apps/web && npm audit --omit=dev --json | tee /tmp/npm-audit-prod.json`
- `cd apps/web && npm audit --omit=dev | tee /tmp/npm-audit-prod.txt`
- `cd apps/web && npm audit --json | tee /tmp/npm-audit-full.json`
- `cd apps/web && npm audit | tee /tmp/npm-audit-full.txt`

## Acceptance criteria

- [ ] All four raw outputs captured.
- [ ] Every distinct CVE becomes a FIND-XXX or `_dismissed.md` row.
- [ ] FIND severity mapping: prod-CVE follows npm-audit's rating; dev-only CVEs downgraded one rank (critical→high, high→medium, medium→low, low→low).
- [ ] FIND evidence: package, installed range, fixed range, advisory URL, prod-or-dev flag.
- [ ] FIND ID convention: `FIND-NPMAUDIT-NNN`.
- [ ] No `package.json` / `package-lock.json` modification.

## Out of scope

- `npm audit fix` (runs in Phase 4 after batching).
- Pinning specific transitive versions.

## Verification

- All four raw outputs present.
- Every CVE reported by either run appears exactly once in FIND or dismissed.

## Notes

When the same CVE appears in both prod and dev runs, use the prod severity and note in evidence ("appears in dev tree too").
