```yaml
id: T-060
title: Produce batching proposal in `05-fix-batches.md`
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/455
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/00-findings.md` (T-059 master, 19 FINDs across 4 categories) read; the four per-category files (`01-dead-code.md`, `02-anti-patterns.md`, `03-outdated-patterns.md`, `04-bugs.md`) already familiar from T-050…T-059; `05-fix-batches.md` (1-line stub) is the target file. No source files in touch scope.
- **Step 2 (one-line per touched file):**
  - `05-fix-batches.md` — pre-edit: 1-line stub; post-edit: full batching proposal with 15 batches covering all 19 FINDs, per-batch severity/complexity rollup, closing summary table, FIND→BATCH coverage proof.
  - No queue.md modification per task spec ("**No fix-task rows added to `docs/tasks/queue.md`**").
- **Step 3 (one-line change):** group the 19 master FINDs into 15 proposed batches per the locked rules (high gets solo; same file + same category bundles up to complexity-bounded limits).
- **Step 4 (measurable):** yes — six acceptance criteria: locked batching rule restated verbatim; every FIND in `00-findings.md` appears in exactly one batch (set-diff verifiable, 19 in → 19 out); each batch carries proposed title + severity + complexity + FIND IDs + count + scope summary; closing table with batch ID → severity → complexity → count → proposed task slug; no fix-task rows added to `queue.md`.
- **Step 5 (out-of-scope does not block goal):** confirmed — no fixing of any finding; no queue rows added; no adjustment of batching rules (locked).

## Goal

From the consolidated `00-findings.md`, propose how findings should be grouped into fix tasks. Output a single document `docs/code-health/05-fix-batches.md`. **Do not yet create the fix tasks in `docs/tasks/queue.md`** — the user reviews the batching proposal first.

## Context

`depends_on:` T-059 (consolidation must be `pr-merged`). This is the last Phase 1d task. After this PR merges, the user reviews `05-fix-batches.md` and decides which proposed batches to convert into fix tasks (those tasks will be `source: code-health` with their `findings:` list filled in).

## Touch scope

Modify:
- `docs/code-health/05-fix-batches.md`

Read: `docs/code-health/00-findings.md` (master list), all four per-category files.

## Acceptance criteria

- [ ] `05-fix-batches.md` opens with the batching rule, restated verbatim:
  - same file (or same package) + same category = one batch
  - severity `critical` and `high` get their own batch each, no bundling
  - complexity `trivial` may bundle up to 20 findings
  - complexity `small` may bundle up to 10 findings
  - complexity `medium` may bundle up to 5 findings
  - complexity `large` runs solo (one batch per finding)
- [ ] Every FIND in `00-findings.md` appears in exactly one proposed batch.
- [ ] Each batch has: proposed title (short imperative), proposed `severity` (= max of batch members), proposed `complexity` (= max of batch members), list of FIND IDs, total finding count, file/package scope summary.
- [ ] Closing summary table: batch ID → severity → complexity → FIND count → proposed task slug.
- [ ] **No fix-task rows added to `docs/tasks/queue.md`.** Adding the actual fix tasks is a separate decision the user makes after reviewing this document.

## Out of scope

- Fixing anything.
- Creating queue rows.
- Adjusting batching rules (those are locked above; deviation requires a separate decision).

## Verification

- Every FIND ID in `00-findings.md` appears in exactly one batch in `05-fix-batches.md` (run set-diff).
- No new rows in `docs/tasks/queue.md`.

## Notes

When a single file accumulates findings from multiple categories (e.g. a single module has dead code AND anti-patterns AND a bug), propose separate batches per category — easier to scope each PR around one tool's output.

Proposed batch ID format: `BATCH-NNN` (zero-padded sequential).
