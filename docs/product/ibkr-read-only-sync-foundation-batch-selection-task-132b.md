# Task 132B — Selectie volgende IBKR read-only sync foundation batch (na Task 131B/131B-R)

## 1) Purpose en boundary

Task 132B is **documentation/planning-only**.

Deze taak selecteert exact één veilige volgende Milestone B implementatiebatch na de account/session-status safetyreeks (Task 130 → 131B → 131B-R), zonder runtime-unlock.

Niet toegevoegd in Task 132B:
- geen runtimegedrag;
- geen API runtimebehavior changes;
- geen storage runtime changes;
- geen migraties;
- geen echte TWS/Gateway network runtime;
- geen account/portfolio sync runtime;
- geen market-data runtime;
- geen FX runtime;
- geen suggesties;
- geen action drafts;
- geen Decision Packages runtime;
- geen orders (submit/modify/cancel/bind);
- geen broker execution;
- geen financiële berekeningen;
- geen fake brokerdata, fake portfoliodata, fake marktdata of andere fake data.

## 2) Huidige foundation-inventaris

### Task 122 — TWS/Gateway preflight en richting
- Technische preflight en integratierichting vastgelegd.
- Read-only sessiestatuscontract als veilige basis, disabled-by-default.

### Task 129 — Milestone B slice-selectiegeschiedenis
- Document-first selectieproces voor de eerste veilige Milestone B implementatieslice.
- Leidde naar Task 130 als status/sessie-boundary stap.

### Task 130 — Session-status boundary
- Disabled-by-default, non-network IBKR session-status adapter boundary.
- API status exposure toegevoegd zonder echte netwerkconnectie.

### Task 131B — Account/session safety mapping
- Veilige mapping van account/session status, inclusief `connection_failed`, `authentication_required`, `pacing_limited`.
- Unknown-status wording en account-mode match/mismatch gedrag verankerd.
- Fake-adapter testdekking toegevoegd.

### Task 131B-R — mismatch-repair
- Regressieherstel voor wrong-account-mode pad zodat `account_mode_status` niet onterecht naar `unknown` terugvalt.

### Bestaande sync- en storage-foundation
- Duurzame IBKR sync snapshot storage bestaat voor:
  - sync runs,
  - cash,
  - posities,
  - open orders,
  - executions.
- Manual sync functie bestaat met fake/injected adapter capability en memory fallback.
- Read-only endpoints bestaan voor syncstatus en latest snapshots (positions/cash/open orders/executions).

### Bestaande gaten (samengevat)
- Geen echte TWS/Gateway netwerkadapter runtime.
- Geen persistente worker-managed IBKR session manager.
- Geen echte account/portfolio sync runtime.

## 3) Huidige gaps

1. Geen real TWS/Gateway network runtime.
2. Geen persistente worker-managed IBKR session manager.
3. Geen real account/portfolio sync runtime.
4. Geen expliciete sync readiness/preflight gate die direct leunt op de Task 131B account/session-status outputs.
5. Bestaand manual sync pad mag geen real-IBKR-beschikbaarheid impliceren.
6. Bestaande sync statusweergave kan explicietere veilige readiness/gating wording gebruiken vóór netwerk-runtime.
7. Geen market-data runtime.
8. Geen suggesties, geen action drafts en geen orders.

## 4) Kandidaat-batches vergeleken

### Candidate A — IBKR read-only sync readiness/preflight gate
- Doel: veilige gate die beslist of handmatige read-only sync toegestaan is op basis van settings + read-only mode + storage readiness + Task 131B account/session outputs.
- Blijft zonder real network runtime.
- Blijft zonder real account/portfolio sync runtime.
- Verduidelijkt statusuitkomsten zoals `Geblokkeerd`, `Controle nodig`, `Klaar voor handmatige read-only sync`.
- Fake-adapter tests kunnen in implementatietaak worden toegevoegd.
- Veiligheidsrisico: laag.

### Candidate B — Read-only sync adapter contract hardening
- Doel: fake-adapter-only contract voor cash/positions/open orders/executions verder verharden.
- Blijft zonder real network.
- Risico: kan groter worden door contract/read-model/storage-impact.

### Candidate C — Durable sync read-model completeness review
- Doel: read model/contract van reeds opgeslagen snapshots verbeteren.
- Blijft zonder runtime sync.
- Risico: nuttig, maar minder direct gekoppeld aan Task 131B statusoutputs.

### Candidate D — Real TWS/Gateway network adapter skeleton
- Voor nu afgewezen.
- Reden: te vroeg; readiness/gating moet eerst expliciet en stabiel zijn.

### Candidate E — Market-data runtime
- Afgewezen.
- Reden: buiten de eerstvolgende Milestone B stap en expliciet geblokkeerd.

### Candidate F — Action draft/order integration
- Afgewezen.
- Reden: expliciet buiten scope.

## 5) Selectie

**Geselecteerd: Candidate A — IBKR read-only sync readiness/preflight gate op basis van Task 131B account/session status outputs.**

### Geselecteerde volgende implementatietaak

**Task 133B — Implementeer IBKR read-only sync readiness/preflight gate met Task 131B account/session status outputs, zonder real TWS/Gateway network runtime, zonder account/portfolio sync runtime, zonder market-data runtime, zonder suggesties, zonder action drafts en zonder orders.**

Motivatie:
- Directe voortzetting van de 131B/131B-R veiligheidslijn.
- Kleinste veilige stap die verkeerde runtime-implicaties voorkomt.
- Verlaagt risico vóór start van echte netwerkadapter- of sync-runtimewerkzaamheden.

## 6) Acceptance criteria voor Task 133B

Task 133B is pas klaar als minimaal dit aantoonbaar is:
- geen real network calls;
- geen auto-connect;
- geen real IBKR sync runtime;
- geen fake brokerdata/fake portfoliodata/fake marktdata;
- geen market data runtime;
- geen suggesties/action drafts/orders;
- order/action booleans blijven `false`;
- sync readiness hangt af van settings + read-only mode + account/session status + storage readiness (waar relevant);
- duidelijke Nederlandse statuses en helptekst (incl. `Geblokkeerd` / `Controle nodig` / `Klaar voor handmatige read-only sync`);
- fake-adapter/fixture testdekking;
- product tracking docs bijgewerkt;
- CI groen op alle zes jobs: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.

## 7) Non-goals voor Task 133B

- geen real TWS/Gateway adapter;
- geen real IBKR session manager;
- geen account/portfolio sync runtime;
- geen market-data runtime;
- geen FX runtime;
- geen suggesties;
- geen action drafts;
- geen Decision Packages runtime;
- geen order submit/modify/cancel/bind;
- geen broker execution;
- geen fake broker/portfolio/market data.

## 8) Risk notes

- Een expliciete sync readiness/preflight gate moet vóór real network sync komen om foutieve indrukken over operationele gereedheid te voorkomen.
- Real network runtime moet wachten tot readiness gates + CI stabiliteit bewezen zijn, zodat safety regressies eerder worden afgevangen.
- Handmatige owner IBKR testing blijft release-candidate-only volgens de geldende policy; partial slices worden via CI/fake adapters/fixtures/contracttests afgedekt.
