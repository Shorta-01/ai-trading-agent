```yaml
id: T-054
title: Run `pip-audit` baseline (Python dependency CVEs) and emit FIND entries
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: (set on push)
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/04-bugs.md` (Phase 0 stub) and `docs/code-health/_dismissed.md` (T-050/T-051/T-052/T-053 sections) read pre-edit. Inspected the actual advisory body for each of the 5 reported vulnerabilities; grep'd the repo for `fastapi[standard]` and `fastar` to confirm the project install path; checked whether `fastar` was actually installed (it is not).
- **Step 2 (one-line per touched file):**
  - `docs/code-health/04-bugs.md` — pre-edit: stub; post-edit: `FIND-PIPAUDIT-001` entry for the `fastapi==0.136.3` MAL-2026-4750 release.
  - `docs/code-health/_dismissed.md` — pre-edit: T-050+T-051+T-052+T-053 sections; post-edit: T-054 section appended with the 4 pip CVEs dismissed + 5 local-package skip notes.
- **Step 3 (one-line change):** run pip-audit, file 1 high-severity FIND for the fastapi malicious release, dismiss 4 pip CVEs (build-time tool only) plus 5 local-package skips.
- **Step 4 (criteria measurable):** yes — raw outputs at `/tmp/pip-audit-baseline.json` + `/tmp/pip-audit-baseline.txt`; 1 FIND covers the fastapi MAL; 4 pip CVE dismissal rows + 5 not-applicable skip rows account for the remaining items; sum = 5 vulnerabilities + 5 skips = 10 finding-like rows.
- **Step 5 (out-of-scope does not block goal):** confirmed — no `requirements*.txt` / `pyproject.toml` modification (the fix would require pinning, but writing the fix is Phase 4 territory; this task only records the finding).

## Goal

Run `pip-audit` after installing all five Python packages editable and triage every CVE into a FIND-XXX entry or `_dismissed.md` row.

## Context

`depends_on:` —. pip-audit reads the live site-packages for vulnerabilities against PyPA's advisory database, so all packages must be installed first.

## Touch scope

Create / append to:
- `docs/code-health/04-bugs.md`
- `docs/code-health/_dismissed.md`

Run:
- `pip install -e ./packages/domain -e ./packages/storage -e ./packages/portfolio -e ./apps/worker -e ./apps/api`
- `pip-audit --format=json | tee /tmp/pip-audit-baseline.json`
- `pip-audit | tee /tmp/pip-audit-baseline.txt`

## Acceptance criteria

- [ ] Raw outputs captured (JSON + text).
- [ ] Every distinct CVE becomes a FIND-XXX or `_dismissed.md` row.
- [ ] FIND severity mapping: pip-audit CVSS ≥ 9 → critical, ≥ 7 → high, ≥ 4 → medium, < 4 → low. When CVSS missing, default `medium`.
- [ ] FIND evidence field includes: package, installed version, fixed version, CVE ID, advisory URL.
- [ ] FIND ID convention: `FIND-PIPAUDIT-NNN`.
- [ ] No `requirements*.txt` / `pyproject.toml` modification.

## Out of scope

- Upgrading any dependency.
- Pinning fixed versions.

## Verification

- Raw outputs present.
- Every CVE reported by the tool appears exactly once across FIND entries and dismissals.

## Notes

`pip-audit` may report transitive dependencies the project doesn't directly use. Document the transitive chain in the FIND evidence ("transitive via <pkg> from <our-pkg>").
