# Reality — web pages

**Scope.** Every `page.tsx` + `layout.tsx` under `apps/web/app/`: the root layout, 16 pages (incl. nested `[id]` dynamic routes under `decision-package/` and `audit/`), and how each page consumes `@/lib/apiClient`.

Sibling docs cover the rest of `apps/web/`:

- `docs/reality/components/web-components-status-and-shared.md` — 19 status / shared / generic-UI components.
- `docs/reality/components/web-components-feature-grids.md` — 11 feature-specific grids, drawers, forms.

`apiClient.ts`, `uiText.ts`, the test scaffolding, and the build/runtime config (Dockerfile, Next.js config) are covered by T-009.

Intent references: `docs/ui-principles.md` + AGENTS.md's Dutch-UI rule.

## 1. Locked UI doctrine (intent)

### `AGENTS.md`

- `AGENTS.md:33` — **"Keep UI Dutch and simple."**
- `AGENTS.md:34` — **"Every UI field must have simple Dutch help text."**
- `AGENTS.md:12` — "No business logic in UI."

### `docs/ui-principles.md`

- `docs/ui-principles.md:3-4` — "Eenvoudige Nederlandse interface / De UI moet duidelijk en begrijpelijk blijven voor niet-experts."
- `docs/ui-principles.md:6-7` — "Hulptekstverplichting / Elk veld, elke status en elke actie krijgt eenvoudige Nederlandse helptekst/tooltip."
- `docs/ui-principles.md:9-10` — "Geen onverklaard jargon / Complexe termen alleen in detail/advanced schermen met begrijpelijke uitleg."
- `docs/ui-principles.md:12-13` — Main sections: "Dashboard, Prestaties, Actiesuggesties, Portefeuille, Volglijst, Kansen en waarschuwingen, Transactiegeschiedenis, Belgische fiscaliteit en compliance, Instellingen."
- `docs/ui-principles.md:16-25` — Canonical help-text bullets: "**Actie:** 'Wat het systeem nu voorstelt...'", "**Risico:** 'Hoe groot de kans is op grotere schommelingen of verlies.'", "**Vertrouwen:** 'Hoe zeker het systeem is op basis van huidige data.'", "**Datakwaliteit:** 'Geeft aan of de gebruikte data volledig en betrouwbaar is.'"
- `docs/ui-principles.md:27-34` — Capability labels: `Toegestaan / Alleen opvolgen / Geblokkeerd / Niet toegestaan in versie 1`. "Dit product mag in versie 1 niet worden gekocht of verkocht…"
- `docs/ui-principles.md:45-47` — Task 17 API-to-UI rule: "API-responses die bedoeld zijn voor UI-weergave moeten eenvoudige Nederlandse labels en helpteksten bevatten."
- `docs/ui-principles.md:49-53` — Task 18 dashboard rules: Dutch help per field/status/action, no fake charts, modern/clean.
- `docs/ui-principles.md:52` — "Geen fake grafieken en geen fake portefeuilledata."
- `docs/ui-principles.md:57-67` — Storage status copy palette: required Dutch labels like "Opslag gepland", "Nog niet verbonden", "Kan nog niet opslaan".

The doctrine is fully verified by the page-level microcopy survey in §3 — every page that fetches data exposes Dutch labels + help text inline.

## 2. Root layout (`apps/web/app/layout.tsx`)

