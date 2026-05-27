# Reality — web components, feature grids

**Scope.** 11 of the 30 non-test `.tsx` files under `apps/web/components/`: the domain-specific grids, drawers, and forms that touch the action-draft / decision-package / IBKR-submission state machines. The 19 generic / status / shared components are covered by `docs/reality/components/web-components-status-and-shared.md`.

Verification: `find apps/web/components -name '*.tsx' -not -name '*.test.tsx'` returns exactly **30 files** → 19 (sibling) + 11 (this doc) = 30, no duplicates.

Intent reference: AGENTS.md Dutch-UI rule + `docs/ui-principles.md` (see `web-pages.md` §1).

## In-scope components (11)

| Component | Lines | Type | Direct `apiClient`? |
|---|---:|---|---|
| `ActionDraftEditForm.tsx` | 177 | client | mutation only (PATCH) |
| `ActionDraftGrid.tsx` | 440 | client | mutations (approve / dismiss / delete) |
| `DecisionPackageDetail.tsx` | 440 | client | mutation (create action draft) |
| `ForecastDaySummaryWidget.tsx` | 150 | client | read (polled 60 s) |
| `ForecastExplanationPanel.tsx` | 278 | client | reads (forecast + DP) |
| `IbkrSubmissionGrids.tsx` | 416 | client | mutation (cancel submitted) |
| `PortefeuilleRealtimeSection.tsx` | 369 | client | reads (4-way parallel, polled 30 s) |
| `PositionPlTraceDetails.tsx` | 115 | **server** | none |
| `SubmissionLifecycleDrawer.tsx` | 288 | client | read |
| `ValuationTraceDetails.tsx` | — | **server** | none |
| `VolglijstColdStartFlow.tsx` | 225 | client | read + 2 mutations |

**Server / client split: 9 client / 2 server.** The two server components are pure prop-driven trace renderers; everything else is `"use client"`.

## 1. `ActionDraftEditForm.tsx`

- **Type:** client (`ActionDraftEditForm.tsx:1`).
- **Props** (`:21-25`): `draft: ActionDraftResponse`, `onCancel: () => void`, `onSaved: () => void`.
- **Data flow:** receives `draft` via props; no read calls; single PATCH on submit. `apiClient.patchActionDraft(draft.action_draft_id, payload)` (`:65`). No `useEffect`.
- **Local state (5×`useState`):** `quantity` (init `draft.quantity`, `:26`); `limitPrice` (init `draft.limit_price_local`, `:27`); `userNote` (init `draft.user_note ?? ""`, `:28`); `busy` (init `false`, `:29`); `error` (init `null`, `:30`).
- **State-machine touchpoint:** `proposed → edited` (or `edited → edited`) via `apiClient.patchActionDraft` (`:65`). Does not drive `user_approved`.
- **Loading / error:** no optimistic updates; `busy` disables both buttons (`:145, :162`); inline error block (`:127-140`).
- **Dutch microcopy:**
  - `"Aantal moet groter dan 0 zijn."` (`:36`)
  - `"Limietprijs moet groter dan 0 zijn."` (`:39`)
  - `"Bewerken mislukt."` (`:71`)
  - `"Aantal"` heading (`:93`); `"Limietprijs (${draft.currency_local})"` (`:105-106`); `"Notitie"` (`:119`); `"Opslaan"` (`:156`); `"Annuleren"` (`:172`).
- **Decimal-as-string boundary:** PATCH payload echoes raw strings (`:53, :55`) — no precision loss on the wire. Validation uses `Number(quantity)` and `Number(limitPrice)` (`:33-34`) only for the `<= 0` / NaN check.
- **Composition:** imports `apiClient`, `ActionDraftResponse` (`:15`).

## 2. `ActionDraftGrid.tsx`

- **Type:** client (`ActionDraftGrid.tsx:1`).
- **Props:** `ActionDraftGrid` `{ drafts: ActionDraftResponse[]; onChange: () => void }` (`:86-92`). Internal `ActionDraftRow` takes one `draft` + `onChange` (`:123-129`).
- **Data flow:** no reads (data via props); three mutations:
  - `apiClient.approveActionDraft(draft.action_draft_id)` (`:154`).
  - `apiClient.dismissActionDraft(draft.action_draft_id, reason || undefined)` (`:169`).
  - `apiClient.deleteActionDraft(draft.action_draft_id)` (`:188`).
- **Local state (3×`useState` in `ActionDraftRow`):** `editing` (`:130`), `busy` (`:131`), `error` (`:132`).
- **State-machine touchpoints:**
  - `proposed | edited → user_approved` via `approveActionDraft` (`:154`).
  - `proposed | edited → dismissed` via `dismissActionDraft` (`:169`).
  - `proposed | edited → deleted` via `deleteActionDraft` (`:188`).
  - Approval gated by `window.prompt` requiring literal `"JA"` (`:141-151`).
