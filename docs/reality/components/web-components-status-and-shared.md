# Reality — web components, status + shared

**Scope.** 19 of the 30 non-test `.tsx` files under `apps/web/components/`: the generic / status / badge / shared-UI primitives. Feature-specific grids, drawers, and forms (the other 11 files) are covered by `docs/reality/components/web-components-feature-grids.md`.

The verification invariant for this doc + its sibling: `find apps/web/components -name '*.tsx' -not -name '*.test.tsx'` returns exactly **30 files** → 19 (this doc) + 11 (sibling) = 30, no duplicates.

Intent reference: AGENTS.md Dutch-UI rule + `docs/ui-principles.md` (see `web-pages.md` §1).

## In-scope components (19)

| Component | Lines | Type | Calls `apiClient`? |
|---|---:|---|---|
| `AccountModeBadge.tsx` | 139 | client | ✓ |
| `ApiUnavailableNotice.tsx` | — | server | ✗ |
| `CalibrationCoverageBadge.tsx` | 138 | client | ✓ |
| `ChartPlaceholder.tsx` | — | server | ✗ |
| `ColdStartBanner.tsx` | — | client | ✓ |
| `DashboardPanel.tsx` | — | server | ✗ |
| `EmptyState.tsx` | — | server | ✗ |
| `HelpText.tsx` | — | server | ✗ |
| `HelpTooltip.tsx` | — | server | ✗ |
| `IconButtonWithTooltip.tsx` | — | server | ✗ |
| `MetricCard.tsx` | — | server | ✗ |
| `PriceFreshnessBadge.tsx` | — | server | ✗ |
| `ReconciliationStatusWidget.tsx` | 201 | client | ✓ |
| `SchedulerStatusBadge.tsx` | 133 | client | ✓ |
| `SectionHeader.tsx` | — | server | ✗ |
| `StatusBadge.tsx` | — | server | ✗ |
| `StatusCard.tsx` | — | server | ✗ |
| `SyncStatusBadge.tsx` | — | server | ✗ |
| `SystemEventsIndicator.tsx` | — | client | ✓ |

**Server/client split: 13 server / 6 client.** All 6 client components are exactly the ones that call `apiClient` directly — 1:1 correspondence between "fetches" and `"use client"`. All 13 server components are stateless presentational primitives.

## 1. `AccountModeBadge.tsx`

- **Type:** client (`AccountModeBadge.tsx:1`).
- **Props:** none (zero-arg export at `:71`).
- **Behaviour:** polls `/ibkr/connection/status` every 30 s (interval declared at `:18`), derives a `Mode`, renders a coloured pill with a status dot. First mount flashes a brighter background for ~500 ms then settles. Render at `:113-138`.
- **State enum** `Mode = "paper" | "live" | "disconnected"` (`:21`) → visuals (`:31-53`):
  - `paper` → `"Paper-rekening: ${id}"` / bg `#1e40af` flash `#3b82f6`.
  - `live` → `"Echte rekening: ${id}"` / bg `#f59e0b` flash `#fbbf24`.
  - `disconnected` → `"Geen IBKR-verbinding"` / bg `#6b7280` flash `#9ca3af`.
  - Derivation `:55-63`.
- **Dutch microcopy:** `"Paper-rekening: ${id ?? "onbekend"}"` (`:35`); `"Echte rekening: ${id ?? "onbekend"}"` (`:43`); `"Geen IBKR-verbinding"` (`:51`); aria-labels at `:36, :44, :52`.
- **`apiClient` usage:** imports at `:16`; calls `apiClient.getIbkrConnectionStatus()` at `:81`.
- **Composition:** none.

## 2. `ApiUnavailableNotice.tsx`

- **Type:** server (no `"use client"`, no hooks). `ApiUnavailableNotice.tsx:3`.
- **Props:** none.
- **Behaviour:** renders a static `dashboard-card-error` article with `role="status"`, `aria-live="polite"`, a heading + body + nested `HelpText`. Render block `:4-10`.
- **Dutch microcopy:** `"API niet bereikbaar"` (`:6`); `"De dashboardgegevens kunnen nu niet worden opgehaald."` (`:7`); `"Start eerst de backend-API. Daarna vernieuw je deze pagina om de status te laden."` (`:8`).
- **`apiClient` usage:** none.
- **Composition:** imports `HelpText` (`:1`).
- **Note:** despite the component existing, **no page imports it** — pages inline their own Dutch fallback (see `web-pages.md` §4).