- **Type:** server component (no `"use client"`).
- **Metadata** (`apps/web/app/layout.tsx:10-13`): `title="Portfolio Outlook Manager"`, `description="Modern dashboard foundation in eenvoudige Nederlandse taal"`.
- **Locale** (`:29`): `<html lang="nl">`.
- **Body shell**: `<div className="app-shell">` (`:31`), `<nav aria-label="Hoofdnavigatie" className="side-nav">` (`:32-34`), `<main className="main-area">` (`:40`).
- **Top status row** (`:41-49`): `<p className="top-title">Release 1 dashboard</p>` (`:43`), `<p className="top-sub">Veilige basis zonder runtime-data.</p>` (`:44`), then `<AccountModeBadge />` (`:47`) + `<SystemEventsIndicator />` (`:48`), then `<ColdStartBanner />` (`:51`) rendered above `{children}` (`:52`).
- **Global CSS:** `import "./globals.css";` (`:8`). **No `next/font` import** — the body has no font class.
- **Hard-coded `navItems`** (`:15-25`): 9 entries — `/` (Dashboard), `/portefeuille`, `/volglijst`, `/suggesties`, `/ibkr-acties`, `/onderzoek`, `/historiek`, `/audit`, `/instellingen`.
- **No global providers, no React Query, no Suspense wrapper, no i18n provider, no theme provider** — children render directly under the shell.

## 3. Page catalogue (16 routes)

Format: route — file — `"use client"` directive — top-level component imports rendered — what it does — `apiClient.*` call sites — Dutch microcopy examples.

### 3.1 `/` — Dashboard (`apps/web/app/page.tsx`, 139 lines)

- `"use client"` (`page.tsx:1`).
- **Renders:** `CalibrationCoverageBadge`, `ChartPlaceholder`, `ForecastDaySummaryWidget`, `ReconciliationStatusWidget`, then 6 `MetricCard`s in a `metrics-grid` (`:77-94`), then 4 `DashboardPanel`s (`:96-136`) — "Portefeuille-evolutie", "Waardering", "Synchronisatie en status", "Systeemstatus". Imports (`:5-14`).
- **State (`useState`×5):** `systemStatus`, `ibkrStatus`, `ibkrSyncStatus`, `valuationReadiness`, `valuationLoading` (`:35-39`). `useMemo` `syncLabel` (`:58`).
- **`useEffect`** (`:41-56`) — single mount-effect; `Promise.all` of 4 endpoints.
- **`apiClient.*` call sites:** `getSystemStatus()` (`:44`), `getIbkrStatus()` (`:45`), `getIbkrSyncStatus()` (`:46`), `getPortfolioValuationReadiness()` (`:47`).
- **Dutch microcopy examples:**
  - `:20` — `"Niet beschikbaar: veilige totaalwaarde ontbreekt."`
  - `:82` — help `"Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is."`
  - `:116` — `<SyncStatusBadge label="Accountmodus" status="vergrendeld" help="Alleen paper-modus is toegestaan." />`

### 3.2 `/portefeuille` (`apps/web/app/portefeuille/page.tsx`, 680 lines)