- **Loading / error:** no optimistic updates; relies on parent `onChange()` re-fetch (`:160, :178, :194`). Per-row error banner (`:346-360`). Buttons disabled when `busy !== null` (`:375, :392, :408, :424`). Empty-state card (`:94-107`). "Goedgekeurd" success banner (`:329-344`).
- **Dutch microcopy:**
  - `"Geen actiedrafts om te keuren."` (`:105`)
  - `"Goedkeuring geannuleerd. Type exact JA om door te gaan."` (`:149`)
  - `"Optionele reden voor dismiss (mag leeg blijven):"` (`:165`)
  - `"Weet je zeker dat je deze draft wil verwijderen?"` (`:183`)
  - `"Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd."` (`:341-342`)
  - `"Advies gewijzigd"` (superseded badge) (`:258`)
  - Buttons: `"Goedkeuren"` (`:386`), `"Bewerken"` (`:402`), `"Dismiss"` (`:418`), `"Verwijder"` (`:434`).
- **Status label vocabulary** in `STATUS_COLOR` (`:47-76`) — 15 Dutch labels: `Voorgesteld`, `Bewerkt`, `Goedgekeurd`, `Genegeerd`, `Verwijderd`, `Verouderd`, `Verstuurd`, `Geaccepteerd`, `Actief`, `Gedeeltelijk uitgevoerd`, `Uitgevoerd`, `Geannuleerd`, `Geweigerd`, `Annulering aangevraagd`, `Wacht op IBKR-bevestiging`.
- **Decimal-as-string boundary:** `fmtDecimal` (`:30-37`) uses `Number(value)` for display only — **potential precision-loss site on render** (`:31`). Wire format unchanged. Renders `draft.quantity`, `draft.limit_price_local`, `draft.notional_eur` via `fmtDecimal` (`:307, :311, :315`). `JA`-prompt also reformats via `fmtDecimal` (`:144-146`). No `parseFloat`.
- **Composition:** imports `apiClient`, `ActionDraftResponse` (`:21`); imports `ActionDraftEditForm` from `./ActionDraftEditForm` (`:23`), rendered at `:284-291`. Status badge inlined.

## 3. `DecisionPackageDetail.tsx`

- **Type:** client (`DecisionPackageDetail.tsx:1`).
- **Props** (`:75-79`): `package: DecisionPackageResponse` (aliased to local `pkg`).
- **Data flow:** receives the full package via props; one mutation on click — `apiClient.createActionDraft({ decision_package_id: pkg.decision_package_id })` (`:91-93`). Uses `useRouter` from `next/navigation` (`:15, :80`) for post-mutation navigation. No `useEffect`.
- **Local state (3×`useState`):** `hashExpanded` (`:81`), `creatingDraft` (`:82`), `draftError` (`:83`).
- **State-machine touchpoint:** creates an `action_draft` row (initial status `proposed`) from a Decision Package via `createActionDraft` (`:91`). This is the DP → action_draft entry-point. Gate enforced by `ACTIONABLE_LABELS = {"Kopen", "Verminderen", "Verkopen"}` (`:69-73`, checked `:86`).
- **Loading / error:** button label flips to `"Bezig…"` while `creatingDraft` (`:419`); button disabled (`:408`); error banner (`:421-435`); on success `router.push(...)` (`:99-101`).
- **Dutch microcopy:**
  - Section headings: `"Voorspelling"` (`:160`), `"Huidige situatie"` (`:207`), `"Gate-uitkomsten"` (`:244`), `"Bewijsbronnen"` (`:290`), `"Onderbouwing"` (`:308`), `"Audit"` (`:324`), `"Actie"` (`:398`).
  - `"Betrouwbaarheid: ..."` (`:143`); `"Samengesteld op ... — geldig tot ..."` (`:150-152`).
  - Column labels (`:170, :178, :185, :192`): `"Bandbreedte (EUR)"`, `"Kans op stijging"`, `"Kans op verlies (>5%)"`, `"Verwachte volatiliteit"`.
  - `"Niet in portefeuille."` (`:237`); `"Geslaagd"` / `"Gefaald"` (`:274`); `"Inkorten" / "Toon volledig"` (`:356`).
  - `"Maak een actiedraft aan in het IBKR Acties scherm. ..."` (`:399-403`); `"Maak actie"` / `"Bezig…"` (`:419`); `"Aanmaken van actiedraft mislukt."` (`:96`).
  - Label vocabulary `LABEL_COLOR` (`:23-27`): `Kopen`, `Verminderen`, `Verkopen`, `Houden`, `Bekijken`.
  - `FRESHNESS_LABEL` (`:40-42`): `Vers`, `Verouderd`, `Niet beschikbaar`.
  - `CONFIDENCE_LABEL` (`:31-33`): `Hoog`, `Gemiddeld`, `Laag`.
