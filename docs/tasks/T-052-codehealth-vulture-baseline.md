```yaml
id: T-052
title: Run `vulture` baseline (dead Python code) and emit FIND entries
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

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/01-dead-code.md` and `docs/code-health/_dismissed.md` read at their current state (`01-dead-code.md` was the Phase 0 stub header; `_dismissed.md` carried T-050 + T-051 sections). Repo-root `pyproject.toml` `[tool.vulture]` block read to confirm `min_confidence = 80` and the five `*/src` paths.
- **Step 2 (one-line per touched file):**
  - `docs/code-health/01-dead-code.md` — pre-edit: stub header; post-edit: header + one `FIND-VULTURE-001` entry.
  - `docs/code-health/_dismissed.md` — pre-edit: T-050 + T-051 sections; post-edit: T-052 section appended with 15 dismissed findings grouped into three categories.
- **Step 3 (one-line change):** run vulture, file 1 finding under `FIND-VULTURE-001` (unsatisfiable `if False else` ternary), dismiss 15 framework-callback / Protocol-signature / backward-compat suppressions.
- **Step 4 (criteria measurable):** yes — raw log at `/tmp/vulture-baseline.log`; 1 FIND + 15 `_dismissed.md` rows = 16 distinct findings; FIND schema honoured.
- **Step 5 (out-of-scope does not block goal):** confirmed — no `# noqa: vulture` comments added; no whitelist file generated; no source modification.

## Goal

Run `vulture` with the repo-root config (`pyproject.toml` `[tool.vulture]`, `min_confidence = 80`) and triage findings into FIND-XXX entries or `_dismissed.md` rows.

## Context

`pyproject.toml` already scopes vulture to the five real-code packages and excludes tests + migrations. Vulture is famously noisy — expect many `_dismissed.md` rows for dynamic dispatch / framework hooks / Pydantic models / SQLAlchemy declarative bases that vulture can't follow. `depends_on:` —.

## Touch scope

Create / append to:
- `docs/code-health/01-dead-code.md`
- `docs/code-health/_dismissed.md`

Run:
- `vulture --min-confidence 80 apps/api/src apps/worker/src packages/domain/src packages/portfolio/src packages/storage/src | tee /tmp/vulture-baseline.log`

## Acceptance criteria

- [ ] Raw output captured.
- [ ] Every distinct finding becomes a FIND-XXX or `_dismissed.md` row.
- [ ] Common false positives (Pydantic field names, SQLAlchemy mapped attributes, FastAPI route handlers reached only via decorators, APScheduler callbacks) get dismissed with the pattern noted ("framework-callback").
- [ ] FIND schema honoured. ID convention: `FIND-VULTURE-NNN`.
- [ ] No source modification.

## Out of scope

- Adding `# noqa: vulture` comments.
- Whitelist-file approach to vulture (`vulture --make-whitelist`) — leave that decision for Phase 4.

## Verification

- Raw log present.
- Sum of FIND-VULTURE-* + dismissed rows = total finding count.

## Notes

If a finding genuinely is dead code that should be removed, file it as FIND-VULTURE-XXX with severity `low` and fix complexity `trivial`. Phase 4 will decide whether to delete or to add a whitelist.