- `"use client"` (`portefeuille/page.tsx:1`).
- **Renders:** `PortefeuilleRealtimeSection` (`:241`), then 9 `dashboard-panel` sections: Portefeuille header + manual-sync button (`:242-295`), Dagbriefing (`:300-349`), Scheduler (`:351-380`), Posities (`:382-418`), Kostbasis + W/V (`:420-462`), Cash (`:464-476`), Open orders (`:478-487`), Executions (`:489-498`), Action drafts (`:500-552`), Decision Packages (`:554-677`). Imports `EmptyState`, `PortefeuilleRealtimeSection`, `StatusBadge`, `PositionPlTraceDetails`, `ValuationTraceDetails` (`:5-9`).
- **State (19× `useState`)** (`:60-78`): `syncStatus`, `valuationReadiness`, `positions`, `cashItems`, `openOrders`, `executions`, `forecasts`, `suggestions`, `decisionPackages`, `actionDrafts`, `explanations`, `explanationStatuses`, `dailyBriefing`, `accountMode`, `schedulerJobs`, `latestSchedulerRun`, `loading`, `loadFailed`, `syncing`. `useMemo`×4 (`:160, :180, :216, :223`).
- **`useEffect`** (`:209-214`) — mount-only; calls `loadData`, `loadDailyBriefing`, `loadAccountMode`, `loadSchedulerInfo`.
- **`apiClient.*` call sites (18 distinct endpoints):** `getIbkrSyncStatus` (`:83`), `getPortfolioValuationReadiness` (`:84`), `getIbkrPositions` (`:85`), `getIbkrCash` (`:86`), `getIbkrOpenOrders` (`:87`), `getIbkrExecutions` (`:88`), `getLatestForecasts` (`:89`), `getLatestSuggestions` (`:90`), `getLatestDecisionPackages` (`:91`), `getLatestActionDrafts` (`:92`), `getDecisionPackageExplanation` (`:110`), `getLatestDailyBriefing` (`:118`), `getIbkrAccountMode` (`:125`), `getSchedulerJobs` (`:133`), `getLatestSchedulerRun` (`:134`), `runDailyBriefing` (`:141`), `runDecisionPackageExplanation` (`:149`), `runIbkrSync` (`:234`).
- **Dutch microcopy examples:**
  - `:267-268` — `"Synchroniseren…" / "Synchroniseer snapshots"`.
  - `:271` — `"Read-only weergave van laatst opgeslagen IBKR snapshots…"`.
  - `:412` — `<StatusBadge label="Read-only" status="info" title="Snapshot uit IBKR-sync." />`.
  - `:556` — `"Immutable evidence-bundels die elke suggestion ondersteunen. Geen action drafts, geen orders."`.
  - `:667` — `"Nog geen AI uitleg geladen. AI bedacht nooit een getal; lees of genereer een samenvatting."`.

### 3.3 `/admin/reconciliation` (`apps/web/app/admin/reconciliation/page.tsx`, 390 lines)

- `"use client"` (`:1`).
- **Renders:** 4 sections — status header (`:136-183`), Wacht op handmatige beoordeling (`:186-257`), Onbekende IBKR-uitvoeringen (`:260-312`), Recente reconciliatieruns (`:315-369`). Inline JSX + local `SummaryCell` helper (`:375-390`); no app components imported.
- **State:** `status`, `pendingReview`, `unmatched`, `runs`, `error` (`:45-55`).
- **`useEffect`** (`:85-87`) — mount-effect → `refresh`.
- **`apiClient.*` call sites:** `getReconciliationStatus` (`:60`), `getReconciliationManualReview` (`:61`), `getReconciliationUnmatchedExecutions` (`:62`), `getReconciliationRuns` (`:63`), `acknowledgeManualReview(queueId, note)` (`:95`).
- **Locked Dutch labels** in `MODE_LABELS` (`:30-35`) — `"Voltooid"`, `"Overgeslagen (vergrendeld)"`, `"Overgeslagen (geen verbinding)"`, `"Fout"`; `REASON_LABELS` (`:37-42`) — `"24u timeout zonder IBKR-data"`, `"Verschil in eindstatus"`, `"Uitvoering zonder draft"`.
- **Dutch microcopy:** `:69` `"Reconciliatiestatus is niet beschikbaar."`; `:148-149` `"Nog geen reconciliatie-runs uitgevoerd."`; `:188` `"Wacht op handmatige beoordeling"`; `:249` `"Bevestig"` button.

### 3.4 `/research-sources` (`apps/web/app/research-sources/page.tsx`, 304 lines)

- `"use client"` (`:1`). Imports `SectionHeader` (`:5`).
- **Renders:** status card, "Bronmetadata toevoegen" form (`:191-202`), "Bestand uploaden" form (`:204-240`), Onderzoeksbronnen table (`:242-249`), Brondetails (`:251-254`), Tekstextractie (`:256-275`), URL-metadata (`:277-283`), Gebruikersnotitie (`:285-291`), Verwerkingsstatus (`:293-295`), Veiligheid + hulp (`:297-301`).
- **State:** 12 `useState`s + `useMemo` `selectedSourceId` (`:26-41`).
- **`useEffect`** (`:59-61`) — mount-effect → `loadSources`.
- **`apiClient.*` call sites:** `listResearchSources` (`:44`), `createResearchSource` (`:71`), `getUrlMetadata` / `getUserNote` / `getLatestProcessingStatus` / `getUploadedFileMetadata` (`:79`), `extractResearchSourceText` (`:96`), `uploadResearchSourceFile` (`:144`), `getResearchSource` (`:173`), `createUrlMetadata` (`:279`), `createUserNote` (`:287`).
- **Dutch microcopy:** `:23` `"Niet ingevuld"`; `:181` `"Onderzoeksbibliotheek"`; `:182` "Hier bewaar je bronnen die later kunnen helpen…"; `:214` `"Bestand veilig uploaden"`.

