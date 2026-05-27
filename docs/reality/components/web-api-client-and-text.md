# Reality — web API client + locked-text + config

**Scope.** The frontend's typed HTTP boundary (`apps/web/lib/apiClient.ts`), the locked Dutch text registry (`apps/web/lib/uiText.ts`), and the five Next.js / Playwright / Vitest / ESLint config files. T-008 documents how pages and components consume `apiClient`; this doc documents the client itself.

Sibling docs:

- `docs/reality/components/web-pages.md` — how pages call `apiClient.*` and render its responses (T-008).
- `docs/reality/components/web-components-status-and-shared.md`, `…-feature-grids.md` — how components consume `apiClient`.
- `docs/reality/components/infra-docker-and-compose.md` — how the build artefact is shipped (T-009).
- `docs/reality/components/build-ci-and-scripts.md` — how the lint/build/test pipeline runs it.

## In-scope files

| File | Lines | Role |
|---|---:|---|
| `apps/web/lib/apiClient.ts` | 1879 | Typed HTTP client — ~90 methods + 92 exported types |
| `apps/web/lib/uiText.ts` | 9 | Locked Dutch text registry (5 keys, `as const`) |
| `apps/web/next.config.ts` | 7 | Minimal Next.js config |
| `apps/web/playwright.config.ts` | 38 | Playwright e2e config (chromium-only smoke) |
| `apps/web/vitest.config.ts` | 20 | Vitest unit-test config (jsdom) |
| `apps/web/eslint.config.mjs` | 19 | ESLint flat-config via `next/core-web-vitals` |
| `apps/web/vitest.setup.ts` | 1 | One-line jest-dom registration |

Total: **1973 lines**.

## 1. `apiClient.ts` — architecture

### Two discriminated-union response wrappers

- **`FetchState<T>`** (`apiClient.ts:1-3`): `{ ok: true; data: T } | { ok: false; reason: "not_reachable" }` — collapses every failure to a single `reason`. Used by methods that go through `getJson` / `putJson` / `postJson`.
- **`ApiResult<T>`** (`apiClient.ts:5-8`): `{ ok: true; data: T } | { ok: false; status: number; message: string } | { ok: false; status: 0; message: "API niet bereikbaar." }` — preserves HTTP status + Dutch `detail` string. Used by methods that go through `requestJson` / `postFormData`.

The two wrappers coexist by design: status-tolerant fetches (where the caller only needs to know "did we reach the server?") use `FetchState`; mutations that must surface backend Dutch error strings use `ApiResult`.

### Base URL strategy

