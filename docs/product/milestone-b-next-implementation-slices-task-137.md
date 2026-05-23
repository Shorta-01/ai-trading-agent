# Task 137 — Milestone B next implementation slices selection (planning-only)

## 1) Verified repository and CI state after Task 136
- Latest merged task in producttracking: **Task 136** (durable/memory IBKR sync status contract alignment).
- Current state marker: repository currently tracks **na Task 136** before this planning update.
- Working tree at start of this task was clean (`git status --short` had no changes).
- Current branch at start: `work`.
- `git fetch origin` kon in deze container niet worden uitgevoerd omdat `origin` niet is geconfigureerd; daardoor is remote-verificatie hier niet lokaal herhaalbaar.
- Planningbesluit blijft daarom gebaseerd op repository source-of-truth docs en lokaal zichtbare task-trackingstatus.

## 2) Completed Milestone B foundations relevant for next slice
- Disabled-by-default IBKR session/status boundary staat al.
- Account/session safety mapping en account-mode mismatch handling staan al.
- Readiness/preflight gate voor handmatige read-only sync staat al.
- Manual sync execution blocking op readiness staat al.
- Payload-validatie vóór persistence staat al.
- Durable + memory sync status contract-uitlijning is afgerond in Task 136.
- Storage foundations voor sync runs, cash, positions, open orders en executions bestaan al.

Conclusie: de fundering is sterk genoeg voor een **grotere maar nog veilige read-only contractverhardingstaak** zonder echte netwerk-runtime.

## 3) Remaining Milestone B gaps
- Geen echte TWS/Gateway read-only netwerkadapter runtime.
- Geen persistent worker-managed IBKR session manager.
- Geen echte runtime synchronisatie met live TWS/Gateway sessiecontext.
- Adapter contractgrenzen en foutcategorieën kunnen nog harder en explicieter.
- Reconciliation/readiness tussen geïmporteerde snapshots en portfolio/readiness views is nog beperkt.
- Operationele diagnostiek kan later verder worden verdiept.

## 4) Candidate slice comparison

### Candidate A — Read-only adapter contract hardening + fake fixtures
**Scopekern**
- Verharding van read-only adaptercontracten voor cash, positions, open orders, executions.
- Deterministische fake fixtures en striktere protocoltests.
- Duidelijke foutclassificatie tussen adapterfouten en payloadvalidatiefouten.

**Voordelen**
- Lage veiligheidsrisico’s.
- Hoge testbaarheid via fake adapters/fixtures.
- Sterke voorbereiding op latere echte netwerkadapter zonder runtime unlock.

**Nadelen**
- Levert nog geen echte netwerkfunctionaliteit.

**Risico**: **Laag**.

### Candidate B — Sync run history en diagnostics verdieping
**Scopekern**
- Betere inspecteerbaarheid van sync runs en validatiesamenvattingen.

**Voordelen**
- Operationeel nuttig.

**Nadelen**
- Risico op API-/weergaveverbreding zonder eerst contractbasis verder te verankeren.

**Risico**: **Laag tot middel**.

### Candidate C — Reconciliation readiness batch
**Scopekern**
- Readinessvergelijking tussen snapshots en interne portfolio/readinessverwachtingen.

**Voordelen**
- Relevante stap richting operationele bruikbaarheid.

**Nadelen**
- Raakt sneller waarderings-/readinesslogica en vergroot regressierisico.

**Risico**: **Middel**.

### Candidate D — Real TWS/Gateway network adapter skeleton
**Risico**: **Middel-hoog tot hoog**; te vroeg zonder extra contractverharding.

### Candidate E — Persistent worker-managed session manager
**Risico**: **Hoog**; afhankelijk van stabiele adaptercontracten en runtimeboundary.

### Candidate F — Market-data/FX runtime
**Risico**: buiten directe Milestone B-read-only kern; **nu niet selecteren**.

## 5) Selected next implementation task

## **Task 138 — Harden IBKR read-only adapter contracts and fake-adapter sync fixtures for cash, positions, open orders and executions.**

Waarom deze keuze:
- Milestone-sized batch (meerdere contract- en testonderdelen in één veilige stap).
- Blijft read-only en fake-adapter-testbaar.
- Verlaagt risico vóór echte TWS/Gateway runtime.
- Past bij green-CI-first discipline en anti-micro-fragmentatie wens.

## 6) Proposed next 3–5 likely Milestone B slices after Task 138
1. **Task 139 (likely):** Read-only sync run history/diagnostics verdieping (statussamenvatting + validatie-inzicht, zonder runtime connectie).
2. **Task 140 (likely):** Read-only reconciliation readiness batch tussen opgeslagen IBKR snapshots en portfolio/readiness blokkades (status-only).
3. **Task 141 (likely):** Real TWS/Gateway read-only network adapter skeleton achter disabled-by-default boundary, zonder orderflow.
4. **Task 142 (likely):** Persistent worker-managed IBKR session manager (read-only sessie lifecycle, nog steeds zonder orderruntime).
5. **Task 143 (optional/conditional):** Account-mode verificatie tegen echte sessiecontext + operationele polish.

Volgordevoorwaarde: elke volgende slice pas starten na groen CI op `main` en na contractbevestiging van de voorgaande slice.

## 7) Acceptance criteria for selected Task 138
- Striktere adapter contracttests bestaan voor cash/positions/open orders/executions.
- Fake adapter fixtures zijn deterministisch en herbruikbaar.
- Foutcategorieën adapterfout vs payloadvalidatiefout zijn expliciet en testbaar.
- Geen echte TWS/Gateway netwerkcalls toegevoegd.
- Geen storage schema/migraties.
- Geen API/web gedragverbreding buiten contractveiligheid.
- Alle zes CI-jobs blijven groen.

## 8) Non-goals and safety boundaries
Task 138 mag **niet** doen:
- real TWS/Gateway runtime toevoegen;
- persistent session manager bouwen;
- market-data of FX runtime toevoegen;
- suggesties/action drafts/orders/broker execution toevoegen;
- live trading of real-money automation toevoegen;
- scope unlock naar opties/futures/leverage/short/crypto/CFD/penny stocks/complexe derivaten.

Version 1 blijft paper-only en read-only binnen Milestone B.

## 9) CI/test strategy for selected Task 138
- Minimaal package checks voor domeinen die contracten/fake fixtures raken.
- Verplichte lokale gates: lint/type/tests voor impacted packages.
- Producttracking checker + project status mee uitvoeren.
- PR alleen mergebaar na groen van alle zes vereiste CI-jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).

## 10) Why this is milestone-sized yet safe
Task 138 bundelt meerdere samenhangende contractverhardingen (niet één microfix), maar blijft:
- runtime-neutraal qua echte brokerconnectie,
- storage-neutraal qua schema,
- productveilig qua read-only/paper-only boundaries,
- CI-eerst met sterke fake-adapter testbaarheid.

Daarmee is dit een betekenisvolle milestone-slice zonder premature runtime-risico’s.