### 3.5 `/ibkr-acties` (`apps/web/app/ibkr-acties/page.tsx`, 242 lines)

- `"use client"` (`:1`). Imports `ActionDraftGrid` (`:19`), `ActiefBijIbkrGrid` + `HistoriekGrid` (`:20-23`), `SubmissionLifecycleDrawer` (`:24`).
- **Renders:** three tabs (`:121-152`) — `"Te keuren"`, `"Actief bij IBKR"`, `"Historiek"` (`TABS` array `:32-36`); active tab panel; lifecycle drawer at `:235-239`.
- **State:** `tab`, `teKeurenDrafts`, `teKeurenError`, `actiefDrafts`, `actiefError`, `historiekDrafts`, `historiekError`, `drawerDraftId` (`:39-60`).
- **`useEffect`** (`:101-109`) — reacts to `tab` change, refreshes data for active tab.
- **`apiClient.*` call sites:** `getActionDraftsTeKeuren` (`:64`), `getIbkrSubmissionActive` (`:77`), `getIbkrSubmissionHistoriek` (`:90`).
- **Dutch microcopy:** `:114-119` "De drie-fase actieflow: Te keuren is jouw to-do laag — Decision Packages worden hier voorbereid als IBKR-orders. Actief bij IBKR toont lopende orders en Historiek de afgeronde orders.".

### 3.6 `/volglijst` (`apps/web/app/volglijst/page.tsx`, 200 lines)

- `"use client"` (`:1`). Imports `ForecastExplanationPanel` (`:21`), `StatusBadge` (`:22`), `VolglijstColdStartFlow` (`:23`), `useRouter` (`:24`).
- **Renders:** loading fallback (`:53-59`); cold-start branch → `<VolglijstColdStartFlow />` (`:61-67`); confirmed branch → `<VolglijstConfirmedView />` (`:69-200`). Confirmed view: import-from-IBKR controls (`:168-174`), local search form (`:176-181`), add-to-watchlist form (`:182-185`), filter banner (`:192-196`), watchlist table (`:197`), `ForecastExplanationPanel` (`:198`).
- **State:** outer `Page` has 2 `useState`s; inner `VolglijstConfirmedView` has 14 (`:75-90`).
- **`useEffect`×3:** load confirmation state (`:49-51`); read `?filter=` query (`:116-120`); load watchlist + forecasts (`:155`).
- **`apiClient.*` call sites:** `getWatchlistConfirmationState` (`:40`); `listWatchlistItems` (`:123`); `getMarketDataLatestSnapshotStatus(conid)` (`:131`); `getForecastsByAccount` (`:148`); `getLatestDecisionPackage` (`:95`); `createActionDraft` (`:103`); `listIbkrWatchlists` (`:170`); `listIbkrWatchlistInstruments` (`:172`); `importIbkrWatchlist` (`:173`); `searchIbkrContracts` (`:176`); `createWatchlistItem` (`:182`); `archiveWatchlistItem` (`:197`).
- **Dutch microcopy:** `:99` `"Geen Decision Package gevonden voor dit asset. Wacht op de volgende morgenrun."`; `:167` `"Volglijst"`; `:184` `"Toevoegen aan Volglijst"`; `:197` table headers `Symbool / IBKR-contract / Gevalideerd / Status / Marktdata / Voorspelling / Actie`.

