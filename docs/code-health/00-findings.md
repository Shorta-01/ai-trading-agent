# Code-health findings — master consolidated list (Phase 1d)

This file is the single source of truth for every code-health finding raised by the T-050…T-058 baselines. Each row is a **master FIND ID** that maps to one or more per-tool entries in the per-category files (`01-dead-code.md`, `02-anti-patterns.md`, `03-outdated-patterns.md`, `04-bugs.md`).

Per-tool IDs (e.g. `FIND-VULTURE-001`, `FIND-NPMAUDIT-001`) are preserved in the per-category files as "discovered by" cross-references so historical greps still work. Going forward, refer to findings by their **master ID** (`FIND-001` … `FIND-019`).

## Severity reconciliation rule

When multiple tools flag the same file:line at different severities, the master entry uses the **MAX severity** reported across all tools. Where T-050…T-058 task specs already encoded a downgrade (e.g. T-058 "dev-only CVEs downgraded one rank"), that downgrade is preserved in the master row — the MAX rule applies between tools, not against task-spec-locked severity policy.

## Totals (Phase 1d baseline as of 2026-05-26)

### By category

| Category | Count | File |
|---|---:|---|
| dead-code | 8 | `01-dead-code.md` |
| anti-pattern | 6 | `02-anti-patterns.md` |
| outdated-pattern | 0 | `03-outdated-patterns.md` (empty) |
| bug / supply-chain | 5 | `04-bugs.md` |
| **Total** | **19** | — |

### By severity

| Severity | Count | Master IDs |
|---|---:|---|
| high | 4 | FIND-010, FIND-012, FIND-015, FIND-016 |
| medium | 3 | FIND-011, FIND-013, FIND-017 |
| low | 12 | FIND-001, FIND-002, FIND-003, FIND-004, FIND-005, FIND-006, FIND-007, FIND-008, FIND-009, FIND-014, FIND-018, FIND-019 |
| **Total** | **19** | — |

### By discovering tool

| Tool | Findings raised |
|---|---:|
| vulture | 1 (FIND-001) |
| knip + ts-prune (dual-source) | 3 (FIND-002, FIND-003, FIND-004) |
| knip (only) | 4 (FIND-005, FIND-006, FIND-007, FIND-008) |
| bandit | 1 (FIND-009) |
| radon (CC) | 2 (FIND-010, FIND-011) |
| radon (MI) | 2 (FIND-012, FIND-013) |
| tsc --noEmit | 1 (FIND-014) |
| pip-audit | 1 (FIND-015) |
| npm-audit | 4 (FIND-016, FIND-017, FIND-018, FIND-019) |
| **Total tool-rows** | **19** (no cross-tool collisions) |

**Collision analysis**: a manual file:line cross-check between the 19 findings revealed **zero file:line collisions** between FINDs. The three knip+ts-prune dual-source entries (FIND-002…FIND-004) are dual-source by design — already merged inside the per-category file before consolidation. So every master row has a single primary tool except the three dual-source rows.

## Master findings table

Columns: `master_id`, `file`, `line`, `category`, `severity`, `complexity`, `tools`, `evidence_excerpt_short`, `link`.

