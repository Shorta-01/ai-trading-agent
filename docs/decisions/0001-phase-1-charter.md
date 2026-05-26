# 0001 — Run four-track Phase 1 audit before any code changes

- **Date:** 2026-05-26
- **Phase:** P1
- **Status:** accepted
- **Supersedes:** —
- **Superseded by:** —

## Context

The codebase has grown through many task-driven slices (see
`docs/product/task-history.md` for the historical record) without a
single moment where someone sat down and wrote a complete,
cited description of what is actually built. The Phase 0 scaffolding
work surfaced enough signals to make this concrete:

- 36 + 39 + 8 = **83 real Python source files** are spread across
  `packages/domain`, `packages/portfolio`, and `packages/storage`, with
  six additional `packages/*/` directories that are README-only stubs.
- The API has **78 modules** with a 26-module IBKR sub-cluster.
- The worker has **37 modules** across six sub-packages
  (`forecasting/`, `ibkr_submission/`, `ibkr_reconciliation/`,
  `decision_package/`, `action_draft/`, `providers/`).
- The frontend has **16 Next.js pages and 41 components**.
- The storage package carries **54 Alembic migrations**.
- The repository already contains substantial intent documents
  (`docs/architecture.md`, `docs/storage-architecture.md`,
  `docs/ai-policy.md`, `docs/risk-policy.md`,
  `docs/product-scope.md`, `docs/roadmap.md`, three ADRs, AGENTS
  guardrails), but no document that traces those intents back to the
  code that implements (or doesn't implement) them.

Without a Phase 1, every future fix or feature decision is made from
memory and assumption rather than from code. That is the failure mode
this charter exists to prevent.

## Decision

Run the four-track Phase 1 audit described in
`docs/intent/_phase-1-charter.md` before any further code changes
(fixes or features) land. Concretely:

1. **Track 1a — Reality docs** runs first because Tracks 1b and 1c
   depend on it. Within 1a, **components → functionality → workflows**
   is a hard order: workflows quote functionality, functionality
   quotes components.
2. **Tracks 1b (architecture review) and 1c (gap analysis)** run
   after 1a components and read the reality docs as source material.
3. **Track 1d — Code health** runs in parallel with the others and
   has no dependencies; it operates directly on the code and on
   tool output.
4. **Phase 1d does not yet propose fixes.** It produces a baseline of
   findings (`01`–`04` per-category files plus the consolidated
   `00-findings.md`), then a batching *proposal* in
   `05-fix-batches.md`. The user reviews the batches and decides
   which fix tasks to add to the queue — that addition is a separate
   decision, not part of Phase 1.

The full file plan and task index live in `docs/00-PHASES.md`.

## Alternatives considered

- **Skip Phase 1 and go straight to fixes.** Rejected: every fix
  task would carry the cost of re-reading the surrounding code from
  scratch, with no cumulative artefact. The first three or four fix
  tasks would re-do the reality work informally and inconsistently.
- **Run only Track 1d (code health) now and defer reality /
  architecture / gap.** Rejected: code-health findings without a
  reality doc become a list of out-of-context line numbers. Knowing a
  function is complex is less valuable than knowing what it does and
  where it sits.
- **Combine Tracks 1a and 1b into a single "audit" pass.** Rejected:
  reality and verdicts have different quality bars. Mixing them
  causes opinion to leak into the descriptive layer and makes the
  reality doc unfit to be quoted by later phases.
- **Single combined Phase 1 task that produces every output in one
  PR.** Rejected: blows the one-task-per-session sizing budget by
  ~50×; impossible to review.
- **Defer the reality docs until after a refactor.** Rejected: the
  refactor would itself need reality docs to be designed safely. The
  reality doc is the prerequisite, not the deliverable.

## Consequences

- **What becomes possible after Phase 1:**
  - Phase 2 plain-English functional docs can paraphrase reality
    without re-reading every module.
  - Phase 3 improvement memo can prioritise from a cited gap list,
    not from memory.
  - Phase 4 brainstorming has named files to point at; every
    decision detail file (`docs/decisions/NNNN-<slug>.md`) can
    reference the relevant gap, finding, or reality entry.
  - Phase 5 recurring code-health runs have a baseline to diff
    against; "new finding since last run" becomes meaningful.
- **Costs accepted:**
  - Roughly 60 tasks of work before any code change merges. The user
    chose this explicitly over the "fix things now" path.
  - Time spent reading code that may later be rewritten. Net positive
    because the rewrite is informed by the reading.
  - Reality docs become stale as the code changes. Mitigated by the
    Phase 4 convention that every fix PR updates the reality docs
    it touches.
- **Constraints introduced:**
  - No fixes during Phase 1 (per `docs/intent/_phase-1-charter.md`).
  - Every Phase 1 output must cite `path:line` and excerpt non-
    trivial claims.
  - Code-health fix tasks are deferred — they are created only after
    the user reviews the `05-fix-batches.md` proposal.

## Tasks generated

Sixty tasks, listed in `docs/00-PHASES.md` under "Phase 1 task index":

- Track 1a — Reality components: **T-001 … T-010** (10 tasks → 25 files)
- Track 1a — Reality functionality: **T-011 … T-024** (14 tasks → 14 files)
- Track 1a — Reality workflows: **T-025 … T-035** (11 tasks → 11 files)
- Track 1b — Architecture review: **T-036 … T-043** (8 tasks → 8 files)
- Track 1c — Gap analysis: **T-044 … T-049** (6 tasks → 6 files)
- Track 1d — Code health baseline + consolidation + batching:
  **T-050 … T-060** (11 tasks → findings entries + 2 roll-up files)
