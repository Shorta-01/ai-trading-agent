- Task 143 completed: read-only IBKR session-status diagnostics uitgebreid met expliciete adapter-readiness en blocked runtime reason-codes; default blijft veilige non-network adapter en orders/suggesties/actions blijven geblokkeerd.
- Task 142 completed: disabled-by-default TWS/Gateway adapter factory wired behind explicit setting with safe diagnostics; default remains non-network safe adapter and all order/suggestion/action booleans blocked.
## Task 141
- Completed: milestone-sized Milestone B adapter-boundary slice met disabled-by-default TWS/Gateway read-only session-status adapter skeleton op injected-client protocol boundary.
- Bevestigd: geen runtime connectivity by default, geen auto-connect/reconnect loop, geen persistente session manager, geen account/portfolio sync runtime, geen market-data of FX runtime, geen suggesties/action drafts/orders/broker execution, geen secrets/raw broker payload exposure en geen storage schema/migraties.

## Task 140-R
- Afgerond: repair-only fix voor merged-red Task 140 (`api` job, stap `mypy src`).
- Oorzaak: reconciliation readiness las niet-bestaande payload-validatie-attributen op `IbkrSyncRunRecord`.
- Herstel: duurzame syncruns gebruiken conservatieve payload-validatie fallback wanneer validatiemetadata niet is opgeslagen; geen historische validatiedetails verzonnen.
- Niet toegevoegd: geen storage schema/migraties, geen echte TWS/Gateway runtime, geen persistente session manager, geen market-data runtime, geen FX runtime, geen suggesties/action drafts/orders/broker execution.

## Task 140
- Completed: read-only reconciliation readiness endpoint toegevoegd (`GET /portfolio/valuation/reconciliation-readiness`) die bestaande waarderingblockers samenvat zonder waarden te verzinnen en met alle order/suggestie/action safetybooleans geblokkeerd. Geen TWS/Gateway runtime, geen session manager, geen schema/migraties, geen market-data/FX runtime, geen suggesties/action drafts/orders/execution.

## Task 138-R handover update
- Afgerond: merged-red repair na Task 138 voor API pytest failures in adapter timeout/provider-foutpaden.
- Bevestigd: timeout/provider adapterfouten rapporteren `payload_validation_status=not_attempted` (niet `passed`) met Nederlandse helptekst dat validatie niet uitgevoerd werd.
- Bevestigd: adapter/runtimefouten blijven gescheiden van payloadvalidatiefouten; geen fake validatie-errors toegevoegd.
- Niet toegevoegd: echte TWS/Gateway runtime, persistente sessiemanager, storage schema/migraties, market-data runtime, suggesties/action drafts/orders/broker execution.

## Task 138 handover update
- Afgerond: contract-hardening voor IBKR read-only sync payloadfamilies (cash/positions/open orders/executions) met deterministische test-only fixtures en expliciete foutclassificatie in tests tussen payloadvalidatie en adapter/runtimefouten.
- Bevestigd: readiness-blocking pad roept adapter niet aan; payloadvalidatiefouten blokkeren memory/durable persistence; timeout/provider-fouten worden niet als payloadvalidatiefout gelabeld.
- Niet toegevoegd: echte TWS/Gateway runtime, persistente sessiemanager, storage schema/migraties, market-data runtime, suggesties/action drafts/orders/broker execution.

# Project Handover — Portfolio Outlook Manager / Ai Trading Agent