## 3. `CalibrationCoverageBadge.tsx`

- **Type:** client (`CalibrationCoverageBadge.tsx:1`).
- **Props:** none (`:81`).
- **Behaviour:** on mount, loads `/calibration/coverage?window_days=90` **once** (no interval). Returns `null` if data missing or API failed (`:103-108`); else renders a pill (`:117-137`).
- **State enum:** three locked visuals at `:35-54`:
  - `healthy` → `"Kalibratie: goed"` bg `#dcfce7` border `#bbf7d0`.
  - `warning` → `"Kalibratie: matig"` bg `#fef3c7` border `#fde68a`.
  - `insufficient` → `"Kalibratie: te weinig data"` bg `#f3f4f6` border `#d1d5db`.
- **Classifier `classify()`** (`:57-78`): hit-rate floors 0.60 / 0.40 and `MIN_SAMPLE_SIZE = 10` (`:24-26`).
- **Dutch microcopy:** labels at `:40, :46, :52`; aria-text at `:114-115`.
- **`apiClient` usage:** imports at `:19-22`; calls `apiClient.getCalibrationCoverage(90)` at `:88`.
- **Composition:** none.

## 4. `ChartPlaceholder.tsx`

- **Type:** server (`ChartPlaceholder.tsx:1`).
- **Props:** inline `{ text: string }` (`:1`).
- **Behaviour:** renders a `<div className="chart-placeholder" role="img" aria-label="Grafiek placeholder">` containing an empty `.chart-grid` div + `<p>{text}</p>` (`:2-7`).
- **Dutch microcopy:** aria-label `"Grafiek placeholder"` (`:3`) — body text is prop-driven.
- **`apiClient` usage:** none.

## 5. `ColdStartBanner.tsx`

- **Type:** client (`ColdStartBanner.tsx:1`).
- **Props:** none (`:27`).
- **Behaviour:** polls `/watchlist/confirmation-state` every 60 s (interval at `:24`). Returns `null` unless `state.state === "unconfirmed"` (`:53-55`); else renders a sticky amber banner with the server-supplied `banner_text` and a `next/link` to `/volglijst` (`:57-92`).
- **State values referenced:** `"unconfirmed"` (renders banner, `:53`), `"confirmed"` and `"no_account_configured"` (render `null`, comment `:9-13`).
- **Dutch microcopy:** server-supplied `banner_text` rendered at `:76`; `"Naar Volglijst"` link label (`:89`).
- **`apiClient` usage:** imports `:19-22`; calls `apiClient.getWatchlistConfirmationState()` at `:35`.
- **Composition:** `next/link` only.

## 6. `DashboardPanel.tsx`

- **Type:** server (`DashboardPanel.tsx:1-14`).
- **Props:** inline `{ title: string; help: string; children: ReactNode }` (`:4`).
- **Behaviour:** wraps `children` in `<section className="dashboard-panel">` with a header containing `<h2>` and a `HelpTooltip` (`:5-13`).
- **Dutch microcopy:** none hardcoded (both `title` and `help` prop-supplied).
- **Composition:** `HelpTooltip` (`:2`).

## 7. `EmptyState.tsx`

- **Type:** server (`EmptyState.tsx:1-8`).
- **Props:** inline `{ title: string; message: string }` (`:1`).
- **Behaviour:** renders `<div className="empty-state">` with `.empty-title` paragraph and a `<p>` body (`:2-7`).
- **Dutch microcopy:** none hardcoded (all prop-driven).

## 8. `HelpText.tsx`

- **Type:** server (`HelpText.tsx:1-12`).
- **Props:** `HelpTextProps = { id?: string; text: string }` (`:1-4`); `id` optional.
- **Behaviour:** renders `<p id={id} className="help-text">` with a fixed `"Help:"` label span + `text` (`:6-11`).
- **Dutch microcopy:** `"Help:"` (`:9`) — the only hardcoded literal.

