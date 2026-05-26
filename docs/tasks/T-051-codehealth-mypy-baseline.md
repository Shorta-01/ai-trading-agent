```yaml
id: T-051
title: Run `mypy --strict` baseline and emit FIND entries
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

Run `mypy --strict` per Python package, triage every reported finding into a FIND-XXX entry or a `_dismissed.md` row.

## Context

`mypy --strict` is already configured per-package in CI. A clean baseline is expected but per-package `[[tool.mypy.overrides]]` `ignore_missing_imports = true` blocks deserve audit. `depends_on:` —.

## Touch scope

Create / append to:
- `docs/code-health/02-anti-patterns.md`
- `docs/code-health/04-bugs.md` (where a typing error indicates a real bug, not just a typing gap)
- `docs/code-health/_dismissed.md`

Run:
- For each Python package, `cd <pkg> && mypy --strict src | tee /tmp/mypy-<pkg>.log` — capture per-package.

Read: each per-package `pyproject.toml` `[tool.mypy]` + `[[tool.mypy.overrides]]` blocks.

## Acceptance criteria

- [ ] Per-package raw output captured.
- [ ] Every distinct file:line:error becomes a FIND-XXX or `_dismissed.md` row.
- [ ] `ignore_missing_imports` overrides each get a `_dismissed.md` row with the reason ("third-party lib without stubs: <module>"). Cite `pyproject:line`.
- [ ] FIND schema honoured (see T-050).
- [ ] FIND ID convention: `FIND-MYPY-NNN`.
- [ ] No source / config modification.

## Out of scope

- Fixing typing issues.
- Adding `py.typed` markers to dependencies.
- Triaging other tools.

## Verification

- Per-package raw logs exist and are referenced.
- Sum of FIND-MYPY-* + dismissed rows = total distinct error lines.

## Notes

`mypy` output includes useful context lines around errors — capture the 3 lines surrounding each error in the FIND evidence excerpt.