Single module-level constant:

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
```

(`apiClient.ts:1354`).

### Four `fetch` wrappers

| Wrapper | File:line | HTTP verbs | Returns | Notes |
|---|---|---|---|---|
| `getJson<T>(path)` | `:1356-1361` | GET | `FetchState<T>` | `cache: "no-store"`; collapses errors to `"not_reachable"`. |
| `putJson<T>(path, body)` | `:1363-1369` | PUT | `FetchState<T>` | JSON body. |
| `postJson<T>(path, body?)` | `:1371-1383` | POST | `FetchState<T>` | `body ?? {}`. |
| `postFormData<T>(path, formData)` | `:1387-1405` | POST | `ApiResult<T>` | Multipart; surfaces backend `detail` string; Dutch fallbacks. |
| `requestJson<T>(path, method, body?)` | `:1407-1428` | GET/POST/PUT/PATCH/DELETE | `ApiResult<T>` | Generic dispatcher; GET uses `cache: "no-store"`; same Dutch fallbacks. |

Two outliers inline raw `fetch` (PATCH/DELETE without going through `requestJson`): `updateWatchlistItem` (`:1807`) and `archiveWatchlistItem` (`:1808`) — both wrapped to return `FetchState<T>` shape.

### Hard constraints

- **No timeouts.** No `AbortController`, no `AbortSignal`, no `signal:` field.
- **No retries.** Single-shot per call.
- **No global cache, no SWR, no React Query.** Cross-references T-008 `web-pages.md` §4: page-level fetches are hand-rolled `useEffect` + `useState`; the client itself has no caching layer either.
- **Error model**: uniform `try { fetch(...) } catch { return error variant }`. JSON parse errors swallowed by `.catch(() => ({}))` (`:1393, :1422`).
- **Cache header**: GETs always `cache: "no-store"` (`:1357, :1420`); writes leave it unset.
- **Dutch error strings come from the backend.** `postFormData` / `requestJson` extract `payload.detail` (`:1395-1397, :1422-1424`); transport failures fall back to `"API niet bereikbaar."` / `"Onbekende fout."`.

## 2. `apiClient.ts` — method catalogue (~90 callables)

All methods live in the single `apiClient` object literal (`apiClient.ts:1430-1764`) plus eight loose `export async function` declarations after it (`apiClient.ts:1782-1877`). Grouped by route family:

### System / Settings / Storage / Integrations

| Method | File:line | HTTP + path | Return |
|---|---|---|---|
| `getSystemStatus()` | `:1431` | `GET /system/status` | `FetchState<SystemStatusSummary>` |
| `getSettingsSummary()` | `:1432` | `GET /settings/summary` | `FetchState<SettingsSummary>` |
| `getAiUsageSummary()` | `:1433` | `GET /usage/ai/summary` | `FetchState<AiUsageSummary>` |
| `getIntegrationsSummary()` | `:1434` | `GET /integrations/summary` | `FetchState<IntegrationsSummary>` |
| `getStorageStatus()` | `:1435` | `GET /storage/status` | `FetchState<StorageStatusSummary>` |
| `getTradingSettings()` | `:1436` | `GET /settings/trading` | `FetchState<TradingSettingsResponse>` |
| `updateTradingSettings(payload)` | `:1713` | `PUT /settings/trading` | `FetchState<TradingSettingsResponse>` |
| `getActiveSystemEvents()` | `:1714` | `GET /system/events/active` | `FetchState<ActiveSystemEventsResponse>` |
| `resolveSystemEvent(id, payload?)` | `:1715` | `POST /system/events/{id}/resolve` | `FetchState<{success}>` |
| `archiveSystemEvent(id, payload?)` | `:1717` | `POST /system/events/{id}/archive` | `FetchState<{success}>` |

### IBKR (status, sync, snapshots, connection audit)

| Method | File:line | HTTP + path |
|---|---|---|
| `getIbkrStatus()` | `:1437` | `GET /broker/ibkr/status` |
| `getIbkrSyncStatus()` | `:1438` | `GET /ibkr/sync/status` |
| `getIbkrPositions()` | `:1440` | `GET /ibkr/portfolio/positions` |
| `getIbkrCash()` | `:1441` | `GET /ibkr/account/cash` |
| `getIbkrOpenOrders()` | `:1442` | `GET /ibkr/orders/open` |
| `getIbkrExecutions()` | `:1443` | `GET /ibkr/executions` |
| `getIbkrAccountMode()` | `:1469` | `GET /ibkr/account/mode` |
| `getIbkrConnectionStatus()` | `:1470` | `GET /ibkr/connection/status` |
| `getIbkrConnectionAudit(limit=20)` | `:1472` | `GET /ibkr/connection/audit?limit=N` |
| `getIbkrSyncPositionsLatest()` | `:1476` | `GET /ibkr/sync/positions/latest` |
| `getIbkrSyncCashLatest()` | `:1478` | `GET /ibkr/sync/cash/latest` |
| `runIbkrSync()` | `:1712` | `POST /ibkr/sync/run` |

### Portfolio valuation

| Method | File:line | HTTP + path |
|---|---|---|
| `getPortfolioValuationReadiness()` | `:1439` | `GET /portfolio/valuation/readiness` |

### Forecast (legacy + new asset-centric)

| Method | File:line | HTTP + path |
|---|---|---|
| `getLatestForecasts()` | `:1444` | `GET /forecasts/latest` |
| `runForecastSync()` | `:1445` | `POST /forecasts/compute` |
| `getForecastLatest(conid)` | `:1507` | `GET /forecast/latest?conid=…` |
| `getForecastsByAccount(accountId?)` | `:1511` | `GET /forecast/by-account[?account_id=…]` |
| `getCalibrationCoverage(windowDays=90)` | `:1517` | `GET /calibration/coverage?window_days=N` |
| `getForecastDaySummary({accountId?, asOfDate?})` | `:1521` | `GET /forecast/day-summary[?…]` |

### Suggestions

| Method | File:line | HTTP + path |
|---|---|---|
| `getLatestSuggestions()` | `:1446` | `GET /suggestions/latest` |
| `runSuggestionsSync()` | `:1447` | `POST /suggestions/compute` |

### Decision Package (plural legacy + singular new)

| Method | File:line | HTTP + path |
|---|---|---|
| `getLatestDecisionPackages()` | `:1448` | `GET /decision-packages/latest` |
| `runDecisionPackagesSync()` | `:1450` | `POST /decision-packages/compute` |
| `runDecisionPackageExplanation(id)` | `:1451` | `POST /decision-packages/{id}/explanation` |
| `getDecisionPackageExplanation(id)` | `:1455` | `GET /decision-packages/{id}/explanation` |
| `getDecisionPackage(id)` | `:1530` | `GET /decision-package/{id}` |
| `getLatestDecisionPackage({conid, accountId?})` | `:1534` | `GET /decision-package/latest?…` |
| `getDecisionPackageChain({conid, accountId, limit?})` | `:1544` | `GET /decision-package/chain?…` |

### Action Draft (Task 133 / Task 134)

| Method | File:line | HTTP + path | Return |
|---|---|---|---|
| `getLatestActionDrafts()` | `:1459` | `GET /action-drafts/latest` | `FetchState<…>` |
| `runActionDraftsSync()` | `:1461` | `POST /action-drafts/compute` | `FetchState<{status}>` |
| `getActionDraftsTeKeuren(accountId?)` | `:1560` | `GET /action-draft/te-keuren[?…]` | `FetchState<…>` |
| `getActionDraft(id)` | `:1566` | `GET /action-draft/{id}` | `FetchState<…>` |
| `createActionDraft(payload)` | `:1568` | `POST /action-draft` | `ApiResult<…>` |
| `patchActionDraft(id, payload)` | `:1570` | `PATCH /action-draft/{id}` | `ApiResult<…>` |
| `approveActionDraft(id)` | `:1576` | `POST /action-draft/{id}/approve` | `ApiResult<…>` |
| `dismissActionDraft(id, reason?)` | `:1581` | `POST /action-draft/{id}/dismiss` | `ApiResult<…>` |
| `deleteActionDraft(id)` | `:1587` | `POST /action-draft/{id}/delete` | `ApiResult<…>` |
| `cancelSubmittedActionDraft(id)` | `:1595` | `POST /action-draft/{id}/cancel-submitted` | `ApiResult<…>` |

Note the convention split: read methods + the legacy `*-sync` endpoints return `FetchState`, while every user-mutation that surfaces Dutch backend error text returns `ApiResult`.

### IBKR Submission (Task 134c)

| Method | File:line | HTTP + path |
|---|---|---|
| `getIbkrSubmissionAudit(accountId?, limit=50)` | `:1600` | `GET /ibkr-submission/audit?…` |
| `getIbkrSubmissionLifecycle(actionDraftId)` | `:1608` | `GET /ibkr-submission/lifecycle/{id}` |
| `getIbkrSubmissionActive(accountId?)` | `:1612` | `GET /ibkr-submission/active[?…]` |
| `getIbkrSubmissionHistoriek(accountId?, limit=50)` | `:1620` | `GET /ibkr-submission/historiek?…` |
| `getIbkrExecutionsForAsset({accountId?, conid})` | `:1631` | `GET /ibkr-executions?…` |

### Reconciliation (Task 135b)

| Method | File:line | HTTP + path |
|---|---|---|
| `getReconciliationStatus(accountId?)` | `:1645` | `GET /reconciliation/status[?…]` |
| `getReconciliationRuns(accountId?, limit=50)` | `:1653` | `GET /reconciliation/runs?…` |
| `getReconciliationAudit(accountId?, limit=50)` | `:1661` | `GET /reconciliation/audit?…` |
| `getReconciliationManualReview(accountId?)` | `:1669` | `GET /reconciliation/manual-review[?…]` |
| `acknowledgeManualReview(queueId, note?)` | `:1677` | `POST /reconciliation/manual-review/{id}/acknowledge[?note=…]` |
| `getReconciliationUnmatchedExecutions(accountId?)` | `:1683` | `GET /reconciliation/unmatched-executions[?…]` |

### Briefings, Scheduler (legacy + v127), Watchlist, Market Data, Audit, Research

Briefings: `runDailyBriefing()` (`:1462`), `getLatestDailyBriefing()` (`:1464`).

Scheduler: `getSchedulerJobs()` (`:1466`), `getLatestSchedulerRun()` (`:1467`), `getSchedulerV127Status()` (`:1691`), `getSchedulerV127Runs(limit=20)` (`:1693`).

Watchlist (cold-start + manual + IBKR import): `getWatchlistConfirmationState()` (`:1480`), `getColdStartWatchlistItems()` (`:1484`), `confirmWatchlist(phrase)` (`:1486`), `deleteColdStartWatchlistItem(id)` (`:1492`); plus 4 loose functions for manual watchlist (`listWatchlistItems`, `createWatchlistItem`, `updateWatchlistItem`, `archiveWatchlistItem`, `:1803-1808`) and 3 for IBKR-side import (`listIbkrWatchlists`, `listIbkrWatchlistInstruments`, `importIbkrWatchlist`, `:1874-1876`).

Market data: `getMarketDataByAccount(accountId?)` (`:1497`), `getMarketDataProviderCalls(limit=20)` (`:1503`), `getMarketDataLatestSnapshotStatus(ibkrConid)` (`:1877`).

Request audit: `getRequestAuditRequestLogs()` / `…RequestLog(id)` / `…ProviderSources()` / `…ProviderSource(id)` / `…FreshnessAudits()` / `…FreshnessAudit(id)` (`:1697-1708`).

Research library (10 mutations + 1 GET, multipart upload included): `listResearchSources` / `getResearchSource` / `createResearchSource` / `createUrlMetadata` / `getUrlMetadata` / `createUserNote` / `getUserNote` / `getLatestProcessingStatus` / `getUploadedFileMetadata` / `extractResearchSourceText` / `uploadResearchSourceFile` (`:1719-1729`). The last is the file is the only multipart caller.

Assets / IBKR contracts (loose): `searchAssetMasterIdentities(query)` (`:1782`), `searchIbkrContracts(query)` (`:1805`).

**Total method count: ~90 callable functions.** Verified by grep of `: async (`, `apiClient = {`, and `export async function` patterns.

## 3. Type taxonomy (92 exported types)

All declared as `export type` (no `export interface`). One non-exported helper: `SystemEventActionInput` (`:1766-1768`).

### Wrappers + literals

- `FetchState<T>` (`:1`), `ApiResult<T>` (`:5`).
- `ForecastLabel = "Kopen" | "Verminderen" | "Verkopen" | "Houden" | "Bekijken" | "Geblokkeerd"` (`:782`) — the **6-label Dutch forecast vocabulary** (matches T-007 `worker-forecasting-and-decision-package.md` §6).
- `ForecastConfidenceLevel = "Laag" | "Gemiddeld" | "Hoog"` (`:790`).
- `ActionDraftStatus` (`:907-924`) — 15-state union: `proposed | edited | user_approved | dismissed | deleted | superseded | submitted | accepted | working | filled | partially_filled | cancelled | rejected | pending_cancellation | awaiting_reply_timeout`. Matches the storage state machine cited in T-007 `worker-actions-and-reconciliation.md` §13.
- `ReconciliationPassName` (`:1038`), `ReconciliationMode` (`:1043`), `ManualReviewReason` (`:1049`), `ManualReviewResolutionStatus` (`:1054`), `UnmatchedExecutionResolutionStatus` (`:1059`) — domain literal unions.

### Request shapes (3)

`TradingSettingsUpdateInput` (`:75`), `CreateActionDraftInput` (`:1161`), `PatchActionDraftInput` (`:1174`).

### Response shapes — by domain

| Domain | Count | Anchor types |
|---|---:|---|
| System / settings / storage / integrations / AI usage | 8 | `SystemStatusSummary:21`, `SettingsSummary:34`, `AiUsageSummary:56`, `StorageStatusSummary:57`, `IntegrationsSummary:59`, `TradingSettingsResponse:61` |
| IBKR (sync snapshots + status + connection) | 16 | `IbkrSyncStatusResponse:82`, `IbkrPositionSnapshot:107`, `IbkrCashSnapshot:119`, `IbkrOpenOrderSnapshot:129`, `IbkrExecutionSnapshot:142`, `IbkrStatusResponse:153`, `IbkrAccountModeResponse:636`, `IbkrConnectionStatusResponse:646`, `IbkrConnectionAuditEntry:656`, `IbkrConnectionAuditResponse:666`, `IbkrPositionLatestRow:672`, `IbkrPositionsLatestResponse:688`, `IbkrCashLatestRow:696`, `IbkrCashLatestResponse:707` |
| System events | 2 | `SystemEventSummary:170`, `ActiveSystemEventsResponse:187` |
| Research library | 3 | `ResearchSourceRecord:193`, `ResearchUploadedFileMetadataRecord:214`, `ResearchExtractTextResponse:224` |
| Request audit | 3 + 3 list | `RequestLogResponse:240`, `ProviderSourceResponse:265`, `FreshnessAuditResponse:1328`, plus 3 list wrappers (`:1351-1353`) |
| Portfolio valuation | 2 | `PortfolioValuationReadinessRow:288`, `PortfolioValuationReadinessResponse:327` |
| Forecast (legacy + new) | 5 | `AssetForecastResponse:354`, `LatestForecastsResponse:391`, `ForecastLatestResponse:798`, `ForecastDaySummaryResponse:826`, `ForecastByAccountRow:1180` + `ForecastByAccountResponse:1190` |
| Suggestions | 2 | `AssetSuggestionResponse:401`, `LatestSuggestionsResponse:428` |
| Decision Package | 9 | `AssetDecisionPackageResponse:440`, `LatestDecisionPackagesResponse:501`, `DecisionPackageExplanationResponse:512`, `DecisionPackageExplanationRunResponse:534`, `DecisionPackageExplanationReadResponse:550`, `DecisionPackageResponse:849`, `DecisionPackageChainResponse:895`, `DecisionPackageGateOutcome:837`, `DecisionPackageEvidenceReference:843` |
| Briefings | 4 | `BriefingAlertResponse:560`, `DailyBriefingResponse:572`, `DailyBriefingRunResponse:1254`, `DailyBriefingReadResponse:1265` |
| Scheduler | 6 | `SchedulerJobResponse:597`, `SchedulerJobsResponse:604`, `SchedulerRunResponse:616`, `LatestSchedulerRunResponse:627`, `SchedulerV127StatusResponse:1225`, `ScheduledRunAuditRow:1236`, `SchedulerV127RunsResponse:1248` |
| Watchlist (cold-start + confirmation + manual) | 7 | `WatchlistConfirmationStateResponse:715`, `WatchlistConfirmResponse:723`, `ColdStartWatchlistItem:731`, `ColdStartWatchlistResponse:740`, `WatchlistItem:1787`, `WatchlistItemResponse:1811`, `WatchlistAssetListingReadiness:1826` |
| Market data | 4 | `MarketDataLatestSnapshotResponse:746`, `MarketDataByAccountRow:762`, `MarketDataByAccountResponse:773`, `MarketDataLatestSnapshotStatusResponse:1854` |
| Action draft | 6 | `ActionDraftResponse:926`, `AssetActionDraftResponse:1274`, `LatestActionDraftsResponse:1316`, `ActiveDraftListResponse:1145`, `HistoriekDraftListResponse:1150`, `ActionDraftListResponse:1155` |
| IBKR submission lifecycle | 6 | `IbkrSubmissionAuditRow:968`, `IbkrSubmissionAuditListResponse:984`, `IbkrSubmissionLifecycleEvent:989`, `IbkrSubmissionLifecycleListResponse:1009`, `IbkrExecutionRow:1014`, `IbkrExecutionListResponse:1030` |
| Reconciliation | 8 | `ReconciliationRunResponse:1064`, `ReconciliationRunListResponse:1078`, `ReconciliationStatusResponse:1083`, `ReconciliationAuditRow:1091`, `ReconciliationAuditListResponse:1104`, `ManualReviewResponse:1109`, `ManualReviewListResponse:1120`, `UnmatchedExecutionRow:1125`, `UnmatchedExecutionListResponse:1140` |
| Calibration / provider audit | 2 | `CalibrationCoverageResponse:1197`, `ProviderCallRow:1207`, `ProviderCallsResponse:1219` |
| Asset master / IBKR contracts (loose) | 4 | `AssetMasterSearchRecord:1771`, `IbkrContractCandidate:1804`, `IbkrWatchlistSummary:1872`, `IbkrWatchlistInstrument:1873` |
| Other (PerAssetCoverage / ValuationInputTrace) | 2 | `ValuationInputTrace:286`, `PerAssetCoverage:792` |

**Total: 92 exported types.**

### Cross-reference with T-057 dead-code findings

- `FIND-UNUSED-003` flagged `MarketDataLatestSnapshotResponse:746` + `updateWatchlistItem:1807` — both verified in the inventory above. `MarketDataLatestSnapshotResponse` overlaps with `MarketDataLatestSnapshotStatusResponse:1854` (which IS consumed by `getMarketDataLatestSnapshotStatus:1877`); the older type is orphaned.
- `FIND-KNIP-004` flagged 24 unused exported types in this file. The full inventory above is the canonical reference T-057 should be cross-checked against. The most likely candidates (single-use chains, paired with the `FIND-KNIP-002` orphan function): `AssetMasterSearchRecord:1771` (paired with `searchAssetMasterIdentities:1782`), `BriefingAlertResponse:560`, `IbkrConnectionAuditEntry:656`.

## 4. `uiText.ts` — locked Dutch text registry

Full content (9 lines):

```ts
export const uiText = {
  projectNaam: "AI-Trading-Agent",
  projectSubtitel: "Paper-only beleggingsassistent",
  veiligeMelding:
    "Je ziet hier de veilige startstatus van het systeem. Er worden nog geen echte orders geplaatst.",
  paperOnlyTitel: "Paper-only",
  paperOnlyHelp:
    "Paper-only betekent: geen echt geld, geen live brokerorders en geen automatische uitvoering.",
} as const;
```

(`uiText.ts:1-9`).

- **One export**: `uiText` (`:1`, terminated with `as const` at `:9` — values narrow to their string literals, not `string`).
- **Five keys**, all flat (no nesting): `projectNaam:2`, `projectSubtitel:3`, `veiligeMelding:4-5`, `paperOnlyTitel:6`, `paperOnlyHelp:7-8`.

### Cross-reference with T-057 + T-008

- T-057's `FIND-UNUSED-001` flagged this file as **unused** (no page or component imports it). Confirmed: the T-008 status-component survey collected 40 Dutch microcopy strings across 19 components, none of which references `uiText.*`. The file is well-formed but currently dead-by-reachability.
- The five locked strings would be excellent candidates for the centralised page-header / paper-only-banner copy; pages currently inline this text in several places (e.g. `app/page.tsx:82, :84` per T-008 `web-pages.md` §7).

## 5. `next.config.ts` (7 lines)

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
```

- **Single setting**: `reactStrictMode: true` (`next.config.ts:4`).
- **No `experimental`**, **no `output: "standalone"`**, no image domains, no rewrites/redirects/headers, no env passthrough.
- **Phase 1c consequence**: the absence of `output: "standalone"` means the Docker `apps/web/Dockerfile` runner stage must copy the entire `node_modules` directory rather than the trimmed `.next/standalone` tree. See `infra-docker-and-compose.md` §3 for the deployment-side observation.

## 6. `playwright.config.ts` (38 lines)

Defined via `defineConfig` (`playwright.config.ts:11`). Key settings:

| Field | Value | File:line |
|---|---|---|
| `testDir` | `"./tests/e2e"` | `:12` |
| `fullyParallel` | `false` | `:13` |
| `retries` | `1` on CI, `0` locally | `:14` |
| `workers` | `1` | `:15` |
| `reporter` | `[["list"]]` | `:16` |
| `timeout` | `60_000` ms | `:17` |
| `expect.timeout` | `10_000` ms | `:18` |
| `use.baseURL` | `"http://127.0.0.1:3100"` | `:20` |
| `use.headless` | `true` | `:21` |
| `use.trace` | `"off"` | `:22` |
| `webServer.command` | `"npm start -- -p 3100 -H 127.0.0.1"` | `:25` |
| `webServer.reuseExistingServer` | `!process.env.CI` | `:27` |
| `webServer.timeout` | `120_000` ms | `:30` |
| Projects | one: `chromium` via `devices["Desktop Chrome"]` | `:32-37` |

**Doc-comment intent** (`playwright.config.ts:3-10`): "Task 126b: minimal Playwright smoke configuration. One browser (chromium) keeps CI fast … runs `next start` against the production build … much faster + more deterministic than `next dev` recompiling per request."

No Firefox / WebKit / mobile profiles. **No snapshot or screenshot settings.** Trace disabled.

## 7. `vitest.config.ts` + `vitest.setup.ts`

`vitest.config.ts` (20 lines):

- Plugin: `react()` from `@vitejs/plugin-react` (`vitest.config.ts:3, :7`).
- Alias `@` → repo dir (`vitest.config.ts:8-11`).
- `test.environment: "jsdom"` (`:14`).
- `test.globals: false` (`:15`) — tests must import `describe`/`it`/`expect` explicitly.
- `test.include: ["components/**/*.test.tsx", "lib/**/*.test.ts"]` (`:16`).
- `test.exclude: ["tests/e2e/**", "node_modules/**", ".next/**"]` (`:17`) — Playwright suite explicitly excluded.
- `test.setupFiles: ["./vitest.setup.ts"]` (`:18`).

`vitest.setup.ts` (1 line):

```ts
import "@testing-library/jest-dom/vitest";
```

(`vitest.setup.ts:1`). Sole effect: registers `@testing-library/jest-dom` custom matchers (`toBeInTheDocument`, `toHaveTextContent`, etc.) against Vitest's `expect`.

## 8. `eslint.config.mjs` (19 lines)

- **Flat-config style** (ESM `export default` of an array) — `eslint.config.mjs:12, :19`.
- Uses `@eslint/eslintrc`'s `FlatCompat` shim (`:1, :8-10`) to translate legacy `extends` into flat-config entries.
- **Extends**: `"next/core-web-vitals"` and `"next/typescript"` via `compat.extends(...)` (`:13`).
- **`ignores`**: `[".next/**", "next-env.d.ts", "node_modules/**"]` (`:15`).
- **No explicit `rules` block**, no per-file overrides, no plugins-array entries. The full ruleset comes verbatim from `next/core-web-vitals` + `next/typescript`.

### Cross-reference with T-057 finding `FIND-KNIP-001` (false-positive analysis)

T-057 flagged `eslint-config-next` as an unused devDependency. The flat-config above does **not** contain a literal `"eslint-config-next"` import or string — it references `"next/core-web-vitals"` and `"next/typescript"`.

However, **`next/core-web-vitals` and `next/typescript` are sub-paths exposed by the `eslint-config-next` npm package** — that's the package whose `package.json` `main`/`exports` resolves both. So the *package* `eslint-config-next` IS transitively required at lint time, even though no statement names it literally. Tools like knip that grep for the literal package name will miss it, but ESLint's flat-config `compat.extends("next/...")` resolver does load it.

**Verdict**: T-057's "unused" flag on `eslint-config-next` is a **false positive**. Removing the dependency would break the lint config. Recommend updating the FIND entry's "Fix approach" to NOT remove this devDep.

## 9. Cross-cutting observations

- **No state-management library, no React Query, no SWR.** Every page + component is hand-rolled `useState` + `useEffect` over `apiClient.*` (T-008 `web-pages.md` §4).
- **Two response wrappers coexist for a reason**: read-only collapses to `not_reachable`, mutations preserve backend Dutch error text. This works but means callers must remember which wrapper a method returns.
- **No client-side timeouts** anywhere. If the backend hangs, the request hangs forever. Phase 4 surface.
- **No retries** at the client layer. The backend's tier-1 / tier-2 guards (T-006 §11) and the worker's submission sweep (T-007 `worker-actions-and-reconciliation.md` §6) handle their own retry semantics; the frontend depends on user-driven refresh.
- **`uiText.ts` is dead-by-reachability** (T-057 `FIND-UNUSED-001`). The five Dutch strings inside it are exactly the kind of content the Dutch-UI invariant prizes — a Phase 4 task could wire them into the layout / paper-only banner.
- **`apiClient.ts` types contain at least 26 unused exports** between T-057's `FIND-UNUSED-003` (2) + `FIND-KNIP-004` (24). Phase 4 pruning candidates — but `FIND-KNIP-001`'s eslint-config-next flag is a false positive (see §8).
- **Playwright suite is chromium-only smoke** (`playwright.config.ts:32-37`). No cross-browser coverage; no mobile profile. This is a deliberate Task-126b decision; a future test-strategy brainstorm could widen.
- **Vitest excludes Playwright explicitly** (`vitest.config.ts:17`) — the two test stacks are non-overlapping by config.