## 9. `HelpTooltip.tsx`

- **Type:** server (`HelpTooltip.tsx:1-5`).
- **Props:** inline `{ text: string }` (`:3`).
- **Behaviour:** thin wrapper over `IconButtonWithTooltip` with the info glyph `ⓘ`, accessible label `"Help"`, and the provided tooltip text (`:4`).
- **Dutch microcopy:** aria-label `"Help"` (`:4`).
- **Composition:** `IconButtonWithTooltip` (`:1`).

## 10. `IconButtonWithTooltip.tsx`

- **Type:** server (`IconButtonWithTooltip.tsx:1-13`).
- **Props:** `{ icon: string; label: string; tooltip: string }` (`:1-5`).
- **Behaviour:** renders a `<button type="button" className="icon-button">` with `aria-label={label}` and `title={tooltip}`, containing an `aria-hidden` span with the glyph (`:7-12`).
- **Dutch microcopy:** none; supplied by callers.

## 11. `MetricCard.tsx`

- **Type:** server (`MetricCard.tsx:1-22`).
- **Props:** `MetricCardProps = { title: string; value: string; status: UiStatus; help: string }` (`:4-9`).
- **Behaviour:** renders `<article className="metric-card">` with a metric head (title + `HelpTooltip`), `<h3>{value}</h3>`, and a `StatusBadge` whose label is also `value` (`:12-21`).
- **State enum:** delegates to `StatusBadge`'s `UiStatus` (see §15).
- **Composition:** `HelpTooltip` + `StatusBadge` (`:1-2`).

## 12. `PriceFreshnessBadge.tsx`

- **Type:** server (`PriceFreshnessBadge.tsx:34`).
- **Props:** local `Props = { readonly freshness: "fresh" | "stale" | "unavailable" }` (`:12-14`).
- **Behaviour:** lookup `VISUALS[freshness]` → single pill `<span>` with `role="status"` and aria-label `"Prijs-versheid: ${label}"` (`:34-54`).
- **State enum + visuals** (`:16-32`):
  - `fresh` → `"Vers"` / bg `#15803d` fg `#ffffff`.
  - `stale` → `"Verouderd"` / bg `#f59e0b` fg `#1f2937`.
  - `unavailable` → `"Niet beschikbaar"` / bg `#6b7280` fg `#ffffff`.
- **Dutch microcopy:** labels (`:20, :24, :28`); aria-label (`:41`).

## 13. `ReconciliationStatusWidget.tsx`

- **Type:** client (`ReconciliationStatusWidget.tsx:1`).
- **Public props:** none on `ReconciliationStatusWidget()` (`:42`). Internal `Metric` helper has `{ label, value, testId, warn?=false }` (`:175-185`).
- **Behaviour:** polls `/reconciliation/status` every 60 s (interval `:25`). If unavailable or `data === null`, renders `null` (`:70-75`). Else renders a clickable `next/link` card to `/admin/reconciliation` with title, mode pill (or `"Nog geen runs"` placeholder), and a 3-column metric grid (`:87-171`).
- **State enum** (`:27-39`):
  - `completed` → `"Voltooid"` / bg `#dcfce7` fg `#166534`.
  - `skipped_locked` → `"Overgeslagen (vergrendeld)"` / bg `#e5e7eb` fg `#374151`.
  - `skipped_disconnected` → `"Overgeslagen (geen verbinding)"` / bg `#fef3c7` fg `#854d0e`.
  - `error` → `"Fout"` / bg `#fecaca` fg `#7f1d1d`.
  - Fallback `"Onbekend"` (`:85`).
- **Dutch microcopy:** mode labels (`:28-31, :85`); card title `"IBKR-reconciliatie"` (`:118`); placeholder `"Nog geen runs"` (`:125`); metric labels `"Hersteld (24u)" / "Wacht op review" / "Onbekende fills"` (`:153, :158, :164`).
- **`apiClient` usage:** imports `:20-23`; calls `apiClient.getReconciliationStatus()` at `:50`.
- **Composition:** `next/link` only; internal `Metric` (`:175-201`).

## 14. `SchedulerStatusBadge.tsx`

