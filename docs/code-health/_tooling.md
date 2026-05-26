# Code Health Tooling

This file documents the tools used by the Phase 1d code-health audit and
the Phase 5 recurring runs, why each was chosen, and where they live.

## Inventory at start of Phase 0

Tools already configured before Phase 0 (preserved unchanged):

| Tool | Where | Status |
|------|-------|--------|
| ruff | each Python package `pyproject.toml`, `select = E/F/I/UP/B`, line-length 100, py312 | configured, run in `ci.yml` |
| mypy `--strict` | each Python package `pyproject.toml` | configured, run in `ci.yml` |
| pytest | each Python package | configured, run in `ci.yml` |
| eslint | `apps/web` (`eslint-config-next`) | configured, run in `ci.yml` |
| `next build` (incl. tsc) | `apps/web` | run in `ci.yml` |
| vitest | `apps/web` | run in `ci.yml` |
| Playwright | `apps/web` | run in `ci.yml` |

Tools missing (and therefore added by Phase 0):

| Tool | Purpose | Added how |
|------|---------|-----------|
| vulture | dead Python code | repo-root `pyproject.toml` `[tool.vulture]` + `code-health.yml` |
| bandit | Python security smells | repo-root `pyproject.toml` `[tool.bandit]` + `code-health.yml` |
| pip-audit | Python dependency CVEs | `code-health.yml` (no config needed) |
| radon | Python complexity + maintainability | `code-health.yml` (CLI-only) |
| explicit `tsc --noEmit` step | catches type errors without a full build | `code-health.yml` |
| knip | unused files/exports in TS/JS | `code-health.yml` (`--no-save` install) |
| ts-prune | unused exports in TS | `code-health.yml` (`--no-save` install) |
| npm audit | JS dependency CVEs | `code-health.yml` |

## Design choices

- **No changes to existing per-package `pyproject.toml` files.** The
  Phase 0 mandate is "do not change behavior of existing passing
  config". New cross-cutting tool config lives in a new repo-root
  `pyproject.toml` whose only purpose is to host those sections.
- **Report-only.** The new `code-health.yml` workflow runs with
  `continue-on-error: true` on every step. Findings appear in the job
  log but do not fail the build until Phase 1d sets a baseline and we
  decide which findings become gates.
- **Additive workflow, not a replacement.** The existing `ci.yml`
  jobs (`domain`, `portfolio`, `storage`, `api`, `worker`, `web`) are
  untouched. Branch-protection required checks should NOT yet include
  `python-health` or `web-health` — those become required only after
  Phase 1d.
- **No changes to `apps/web/package.json` dev dependencies.** knip and
  ts-prune are installed in the workflow with `--no-save` so the
  existing lockfile stays as-is during Phase 0.
- **mypy `--strict` everywhere in code-health.** Some packages may have
  mypy gaps if treated strictly; that is exactly what Phase 1d wants
  to see. Failures are reported, not enforced, until the gate tightens.

## When to tighten the gates

After Phase 1d produces a baseline:

1. Catalogue all findings into `00-findings.md` and the per-category
   files (`01`–`04`).
2. Sort into `05-fix-batches.md`.
3. Once a tool's findings are at zero (or all remaining are documented
   in `_dismissed.md`), promote it from `continue-on-error: true` to a
   hard failure and add it to the branch-protection required checks
   list (see `docs/tasks/_branch-protection-checklist.md`).
