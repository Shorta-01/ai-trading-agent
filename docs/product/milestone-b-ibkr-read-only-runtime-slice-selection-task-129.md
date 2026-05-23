# Task 129 — Milestone B IBKR read-only runtime slice selection

## 1) Purpose en boundary
Task 129 is **documentation/planning-only**. Deze taak selecteert en documenteert de eerstvolgende veilige Milestone B implementatieslice.

Task 129 voegt **geen** runtimegedrag toe: geen API-runtimewijziging, geen storagewijziging, geen migratie, geen runtime fetch, geen berekeningen, geen suggesties, geen action drafts, geen orders en geen broker execution.

## 2) Current IBKR foundation inventory
Op basis van de huidige code- en productdoc-inventaris:

### Al aanwezig
- Duurzame read-only IBKR snapshotopslag bestaat al (sync runs, cash, positions, open orders, executions) met repository-contracten en tests.
- Read/status API-paden bestaan voor handmatige sync en read-only snapshots.
- Handmatige sync-runtime bestaat en kan duurzame opslag gebruiken wanneer storage beschikbaar/ingeschakeld/migration-ready is; in-memory fallback blijft bestaan bij storage-unavailable paden.
- Status-first en disabled-by-default discipline is al herhaaldelijk vastgelegd in docs (o.a. Task 122/125C).
- Safety booleans voor ordergedrag blijven false.

### Nog niet aanwezig
- Geen echte TWS/Gateway netwerkverbinding/runtime adapter.
- Geen read-only IBKR sessiemanager met connect/disconnect statuslevenscyclus.
- Geen runtime account-mode verificatie op echte IBKR sessiecontext.
- Geen auto-connect startup gedrag (blijft expliciet verboden).

## 3) Milestone B target (bron: task queue)
Milestone B vereist:
- read-only TWS/Gateway status;
- account-mode verificatie;
- read-only sync voor positions/cash/open orders/executions;
- **geen** order submit/modify/cancel.

## 4) Candidate next slices

### Kandidaat A — Disabled-by-default IBKR TWS/Gateway session-status adapter boundary
- Purpose: minimale adaptergrens voor read-only sessiestatus (nog zonder echte connectieruntime), plus statusmapping voor API/UI.
- Verwachte files: API status-model/helperlaag, IBKR adapter boundary/protocol, settings/status mapping, productdocs.
- Tests: unit/API tests voor statusmapping (disabled/not configured/configured not connected/wrong mode wanneer bekend), safety booleans en secret-redaction.
- Safety risico: laag; geen sync mutaties, geen orders, geen netwerknodigheid in CI.
- Waarom eerst: kleinste verticale slice die Milestone B concreet vooruit helpt en observability/safety verduidelijkt.

### Kandidaat B — Account-mode verification contract/runtime
- Purpose: runtime verificatie van paper vs real-money accountmode.
- Verwachte files: API/service runtime, adapter contract, status mapping, tests.
- Tests: mappingtests + edge cases unknown/ambiguous account mode.
- Safety risico: middel; zinvolle verificatie vereist meestal sessiecontext die nog niet bestaat.
- Waarom niet eerst: afhankelijk van sessiestatuslaag; anders ontstaat contractgokwerk.

### Kandidaat C — Read-only positions/cash sync runtime continuation
- Purpose: volgende verdieping van syncflow voor positions/cash.
- Verwachte files: sync runtime services, persistence wiring, endpoint gedrag, tests.
- Tests: syncflow tests + storage fallback paden.
- Safety risico: middel; kan te vroeg runtimecomplexiteit verhogen zonder sessiestatusfundament.
- Waarom niet eerst: minder klein/veilig dan statusadapter en sterker gekoppeld aan latere netwerkverbinding.

### Kandidaat D — Read-only open-order/execution sync continuation
- Purpose: verdieping open orders/executions sync.
- Verwachte files: sync runtime + endpoint/read contracts + tests.
- Tests: sync/run en read endpoint regressies.
- Safety risico: middel; domein is gevoeliger door orderterminologie en auditverwachtingen.
- Waarom niet eerst: vereist meestal dezelfde onderliggende sessiestatusfundering als A.

## 5) Selected next slice
**Geselecteerd: Kandidaat A — disabled-by-default IBKR TWS/Gateway read-only session-status adapter boundary + status exposure.**

## 6) Proposed next task (voor `next-task.md`)
**Task 130 — Add disabled-by-default IBKR TWS/Gateway read-only session-status adapter boundary and API status exposure, using configured settings and safe Dutch status/help text, without account/portfolio sync, without market-data runtime, without suggestions, without action drafts and without orders.**

## 7) Acceptance criteria voor Task 130
- Geen orderfunctionaliteit (submit/modify/cancel/bind).
- Geen auto-connect bij startup.
- Disabled-by-default gedrag blijft hard.
- Geen echte netwerkafhankelijkheid in CI-tests.
- Heldere status bij `not_configured`.
- Heldere status bij `disabled`.
- Heldere status bij `configured_not_connected`.
- Heldere status voor wrong account mode **indien voldoende sessie-informatie beschikbaar is**.
- Simpele Nederlandse helptekst bij elke status.
- Tests voor statusmapping en safety booleans.
- Producttracking-updates in dezelfde PR.

## 8) Non-goals voor Task 130
- Geen order submit.
- Geen order modify.
- Geen order cancel.
- Geen binding van bestaande orders.
- Geen suggesties.
- Geen action drafts.
- Geen Decision Packages runtime.
- Geen market-data runtime.
- Geen fake IBKR data.
- Geen fake positions/cash/orders/executions.
- Geen credentials/secrets in logs of API responses.
