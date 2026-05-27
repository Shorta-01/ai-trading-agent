# Fix Batches — proposal (Phase 1d, end-of-track)

This document proposes how the 19 master FINDs in `00-findings.md` should be grouped into PR-sized fix tasks. **It does NOT create queue rows** — the user reviews this proposal and decides which batches to convert into `source: code-health` tasks in `docs/tasks/queue.md`.

## Batching rule (locked, verbatim from T-060 spec)

- **Same file (or same package) + same category = one batch.**
- **Severity `critical` and `high` get their own batch each, no bundling.**
- **Complexity `trivial` may bundle up to 20 findings.**
- **Complexity `small` may bundle up to 10 findings.**
- **Complexity `medium` may bundle up to 5 findings.**
- **Complexity `large` runs solo (one batch per finding).**

Per-batch severity = MAX of member findings. Per-batch complexity = MAX of member findings. When a single file accumulates findings from multiple categories, propose separate batches per category (one tool's output per PR is easier to review).

## Proposal — 15 batches covering 19 FINDs

The 19 master FINDs from `00-findings.md` group into **15 batches**: 4 high-severity solo batches (per rule), 3 medium-severity solo batches (no in-file siblings), and 8 low-severity batches (3 bundled + 5 solo).

### BATCH-001 — Refactor 10 high-CC functions (rank E/F, CC 33–58)

- **Severity (max of members):** **high**
- **Complexity (max of members):** medium (per function)
- **FIND IDs:** FIND-010
- **Total finding count:** 1 master FIND covering 10 functions across 9 files.
- **File / package scope:** `apps/api/{ibkr_sync_validation, portfolio_valuation_readiness, ibkr_sync, decision_package_sync, market_data_sync, status_routes}.py` + `apps/worker/{orchestrator, ibkr_submission/safety_recheck}.py` + `packages/portfolio/{predictor_feedback, action_draft_safety}.py`.
- **Proposed approach:** extract inner branching per function into named helpers; target CC ≤ 10 per refactored helper; **safety-critical functions first** (`evaluate_submission_gates`, `build_portfolio_valuation_readiness`, `validate_ibkr_sync_payloads`). Solo per "high gets its own batch" rule + "no behaviour change" discipline — every refactor PR needs unit tests asserting the input/output table is unchanged.
- **Proposed task slug:** `task/T-NNN-refactor-high-cc-functions`
- **Notes:** likely too large for a single PR even after the rule; the user may want to sub-batch this further at queue-creation time (e.g. one PR per file, prioritised safety-critical first).

### BATCH-002 — Module splits for 9 low-MI modules

- **Severity:** **high**
- **Complexity:** large
- **FIND IDs:** FIND-012
- **Total finding count:** 1 master FIND covering 9 modules.
- **File / package scope:** `apps/api/{status_routes, portfolio_valuation_readiness, research_sources}.py` + 3 tests under `apps/api/tests/` + `packages/storage/.../sql_repositories.py` + `packages/storage/tests/test_sql_repositories.py` + `packages/domain/.../settings.py`.
- **Proposed approach:** module-split is the only reliable lever for MI = 0.00 modules. Split `status_routes.py` into per-cluster routers (infra / IBKR / forecast / actions per T-006); split `portfolio_valuation_readiness.py` into builder + sub-readiness modules; split `sql_repositories.py` into per-aggregate repository files. The natural cluster boundaries are already documented in T-006 / T-003 reality docs. **Large = solo per rule.**
- **Proposed task slug:** `task/T-NNN-split-low-mi-modules`
- **Notes:** large structural change — likely sub-batched at queue-creation time (one module-split per PR).

### BATCH-003 — Pin away from `fastapi==0.136.3` MAL-2026-4750

- **Severity:** **high**
- **Complexity:** small
- **FIND IDs:** FIND-015
- **Total finding count:** 1.
- **File / package scope:** `apps/api/pyproject.toml:7` (the unbounded `fastapi>=0.115.0` pin that resolved to the malicious release).
- **Proposed approach:** change `"fastapi>=0.115.0"` to a bounded range (e.g. `"fastapi>=0.115.0,<0.136"` or pin a specific known-clean version like `"fastapi==0.115.6"`). Refresh the venv. Solo per "high gets its own batch".
- **Proposed task slug:** `task/T-NNN-pin-fastapi-away-from-mal-release`
- **Notes:** Phase 4 follow-up to wire `pip-audit` against the lockfile at merge time is a separate task — explicitly out of scope per the FIND-015 body.

### BATCH-004 — Bump `next` 15.2.6 → 15.5.18

- **Severity:** **high**
- **Complexity:** small
- **FIND IDs:** FIND-016
- **Total finding count:** 1 master FIND covering 22 GHSAs rolled up under `next`.
- **File / package scope:** `apps/web/package.json:7` (`"next": "15.2.6"`).
- **Proposed approach:** `npm install next@15.5.18 --legacy-peer-deps`; smoke-test via the existing Playwright suite (`apps/web/playwright.config.ts:25`). 22 GHSAs resolve wholesale. Solo per "high gets its own batch".
- **Proposed task slug:** `task/T-NNN-bump-next-15-5-18`
- **Notes:** BATCH-007 (`postcss` XSS) resolves automatically when this batch lands — `postcss` is transitive via `next`. The user could choose to merge BATCH-004 + BATCH-007 into a single PR despite the "same package" rule blocking automatic bundling (different npm packages even though they update in lockstep). Recommend leaving as proposed (separate batches) to keep audit trails clean per FIND.

### BATCH-005 — Refactor 202 medium-CC functions (rank C/D)

- **Severity:** medium
- **Complexity:** small (per function)
- **FIND IDs:** FIND-011
- **Total finding count:** 1 master FIND covering 202 functions.
- **File / package scope:** spread across `apps/{api,worker}/src` + `packages/portfolio/src` + a heavy tail in `apps/api/src/.../status_routes.py` (14 entries). 113 in production, 89 in test files.
- **Proposed approach:** small-per-function extraction; lower priority than BATCH-001. Solo because single master FIND, but **the user almost certainly wants to sub-batch this at queue-creation time** — e.g. one PR per top-3 file (status_routes.py: 14 entries, test_market_data_readiness_endpoint.py: 6, test_alembic_skeleton.py: 5). Tests deserve a different fix approach (split into `pytest.mark.parametrize`) than production code (helper extraction). Pydantic `validate_*` methods (23 entries in `packages/domain/`) may even be dismissible per-site after review.
- **Proposed task slug:** `task/T-NNN-refactor-medium-cc-functions`
- **Notes:** 202 findings in one master batch is the largest in the proposal; the rule does not bound a single-FIND batch by count, but a "one PR per file" sub-batching is the obvious next step.

### BATCH-006 — Module splits for 8 medium-MI modules

- **Severity:** medium
- **Complexity:** medium
- **FIND IDs:** FIND-013
- **Total finding count:** 1 master FIND covering 8 modules.
- **File / package scope:** 5 modules in `packages/domain/` (`broker_reconciliation.py`, `suggestion_engine.py`, `storage.py`, `research_library.py`, `research_suggestions.py`) + 3 test files in `apps/api/tests/` + `packages/storage/tests/`.
- **Proposed approach:** same as BATCH-002 but lower urgency. Domain splits are mostly mechanical — `broker_reconciliation.py` → reconciliation + execution sub-files, `suggestion_engine.py` → engine + gate evaluation, etc.
- **Proposed task slug:** `task/T-NNN-split-medium-mi-modules`
- **Notes:** 5 Pydantic domain modules + 3 test modules — splitting tests follows the production-split, so the user may sequence "domain split → test split" as two PRs.

### BATCH-007 — postcss XSS upgrade (transitive via `next`)

- **Severity:** medium
- **Complexity:** small
- **FIND IDs:** FIND-017
- **Total finding count:** 1.
- **File / package scope:** `apps/web/node_modules/postcss` (transitive via `next`).
- **Proposed approach:** **Resolves automatically when BATCH-004 lands** (`next` 15.5.18 transitively bumps `postcss` to ≥8.5.10). The user could choose to skip this batch if BATCH-004 has already landed by the time queue rows are created. If kept separate, it's still a single `npm install` against the lockfile.
- **Proposed task slug:** `task/T-NNN-bump-postcss-via-next-upgrade` (or merge into BATCH-004 at queue time)
- **Notes:** Single FIND, no sibling in the same package — solo by default.

### BATCH-008 — `apps/web/app/audit/auditFormatting.ts` dead-code (same file)

- **Severity:** low
- **Complexity (max):** medium (FIND-003 is medium; FIND-007 is small)
- **FIND IDs:** FIND-003, FIND-007
- **Total finding count:** 2 master FINDs covering 7 unused Dutch label helpers + 1 duplicate-export.
- **File / package scope:** single file — `apps/web/app/audit/auditFormatting.ts`.
- **Proposed approach:** either wire the helpers into the 3 audit detail pages (normalises the per-page inline label maps per T-008 §3.12-3.14) OR delete the unused functions. The wiring option is the planned-intent reading; the deletion option is the minimum-PR reading. The duplicate-export `missingLinksLabel|missingMetadataFieldsLabel` (FIND-007) is resolved as a side-effect of either approach.
- **Proposed task slug:** `task/T-NNN-cleanup-auditformatting-dead-code`
- **Notes:** bundled per "same file + same category" rule. 2 FINDs within medium-complexity bundle limit (max 5).

### BATCH-009 — `apps/web/lib/apiClient.ts` dead-code (same file)

- **Severity:** low
- **Complexity:** small (all members are small)
- **FIND IDs:** FIND-004, FIND-006, FIND-008
- **Total finding count:** 3 master FINDs covering 1 unused type + 2 unused functions + 24 unused exported types.
- **File / package scope:** single file — `apps/web/lib/apiClient.ts`.
- **Proposed approach:** delete the 2 unused exports (FIND-004: `MarketDataLatestSnapshotResponse:746` + `updateWatchlistItem:1807`) and the orphan `searchAssetMasterIdentities:1782` (FIND-006). For the 24 unused exported types (FIND-008), the user should decide a policy first — see FIND-008 body for the three Phase-4-decision options (keep all row-types exported / delete orphan response types / inline single-use enums). Without a policy decision, FIND-008 cannot be safely batched.
- **Proposed task slug:** `task/T-NNN-cleanup-apiclient-dead-exports`
- **Notes:** 3 FINDs within small-complexity bundle limit (max 10). At queue-creation time, the user may want to split this into "uncontroversial deletions" (FIND-004 + FIND-006) and "policy-dependent type pruning" (FIND-008).

### BATCH-010 — `apps/web/` "delete unused" (same package)

- **Severity:** low
- **Complexity:** small (FIND-002 is small; FIND-005 is trivial)
- **FIND IDs:** FIND-002, FIND-005
- **Total finding count:** 2 master FINDs covering 3 unused source files + 2 unused devDependencies (one of which is a false positive — see notes).
- **File / package scope:** `apps/web/` (mixed: 3 source files + `package.json` devDeps).
- **Proposed approach:** delete `apps/web/{app/volglijst/AssetIdentityPicker.tsx, components/ApiUnavailableNotice.tsx, lib/uiText.ts}` (FIND-002). Delete `@testing-library/user-event` from `apps/web/package.json:24` (FIND-005). **DO NOT delete `eslint-config-next`** from `:30` — T-009 `web-api-client-and-text.md` §8 documents that this devDep is transitively required via `next/core-web-vitals` despite knip's flag. The "delete only" core of FIND-005 is the user-event devDep.
- **Proposed task slug:** `task/T-NNN-cleanup-apps-web-unused`
- **Notes:** bundled per "same package + same category" rule. 2 FINDs within small-complexity bundle limit. Mixed file types but all delete-only changes.

### BATCH-011 — Trivial Python dead-code fix

- **Severity:** low
- **Complexity:** trivial
- **FIND IDs:** FIND-001
- **Total finding count:** 1.
- **File / package scope:** `packages/domain/src/portfolio_outlook_domain/research_suggestions.py:281`.
- **Proposed approach:** drop the unreachable `WEBPAGE if False else UNKNOWN` ternary branch — replace with `ResearchSourceType.UNKNOWN` directly. One-line change.
- **Proposed task slug:** `task/T-NNN-remove-unsatisfiable-ternary`
- **Notes:** single FIND, single file in `packages/domain/`. No siblings in the same file with same category (the rest of `packages/domain/` has no dead-code FINDs).

### BATCH-012 — Bandit B101 assert-for-narrowing cleanup (20 sites)

- **Severity:** low
- **Complexity:** small (per-site one-line swap)
- **FIND IDs:** FIND-009
- **Total finding count:** 1 master FIND covering 20 occurrences across 8 files.
- **File / package scope:** spread across `apps/{api,worker}` + `packages/{portfolio,storage}`. Eight distinct files; not bundleable into one file-scope batch.
- **Proposed approach:** per-site swap — `if x is None: raise RuntimeError(...)` or `typing.cast(T, x)` depending on whether the assert documents an invariant or a post-validation guarantee. **At queue-creation time, sub-batch by file** (8 files → 8 PRs, or grouped by package). Most files have only 1-2 sites; `action_draft.py` has 9.
- **Proposed task slug:** `task/T-NNN-cleanup-b101-asserts`
- **Notes:** sub-batching at queue time recommended. The 9 asserts in `apps/api/src/portfolio_outlook_api/action_draft.py` could be one PR; the 4 in `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py` another; the remaining 7 single-occurrence files together.

### BATCH-013 — TS2739 test-fixture drift in `ActionDraftGrid.test.tsx`

- **Severity:** low
- **Complexity:** trivial (3-line addition)
- **FIND IDs:** FIND-014
- **Total finding count:** 1.
- **File / package scope:** `apps/web/components/ActionDraftGrid.test.tsx:14`.
- **Proposed approach:** add `submission_block_reason: null, submission_started_at: null, terminal_state_at: null` to the `HAPPY` fixture. One-PR trivial fix.
- **Proposed task slug:** `task/T-NNN-fix-actiondraftgrid-test-fixture`
- **Notes:** solo despite trivial complexity — no other trivial anti-pattern FIND in the same `apps/web/components/` file scope to bundle with (FIND-014 is the only test-file FIND).

### BATCH-014 — eslint chain ReDoS dev-dep bump

- **Severity:** low
- **Complexity:** trivial
- **FIND IDs:** FIND-018
- **Total finding count:** 1 (covers 2 packages: `@eslint/plugin-kit` + `eslint`).
- **File / package scope:** `apps/web/node_modules/{@eslint/plugin-kit, eslint}` (transitive resolution via `apps/web/package.json` devDeps).
- **Proposed approach:** `npm install --save-dev --legacy-peer-deps eslint@9.39.4` — transitive `@eslint/plugin-kit` bump comes along. Verify ESLint flat-config plugins still load. Solo because no other trivial-complexity dev-dep finding in the same package to bundle with.
- **Proposed task slug:** `task/T-NNN-bump-eslint-redos-fix`
- **Notes:** Could in principle be bundled with BATCH-010's `@testing-library/user-event` removal (both `apps/web/` devDep manipulation), but the eslint chain is a bump (different mechanic) and crosses dead-code/bug category boundary — per rule, same-file/package AND same-category → separate batches.

### BATCH-015 — vitest 2→4 breaking upgrade

- **Severity:** low
- **Complexity:** medium-large (breaking)
- **FIND IDs:** FIND-019
- **Total finding count:** 1 master FIND covering 5 packages (`esbuild`, `vite`, `@vitest/mocker`, `vite-node`, `vitest`).
- **File / package scope:** `apps/web/node_modules/{esbuild, vite, @vitest/mocker, vite-node, vitest}` (transitive resolution via `apps/web/package.json:30` `"vitest": "^2.1.9"`).
- **Proposed approach:** the conservative path is `vitest@3.x` (smaller test-API drift than vitest 4); the `npm audit fix --force` path is vitest 4.1.7 (two majors ahead). **At queue-creation time**, the user should decide between (a) conservative manual bump to 3.x, (b) aggressive `--force` to 4.1.7, or (c) status-quo accept dev-only LOW until a tooling brainstorm. Solo per "large runs solo" rule (treating medium-large as solo).
- **Proposed task slug:** `task/T-NNN-bump-vitest-chain`
- **Notes:** breaking change. The 4 transitive packages (esbuild / vite / @vitest/mocker / vite-node) resolve in lockstep when `vitest` upgrades — they're not separately fixable.

## Closing summary table

| Batch ID | Severity | Complexity | FIND count | Member FINDs | Proposed task slug |
|---|---|---|---:|---|---|
| BATCH-001 | high | medium | 1 (covers 10 functions) | FIND-010 | `refactor-high-cc-functions` |
| BATCH-002 | high | large | 1 (covers 9 modules) | FIND-012 | `split-low-mi-modules` |
| BATCH-003 | high | small | 1 | FIND-015 | `pin-fastapi-away-from-mal-release` |
| BATCH-004 | high | small | 1 (covers 22 GHSAs) | FIND-016 | `bump-next-15-5-18` |
| BATCH-005 | medium | small | 1 (covers 202 functions) | FIND-011 | `refactor-medium-cc-functions` |
| BATCH-006 | medium | medium | 1 (covers 8 modules) | FIND-013 | `split-medium-mi-modules` |
| BATCH-007 | medium | small | 1 | FIND-017 | `bump-postcss-via-next-upgrade` |
| BATCH-008 | low | medium | 2 | FIND-003, FIND-007 | `cleanup-auditformatting-dead-code` |
| BATCH-009 | low | small | 3 | FIND-004, FIND-006, FIND-008 | `cleanup-apiclient-dead-exports` |
| BATCH-010 | low | small | 2 | FIND-002, FIND-005 | `cleanup-apps-web-unused` |
| BATCH-011 | low | trivial | 1 | FIND-001 | `remove-unsatisfiable-ternary` |
| BATCH-012 | low | small | 1 (covers 20 sites in 8 files) | FIND-009 | `cleanup-b101-asserts` |
| BATCH-013 | low | trivial | 1 | FIND-014 | `fix-actiondraftgrid-test-fixture` |
| BATCH-014 | low | trivial | 1 | FIND-018 | `bump-eslint-redos-fix` |
| BATCH-015 | low | medium-large | 1 (covers 5 packages) | FIND-019 | `bump-vitest-chain` |
| **Total** | — | — | **19 FINDs** | — | **15 batches** |

## FIND → BATCH coverage proof (verification)

Every master FIND in `00-findings.md` appears in exactly one batch:

| FIND | Batch |
|---|---|
| FIND-001 | BATCH-011 |
| FIND-002 | BATCH-010 |
| FIND-003 | BATCH-008 |
| FIND-004 | BATCH-009 |
| FIND-005 | BATCH-010 |
| FIND-006 | BATCH-009 |
| FIND-007 | BATCH-008 |
| FIND-008 | BATCH-009 |
| FIND-009 | BATCH-012 |
| FIND-010 | BATCH-001 |
| FIND-011 | BATCH-005 |
| FIND-012 | BATCH-002 |
| FIND-013 | BATCH-006 |
| FIND-014 | BATCH-013 |
| FIND-015 | BATCH-003 |
| FIND-016 | BATCH-004 |
| FIND-017 | BATCH-007 |
| FIND-018 | BATCH-014 |
| FIND-019 | BATCH-015 |

**Count check**: 19 distinct FIND IDs, each appears exactly once → ✓.

## Sequencing recommendations (advisory, not part of the locked rule)

If the user wants a recommended landing order for Phase 4 fix tasks:

1. **BATCH-003** (fastapi MAL pin) — supply-chain malicious release; quick fix; high.
2. **BATCH-004** (next 15.5.18 bump) — supply-chain umbrella; smoke-test risk is low because the production exposure surface is mitigated by the project's runtime configuration (see FIND-016 body). Resolves BATCH-007 as a side-effect.
3. **BATCH-011** (one-line unreachable-ternary) — clean signal.
4. **BATCH-013** (one-line test fixture) — clean signal.
5. **BATCH-008** + **BATCH-009** + **BATCH-010** (apps/web dead-code cleanup) — sequence per logical scope; small risk.
6. **BATCH-012** (B101 asserts) — sub-batched per file; cumulative gain.
7. **BATCH-001** + **BATCH-002** (high-severity CC + MI refactors) — large, behaviour-preserving; expect multiple sub-PRs.
8. **BATCH-005** + **BATCH-006** (medium-CC + medium-MI) — only after the high-severity refactors are stable.
9. **BATCH-014** + **BATCH-015** (eslint + vitest dev-dep bumps) — dev-tooling refresh; can land anytime after the trivials.

## Out of scope for this document

- **No queue rows added.** Per the T-060 spec, this proposal is reviewed first; queue rows are created as a separate decision.
- **No code modification.**
- **No batching rule adjustment.** The rules at the top are locked; deviation requires a separate decision.

## Cross-cuts

- The 4 HIGH-severity batches (BATCH-001 … BATCH-004) are the natural Phase 4 anchor — they cover the 4 high-severity FINDs identified at the bottom of `00-findings.md` ("prime Phase 4 batching candidates").
- The 3 false-positive-adjacent annotations from the master list are preserved in their respective batches: FIND-005's `eslint-config-next` exclusion noted in BATCH-010; FIND-008's policy-decision dependency noted in BATCH-009; FIND-014's "production unaffected" noted in BATCH-013.
- **Largest single batch is BATCH-005 (202 functions).** Sub-batching at queue-creation time recommended.
- **The "same package" rule** was applied conservatively: `apps/web/` is treated as one npm package (so BATCH-010 bundles 2 FINDs across source and `package.json`), but the npm transitive packages (`next` vs `postcss`, `eslint` vs `@eslint/plugin-kit`, `vitest` vs `esbuild`) are treated as separate packages despite shared upgrade paths. This keeps the audit trail clean per-FIND.
