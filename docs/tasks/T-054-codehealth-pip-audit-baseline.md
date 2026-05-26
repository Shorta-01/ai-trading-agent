```yaml
id: T-054
title: Run `pip-audit` baseline (Python dependency CVEs) and emit FIND entries
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
