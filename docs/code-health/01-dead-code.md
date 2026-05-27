# Dead Code — populated in Phase 1d

## FIND-VULTURE-001 — unsatisfiable `if False else` ternary in research-source reference validator

- **File:** `packages/domain/src/portfolio_outlook_domain/research_suggestions.py:281`
- **Tool:** `vulture 2.16`, raw output `/tmp/vulture-baseline.log` (T-052)
- **Evidence:**

  ```python
  # packages/domain/src/portfolio_outlook_domain/research_suggestions.py:278-285
  def _validate_reference(self) -> "ResearchSourceReference":
      if self.source_type in {
          ResearchSourceType.USER_URL,
          ResearchSourceType.WEBPAGE if False else ResearchSourceType.UNKNOWN,
      }:
          pass
      if (
          self.source_type
  ```

- **Why it matters (plain English):** the literal `if False else X` ternary always evaluates to `X` (here `ResearchSourceType.UNKNOWN`), so the `ResearchSourceType.WEBPAGE` branch is unreachable. The set always contains `{USER_URL, UNKNOWN}`. Already surfaced as an Open Question in `docs/reality/components/domain-research-and-suggestions.md` ("looks like leftover refactor"); independently confirmed by vulture at 100% confidence.
- **Fix approach:** drop the unreachable branch — replace with `ResearchSourceType.UNKNOWN` directly. If `WEBPAGE` was meant to be in the set, restore it; the comment context in the surrounding file suggests `WEBPAGE` belongs to a *different* enum (`ResearchDocumentType`), so the leftover form is genuinely dead.
- **Complexity:** trivial.
- **Severity:** low. The validator's `pass` body means the dead branch has no observable effect today — but it's a typed-enum red flag that will mislead future readers.
- **Related findings:** none yet; this is the only `unsatisfiable` finding emitted by vulture in this baseline.

## FIND-UNUSED-001 — three unused source files in `apps/web` (knip + ts-prune)

- **Tool:** `knip 5.x` + `ts-prune 0.10.x` — both flag the same three files. Raw outputs `/tmp/knip-baseline.txt` (lines 2-4) + `/tmp/ts-prune-baseline.txt` (lines 7, 69, 87) (T-057).
- **Files:**
  - `apps/web/app/volglijst/AssetIdentityPicker.tsx` — knip "Unused files" + ts-prune `:13 - AssetIdentityPicker`.
  - `apps/web/components/ApiUnavailableNotice.tsx` — knip "Unused files" + ts-prune `:3 - ApiUnavailableNotice`.
  - `apps/web/lib/uiText.ts` — knip "Unused files" + ts-prune `:1 - uiText`.
- **Why it matters (plain English):**
  - `AssetIdentityPicker.tsx` — appears to be an in-progress component for the Volglijst flow; not imported anywhere in `apps/web/`. Verified by `grep -r "AssetIdentityPicker" apps/web/` returning only its own file and the `app/volglijst/page.tsx` test file (the page itself uses `searchIbkrContracts` flow inline, see T-008 `web-pages.md` §3.6).
  - `ApiUnavailableNotice.tsx` — independently surfaced in T-008 `web-pages.md` §4 and `web-components-status-and-shared.md` §2 as "exists but no page imports it". Pages inline their own Dutch fallback (`"API niet bereikbaar."` etc.).
  - `uiText.ts` — a Dutch-label dictionary file; the surrounding cluster prefers per-component locked Dutch literals (see T-008 status-component microcopy survey — 40 hard-coded Dutch strings across 19 components, none referencing `uiText.ts`).
- **Fix approach:** delete the three files, OR wire them into the pages that should use them. The `ApiUnavailableNotice` case is the most interesting candidate for "wire" — its Dutch text follows the doctrine perfectly and would reduce per-page duplication.
- **Complexity:** small (delete one file each, OR small refactor to centralise the Dutch fallback).
- **Severity:** **low** — dead code that doesn't ship to the runtime bundle (Next.js tree-shakes), but it accumulates technical debt and confuses readers ("which is the canonical fallback?").
- **Related findings:** T-052 `FIND-VULTURE-001` is a similar dead-code pattern in Python; the project has no centralised dead-code policy yet.

## FIND-UNUSED-002 — seven unused exports in `app/audit/auditFormatting.ts` (knip + ts-prune)

