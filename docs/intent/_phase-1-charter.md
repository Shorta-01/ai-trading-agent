# Phase 1 Charter — four-track audit, code reading only

## Purpose

Establish a complete, cited, plain-fact baseline of what this codebase
actually is and does — before any opinions, fixes, or new features.
Phase 1 is the foundation everything else (Phase 2 functional docs,
Phase 3 improvement memo, Phase 4 brainstorming and execution) builds
on. Without it, every later phase risks being argument from assumption
rather than from code.

## Four tracks

Phase 1 runs four parallel tracks. Each writes into a dedicated
directory under `docs/`.

- **Track 1a — Reality docs.** What the system actually does today.
  Three sub-streams, in this strict order: **components** (per-module
  reality, one file per coherent module group); then **functionality**
  (per major end-to-end functionality, one file each); then
  **workflows** (per user-facing or system-driven workflow, one file
  each, `user-` / `system-` prefixed). Outputs go to
  `docs/reality/components/`, `docs/reality/functionality/`,
  `docs/reality/workflows/`.

- **Track 1b — Architecture review.** Verdict-driven assessment of
  every architectural choice the code makes. Each verdict records the
  current implementation (with file refs), the named state-of-the-art
  alternative, a verdict (`state-of-the-art` / `acceptable` /
  `outdated` / `risky`), the performance implication, and a concrete
  improvement when not state-of-the-art. Output: 8 files in
  `docs/architecture-review/`.

- **Track 1c — Gap analysis.** Deltas between the system's intent
  (existing product docs + AGENTS guardrails + reality docs) and what
  the code actually delivers. Each gap is recorded with: name, why it
  matters in plain English, where it would live in current
  architecture, effort estimate (small/medium/large), dependency,
  MoSCoW priority. Output: 6 files in `docs/gap-analysis/`.

- **Track 1d — Code health.** Baseline of every code-health tool
  listed in `docs/code-health/_tooling.md`. Each tool's findings are
  triaged into FIND-XXX entries with `file:line` evidence, plain-
  English "why wrong", a fix sketch, complexity, and severity. Output
  populates `docs/code-health/01-dead-code.md` through
  `04-bugs.md`, then is rolled up into `00-findings.md` and finally
  proposed batches into `05-fix-batches.md`.

## Scope boundary — what Phase 1 does NOT do

- **No fixes.** Phase 1 only describes. Every finding goes into a
  document; nothing is patched. Fix tasks are created later, after
  the user reviews the batching proposal (Phase 4).
- **No code changes** of any kind. No refactors. No "while I was in
  there" cleanups. No formatter sweeps.
- **No Phase 2 plain-English docs.** The functional docs in
  `docs/functional/` come *after* reality is documented. Phase 1
  output is cited and precise; Phase 2 will paraphrase it into
  user-facing language.
- **No speculation.** When the code is ambiguous or unreachable from
  the surface, mark uncertainty explicitly (`uncertain — couldn't
  reach this path from main`, etc.) rather than guess.
- **No new product decisions.** Phase 1 does not pick what the system
  *should* be; it records what it *is*. Intent updates that surface
  during reading land in `docs/intent/` but stay descriptive of
  existing prior commitments (AGENTS.md, ADRs, frozen product docs)
  rather than introducing new ones.

## Success criteria — Phase 1 as a whole

Phase 1 is complete when:

1. Every directory listed in §"Four tracks" contains its full planned
   file set (see `docs/00-PHASES.md` for the locked file plan).
2. Every claim in every Phase 1 output cites at least one
   `path/to/file:NNN` reference. Non-trivial claims include a code
   excerpt.
3. `docs/code-health/00-findings.md` is the consolidated master list
   of every FIND-XXX across all per-tool categories.
4. `docs/code-health/05-fix-batches.md` contains a batching proposal
   (not yet executed fix tasks).
5. `docs/architecture-review/00-summary.md` and
   `docs/gap-analysis/00-summary.md` are the last files written in
   their tracks, summarising the seven / five sibling files
   underneath.
6. Every Phase 1 task in `docs/tasks/queue.md` reaches `pr-merged`
   status.

## Quality standards

These are non-negotiable for every Phase 1 output file:

- **Cite, don't claim.** Every factual statement carries at least
  one `path/to/file:NNN` ref. Cite the most stable identifier
  available (function name + line, class name, route path) so refs
  survive minor edits.
- **Excerpt non-trivial claims.** When the claim is more than
  "module X exists and exports Y", include the short code excerpt
  that proves it. Aim for 3–10 lines; never paste whole files.
- **No speculation.** If the code is unclear, write "unclear —
  reason" and move on. Phase 4 brainstorming can resolve it later.
- **Mark uncertainty explicitly.** Tags like `uncertain:`,
  `couldn't reach this path:`, `unused as of HEAD:` make uncertainty
  searchable.
- **Plain English over jargon.** Reality docs are read by future
  Claude sessions and by the user. Domain terms are fine; private
  shorthand is not.
- **One file per coherent unit.** Don't combine two unrelated
  components into one file just because they fit; don't split one
  coherent component across two files just for length.
- **No editorialising.** Phase 1 outputs describe; they don't praise
  or critique. Track 1b is the only place verdicts live; even there,
  the verdict is on the architectural choice, not on the code's
  author.