- Producttrackingstatus: Task 137 is afgerond als planning/documentation-only Milestone B sliceslectie na Task 136. Geselecteerde volgende implementatietaak is Task 138: harden IBKR read-only adapter contracts + deterministic fake-adapter sync fixtures voor cash/positions/open orders/executions. Geen runtimecode, geen API/web behaviorwijziging, geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 135B-R is afgerond als repair-only follow-up na merged-red Task 135B: API Ruff E501 line-too-long failures in IBKR sync validation/testbestanden zijn hersteld met formatting-only wijzigingen; geen runtime/API/storage/migratie/scope-uitbreiding, geen market-data runtime, suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 136 is afgerond als nauwe contract-uitlijning na Task 135B-R: duurzame `/ibkr/sync/status` responses bevatten nu dezelfde Task 135B payload-validatievelden en safetyvelden als de memory/read-status route. Historische duurzame runs zonder opgeslagen payload-validatie-details blijven conservatief `not_available` (geen verzonnen validatiefouten). Geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 135A is afgerond als documentatie-only audit/reconciliatie na Task 134B-R2 (PR #326) en herstelde producttrackingdrift naar repository-truth op `main` (markerfix in `current-state`, Milestone B queue/backlog driftfix, auditdocument toegevoegd, handover/history/scope/next-task opnieuw uitgelijnd). Task 135B blijft de volgende implementatiestap in `docs/product/next-task.md` op basis van deze audit. Geen runtime-, API-, web-, storage-, migratie-, netwerk- of berekeningsgedrag gewijzigd; geen echte TWS/Gateway netwerkruntime, geen market-data runtime, geen suggesties, geen action drafts, geen orders en geen fake data toegevoegd.

## Purpose

Dit document zorgt dat nieuwe sessies starten vanuit repository-truth, niet chatgeheugen.

## Verplichte leesvolgorde voor elke nieuwe sessie

1. Source-of-truth productdocs:
   - `docs/product/final-solution-vision.md`
   - `docs/product/release-1-functional-workflow-blueprint.md`
   - `docs/product/current-state.md`
   - `docs/product/locked-decisions.md`
   - `docs/product/version-1-scope-register.md`
   - `docs/product/version-1-backlog.md`
2. CI-procesregels:
   - `docs/product/codex-ci-quality-rules.md`
3. Actuele voortgang:
   - laatste gemergede PR + CI status op main
   - open PR’s en hun CI-status
4. Volgende implementatiestap:
   - `docs/product/next-task.md`


## Read-only readiness terminologie-startpunt

Voor consistente reviewtaal in nieuwe sessies (documentatie/review guardrails, **geen runtime-unlock**) raadpleeg vroeg:
- `docs/product/read-only-readiness-ui-contract-inventory.md`
- `docs/product/read-only-readiness-pr-checklist.md`
- `docs/product/read-only-readiness-product-doc-terminology-audit.md`

## Kerncontext

- Producttrackingstatus: Task 128 (PR #308) is merged als workflowprocespivot; Task 125W is bewust gedeferreerd/vervangen. Producttrackingdocs moeten dit expliciet reflecteren en `next-task.md` moet nu op Task 130 staan als volgende taak (Task 129 is afgerond als planning-only selectie).

- Productnaam: Portfolio Outlook Manager.
- Repositorynaam: Ai Trading Agent.
- Version 1 ondersteunt paper en real-money accountmodus als zichtbare veiligheidscontext; productidentiteit blijft account-mode-aware en user-approved.
- Geen live trading, geen brokeractie zonder expliciete usergoedkeuring, geen automatische orders.
- AI is uitleg/evidence-interpretatie; Python/modelcode berekent.

## Navigatie

- Eindvisie: `docs/product/final-solution-vision.md`
- Release 1 workflow blueprint: `docs/product/release-1-functional-workflow-blueprint.md`
- Resterend werk: `docs/product/version-1-backlog.md`
- Volgende taak: `docs/product/next-task.md`


## Producttracking drift-preventieregel (documentation/review discipline)

Wanneer een taak als afgerond wordt vastgelegd in productdocs, moet dezelfde PR altijd expliciet controleren en zo nodig bijwerken:
- `docs/product/current-state.md` titel;
- `Huidige toestand:`-regel in `docs/product/current-state.md`;
- task completion-regel in `docs/product/current-state.md`;
- `docs/product/task-history.md`;
- `docs/product/version-1-scope-register.md`;
- `docs/product/version-1-backlog.md`;
- `docs/product/next-task.md`.

Aanvullend:
- `next-task.md` mag geen nieuwe drift-only taak plannen tenzij er echte trackingdrift te herstellen is.
- Als de enige noodzakelijke fix een tasknummercorrectie in `current-state.md` is, moet die correctie in dezelfde PR worden meegebundeld en niet als losse volgende taak worden gepland.
- Dit is een documentatie/review-discipline-regel en **geen** geautomatiseerde CI-regel.

- Verplicht lezen: docs/product/action-draft-prediction-diary-alerts-decision-locks-task-127.md


## Task 128 workflowpivot
- Gebruik voortaan `docs/product/codex-task-template.md` en `docs/product/task-queue.md` voor kortere milestone-gerichte opdrachten.
- Red/green CI discipline volgt `docs/product/codex-red-green-ci-workflow.md`.
- Geen auto-merge; human review en manual merge blijven verplicht.

## Task 130P workflow rule (nieuw)
- Task 130P is afgerond als process/documentation-only workflowupdate.
- Geen handmatige owner-testing voor partial, unfinished slices; handmatige testing pas bij volledige Version 1 release candidate.
- Partial features moeten via CI + fake adapters/fixtures/contracttests worden afgedekt.
- Toekomstige taken moeten waar veilig milestone-batches gebruiken binnen strikte safety boundaries.
- Eerdere kleine Task 131-route is vervangen door Task 131B in `docs/product/next-task.md` (tenzij latere inspectie een nog veiligere batch oplevert).


## Task 130Q handover update
- Owner workshop productrichting is nu vergrendeld in `docs/product/version-1-owner-workshop-decision-locks-task-130q.md` (mission-control dashboard, daily operating model, Action Center, Research Desk, structured order drafts, evidence-gated engine).
- Tracking marker drift in `docs/product/current-state.md` is met Task 130Q-R verder gecorrigeerd naar **na Task 130Q-R**.
- Task 131B is afgerond en Task 131B-R heeft de merged-red API statusregressie gerepareerd; volgende implementatierichting is Task 133B (tenzij latere inspectie een veiligere batch oplevert).

- Nieuw in Task 139: status-only inspectie van recente IBKR syncruns via `/ibkr/sync/runs` en detail via `/ibkr/sync/runs/{sync_run_id}`. In-memory history, geen real-runtime toevoegingen.
