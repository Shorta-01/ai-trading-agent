```yaml
id: T-051
title: Run `mypy --strict` baseline and emit FIND entries
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/437
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is `docs/code-health/02-anti-patterns.md`, `docs/code-health/04-bugs.md`, `docs/code-health/_dismissed.md`. All three were read at their current state (`_dismissed.md` already carries the T-050 section). Every `[tool.mypy]` and `[[tool.mypy.overrides]]` block across `packages/{domain,portfolio,storage}/pyproject.toml` and `apps/{api,worker}/pyproject.toml` was read to record the config context.
- **Step 2 (one-line per touched file):**
  - `docs/code-health/_dismissed.md` — pre-edit: T-050 section only; post-edit: T-051 section appended with per-package result table + 7 `ignore_missing_imports` rows + 191 `# type: ignore` inventory grouped by error code.
  - `docs/code-health/02-anti-patterns.md`, `docs/code-health/04-bugs.md` — pre-edit: stub headers; post-edit: unchanged (mypy produced zero errors, nothing to add).
- **Step 3 (one-line change):** run `mypy --strict` against the full Python codebase, confirm zero errors across 198 source files, and record the pre-existing `ignore_missing_imports` overrides + `# type: ignore` suppressions in `_dismissed.md`.
- **Step 4 (criteria measurable):** yes — per-package raw output captured at `/tmp/mypy-{domain,portfolio,storage,worker,api}.log`; sum of FIND-MYPY-* (= 0) + dismissed rows accounts for all distinct error sources; `# type: ignore` count (191) and ignore_missing_imports count (7) are independently verifiable via grep.
- **Step 5 (out-of-scope does not block goal):** confirmed — no fixes; no `py.typed` markers added to deps; no other-tool triage; only `_dismissed.md` is appended.

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