| master_id | file | line | category | severity | complexity | tools | evidence_excerpt_short | link |
|---|---|---|---|---|---|---|---|---|
| FIND-001 | `packages/domain/src/portfolio_outlook_domain/research_suggestions.py` | 281 | dead-code | low | trivial | vulture | Unsatisfiable `if False else` ternary; `WEBPAGE` branch unreachable, set always `{USER_URL, UNKNOWN}` | [01-dead-code.md](./01-dead-code.md#find-001-was-find-vulture-001--unsatisfiable-if-false-else-ternary-in-research-source-reference-validator) |
| FIND-002 | `apps/web/{app/volglijst/AssetIdentityPicker.tsx, components/ApiUnavailableNotice.tsx, lib/uiText.ts}` | — | dead-code | low | small | knip + ts-prune | Three unused source files; `ApiUnavailableNotice` exists but no page imports it; pages inline their own Dutch fallback | [01-dead-code.md](./01-dead-code.md#find-002-was-find-unused-001--three-unused-source-files-in-appsweb-knip--ts-prune) |
| FIND-003 | `apps/web/app/audit/auditFormatting.ts` | 7,14,15,26,27,29,30 | dead-code | low | medium | knip + ts-prune | Seven unused Dutch label helpers + pretty-printers; never wired into the 3 audit detail pages | [01-dead-code.md](./01-dead-code.md#find-003-was-find-unused-002--seven-unused-exports-in-appauditauditformattingts-knip--ts-prune) |
| FIND-004 | `apps/web/lib/apiClient.ts` | 746, 1807 | dead-code | low | small | knip + ts-prune | `MarketDataLatestSnapshotResponse` (type) + `updateWatchlistItem` (function) — no caller anywhere | [01-dead-code.md](./01-dead-code.md#find-004-was-find-unused-003--two-unused-exports-in-libapiclientts-knip--ts-prune) |
| FIND-005 | `apps/web/package.json` | 24, 30 | dead-code | low | trivial | knip | Two unused devDependencies (`@testing-library/user-event`, `eslint-config-next`). NOTE T-009 correction: `eslint-config-next` is transitively required via `next/core-web-vitals` — false positive on that entry | [01-dead-code.md](./01-dead-code.md#find-005-was-find-knip-001--two-unused-devdependencies-in-appswebpackagejson-knip-only) |
| FIND-006 | `apps/web/lib/apiClient.ts` | 1782 | dead-code | low | small | knip | Unused export `searchAssetMasterIdentities` (api uses `searchIbkrContracts`, a different endpoint family) | [01-dead-code.md](./01-dead-code.md#find-006-was-find-knip-002--one-unused-export-searchassetmasteridentities-in-libapiclientts-knip-only) |
| FIND-007 | `apps/web/app/audit/auditFormatting.ts` | 28-29 | dead-code | low | small | knip | Duplicate export `missingLinksLabel \| missingMetadataFieldsLabel` — TypeScript permits but ambiguous | [01-dead-code.md](./01-dead-code.md#find-007-was-find-knip-003--duplicate-export-missinglinkslabel--missingmetadatafieldslabel-in-appauditauditformattingts-knip-only) |
| FIND-008 | `apps/web/lib/apiClient.ts` | multiple | dead-code | low | small (per type) | knip | 24 unused exported types — internally chained but no external consumer; Phase 4 pruning candidates | [01-dead-code.md](./01-dead-code.md#find-008-was-find-knip-004--24-unused-exported-types-in-libapiclientts-knip-only) |
| FIND-009 | 8 Python files (apps/api, apps/worker, packages/portfolio, packages/storage) | 20 occurrences | anti-pattern | low | small | bandit | `assert` used for mypy type-narrowing after explicit `raise`; removable by `python -O` but currently safe because prior validation raises | [02-anti-patterns.md](./02-anti-patterns.md#find-009-was-find-bandit-001--assert-used-for-type-narrowing-in-production-paths-20-occurrences-across-8-files) |
| FIND-010 | 9 files (worker orchestrator, ibkr safety_recheck, ibkr_sync_validation, portfolio_valuation_readiness, etc.) | 10 functions | anti-pattern | **high** | medium per function | radon (CC) | 10 functions at CC rank E/F (CC 33–58); worst: `validate_ibkr_sync_payloads` + `build_portfolio_valuation_readiness` tied at CC 58 | [02-anti-patterns.md](./02-anti-patterns.md#find-010-was-find-radon-001--high-severity-cyclomatic-complexity-rank-ef-10-functions-across-9-files) |
| FIND-011 | many | 202 functions | anti-pattern | medium | small per function | radon (CC) | 202 functions at CC rank C/D (113 production + 89 tests); hottest module `status_routes.py` (14 entries) | [02-anti-patterns.md](./02-anti-patterns.md#find-011-was-find-radon-002--medium-severity-cyclomatic-complexity-rank-cd-202-functions) |
| FIND-012 | 9 modules incl. `status_routes.py`, `portfolio_valuation_readiness.py`, `sql_repositories.py`, `settings.py`, `research_sources.py` | :1 (anchor) | anti-pattern | **high** | large (module-split) | radon (MI) | 9 modules at MI rank C (MI < 10); six at MI 0.00 | [02-anti-patterns.md](./02-anti-patterns.md#find-012-was-find-radon-003--high-severity-maintainability-hotspots-mi-rank-c-9-modules) |
| FIND-013 | 8 modules in `packages/domain/`, test fixtures, and `apps/api/tests/` | :1 (anchor) | anti-pattern | medium | medium | radon (MI) | 8 modules at MI rank B (MI 10–19); 5 in `packages/domain/` are Pydantic dataclass + validator files | [02-anti-patterns.md](./02-anti-patterns.md#find-013-was-find-radon-004--medium-severity-maintainability-hotspots-mi-rank-b-8-modules) |
| FIND-014 | `apps/web/components/ActionDraftGrid.test.tsx` | 14 | anti-pattern | low | trivial (3-line fix) | tsc --noEmit | TS2739: `HAPPY` fixture missing 3 Task-134 lifecycle fields (`submission_block_reason`, `submission_started_at`, `terminal_state_at`); production unaffected (`next build` excludes `*.test.tsx`) | [02-anti-patterns.md](./02-anti-patterns.md#find-014-was-find-tsc-001--actiondraftgridtesttsx-happy-fixture-drifts-from-the-actiondraftresponse-type-ts2739-3-missing-task-134-lifecycle-fields) |
| FIND-015 | `apps/api/pyproject.toml` | 7 (the unbounded `fastapi>=0.115.0` pin) | bug | **high** | small | pip-audit | `fastapi==0.136.3` MAL-2026-4750 — malicious release with undocumented `fastar` dependency injected; blast radius theoretical today (no `fastapi[standard]` install path) but actively-running tainted release | [04-bugs.md](./04-bugs.md#find-015-was-find-pipaudit-001--fastapi01363-is-a-malicious-release-injecting-an-undocumented-fastar-dependency-mal-2026-4750) |
| FIND-016 | `apps/web/package.json` | 7 (`"next": "15.2.6"`) | bug | **high** | small (single upgrade) | npm-audit | `next@15.2.6` umbrella with 22 distinct GHSAs (9 high + 11 moderate + 2 low); fix: bump to `15.5.18`. Per T-008 + T-009 cross-ref, most exposure paths latent (no middleware, no `next/image`, no Server Actions) | [04-bugs.md](./04-bugs.md#find-016-was-find-npmaudit-001--next1526-is-exposed-to-22-distinct-ghsa-advisories-high-severity-umbrella-production-dependency) |
| FIND-017 | `apps/web/node_modules/postcss` (transitive via `next`) | — | bug | medium | small | npm-audit | `postcss@8.4.31` XSS via unescaped `</style>` in CSS stringify (`GHSA-qx2v-qp2m-jg93`); resolves with the same FIND-016 upgrade | [04-bugs.md](./04-bugs.md#find-017-was-find-npmaudit-002--postcss8431-xss-via-unescaped-style-in-css-stringify-output-moderate-transitive-via-next) |
| FIND-018 | `apps/web/node_modules/{@eslint/plugin-kit, eslint}` | — | bug | low | trivial | npm-audit | `@eslint/plugin-kit@0.2.8` + `eslint@9.17.0` ReDoS in `ConfigCommentParser` (`GHSA-xffm-g5w8-qvg7`); dev-only — original npm-audit `low` (per T-058 dev-floor severity policy) | [04-bugs.md](./04-bugs.md#find-018-was-find-npmaudit-003--eslintplugin-kit028--eslint9170-redos-in-configcommentparser-low--low-dev-only) |
| FIND-019 | `apps/web/node_modules/{esbuild, vite, @vitest/mocker, vite-node, vitest}` | — | bug | low | medium-large (breaking) | npm-audit | esbuild dev-server CSRF + vite path-traversal + 3 transitive vitest packages; dev-server only — never reaches production. Fix requires breaking vitest 2→4 upgrade. Per T-058 dev-only downgrade policy: moderate → low | [04-bugs.md](./04-bugs.md#find-019-was-find-npmaudit-004--esbuild-dev-server-csrf--vite-path-traversal--3-transitive-vitest-packages-moderate--low-dev-only) |

**Total: 19 master FIND rows.** Verifiable: `grep -c "^| FIND-" docs/code-health/00-findings.md` returns 19.

## Discovery → Master ID mapping (legacy ID lookup)

| Per-tool ID (legacy) | Master ID | Category file |
|---|---|---|
| `FIND-VULTURE-001` | FIND-001 | 01-dead-code.md |
| `FIND-UNUSED-001` | FIND-002 | 01-dead-code.md |
| `FIND-UNUSED-002` | FIND-003 | 01-dead-code.md |
| `FIND-UNUSED-003` | FIND-004 | 01-dead-code.md |
| `FIND-KNIP-001` | FIND-005 | 01-dead-code.md |
| `FIND-KNIP-002` | FIND-006 | 01-dead-code.md |
| `FIND-KNIP-003` | FIND-007 | 01-dead-code.md |
| `FIND-KNIP-004` | FIND-008 | 01-dead-code.md |
| `FIND-BANDIT-001` | FIND-009 | 02-anti-patterns.md |
| `FIND-RADON-001` | FIND-010 | 02-anti-patterns.md |
| `FIND-RADON-002` | FIND-011 | 02-anti-patterns.md |
| `FIND-RADON-003` | FIND-012 | 02-anti-patterns.md |
| `FIND-RADON-004` | FIND-013 | 02-anti-patterns.md |
| `FIND-TSC-001` | FIND-014 | 02-anti-patterns.md |
| `FIND-PIPAUDIT-001` | FIND-015 | 04-bugs.md |
| `FIND-NPMAUDIT-001` | FIND-016 | 04-bugs.md |
| `FIND-NPMAUDIT-002` | FIND-017 | 04-bugs.md |
| `FIND-NPMAUDIT-003` | FIND-018 | 04-bugs.md |
| `FIND-NPMAUDIT-004` | FIND-019 | 04-bugs.md |

## Master-ID assignment rule (locked, reproducible)

Per T-059 spec: walk per-category files in numerical order (`01` → `04`); within each file walk by per-tool ID alphanumeric order (since the per-category files already display findings in that order). Master IDs are assigned sequentially. This rule produces the mapping above and is reproducible from any future re-run of T-059.

## Notes for downstream consumers

- **Severity column** is the locked T-NNN-baseline-task severity. Where the master row should use a tool-MAX (no collisions occurred this round), no override was needed.
- **Complexity column** is the "complexity to fix" estimate from the per-category FIND's body, summarised as trivial / small / medium / large.
- **The 4 HIGH-severity findings** are the prime Phase 4 batching candidates (T-060): two are runtime-dependency upgrades with clean paths (FIND-015 `fastapi`, FIND-016 `next`), and two are large structural pieces (FIND-010 high-CC functions, FIND-012 module splits).
- **The 4 false-positive-adjacent findings** are flagged in their per-category FIND bodies but kept in the master list for completeness: FIND-005 (`eslint-config-next` is transitively used — T-009 correction); FIND-007 (TypeScript would normally surface a real duplicate-symbol error, so this is shadow-export pattern); FIND-009 (assert-for-mypy-narrowing is safe today but `python -O` fragile); FIND-014 (production unaffected).

## How to extend this file

When a new baseline task (T-NNN) raises new findings:

1. Add each per-tool finding to the appropriate `0N-*.md` per-category file using its per-tool ID (e.g. `FIND-NEWTOOL-001`).
2. Open a consolidation PR that:
   - Allocates the next master IDs (continuing from FIND-020).
   - Inserts rows into this master table in the assignment order rule above.
   - Updates the totals blocks.
   - Adds the master-ID anchor link at the top of each new per-tool entry.
   - Updates the discovery-mapping table.
