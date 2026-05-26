```yaml
id: T-058
title: Run `npm audit` baseline (JS dependency CVEs) and emit FIND entries
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