- **Type:** client (`SchedulerStatusBadge.tsx:1`).
- **Props:** none (`:75`).
- **Behaviour:** polls `/scheduler/v127/status` every 60 s (interval `:24`). Derives state via `deriveState()` (`:34-43`) then renders a coloured pill + status dot + Dutch label (`:111-132`).
- **State enum** `BadgeState = "actief" | "uitgeschakeld" | "fout"` (`:26`) → visuals (`:28-32`):
  - `actief` → bg `#15803d` fg `#ffffff` — label `` `Actief — volgende run om ${time}` `` or `"Actief"` (`:70-73`).
  - `uitgeschakeld` → bg `#6b7280` fg `#ffffff` — label `"Uitgeschakeld"` (`:63`).
  - `fout` → bg `#f59e0b` fg `#1f2937` — label `` `Fout in laatste ${last_run_type}` `` or `"Fout in laatste run"` (`:64-69`).
  - Derivation: API error → `fout`; null status → `uitgeschakeld`; `!enabled` → `uitgeschakeld`; `last_outcome==="error"` → `fout`; else `actief` (`:34-43`).
- **Dutch microcopy:** labels (`:63, :67-68, :72`); aria-label `` `Scheduler-status: ${label}` `` (`:116`); time formatting locale `"nl-BE"` (`:50`).
- **`apiClient` usage:** imports `:22`; calls `apiClient.getSchedulerV127Status()` at `:85`.

## 15. `SectionHeader.tsx`

- **Type:** server (`SectionHeader.tsx:1-15`).
- **Props:** `SectionHeaderProps = { title: string; helpText: string }` (`:3-6`).
- **Behaviour:** renders `<header className="section-header">` with `<h2>{title}</h2>` and a `HelpText` (`:9-14`).
- **Composition:** `HelpText` (`:1`).

## 16. `StatusBadge.tsx`

- **Type:** server (`StatusBadge.tsx:1-34`).
- **Props:** `StatusBadgeProps = { label: string; status?: UiStatus; title?: string }` (`:11-15`). Default `status = "info"` (`:28`). Exported type `UiStatus` (`:1-9`).
- **Behaviour:** renders a `<span>` with class derived from `classMap[status]` and optional `title` (`:28-33`).
- **State enum (`UiStatus`)** — eight values + class mapping (`:1-9, :17-26`):

| Value | Class |
|---|---|
| `ok` | `status-badge status-badge-ok` |
| `aandacht` | `status-badge status-badge-aandacht` |
| `geblokkeerd` | `status-badge status-badge-geblokkeerd` |
| `wacht` | `status-badge status-badge-wacht` |
| `niet-beschikbaar` | `status-badge status-badge-niet-beschikbaar` |
| `sync` | `status-badge status-badge-sync` |
| `vergrendeld` | `status-badge status-badge-vergrendeld` |
| `info` (default) | `status-badge status-badge-info` |

- **Dutch microcopy:** no hardcoded Dutch — the status keys themselves are Dutch tokens (`aandacht / geblokkeerd / wacht / niet-beschikbaar / vergrendeld`) acting as the public taxonomy.

## 17. `StatusCard.tsx`

- **Type:** server (`StatusCard.tsx:1-21`).
- **Props:** `StatusCardProps = { title: string; description: string; statusLabel: string; status: UiStatus }` (`:3-8`).
- **Behaviour:** renders `<article className="dashboard-card" aria-label="${title} kaart">` with a `.card-topline` row (`<h3>{title}</h3>` + `StatusBadge`) and a `<p>{description}</p>` below (`:10-20`).
- **Dutch microcopy:** aria-label suffix `"${title} kaart"` (`:12`) — the literal Dutch word `kaart` is the only hardcoded copy.
- **Composition:** `StatusBadge`, `UiStatus` (`:1`).

## 18. `SyncStatusBadge.tsx`

- **Type:** server (`SyncStatusBadge.tsx:1-11`).
- **Props:** `SyncStatusBadgeProps = { label: string; status: UiStatus; help: string }` (`:3-7`).
- **Behaviour:** trivial pass-through to `StatusBadge` using `help` as `title` (`:9-11`).
- **Composition:** `StatusBadge`, `UiStatus` (`:1`).

## 19. `SystemEventsIndicator.tsx`