- **Decimal-as-string boundary:** `fmtEUR` uses `Number(value).toFixed(2)` (`:56`) — **precision-loss site** on `pkg.p10_price_eur`, `pkg.p50_price_eur`, `pkg.p90_price_eur`, `pkg.current_price_eur`. `fmtPct` uses `Number(value) * 100` (`:60`) — applied to `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized`. `pkg.current_price_local`, `held_quantity`, `held_avg_cost_local` rendered raw (`:222, :236`) — safe.
- **Composition:** imports `apiClient`, `DecisionPackageResponse`, `ForecastConfidenceLevel` (`:17`); `useRouter` (`:15`).

## 4. `ForecastDaySummaryWidget.tsx`

- **Type:** client (`ForecastDaySummaryWidget.tsx:1`).
- **Props:** none (`:47`).
- **Data flow:** `apiClient.getForecastDaySummary()` (`:55`). `useEffect` deps `[]` (mount-only, `:51-73`). Polls every 60 000 ms via `window.setInterval` (`:66`). Cleanup clears interval (`:71`).
- **Local state (2×`useState`):** `data` (`:48`), `unavailable` (`:49`).
- **State-machine touchpoint:** none — read-only widget.
- **Loading / error:** returns `null` when unavailable (`:75-77`) or while data is loading (`:78-80`) — no spinner. Empty-state at `:106-112` when `total_forecasts === 0`.
- **Dutch microcopy:**
  - Header `"Vandaag's voorspellingen"` (`:103`).
  - Empty state `"Geen voorspellingen vandaag — wacht op volgende morgenrun om 07:00."` (`:111`).
  - Totals line `"${total_forecasts} voorspellingen, ${total_blocked} geblokkeerd."` (`:118-119`).
  - Pill labels from `LABEL_ORDER` (`:28-35`): `Kopen`, `Bekijken`, `Houden`, `Verminderen`, `Verkopen`, `Geblokkeerd`.
- **Decimal-as-string boundary:** none — only integer counts.
- **Composition:** imports `Link` (`:17`); `apiClient`, `ForecastDaySummaryResponse`, `ForecastLabel` (`:20-24`).

## 5. `ForecastExplanationPanel.tsx`

- **Type:** client (`ForecastExplanationPanel.tsx:1`).
- **Props** (`:31-35`): `conid: string`, `open: boolean`, `onClose: () => void`.
- **Data flow:** two reads chained in the same `useEffect`:
  - `apiClient.getForecastLatest(conid)` (`:69`).
  - `apiClient.getLatestDecisionPackage({ conid })` (`:80`).
  - `useEffect` deps `[open, conid]` (`:90`); cancel-guarded.
- **Local state (3×`useState`):** `data` (`:53`), `errorReason` (`:54`), `decisionPackageId` (`:55-57`).
- **State-machine touchpoint:** none — informational only. Provides a deep-link to `/decision-package/{id}` at `:248` but does not mutate.
- **Loading / error:** `"Bezig met laden…"` (`:165-167`); `"Voorspelling is op dit moment niet beschikbaar."` (`:159-163`); modal renders nothing if `!open` (`:92-94`).
- **Dutch microcopy:**
  - Title `"Waarom deze voorspelling?"` (`:140`).
  - Close aria-label `"Sluiten"` (`:146`).
  - Section labels (`:179, :189, :194, :199, :209, :214, :219, :225, :230, :235`): `Verwachte richting`, `Kans op stijging`, `Kans op verlies (>5%)`, `Verwachte bandbreedte`, `Risico (verwachte volatiliteit)`, `Betrouwbaarheid`, `Onderbouwing`, `Methode`, `Geldig tot`, `Kalibratie (laatste 90 dagen)`.
  - Method constant `"Historische bootstrap, 252 dagen, blok-resampling"` (`:37`).
  - `"Bekijk Decision Package"` link (`:260`).
  - Footer disclaimer `"Informatief — geen handelsadvies. Orders worden alleen na expliciete bevestiging in de approval-gate ingelegd."` (`:272-273`).
- **Decimal-as-string boundary:** `pct` uses `Number(value) * 100` (`:40`) — **precision-loss site** for `data.prob_positive` (`:191`), `data.prob_loss_gt_5pct` (`:196`), `data.expected_volatility_annualized` (`:211`). Inline `Number(data.per_asset_coverage.hit_rate_within_band) * 100` at `:239`. Prices (`p10/p90_price_local`, `p10/p90_price_eur`, `p50_log_return`) rendered raw — safe.
- **Composition:** imports `apiClient`, `ForecastLatestResponse` (`:26-29`).