### 3.7 `/instellingen` (`apps/web/app/instellingen/page.tsx`, 171 lines)

- `"use client"` (`:1`). No app components imported.
- **Renders:** loading (`:84-85`), empty (`:86-87`), or single "Actie-instellingen" section (`:90-167`) with `Cashbuffer (EUR)` number input + Save.
- **State:** `data`, `buffer`, `loading`, `saving`, `error`, `savedMessage` (`:24-29`).
- **`useEffect`** (`:48-50`) — mount-effect → `refresh`.
- **`apiClient.*` call sites:** `getTradingSettings` (`:33`), `updateTradingSettings({ user_buffer_eur, reason_nl })` (`:66`).
- **Dutch microcopy:** `:57` `"Cashbuffer moet ≥ 0 zijn."`; `:69` `"Cashbuffer voor actiedrafts aangepast."`; `:100-101` `"De cashbuffer wordt afgetrokken van je beschikbare cash voordat de voorgestelde aankoophoeveelheid wordt berekend. Standaard €0."`.
- **Note:** the page edits only **one** field (`user_buffer_eur`) despite the header comment (`:3-14`) acknowledging the trading-settings JSON column has other fields. Other settings are read-only here.

### 3.8 `/systeemmeldingen` (`apps/web/app/systeemmeldingen/page.tsx`, 131 lines)

- `"use client"` (`:1`). No app components imported.
- **Renders:** `<h1>Systeemmeldingen</h1>` (`:89`) + description (`:90-91`) + summary card (`:93-97`) + refresh button (`:99`) + state-conditional list (`:102-128`).
- **State:** `eventsResponse`, `loading`, `error`, `actionStatus` (`:38-41`) + `useMemo` `events` (`:43`).
- **`useEffect`** (`:58-60`) — mount-effect → `loadEvents`.
- **`apiClient.*` call sites:** `getActiveSystemEvents` (`:48`), `resolveSystemEvent(systemEventId, {reason_nl: "Gemarkeerd als opgelost vanuit de webinterface."})` (`:63`), `archiveSystemEvent(systemEventId, {reason_nl: "Gearchiveerd vanuit de webinterface."})` (`:73`).
- **Severity labels** (`:13-15`): `"Fout"`, `"Waarschuwing"`, `"Info"`.
- **Dutch microcopy:** `:90` `"Hier zie je belangrijke fouten, waarschuwingen en blokkeringen van het systeem."`; `:104` `"Geen actieve systeemmeldingen."`; `:122-124` action buttons `Oplossen / Archiveren / Details kopiëren`.

### 3.9 `/decision-package/[id]` (`apps/web/app/decision-package/[id]/page.tsx`, 76 lines)

- `"use client"` (`:1`). Imports `DecisionPackageDetail` (`:23`).
- **URL param:** `[id]` via `useParams<{ id: string }>()` (`:30`).
- **State:** `pkg`, `unavailable` (`:31-32`).
- **`useEffect`** (`:34-53`) — on `params?.id` change; cancel-guarded.
- **`apiClient.*` call site:** `getDecisionPackage(params.id)` (`:38`).
- **Dutch microcopy:** `:59` `"Decision Package niet gevonden."`; `:67` `"Bezig met laden…"`.
- **Render:** unavailable / loading / success → delegates to `<DecisionPackageDetail package={pkg} />` (`:73`).

### 3.10 `/audit` (`apps/web/app/audit/page.tsx`, 40 lines)

