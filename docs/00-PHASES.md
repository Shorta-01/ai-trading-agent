# Audit & Execution Workflow — Phase Plan

One-page map of the multi-phase audit and execution workflow. Each
phase populates specific directories; this file is the index from
phase → output location → status.

## Phase 0 — Scaffolding _(current)_

Set up directories, templates, configs, and CI tooling so later phases
have a consistent place to write into. No source-code analysis beyond
inventorying CI tools.

Outputs:
- All `docs/` audit directories created with READMEs and `.gitkeep`.
- `docs/tasks/queue.md`, `docs/tasks/_task-template.md`,
  `docs/tasks/_standing-prompt.md`, `docs/tasks/_audit-discipline.md`,
  `docs/tasks/_branch-protection-checklist.md`.
- `docs/decisions/decision-log.md`.
- `docs/code-health/` skeleton (`00`–`05`, `_dismissed.md`, `_tooling.md`).
- `docs/00-PHASES.md` (this file).
- `.github/workflows/code-health.yml` in report-only mode.
- Repo-root `pyproject.toml` for cross-cutting Python tool config.

## Phase 1 — Four-track analysis

Four parallel tracks producing as-is documentation and a code-health
baseline. Each track writes into its own directory.

| Track | Description | Output directory |
|-------|-------------|------------------|
| 1a — Reality docs | What the system actually does today, derived from the code. | `docs/reality/functionality/`, `docs/reality/workflows/`, `docs/reality/components/` |
| 1b — Architecture review | Structural assessment of layering, boundaries, dependencies. | `docs/architecture-review/` |
| 1c — Gap analysis | Deltas between intended behaviour (`docs/intent/`, `docs/product/`) and reality. | `docs/gap-analysis/` |
| 1d — Code health | Baseline of code-health tool findings (`ruff`, `mypy --strict`, `vulture`, `bandit`, `pip-audit`, `radon`, `tsc --noEmit`, `knip`, `ts-prune`, `npm audit`). | `docs/code-health/` |

Phase 1 also drafts `docs/intent/` files where needed so Phase 1c has
both sides of the comparison.

## Phase 2 — Plain-English functional docs

User-facing, jargon-free descriptions of what the product does and how
to use it. Distinct from reality docs (which describe code).

Output directory: `docs/functional/`.

## Phase 3 — Improvement memo

Synthesise Phases 1 and 2 into a prioritised memo: what is most worth
changing, in what order, with what trade-offs. The memo is the input
to Phase 4 brainstorming.

Output: a single dated memo file (location decided in Phase 3 — likely
`docs/improvement-memo-YYYY-MM-DD.md`).

## Phase 4 — Brainstorm → tasks → PRs → merges

Topic-by-topic working loop. For each topic:

1. Brainstorm (record outcomes in `docs/decisions/NNNN-<slug>.md` plus
   a row in `docs/decisions/decision-log.md`).
2. Break into tasks; add rows to `docs/tasks/queue.md` and create
   working files at `docs/tasks/T-NNN-<slug>.md` for non-trivial tasks.
3. Execute tasks one PR at a time, using
   `docs/tasks/_audit-discipline.md` and the PR template.
4. Merge; update `docs/reality/` and `docs/functional/` as behaviour
   changes.

This is where Claude becomes the executor. Standing prompt lives at
`docs/tasks/_standing-prompt.md`.

## Phase 5 — Recurring code-health runs

After Phase 1d baselines, promote code-health gates one tool at a time
(see `docs/code-health/_tooling.md`) and run periodic full sweeps. Each
sweep writes a dated report into `docs/code-health/` (e.g.
`YYYY-MM-DD-sweep.md`) and produces tasks back into `docs/tasks/queue.md`.

## Directory → phase quick reference

| Directory | Populated by |
|-----------|--------------|
| `docs/reality/{functionality,workflows,components}/` | Phase 1a |
| `docs/architecture-review/` | Phase 1b |
| `docs/intent/` | Phase 1 (drafted) → Phase 3 (refined) |
| `docs/gap-analysis/` | Phase 1c |
| `docs/code-health/` | Phase 1d, then Phase 5 |
| `docs/functional/` | Phase 2 |
| `docs/decisions/` | Phase 4 onward |
| `docs/tasks/` | Phase 4 onward |