## 6. `IbkrSubmissionGrids.tsx`

- **Type:** client (`IbkrSubmissionGrids.tsx:1`).
- **Public props:** two named exports —
  - `ActiefBijIbkrGrid` (`:123-131`): `{ drafts: ActionDraftResponse[]; onChange: () => void; onOpenLifecycle: (actionDraftId: string) => void }`.
  - `HistoriekGrid` (`:307-313`): `{ drafts: ActionDraftResponse[]; onOpenLifecycle: (actionDraftId: string) => void }`.
- **Data flow:** props-driven; single mutation in `ActiefBijIbkrRow`: `apiClient.cancelSubmittedActionDraft(draft.action_draft_id)` (`:186`). No `useEffect`.
- **Local state (in `ActiefBijIbkrRow`):** `busy` (`:171`), `error` (`:172`). `HistoriekRow` is stateless.
- **State-machine touchpoint:** `submitted | accepted | working | partially_filled → pending_cancellation` via `cancelSubmittedActionDraft` (`:186`). Predicate `cancellable` (`:173-177`) gates which statuses expose the button.
- **Loading / error:** label flips to `"Bezig…"` when `busy` (`:295`), disabled via `busy` (`:284`); inline error block (`:262-276`). Empty states: `"Geen actieve IBKR-orders."` (`:144`) / `"Geen afgeronde orders."` (`:326`). No optimistic update — parent `onChange()` (`:194`).
- **Dutch microcopy:**
  - Cancel prompt `"Order voor ${qty}× ${symbol} annuleren?"` (`:180-182`); `"Annulering mislukt."` (`:191`); `"Annuleer" / "Bezig…"` button (`:295`).
  - Column labels (`:248-258, :401-411`): `Aantal`, `Limietprijs`, `Notional EUR`, `Verstuurd op`, `Afgesloten op`; `"Lifecycle"` button (`:236, :389`).
  - `STATUS_BADGE` table (`:31-58`) — 15 Dutch labels matching `ActionDraftGrid.STATUS_COLOR`.
- **Decimal-as-string boundary:** `fmtDecimal` uses `Number(value)` (`:74`) — **precision-loss site** for `draft.quantity`, `draft.limit_price_local`, `draft.notional_eur` (`:249, :252, :255, :402, :405, :408`). No `parseFloat`.
- **Composition:** imports `apiClient`, `ActionDraftResponse`, `ActionDraftStatus` (`:21-25`). Internal sub-components `StatusBadge` (`:82-99`) + `SideBadge` (`:101-117`) used by both row types. Parent wires `SubmissionLifecycleDrawer` via the `onOpenLifecycle` callback.

## 7. `PortefeuilleRealtimeSection.tsx`

- **Type:** client (`PortefeuilleRealtimeSection.tsx:1`).
- **Public props:** none on the outer component (`:64`). Internal sub-components `CashSummaryCard` (`:200-203`) and `PositionsGrid` (`:275-281`) take typed snapshot data.
- **Data flow:** `Promise.all` of four reads —
  - `apiClient.getIbkrConnectionStatus()` (`:82`).
  - `apiClient.getIbkrSyncPositionsLatest()` (`:83`).
  - `apiClient.getIbkrSyncCashLatest()` (`:84`).
  - `apiClient.getMarketDataByAccount()` (`:85`).
  - `useEffect` deps `[]` (mount-only, `:76-106`). Polls every 30 000 ms (`:99-101`); cleanup clears interval and toggles `cancelled` flag.
- **Local state (6×`useState`):** `status` (`:65-67`), `positions` (`:68-69`), `cash` (`:70`), `marketData` (`:71-72`), `loaded` (`:73`), `hasStorageError` (`:74`).
- **State-machine touchpoint:** none — read-only.
- **Loading / error:** skeleton state (`:108-149`, `aria-busy="true"`); disconnected banner with `role="alert"` (`:153-180`); storage-error sub-message (`:172-176`); cash card empty variant (`:205-221`); positions grid empty variant (`:282-289`).
- **Dutch microcopy:**
  - Heading `"IBKR portefeuille"` (`:116, :189`); `"Bezig met laden…"` (`:119`).
  - `"IBKR-verbinding ontbreekt. Controleer Instellingen of activeer de verbinding."` (`:170-171`).
  - `"De opslag is momenteel niet bereikbaar."` (`:174`).
  - `"Niet beschikbaar — nog geen cash-snapshot opgeslagen."` (`:218`); `"Niet beschikbaar"` constant (`:34`).
  - Cash columns (`:243-247`): `Valuta`, `Beschikbare middelen`, `Netto liquidatie`, `Totale cash`, `Buying power`.
  - `"Kassaldo"` (`:217, :233`); `"Bijgewerkt: {ts}"` (`:235`).
  - `"Geen posities in deze rekening."` (`:286`).
  - Positions columns (`:315-323`): `Symbool`, `Beurs`, `Aantal`, `Gem. kostprijs`, `Huidige prijs`, `Waarde (EUR)`, `Niet-gerealiseerde W/V`, `Verversingsstatus`, `Verversingsdatum`.
  - `"Prijzen bijgewerkt: {date} via {via}"` / `"Prijzen nog niet opgehaald"` (`:298-299`).