- `"use client"` (`:1`). Imports `Link` (`:2`) + audit-formatting helpers (`:5`); no app components.
- **State:** `logs`, `sources`, `freshness`, `q`, `type`, `provider`, `status` (`:8-11`) + `useMemo` `providerOptions`, `statusOptions` (`:13-14`).
- **`useEffect`** (`:12`) — mount-effect; `Promise.all` of three endpoints.
- **`apiClient.*` call sites:** `getRequestAuditRequestLogs`, `getRequestAuditProviderSources`, `getRequestAuditFreshnessAudits` (all on `:12`).
- **Dutch microcopy:** `:24` `"Read-only records · Deze pagina start geen runtime-fetch · Geen orders"`; `:32` summary `"Read-only records / Geblokkeerd voor analyse / Suggesties geblokkeerd / Geen actiedrafts"`; `:33` `"Geen records gevonden."`; `:36-38` headings `"Request logs" / "Provider/source metadata" / "Freshness-audits"`.

### 3.11 `/suggesties` (`apps/web/app/suggesties/page.tsx`, 22 lines)

- **Server component** — no `"use client"`.
- **Renders:** `<h2>Suggesties</h2>` + single explainer `<p>` (`:13-19`).
- **Dutch microcopy** (`:14-18`): "Suggesties komen binnenkort. Decision Packages worden nu opgebouwd op de achtergrond. Bekijk individuele Decision Packages via de 'Bekijk Decision Package' knop op elke voorspelling in Volglijst."

### 3.12 `/audit/request-logs/[requestLogId]` (`apps/web/app/audit/request-logs/[requestLogId]/page.tsx`, 19 lines)

- `"use client"` (`:1`). Imports `Link` (`:2`).
- **URL param:** `[requestLogId]` (`:11`).
- **State:** `record`, `state: "loading" | "ok" | "not_found" | "error"` (`:12-13`).
- **`useEffect`** (`:14`) — on `[params.requestLogId]`.
- **`apiClient.*` call site:** `getRequestAuditRequestLog(params.requestLogId)` (`:14`).
- **Dutch microcopy:** `:15` `"Laden..."`; `:16` `"Record niet gevonden." / "← Terug naar auditoverzicht"`; `:17` `"API niet bereikbaar."`; `:18` field labels `ID / Status / Provider / Domein / Aangemaakt / safe_for_analysis`.

### 3.13 `/audit/freshness-audits/[freshnessAuditId]` (19 lines)

- `"use client"` (`:1`). Identical four-state machine to §3.12.
- **`apiClient.*` call site:** `getRequestAuditFreshnessAudit(params.freshnessAuditId)` (`:14`).
- **Dutch microcopy:** field labels `ID / Status / Reason / Bron timestamp / Geëvalueerd / safe_for_analysis` (`:18`).

### 3.14 `/audit/provider-sources/[providerSourceId]` (17 lines)

- `"use client"` (`:1`). Simplest of the three audit details.
- **`apiClient.*` call site:** `getRequestAuditProviderSource(params.providerSourceId)` (`:12`).
- **Dutch microcopy:** field labels `ID / Provider / Domein / Disabled op / Disabled reden` (`:16`); fallback `"Geen disabled-status in huidig storagecontract."`.

### 3.15 `/onderzoek` (`apps/web/app/onderzoek/page.tsx`, 10 lines)

- **Server component** — no `"use client"`. Imports `EmptyState` (`:1`).
- **Renders:** `<h2>Onderzoek</h2>` + `<EmptyState title="Module in opbouw" message="Deze pagina toont later echte workflow-data zodra de benodigde runtime actief is." />`.

### 3.16 `/historiek` (`apps/web/app/historiek/page.tsx`, 10 lines)

- **Server component** — no `"use client"`. Identical placeholder shell to `/onderzoek` (same `EmptyState` copy).

## 4. `apiClient` consumption pattern

Across all 13 client pages the **same dominant pattern** appears:

1. **`useState` per data slot**, typed via `apiClient` response types.
2. **`useEffect` with mount-only deps** dispatches an async loader that awaits `apiClient.X()`; multi-endpoint pages parallelise via `Promise.all`.
3. **`Result.ok` discrimination** — every `apiClient` call returns the tagged union `{ ok: true; data } | { ok: false; status; message }`; pages branch on `result.ok` and set state to `null` / an inline Dutch error message accordingly.
4. **No global cache, no React Query, no SWR** — every page is hand-rolled.
5. **No polling** at the page layer (intervals exist only inside the badge components — see `web-components-status-and-shared.md`).
6. **Re-fetch after mutation** — `acknowledgeManualReview` (`admin/reconciliation/page.tsx:103`), `runIbkrSync` (`portefeuille/page.tsx:235`), `resolveSystemEvent` / `archiveSystemEvent` (`systeemmeldingen/page.tsx:69, 78`) all re-invoke the loader.
7. **`ApiUnavailableNotice` is NOT used by any page.** The component exists (see `web-components-status-and-shared.md` §ApiUnavailableNotice) but every page inlines its own Dutch fallback (e.g. `"API niet bereikbaar."` at `audit/request-logs/[requestLogId]/page.tsx:17`).
8. **`EmptyState`** is the empty/loading affordance — used in `app/page.tsx:10`, `app/portefeuille/page.tsx:5`, `app/onderzoek/page.tsx:1`, `app/historiek/page.tsx:1`.

Sample call sites (10):

- `app/page.tsx:44` — `apiClient.getSystemStatus()`
- `app/page.tsx:47` — `apiClient.getPortfolioValuationReadiness()`
- `app/portefeuille/page.tsx:83` — `apiClient.getIbkrSyncStatus()`
- `app/portefeuille/page.tsx:91` — `apiClient.getLatestDecisionPackages()`
- `app/portefeuille/page.tsx:234` — `apiClient.runIbkrSync()` (mutation)
- `app/admin/reconciliation/page.tsx:60-63` — four `getReconciliationX()` calls in parallel
- `app/admin/reconciliation/page.tsx:95` — `apiClient.acknowledgeManualReview(queueId, note ?? undefined)`
- `app/ibkr-acties/page.tsx:64` — `apiClient.getActionDraftsTeKeuren()`
- `app/volglijst/page.tsx:103` — `apiClient.createActionDraft({ decision_package_id })`
- `app/instellingen/page.tsx:66` — `apiClient.updateTradingSettings({ ... reason_nl: "Cashbuffer voor actiedrafts aangepast." })`

## 5. Server / client component split

**Pure server components (4 of 17):** `app/layout.tsx`, `app/suggesties/page.tsx`, `app/onderzoek/page.tsx`, `app/historiek/page.tsx`. All are static — they render headings + an `EmptyState` and nothing else.

**Client components (`"use client"`) — 13 of 17 routes:** every page that fetches data declares `"use client"` and uses `useEffect` + `useState`. **No page uses Next.js `async` server-component data fetching** — there is no `await fetch()` in a page body anywhere.

**Pattern observed.** The doctrine is effectively *client-first* for any page that touches the API; the SSR shell is the layout + nav + three placeholder pages. The Next.js App Router's server-component default is **not** leveraged for runtime data — every API consumer is a `"use client"` page with `useEffect`. This is a measurable departure from typical Next.js 15 idiom.

## 6. Nested + dynamic routes

All four `[id]`-shaped routes share the same control pattern: `useParams<{...}>()` → guard → `useEffect` → `apiClient.getX(id)` → state machine (`loading | ok | not_found | error`) → Dutch fallback text for each non-`ok` branch.

| Route | File | URL param hook | `apiClient` call | File:line |
|---|---|---|---|---|
| `/decision-package/[id]` | `decision-package/[id]/page.tsx` | `useParams<{ id: string }>()` (`:30`) | `getDecisionPackage(params.id)` | `:38` |
| `/audit/request-logs/[requestLogId]` | `audit/request-logs/[requestLogId]/page.tsx` | `useParams<{ requestLogId: string }>()` (`:11`) | `getRequestAuditRequestLog(params.requestLogId)` | `:14` |
| `/audit/freshness-audits/[freshnessAuditId]` | `audit/freshness-audits/[freshnessAuditId]/page.tsx` | `useParams<{ freshnessAuditId: string }>()` (`:11`) | `getRequestAuditFreshnessAudit(params.freshnessAuditId)` | `:14` |
| `/audit/provider-sources/[providerSourceId]` | `audit/provider-sources/[providerSourceId]/page.tsx` | `useParams<{ providerSourceId: string }>()` (`:9`) | `getRequestAuditProviderSource(params.providerSourceId)` | `:12` |