- **Type:** client (`SystemEventsIndicator.tsx:1`).
- **Props:** none (`:8`).
- **Behaviour:** on mount, calls `apiClient.getActiveSystemEvents()` once (no polling). Renders a `next/link` to `/systeemmeldingen` whose class includes `events-indicator-active` when count > 0, plus a count badge if a number is known (`:26-32`).
- **Visual modes:** active (`activeCount > 0`, class `events-indicator-active`) vs idle (`:24, :27`). No enum.
- **Dutch microcopy:** `title="Bekijk actieve systeemmeldingen."` (`:27`); label `"Systeemmeldingen"` (`:29`); glyph `🔔` (`:28`).
- **`apiClient` usage:** imports `:6`; calls `apiClient.getActiveSystemEvents()` at `:13`.

## A. Server vs client component count

| Type | Count | Components |
|---|---:|---|
| Client (`"use client"`) | **6** | `AccountModeBadge`, `CalibrationCoverageBadge`, `ColdStartBanner`, `ReconciliationStatusWidget`, `SchedulerStatusBadge`, `SystemEventsIndicator` |
| Server (stateless) | **13** | `ApiUnavailableNotice`, `ChartPlaceholder`, `DashboardPanel`, `EmptyState`, `HelpText`, `HelpTooltip`, `IconButtonWithTooltip`, `MetricCard`, `PriceFreshnessBadge`, `SectionHeader`, `StatusBadge`, `StatusCard`, `SyncStatusBadge` |

**Pattern: every client component in this cluster directly calls `apiClient`** — 1:1 between `"use client"` and `apiClient` import.

## B. Polling cadences (client cluster only)

| Component | Poll interval | Init |
|---|---|---|
| `AccountModeBadge` | **30 s** (`AccountModeBadge.tsx:18`) | first paint flash 500 ms |
| `ColdStartBanner` | **60 s** (`ColdStartBanner.tsx:24`) | mount |
| `ReconciliationStatusWidget` | **60 s** (`ReconciliationStatusWidget.tsx:25`) | mount |
| `SchedulerStatusBadge` | **60 s** (`SchedulerStatusBadge.tsx:24`) | mount |
| `CalibrationCoverageBadge` | mount-only (no interval) | — |
| `SystemEventsIndicator` | mount-only (no interval) | — |

## C. Dutch microcopy collected (40 strings across 19 components)

The full inventory below is the verification surface for the Dutch-UI invariant at the component layer.