- **Decimal-as-string boundary — exemplary preservation:** `formatNumber` (`:36-39`) **passes Decimal strings verbatim** without `Number(...)` conversion. Doctrine comment at `:18-19`. Used for `row.quantity`, `row.avg_cost`, `currentPrice`, `valueEur`, `row.unrealized_pnl` (`:338-342`). `formatCashLabel` (`:58-62`) prepends currency code to raw string. No `parseFloat`, no `Number(...)` on financial fields anywhere in this component.
- **Composition:** imports `apiClient` + 5 response types (`:22-29`); imports `PriceFreshnessBadge` (`:30`), rendered at `:344-346`. Internal `CashSummaryCard` (`:200`) + `PositionsGrid` (`:275`).

## 8. `PositionPlTraceDetails.tsx`

- **Type:** **server** (no `"use client"`, no hooks). File starts at `:1` with `import type { ReactElement } from "react";`.
- **Props:** `type PositionPlTraceDetailsProps` (`:6-25`): `row: Pick<PortfolioValuationReadinessRow, ...>` — 13 picked fields (`missing_cost_basis_inputs`, `missing_pl_inputs`, `cost_basis_input_trace`, `unrealized_pl_input_trace`, `cost_basis_status_nl`, `cost_basis_help_nl`, `unrealized_pl_status_nl`, `unrealized_pl_help_nl`, `conid`, `symbol`, `currency`, `quantity`, `average_cost`, `last_market_snapshot_id`, `market_price_timestamp`).
- **Data flow:** none — props-only. No hooks. No `useReducer`.
- **State-machine touchpoint:** none — read-only audit/trace view.
- **Loading / error:** renders inside a `<details>` collapsible (`:82`) — no spinner. `"Niet beschikbaar"` fallback via `showValue` (`:76-78`); raw-audit `<details>` sub-section (`:62-67`).
- **Dutch microcopy:**
  - Header `"Details"` (`:83`).
  - Disclaimer `"Controle en herkomst van kostbasis en winst/verlies. Alleen opgeslagen gegevens worden getoond; er worden geen waarden berekend in de browser."` (`:84`).
  - Field labels (`:86-92`): `Conid:`, `Symbool:`, `Valuta:`, `Aantal:`, `Gemiddelde kost (brokerinput):`, `Marktsnapshot:`, `Prijsmoment:`.
  - Section headings: `"Kostbasiscontrole"` (`:95`), `"Winst/verliescontrole"` (`:103`).
  - `"Geen ontbrekende kostbasisinvoer gevonden"` (`:100`); `"Geen ontbrekende winst/verliesinvoer gevonden"` (`:108`).
  - `"Ruwe auditdata (technisch, geen adviessignaal)"` (`:63`).
  - `"Niet direct leesbaar: detaillijst beschikbaar."` / `"Niet direct leesbaar: detailobject beschikbaar."` / `"Niet beschikbaar"` (`:40-42, :77`).
  - Section titles via `renderTraceSection` (`:111-112`): `"Herkomst kostbasis"`, `"Herkomst winst/verlies"`.
- **Decimal-as-string boundary:** `row.quantity`, `row.average_cost` rendered raw via `showValue` (`:89-90`) — no conversion. Safe.
- **Composition:** type imports only (`:1-2`).

## 9. `SubmissionLifecycleDrawer.tsx`