All three audit details share helpers from `../../auditFormatting` (e.g. `formatDateTime`, `booleanBlockedLabel`) and use `<Link href="/audit">← Terug naar auditoverzicht</Link>` for breadcrumb back-navigation.

The `/decision-package/[id]` route is a thin wrapper around `<DecisionPackageDetail package={pkg} />` (T-008 sibling doc); the audit details render inline field grids.

## 7. Dutch microcopy invariant — eight cross-page examples

The Dutch-UI invariant from `AGENTS.md:33` + `docs/ui-principles.md:6-7` is enforced page-by-page. Eight concrete examples:

1. `app/page.tsx:82` → `"Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is."` (MetricCard help).
2. `app/portefeuille/page.tsx:274` → `"De waarderingsstatus kon niet worden opgehaald. Er worden geen waarden verzonnen."` (EmptyState message).
3. `app/admin/reconciliation/page.tsx:148-149` → `"Nog geen reconciliatie-runs uitgevoerd."` (empty state on status card).
4. `app/ibkr-acties/page.tsx:114-119` → "De drie-fase actieflow: Te keuren is jouw to-do laag — Decision Packages worden hier voorbereid als IBKR-orders. Actief bij IBKR toont lopende orders en Historiek de afgeronde orders." (page intro).
5. `app/instellingen/page.tsx:100-101` → "De cashbuffer wordt afgetrokken van je beschikbare cash voordat de voorgestelde aankoophoeveelheid wordt berekend. Standaard €0." (field help).
6. `app/research-sources/page.tsx:182` → "Hier bewaar je bronnen die later kunnen helpen bij het onderzoek naar assets. … In deze versie bewaart het systeem alleen metadata." (page lede).
7. `app/systeemmeldingen/page.tsx:90` → "Hier zie je belangrijke fouten, waarschuwingen en blokkeringen van het systeem." (page lede).
8. `app/suggesties/page.tsx:14-18` → entire body, single Dutch paragraph explaining the gating.

The invariant is **fully verified** at the page layer.

## 8. Cross-cutting observations

- **Component count was 30, not 41.** The task spec quoted "41 components"; the actual `find apps/web/components -name '*.tsx' -not -name '*.test.tsx'` returns 30 files (split 19 + 11 across the two sibling docs).
- **`ApiUnavailableNotice` exists but is never imported by a page.** Pages prefer their own inline Dutch fallback. The component is reachable only from components that compose it (e.g. it could be rendered as a side-panel fallback inside `PortefeuilleRealtimeSection` — but that doesn't happen here either).
- **`/portefeuille` is the heavyweight client page.** 19 `useState` calls, 18 distinct `apiClient` endpoints touched per mount. Worth flagging for `FIND-RADON-002` cross-reference — though Radon does not run on TypeScript, the per-component complexity story is similar.
- **No `next/font`, no providers, no theming, no client-side i18n.** Dutch labels are baked at source rather than localised. If a second locale is ever added, every page is a touch point.
- **Client-first, not server-first.** Despite Next.js 15 defaulting to server components, every API-touching page declares `"use client"`. The doctrine ships a thin static shell + client-rendered data panels.
- **No polling at page level.** Refresh is user-driven (refresh buttons, tab changes, post-mutation reload). Intervals live inside polling badges (see sibling doc) at 30 s and 60 s cadences.
- **Server vs client split is binary** — there are no "server component shell + client component leaf" pages. The whole page is either static (4 routes) or fully client (13 routes).