- **Tool:** `knip` (lines 9-16) + `ts-prune` (lines 70-77). Raw outputs `/tmp/knip-baseline.txt` + `/tmp/ts-prune-baseline.txt` (T-057).
- **Unused exports:**

  | Name | File:line | knip | ts-prune |
  |---|---|---|---|
  | `displayValue` | `apps/web/app/audit/auditFormatting.ts:7` | ✓ | ✓ |
  | `linkedIdLabel` | `apps/web/app/audit/auditFormatting.ts:14` | ✓ | ✓ |
  | `recordTypeLabel` | `apps/web/app/audit/auditFormatting.ts:15` | ✓ | ✓ |
  | `chainCompletenessLabel` | `apps/web/app/audit/auditFormatting.ts:26` | ✓ | ✓ |
  | `statusQualityLabel` | `apps/web/app/audit/auditFormatting.ts:27` | ✓ | ✓ |
  | `missingMetadataFieldsLabel` | `apps/web/app/audit/auditFormatting.ts:29` | ✓ | ✓ |
  | `statusQualityBadgeClass` | `apps/web/app/audit/auditFormatting.ts:30` | ✓ | ✓ |

  (`missingLinksLabel` at `:28` is also unused but caught by the duplicate-export rule — see `FIND-KNIP-003`.)
- **Why it matters (plain English):** these are Dutch label helpers and pretty-printers for the audit detail pages (`/audit/request-logs/[id]`, etc.) that were built but never wired into the page renderers. T-008 `web-pages.md` §3.12-3.14 documents that the three audit detail pages use a separate set of formatters from `../../auditFormatting` — but the dynamic-route pages use inline JSX field grids, not these helpers. Result: 7 of 8 named exports in this file are dead.
- **Fix approach:** either wire the helpers into the audit detail pages (likely the original intent — would normalise the per-page inline label maps) or delete the unused functions. The page-by-page audit detail rendering pattern in T-008 strongly suggests the helpers were the planned shared utilities; a single PR could substitute them in and remove the inline maps.
- **Complexity:** medium — touches three audit detail pages, must preserve Dutch labels exactly.
- **Severity:** **low** — dead code only, no runtime impact (Next.js tree-shakes unused exports out of the bundle).
- **Related findings:** `FIND-KNIP-003` (duplicate export in the same file).

## FIND-UNUSED-003 — two unused exports in `lib/apiClient.ts` (knip + ts-prune)

- **Tool:** `knip` (lines 17-18, 28) + `ts-prune` (lines 8, 33). Raw outputs `/tmp/knip-baseline.txt` + `/tmp/ts-prune-baseline.txt` (T-057).
- **Unused exports:**

  | Name | Kind | File:line | knip | ts-prune |
  |---|---|---|---|---|
  | `MarketDataLatestSnapshotResponse` | type | `apps/web/lib/apiClient.ts:746` | ✓ (unused exported type) | ✓ (NOT marked "used in module" — true unused) |
  | `updateWatchlistItem` | function | `apps/web/lib/apiClient.ts:1807` | ✓ (unused export) | ✓ (NOT marked "used in module" — true unused) |
- **Why it matters (plain English):**
  - `MarketDataLatestSnapshotResponse` — was the response shape for a planned market-data UI; T-008 `web-pages.md` §3.6 confirms `getMarketDataLatestSnapshotStatus` is called from `/volglijst/page.tsx:131` but it uses `MarketDataLatestSnapshotStatusResponse` (a different type), not this one. The type is genuinely orphaned.
  - `updateWatchlistItem` — a PATCH mutation function. T-008 `web-pages.md` §3.6 confirms only `createWatchlistItem` and `archiveWatchlistItem` are called from the Volglijst page; `updateWatchlistItem` has no caller anywhere in `apps/web/`.
- **Fix approach:** delete the two exports. If a future feature needs them, the API contract on the backend still works — only the typed wrapper would be re-added.
- **Complexity:** small (two deletions in one file).
- **Severity:** **low** — dead code, no runtime impact.
- **Related findings:** `FIND-KNIP-002` (`searchAssetMasterIdentities` is a sibling case but flagged only by knip — ts-prune sees it referenced internally inside `apiClient.ts`).

## FIND-KNIP-001 — two unused devDependencies in `apps/web/package.json` (knip only)