- **Type:** client (`SubmissionLifecycleDrawer.tsx:1`).
- **Props** (`:64-72`): `actionDraftId: string | null`, `open: boolean`, `onClose: () => void`.
- **Data flow:** `apiClient.getIbkrSubmissionLifecycle(actionDraftId)` (`:88-90`). `useEffect` deps `[open, actionDraftId]` (`:105`); cancel-guarded.
- **Local state (2×`useState`):** `events` (`:73-75`), `error` (`:76`).
- **State-machine touchpoint:** none — read-only timeline of `status_change`, `fill`, `commission_report`, `cancellation_request` events.
- **Loading / error:** `"Bezig met laden…"` (`:172`); error banner (`:157-169`); empty placeholder (`:173-176`); returns `null` when not open or no draft ID (`:107`).
- **Dutch microcopy:**
  - `EVENT_LABEL_NL` (`:23-31`): `Statuswijziging`, `Uitvoering`, `Commissie`, `Annulering door gebruiker`.
  - `STATUS_LABEL_NL` map (`:33-43`): `Verstuurd`, `Geaccepteerd`, `Actief bij IBKR`, `Gedeeltelijk uitgevoerd`, `Uitgevoerd`, `Geannuleerd`, `Geweigerd`, `Annulering aangevraagd`, `Wacht op IBKR-bevestiging`.
  - Header `"Lifecycle"` (`:136`); `"Sluiten"` (`:150`).
  - `"Lifecycle kon niet worden geladen. Controleer of de API draait."` (`:94-95`).
  - `"Nog geen lifecycle-events voor deze draft."` (`:175`).
  - DT labels (`:224, :228, :234, :246, :250, :254, :262`): `Van`, `Naar`, `IBKR-status`, `Hoeveelheid`, `Prijs`, `Nieuwe status`, `Commissie`.
- **Decimal-as-string boundary:** `fmtDecimal` uses `Number(value)` (`:57`) — **precision-loss site** for `event.fill_quantity`, `event.fill_price_local`, `event.commission` (`:248, :252, :264`).
- **Composition:** imports `apiClient`, `IbkrSubmissionLifecycleEvent` (`:18-21`).

## 10. `ValuationTraceDetails.tsx`

- **Type:** **server** (no `"use client"`, no hooks). File begins with `import type { ReactElement }` at `:1`.
- **Props:** `type ValuationTraceDetailsProps` (`:6-17`): `readiness: Pick<PortfolioValuationReadinessResponse, ...>` — 7 picked fields (`valuation_input_trace`, `missing_total_value_inputs`, `missing_market_data_conids`, `missing_cash_inputs`, `missing_fx_pairs`, `stale_fx_pairs`, `invalid_fx_pairs`).
- **Data flow:** none.
- **State-machine touchpoint:** none.
- **Loading / error:** collapsible `<details>` wrapper (`:61`); `hasBlockers` (`:37-46`) gates blocker list (`:68-77`) vs `"Geen blokkerende details gevonden..."` (`:78`); empty-trace fallback (`:82-83`); raw audit nested `<details>` (`:94-99`).
- **Dutch microcopy:**
  - `"Controle en herkomst"` (`:62`).
  - `"Hier zie je waarom de totaalwaarde wel of niet veilig getoond wordt en uit welke opgeslagen gegevens de waardering komt."` (`:64-65`).
  - Section headings: `"Blokkerende details"` (`:67`), `"Trace van invoer"` (`:81`), `"Ruwe auditdata (technisch, geen adviessignaal)"` (`:96`).
  - Blocker labels (`:70-75`): `Ontbrekende invoer`, `Marktdata ontbreekt`, `Cashsnapshot ontbreekt`, `Wisselkoers ontbreekt`, `Wisselkoers verouderd`, `Wisselkoers ongeldig`.
  - Fallbacks (`:32-34`): `"Niet direct leesbaar: detaillijst beschikbaar."`, `"Niet direct leesbaar: detailobject beschikbaar."`, `"Niet beschikbaar"`.
- **Decimal-as-string boundary:** renders no numeric Decimal fields directly; raw JSON dump via `JSON.stringify` (`:97`). Safe.
- **Composition:** type imports only (`:1-2`).

## 11. `VolglijstColdStartFlow.tsx`

- **Type:** client (`VolglijstColdStartFlow.tsx:1`).
- **Props** (`:26-30`): `readonly onConfirmed: () => void`.
- **Data flow:** fetch on mount + two mutations:
  - `apiClient.getColdStartWatchlistItems()` (`:43`).
  - `apiClient.deleteColdStartWatchlistItem(watchlistItemId)` (`:58-60`).
  - `apiClient.confirmWatchlist(phrase)` (`:74`).
  - `useEffect` deps `[]` (`:40-54`); cancel-guarded.
- **Local state (5×`useState`):** `items` (`:34`), `phrase` (`:35`), `error` (`:36`), `submitting` (`:37`), `loaded` (`:38`).
- **State-machine touchpoints** (watchlist confirmation flow):
  - `cold_start_watchlist_item.active → archived` via `deleteColdStartWatchlistItem` (`:58`).
  - `watchlist confirmation: unconfirmed → confirmed` via `confirmWatchlist` (`:74`). **Requires literal `"BEVESTIG"` typed by the user.**