| Component | String | File:line |
|---|---|---|
| `AccountModeBadge` | `Paper-rekening: ${id ?? "onbekend"}` | `AccountModeBadge.tsx:35` |
| `AccountModeBadge` | `IBKR paper-rekening verbonden` (aria) | `AccountModeBadge.tsx:36` |
| `AccountModeBadge` | `Echte rekening: ${id ?? "onbekend"}` | `AccountModeBadge.tsx:43` |
| `AccountModeBadge` | `IBKR live-rekening verbonden` (aria) | `AccountModeBadge.tsx:44` |
| `AccountModeBadge` | `Geen IBKR-verbinding` (label) | `AccountModeBadge.tsx:51` |
| `AccountModeBadge` | `Geen IBKR-verbinding` (aria) | `AccountModeBadge.tsx:52` |
| `ApiUnavailableNotice` | `API niet bereikbaar` | `ApiUnavailableNotice.tsx:6` |
| `ApiUnavailableNotice` | `De dashboardgegevens kunnen nu niet worden opgehaald.` | `ApiUnavailableNotice.tsx:7` |
| `ApiUnavailableNotice` | `Start eerst de backend-API. Daarna vernieuw je deze pagina om de status te laden.` | `ApiUnavailableNotice.tsx:8` |
| `CalibrationCoverageBadge` | `Kalibratie: goed` | `CalibrationCoverageBadge.tsx:40` |
| `CalibrationCoverageBadge` | `Kalibratie: matig` | `CalibrationCoverageBadge.tsx:46` |
| `CalibrationCoverageBadge` | `Kalibratie: te weinig data` | `CalibrationCoverageBadge.tsx:52` |
| `CalibrationCoverageBadge` | `Geen voorspellingen geëvalueerd in laatste ${window_days} dagen.` | `CalibrationCoverageBadge.tsx:114` |
| `CalibrationCoverageBadge` | `${n} voorspellingen geëvalueerd in laatste ${window_days} dagen; ${pct}% binnen p10–p90 band.` | `CalibrationCoverageBadge.tsx:115` |
| `ChartPlaceholder` | `Grafiek placeholder` (aria) | `ChartPlaceholder.tsx:3` |
| `ColdStartBanner` | `Naar Volglijst` | `ColdStartBanner.tsx:89` |
| `HelpText` | `Help:` | `HelpText.tsx:9` |
| `HelpTooltip` | `Help` (aria) | `HelpTooltip.tsx:4` |
| `PriceFreshnessBadge` | `Vers` | `PriceFreshnessBadge.tsx:20` |
| `PriceFreshnessBadge` | `Verouderd` | `PriceFreshnessBadge.tsx:24` |
| `PriceFreshnessBadge` | `Niet beschikbaar` | `PriceFreshnessBadge.tsx:28` |
| `PriceFreshnessBadge` | `Prijs-versheid: ${label}` (aria) | `PriceFreshnessBadge.tsx:41` |
| `ReconciliationStatusWidget` | `Voltooid` | `ReconciliationStatusWidget.tsx:28` |
| `ReconciliationStatusWidget` | `Overgeslagen (vergrendeld)` | `ReconciliationStatusWidget.tsx:29` |
| `ReconciliationStatusWidget` | `Overgeslagen (geen verbinding)` | `ReconciliationStatusWidget.tsx:30` |
| `ReconciliationStatusWidget` | `Fout` | `ReconciliationStatusWidget.tsx:31` |
| `ReconciliationStatusWidget` | `Onbekend` (fallback) | `ReconciliationStatusWidget.tsx:85` |
| `ReconciliationStatusWidget` | `IBKR-reconciliatie` | `ReconciliationStatusWidget.tsx:118` |
| `ReconciliationStatusWidget` | `Nog geen runs` | `ReconciliationStatusWidget.tsx:125` |
| `ReconciliationStatusWidget` | `Hersteld (24u)` | `ReconciliationStatusWidget.tsx:153` |
| `ReconciliationStatusWidget` | `Wacht op review` | `ReconciliationStatusWidget.tsx:158` |
| `ReconciliationStatusWidget` | `Onbekende fills` | `ReconciliationStatusWidget.tsx:164` |
| `SchedulerStatusBadge` | `Uitgeschakeld` | `SchedulerStatusBadge.tsx:63` |
| `SchedulerStatusBadge` | `Fout in laatste ${run_type}` / `Fout in laatste run` | `SchedulerStatusBadge.tsx:67-68` |
| `SchedulerStatusBadge` | `Actief — volgende run om ${time}` / `Actief` | `SchedulerStatusBadge.tsx:72` |
| `SchedulerStatusBadge` | `Scheduler-status: ${label}` (aria) | `SchedulerStatusBadge.tsx:116` |
| `StatusCard` | `${title} kaart` (aria) | `StatusCard.tsx:12` |
| `SystemEventsIndicator` | `Bekijk actieve systeemmeldingen.` | `SystemEventsIndicator.tsx:27` |
| `SystemEventsIndicator` | `Systeemmeldingen` | `SystemEventsIndicator.tsx:29` |

The `ColdStartBanner` body text is server-supplied (`banner_text` from the API response, rendered at `ColdStartBanner.tsx:76`) — not hardcoded but still Dutch by API contract.

## D. Badge / status-enum vocabulary (combined)

Two distinct status taxonomies coexist:

(a) **The generic CSS-class `UiStatus` enum** in `StatusBadge.tsx:1-9` (8 Dutch tokens: `ok / aandacht / geblokkeerd / wacht / niet-beschikbaar / sync / vergrendeld / info`) — reused by `MetricCard`, `StatusCard`, `SyncStatusBadge`.

(b) **Per-feature locked enums** embedded inside each polling badge (account mode, calibration, price freshness, scheduler, reconciliation mode, cold-start state) — these don't go through `StatusBadge` and have their own inline-styled colour tables.