- **Tool:** `knip 5.x`, raw output `/tmp/knip-baseline.txt:5-7` (T-057).
- **Unused devDependencies:**
  - `@testing-library/user-event` — declared at `apps/web/package.json:24` but no import anywhere in `apps/web/`.
  - `eslint-config-next` — declared at `apps/web/package.json:30` but not referenced from `apps/web/eslint.config.mjs` (which uses the flat-config import from `@next/eslint-plugin-next` directly, not the legacy `eslint-config-next` package).
- **Why it matters (plain English):** dead devDependencies bloat `node_modules` and add transitive attack surface (the `pip-audit` parallel doesn't apply here, but knip's `eslint-config-next` flag aligns with the modern flat-config migration — `eslint-config-next` is a leftover from the older `.eslintrc.json` era). `@testing-library/user-event` is likely a forgotten Phase-0 vitest dep that was superseded by direct `fireEvent` usage in current tests (confirmed by `grep -r "user-event" apps/web/components/` returning zero hits).
- **Fix approach:** remove both lines from `apps/web/package.json` devDependencies and run `npm install`. If `user-event` is later needed for a new test, re-add it on demand.
- **Complexity:** trivial (two-line `package.json` edit).
- **Severity:** **low** — installed bytes only, no shipped impact.
- **Related findings:** complements the per-file-ignore inventory in T-050 `_dismissed.md` (ruff baseline) — both are "dead config" patterns.

## FIND-KNIP-002 — one unused export `searchAssetMasterIdentities` in `lib/apiClient.ts` (knip only)

- **Tool:** `knip` (`/tmp/knip-baseline.txt:17`). ts-prune marks the same export as `(used in module)` — meaning ts-prune sees an internal reference but no external import. **knip is correct**: the internal reference is from a comment-style example or an unused helper.
- **Site:** `apps/web/lib/apiClient.ts:1782` — `function searchAssetMasterIdentities`.
- **Why it matters (plain English):** the function exposes the `/asset-master/search` endpoint as a typed wrapper, but no page calls it. T-008 `web-pages.md` documents that `/volglijst` uses `searchIbkrContracts` (`page.tsx:176`) for asset search — that's a different endpoint family (IBKR-side, not asset-master).
- **Fix approach:** delete the export. The `AssetMasterSearchRecord` type (`apiClient.ts:1771`, also flagged in `FIND-KNIP-004`) is paired with this function and would be deleted together.
- **Complexity:** small.
- **Severity:** **low**.
- **Related findings:** `FIND-KNIP-004` covers `AssetMasterSearchRecord` (the response-type sibling).

## FIND-KNIP-003 — duplicate export `missingLinksLabel | missingMetadataFieldsLabel` in `app/audit/auditFormatting.ts` (knip only)

- **Tool:** `knip` (`/tmp/knip-baseline.txt:45-46`). ts-prune marks `missingLinksLabel:28` as `(used in module)` precisely because of the duplicate-export shadowing — interesting cross-tool disagreement that **knip resolves correctly**.
- **Site:** `apps/web/app/audit/auditFormatting.ts:28-29` — `missingLinksLabel` and `missingMetadataFieldsLabel` are both exported, but knip's "Duplicate exports" check flags them together. The most likely cause is a re-export collision: either both names point at the same function body (true duplicate), or the file mistakenly re-exports both under one alias somewhere.
- **Why it matters (plain English):** TypeScript would normally surface a real duplicate-symbol error; knip's flag here indicates a *named-export-collision-via-pattern* (e.g. via `export { ... }` repeating a name, or via barrel re-export). The runtime impact is zero (TypeScript compiles either to the last declaration or errors out), but the source-of-truth is ambiguous to a reader.
- **Fix approach:** open `auditFormatting.ts:28-29` and verify whether both names export the same body or different bodies; collapse to a single export or split into two unambiguous ones.
- **Complexity:** small — single-file inspection.
- **Severity:** **low**.
- **Related findings:** `FIND-UNUSED-002` (the audit-formatting helper cluster as a whole is dead-coded).

## FIND-KNIP-004 — 24 unused exported types in `lib/apiClient.ts` (knip only)

- **Tool:** `knip` (`/tmp/knip-baseline.txt:19-44`, minus `MarketDataLatestSnapshotResponse` which is in `FIND-UNUSED-003`). ts-prune marks all 24 of these as `(used in module)` — meaning the type is referenced by *another* (also-exported) type or function inside `apiClient.ts`, but the chain ultimately has no external consumer.
- **Pattern:** these are the response-shape types for endpoints that the frontend either doesn't call, or calls but doesn't import the response type for (using inferred `Result<T>` instead).