- **Optimistic UI:** after archive API success, the row is removed from local state without re-fetch — `setItems((prev) => prev.filter(...))` (`:65-67`). This is the **only optimistic update in the 11-component cluster**.
- **Loading / error:** `"Bezig met laden…"` (`:111`); empty-list placeholder (`:112-115`); error message `role="alert"` (`:212-220`); submit button disabled when `!canSubmit || submitting`; label flips to `"Bezig met bevestigen…"` (`:210`).
- **Dutch microcopy:**
  - Yellow card `"Startvoorstel. Verwijder of voeg toe wat je wilt. Klik op 'Volglijst bevestigen' wanneer je tevreden bent."` (`:100-102`).
  - `"Volglijst-startvoorstel"` heading (`:107`).
  - `"Geen items in het startvoorstel."` (`:114`).
  - `"+ Asset toevoegen"` (`:159`); `"Verwijder"` (`:150`).
  - `"Bevestig je Volglijst"` (`:171`).
  - `"Typ het woord BEVESTIG (in hoofdletters) om te bevestigen. Daarna start het systeem met geplande runs."` (`:174-177`).
  - `"Bevestigingsfrase"` aria (`:193`).
  - `"Volglijst bevestigen"` / `"Bezig met bevestigen…"` (`:210`).
- **Decimal-as-string boundary:** none — items contain only `symbol`, `name`, `exchange`, `watchlist_item_id`.
- **Composition:** imports `apiClient`, `ColdStartWatchlistItem` (`:20-23`).

## A. Server vs client component count

| Type | Count | Components |
|---|---:|---|
| Client (`"use client"`) | **9** | `ActionDraftEditForm`, `ActionDraftGrid`, `DecisionPackageDetail`, `ForecastDaySummaryWidget`, `ForecastExplanationPanel`, `IbkrSubmissionGrids`, `PortefeuilleRealtimeSection`, `SubmissionLifecycleDrawer`, `VolglijstColdStartFlow` |
| Server (props-only) | **2** | `PositionPlTraceDetails`, `ValuationTraceDetails` |

The two server components are pure prop-driven `<details>`-based audit/trace renderers — no state, no fetching, no `apiClient` import.

## B. `apiClient` mutation call sites (aggregate)

Read calls are listed per-component above. Mutations across this cluster:

| Mutation method | Call site | Transition |
|---|---|---|
| `apiClient.patchActionDraft` | `ActionDraftEditForm.tsx:65` | `proposed → edited` (or self) |
| `apiClient.approveActionDraft` | `ActionDraftGrid.tsx:154` | `proposed | edited → user_approved` |
| `apiClient.dismissActionDraft` | `ActionDraftGrid.tsx:169` | `proposed | edited → dismissed` |
| `apiClient.deleteActionDraft` | `ActionDraftGrid.tsx:188` | `proposed | edited → deleted` |
| `apiClient.createActionDraft` | `DecisionPackageDetail.tsx:91-93` | DP → `action_draft(proposed)` |
| `apiClient.cancelSubmittedActionDraft` | `IbkrSubmissionGrids.tsx:186` | `submitted | accepted | working | partially_filled → pending_cancellation` |
| `apiClient.deleteColdStartWatchlistItem` | `VolglijstColdStartFlow.tsx:58-60` | starter item → archived |
| `apiClient.confirmWatchlist` | `VolglijstColdStartFlow.tsx:74` | watchlist `unconfirmed → confirmed` |

## C. State-machine transitions initiated from the frontend

### `action_draft.status` (from this cluster)

- `proposed → edited` — `ActionDraftEditForm.tsx:65`.
- `proposed | edited → user_approved` — `ActionDraftGrid.tsx:154`.
- `proposed | edited → dismissed` — `ActionDraftGrid.tsx:169`.
- `proposed | edited → deleted` — `ActionDraftGrid.tsx:188`.
- `submitted | accepted | working | partially_filled → pending_cancellation` — `IbkrSubmissionGrids.tsx:186`.

### Decision-package side

The frontend never mutates a DP itself. The only DP-adjacent action is **fan-out to a new action_draft** via `createActionDraft({ decision_package_id })` at `DecisionPackageDetail.tsx:91-93`.

### `ibkr_submission` side

No direct mutations — the cluster only triggers `pending_cancellation` through the action_draft state machine. Per the docstring at `IbkrSubmissionGrids.tsx:12-15`, the worker then translates that into `ib.cancelOrder` (note: that wiring is documented in `docs/reality/components/worker-actions-and-reconciliation.md` §6 as **declared but not yet implemented** in production). All `ibkr_submission` lifecycle events are **observed read-only** in `SubmissionLifecycleDrawer.tsx:88-90`.