| Component | Status value | Dutch label | File:line |
|---|---|---|---|
| `AccountModeBadge` | `paper` | `Paper-rekening: ${id}` | `AccountModeBadge.tsx:35` |
| `AccountModeBadge` | `live` | `Echte rekening: ${id}` | `AccountModeBadge.tsx:43` |
| `AccountModeBadge` | `disconnected` | `Geen IBKR-verbinding` | `AccountModeBadge.tsx:51` |
| `CalibrationCoverageBadge` | `healthy` | `Kalibratie: goed` | `CalibrationCoverageBadge.tsx:40` |
| `CalibrationCoverageBadge` | `warning` | `Kalibratie: matig` | `CalibrationCoverageBadge.tsx:46` |
| `CalibrationCoverageBadge` | `insufficient` | `Kalibratie: te weinig data` | `CalibrationCoverageBadge.tsx:52` |
| `PriceFreshnessBadge` | `fresh` / `stale` / `unavailable` | `Vers` / `Verouderd` / `Niet beschikbaar` | `PriceFreshnessBadge.tsx:20, 24, 28` |
| `SchedulerStatusBadge` | `actief` / `uitgeschakeld` / `fout` | dynamic / `Uitgeschakeld` / `Fout in laatste …` | `SchedulerStatusBadge.tsx:63, 67-72` |
| `StatusBadge (UiStatus)` | `ok` / `aandacht` / `geblokkeerd` / `wacht` / `niet-beschikbaar` / `sync` / `vergrendeld` / `info` | label via prop; CSS modifier per status | `StatusBadge.tsx:1-9, :17-26` |
| `ReconciliationStatusWidget` | `completed` / `skipped_locked` / `skipped_disconnected` / `error` / *(unknown)* | `Voltooid` / `Overgeslagen (vergrendeld)` / `Overgeslagen (geen verbinding)` / `Fout` / `Onbekend` | `ReconciliationStatusWidget.tsx:28-31, :85` |
| `ColdStartBanner` (server state) | `unconfirmed` | banner_text from server | `ColdStartBanner.tsx:53, :76` |
| `ColdStartBanner` | `confirmed` / `no_account_configured` | renders `null` | `ColdStartBanner.tsx:9-13, :53` |

## E. Inter-component composition graph

Imports between the 19 components:

- `ApiUnavailableNotice` → `HelpText` (`ApiUnavailableNotice.tsx:1`).
- `DashboardPanel` → `HelpTooltip` (`DashboardPanel.tsx:2`).
- `HelpTooltip` → `IconButtonWithTooltip` (`HelpTooltip.tsx:1`).
- `MetricCard` → `HelpTooltip` + `StatusBadge` (`MetricCard.tsx:1-2`).
- `SectionHeader` → `HelpText` (`SectionHeader.tsx:1`).
- `StatusCard` → `StatusBadge` (`StatusCard.tsx:1`).
- `SyncStatusBadge` → `StatusBadge` (`SyncStatusBadge.tsx:1`).

All other 12 components have no imports from this set.

## F. Cross-cutting observations

- **No component declares an `extra` / spread prop.** All public surfaces are explicitly enumerated — useful for the strict-types invariant.
- **`ApiUnavailableNotice` is documented here but not used by any page** (verified in `web-pages.md` §4). It composes `HelpText` cleanly but pages prefer inline Dutch fallbacks.
- **Two distinct status taxonomies coexist** — see §D. Both are Dutch-token-based; the generic `UiStatus` set is reused most widely. A future consolidation pass could collapse the per-feature enums into `UiStatus`-class tokens, but the per-feature colour tables are richer than `UiStatus` allows.
- **Polling at 30 s / 60 s** is the entire client-side cadence — no SWR, no React Query, no WebSockets. Page-level refreshes are user-driven (see `web-pages.md` §4).
- **All 6 client components fetch one endpoint each.** No client component chains two `apiClient` calls — that pattern lives in the feature-grid cluster (sibling doc, e.g. `ForecastExplanationPanel`).
- **No component receives or emits Decimal-as-string fields.** Numeric formatting on the status side is integer-only (`ReconciliationStatusWidget`'s metric counts at `:153, :158, :164`).