### Inventory (file:line in `apps/web/lib/apiClient.ts`)

| Name | File:line |
|---|---|
| `ServiceStatusCard` | `:10` |
| `IntegrationCard` | `:58` |
| `ValuationInputTrace` | `:286` |
| `BriefingAlertResponse` | `:560` |
| `SchedulerJobResponse` | `:597` |
| `IbkrConnectionAuditEntry` | `:656` |
| `IbkrPositionLatestRow` | `:672` |
| `IbkrCashLatestRow` | `:696` |
| `PerAssetCoverage` | `:792` |
| `DecisionPackageGateOutcome` | `:837` |
| `DecisionPackageEvidenceReference` | `:843` |
| `IbkrSubmissionAuditRow` | `:968` |
| `IbkrExecutionRow` | `:1014` |
| `ReconciliationPassName` | `:1038` |
| `ReconciliationMode` | `:1043` |
| `ManualReviewReason` | `:1049` |
| `ManualReviewResolutionStatus` | `:1054` |
| `UnmatchedExecutionResolutionStatus` | `:1059` |
| `ReconciliationAuditRow` | `:1091` |
| `ProviderCallRow` | `:1207` |
| `ScheduledRunAuditRow` | `:1236` |
| `AssetMasterSearchRecord` | `:1771` |
| `WatchlistItem` | `:1787` |
| `WatchlistAssetListingReadiness` | `:1826` |

### Why it matters (plain English)

`apiClient.ts` is the single typed boundary between the frontend and the backend API. Most response shapes are declared even when the frontend doesn't yet render every field — that's a defensible practice (it makes the API contract explicit and ready for future UI). But 24 unused public types is enough to be worth a Phase-4 pruning pass:

- Some are "row" types used internally to compose `*ListResponse` envelopes that themselves *are* used — these are arguably correct to export (consumers might want to type individual rows). Examples: `IbkrPositionLatestRow`, `IbkrCashLatestRow`, `IbkrSubmissionAuditRow`.
- Some are pure-enum aliases (`ReconciliationPassName`, `ReconciliationMode`, `ManualReviewReason`, `ManualReviewResolutionStatus`, `UnmatchedExecutionResolutionStatus`) — useful for any consumer that wants to switch on the literal union; potentially worth keeping.
- Some are stale (`ValuationInputTrace`, `PerAssetCoverage`, `BriefingAlertResponse`) — likely orphans from earlier UI iterations.
- Some are paired with the unused function in `FIND-KNIP-002` (`AssetMasterSearchRecord`).

### Fix approach

Phase 4 brainstorm should decide a policy:

1. **Keep all "row" types exported** — they document the API contract.
2. **Delete orphan top-level response types** that have no UI consumer (e.g. `BriefingAlertResponse` if no page reads `briefing.alerts`).
3. **Delete or inline single-use enums** (the five `Reconciliation*` / `ManualReview*` / `UnmatchedExecution*` literals could be inlined at the call site).

Concrete deletion candidates from the list (response-shape orphans paired with code that doesn't read the field):

- `BriefingAlertResponse` (`:560`) — used by `DailyBriefingReadResponse` chain, but T-008 `web-pages.md` §3.2 shows `/portefeuille` renders briefing summary text only, not alerts.
- `SchedulerJobResponse` (`:597`) — superseded by Task-127 `SchedulerV127StatusResponse` (the one the frontend actually consumes per T-008 §3.2 + status-component §14 polling badge).
- `IbkrConnectionAuditEntry` (`:656`) — read-only by the worker (T-007); the frontend doesn't currently render the audit trail.
- `AssetMasterSearchRecord` (`:1771`) — paired with `FIND-KNIP-002`'s dead function.

### Complexity / severity

- Complexity to fix: **small per type** (one-line deletion) but **policy first** — see above.
- Severity: **low**. No runtime impact (types vanish at compile time). The cost is documentation drift: a reader of `apiClient.ts` sees 24 types that look usable but have no caller.

### Related findings

- `FIND-UNUSED-003` covers two more `apiClient.ts` exports flagged by both tools.
- `FIND-KNIP-002` covers the function paired with `AssetMasterSearchRecord`.