### Watchlist confirmation (adjacent state machine)

- `cold_start_watchlist_item.active → archived` — `VolglijstColdStartFlow.tsx:58`.
- `watchlist.confirmation_state: unconfirmed → confirmed` — `VolglijstColdStartFlow.tsx:74`.

## D. Decimal-as-string boundary audit

**No `parseFloat` was found in any of the 11 components — good.** However, the following `Number(...)` call sites operate on Decimal-as-string fields and are **potential display-rounding sites** (the wire format is preserved on the way back to the API, but the rendered value may round):

| Site | Field(s) converted | Risk |
|---|---|---|
| `ActionDraftEditForm.tsx:33` | `quantity` | **low** — validation only, not rendered |
| `ActionDraftEditForm.tsx:34` | `limitPrice` | **low** — validation only |
| `ActionDraftGrid.tsx:31` (`fmtDecimal`) | `quantity`, `limit_price_local`, `notional_eur` | display rounding via `toLocaleString` — **flag** |
| `DecisionPackageDetail.tsx:56` (`fmtEUR`) | `p10/p50/p90_price_eur`, `current_price_eur` | `Number().toFixed(2)` — **flag** |
| `DecisionPackageDetail.tsx:60` (`fmtPct`) | `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized` | `Number(v) * 100` — **flag** |
| `ForecastExplanationPanel.tsx:40` (`pct`) | `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized` | `Number(v) * 100` — **flag** |
| `ForecastExplanationPanel.tsx:239` | `per_asset_coverage.hit_rate_within_band` | `Number().toFixed(0)` — **flag** |
| `IbkrSubmissionGrids.tsx:74` (`fmtDecimal`) | `quantity`, `limit_price_local`, `notional_eur` | display rounding — **flag** |
| `SubmissionLifecycleDrawer.tsx:57` (`fmtDecimal`) | `event.fill_quantity`, `event.fill_price_local`, `event.commission` | display rounding — **flag** |

**Exemplary preservation:** `PortefeuilleRealtimeSection.tsx:36-39` (`formatNumber`) renders Decimal-as-string verbatim and is explicitly documented as such in the file docstring (`:18-19`). `PositionPlTraceDetails.tsx`, `ValuationTraceDetails.tsx`, `ActionDraftEditForm.tsx` (in PATCH payload echo), and `ForecastExplanationPanel.tsx` (for prices like `p10_price_local`, `p90_price_eur`, `p50_log_return`) also pass strings through untouched.

**Pattern observation:** every `Number(...)` site is gated by `Number.isNaN(...)` check (e.g. `ActionDraftGrid.tsx:32`, `IbkrSubmissionGrids.tsx:75`, `SubmissionLifecycleDrawer.tsx:58`, `ForecastExplanationPanel.tsx:41`) that returns the raw string on NaN — partial defence, but the float conversion still happens for valid numerics. **Risk is bounded to display formatting (locale grouping, percentage scaling, EUR rounding); the wire-format payload to API mutations remains the raw string in every observed mutation** (e.g. `ActionDraftEditForm.tsx:52-59`).

## E. Cross-cutting observations

- **Server / client split is 9 / 2.** The two server-eligible components (`PositionPlTraceDetails`, `ValuationTraceDetails`) are pure prop-driven `<details>` audit renderers — they could plausibly stay server-components if the parent pages were converted, but the parent pages all declare `"use client"`, so the SSR boundary never realises.
- **Only one component does an optimistic UI update** — `VolglijstColdStartFlow` archive (`:65-67`). Every other mutation re-fetches via parent `onChange()` or `router.push`.
- **Approval requires explicit confirmation strings.** Two flows hard-require literal Dutch tokens: `"JA"` for action-draft approval (`ActionDraftGrid.tsx:141-151`) and `"BEVESTIG"` for watchlist confirmation (`VolglijstColdStartFlow.tsx:174-177`). These are friction-by-design and match the AGENTS.md "No silent data correction" + "Every decision must be logged" guardrails.
- **Display-rounding sites are widespread but consistent.** 9 `Number(...)` sites across 6 components. The wire format stays untouched on the mutation side; the precision-loss risk is bounded to UI rendering.
- **The submitted-order cancellation path on the frontend creates `pending_cancellation`, which is currently a dead-letter state on the worker side** — see `docs/reality/components/worker-actions-and-reconciliation.md` §6 ("Worker-owned cancel pattern — declared but unused"). The frontend will produce drafts in `pending_cancellation` that no worker code path currently resolves to `cancelled`. This is a Phase 4 wiring gap.
- **No `useReducer`, no `useContext`, no global state.** Every component is local-state-only.
