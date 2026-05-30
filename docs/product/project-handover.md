- Task 152-R6 completed: repair-only merged-red CI fix after Task 152-R5 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 prerequisite gate set in tests, including dummy `ibkr_sync_host`, `ibkr_sync_port`, and `ibkr_sync_client_id` values alongside `ibkr_tws_readonly_real_client_enabled=True`. Missing host/port/client-id blockers remain tested for default/real configuration gaps, default-blocked tests still verify disabled-by-default safety-gated behavior, no-secret checks remain strict (no raw config/account payload leaks), and no production runtime behavior was widened (runtime default-disabled, readiness never connects, no sync/market-data/FX/suggestions/actions/orders/broker execution, no auto-connect/reconnect/persistent session manager, no schema/migrations, no `ib_insync`).
- Task 152-R5 completed: repair-only merged-red CI fix after Task 152-R4 for the `api` job `pytest` failures; fake-client execution helpers now enable the full Task 152 gate set including `ibkr_tws_readonly_real_client_enabled=True`, and remaining fake-client execution/error-path tests that still used `_settings(...)` were corrected to use `_fake_client_ready_settings(...)`. Default-blocked tests still prove disabled-by-default and safety-gated behavior. No production runtime widening: runtime remains disabled by default, readiness endpoint never connects, no account/portfolio sync, no positions/cash/open-orders/executions sync, no market-data runtime, no FX runtime, no suggestions/action drafts/orders/broker execution, no auto-connect/reconnect loop, no persistent session manager, no schema/migrations, no `ib_insync`, and no secret/raw broker payload exposure.
- Task 152-R4 (repair-only) completed: repaired merged-red CI after Task 152-R3 in `api` job (`pytest` failed while `ruff` and `mypy` were green) by fixing stale fake-client manual status-check test expectations introduced by stricter Task 152 gate behavior. Fake-client execution tests now enable all required gates before expecting connection/check/disconnect behavior; default-blocked tests still prove disabled-by-default behavior; and no-secret tests now reject exact raw configured values rather than safe diagnostic code names like `missing_host`. Real manual status-check capability remains. Runtime remains disabled by default; readiness endpoint still never connects; no account/portfolio sync runtime, no positions/cash/open-orders/executions sync, no market-data runtime, no FX runtime, no suggestions/action drafts/orders, no broker execution, no auto-connect/reconnect loop, no persistent session manager, no schema/migrations, no `ib_insync`, and no secrets/raw broker payload exposure.
- Task 152-R2 (repair-only) completed: repaired merged-red CI after Task 152-R in `api` job (`ruff check.`) by replacing Ruff-B009-triggering constant-attribute `getattr(...)` in `ibkr_ibapi_manual_status_client.py` with Ruff-compliant direct attribute access using narrow local Any-casts, while preserving the typed `ibapi` protocol/factory boundary and real manual status-check capability. Runtime remains disabled by default; readiness endpoint still never connects; no account/portfolio sync runtime, no positions/cash/open-orders/executions sync, no market-data runtime, no FX runtime, no suggestions/action drafts/orders, no broker execution, no auto-connect/reconnect loop, no persistent session manager, no schema/migrations, no `ib_insync`, and no secrets/raw broker payload exposure.
- Task 152-R (repair-only) completed: repaired merged-red CI after Task 152 (`api` job, `mypy src`) by isolating untyped `ibapi` usage behind typed protocol/factory boundary in manual status client. Real manual status-check remains; runtime disabled by default; readiness endpoint still never connects; no sync/market-data/FX/suggestions/orders/broker execution expansion; no schema changes; no `ib_insync`.
- Task 151: dependency-isolated `ibapi` façade toegevoegd (preflight-only, geen connectiviteit/wiring/runtimeuitbreiding).
- Task 150-R completed: merged-red repair na Task 150 voor API `pytest` failure in `test_repository_does_not_introduce_ib_insync`; preflightscan vernauwd naar projectmetadata + productie-runtime broncode i.p.v. alle repository-testbestanden, zodat bestaande safety-assertions met `ib_insync` in tests (zoals `packages/storage/tests/test_alembic_skeleton.py`) geen vals-positieve dependencyintroductie meer triggeren. `ibapi` blijft dependency/install-import preflight-only, geen productie-runtime import van `ibapi`, geen `ib_insync` dependency, geen runtime-connectiviteit/sockets by default, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 150 completed: selected `ibapi` dependency toegevoegd in `apps/api/pyproject.toml` voor dependency/install/import CI preflight; import smoke test toegevoegd in `apps/api/tests/test_ibkr_client_dependency_preflight.py` met no-socket guard op import. Geen productie-runtime import van `ibapi`, geen `ib_insync`, geen runtime-connectiviteit, geen echte TWS/Gateway clientimplementatie, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggestions/action drafts/orders/broker execution, geen API/web-gedragswijziging en geen storage schema/migraties.
- Task 149 completed: IBKR client dependency-selectie compatibiliteitspreflight (documentatie/preflight-only) toegevoegd; `ibapi` en `ib_insync` vergeleken zonder runtime-connectiviteit; geen runtime/API/web/storage-schemawijzigingen en geen dependency-introductie in projectmetadata. Aanbevolen vervolg: Task 150 dependency-only CI install/import preflight met voorkeur `ibapi`.
- Task 148: documentatie/planning/decision-gate voltooid met expliciete dependency-keuzegate vóór enige echte TWS/Gateway client dependency. Vergelijking vastgelegd voor `ibapi`, `ib_insync`, dependency-free voortzetting en deferral. Aanbevolen vervolgstap is Task 149 preflight voor dependency-compatibiliteit zonder runtime-connectiviteit. Geen runtime/API/web/storage-schemawijzigingen en geen dependency toegevoegd.
- Task 147-R completed: product-tracking drift na Task 147 gerepareerd; `next-task.md` wijst niet langer naar afgeronde Task 147 en is nu copy-paste klaar voor Task 148; `Huidige toestand` staat op `na Task 147-R`. Repair-only documentatie/product-tracking: geen runtime code gewijzigd, geen API-gedrag gewijzigd, geen web-gedrag gewijzigd, geen storage schema/migraties, geen echte TWS/Gateway runtime, geen echte low-level IBKR client, geen `ibapi`/`ib_insync`, geen socket/netwerkverbinding by default, geen auto-connect/reconnect/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime en geen suggesties/action drafts/orders/broker execution toegevoegd.
- Task 147 completed: operator-facing readiness diagnostics toegevoegd via GET /ibkr/session/manual-readonly-status-check/readiness; endpoint doet geen connectiepoging; runtime blijft default disabled; geen echte low-level client, geen ibapi/ib_insync, geen sockets/network by default, geen auto-connect/reconnect/persistente session manager, geen sync/market-data/FX runtime, geen suggesties/action drafts/orders/broker execution, geen schema/migraties.
- Task 146-R: **completed** — repair-only na merged-red Task 146/PR #342: CI-fout in `api` job (`mypy src`) hersteld door `_run_manual_tws_readonly_status_check_endpoint(...)` te voorzien van type-annotatie `runtime_settings: Settings`. Geen endpointgedrag gewijzigd; geen runtime-connectiviteit ingeschakeld; geen echte low-level IBKR-client; geen `ibapi`/`ib_insync`; geen socket/netwerk by default; geen auto-connect/reconnect/persistente session manager; geen account/portfolio sync runtime; geen market-data/FX runtime; geen suggesties, action drafts of orders toegevoegd.
- Task 146: manual read-only TWS/Gateway status-check endpoint shell toegevoegd; gebruikt Task 145 dependency-free runtime boundary, default/no-client runtime geblokkeerd, fake clients alleen test-only, runtime default uit, geen ibapi/ib_insync/sockets/auto-connect/reconnect/persistente sessie/sync/market-data/FX/suggesties/action drafts/orders/broker execution/migraties.
- Task 144 completed: expliciete preflight-checklist toegevoegd voor toekomstige echte TWS/Gateway read-only runtime-connection enablement, inclusief harde configuratie/account-mode/lifecycle/no-secret/failure-handling/test gates. Deze taak is documentatie/preflight-only: geen runtime connectivity enabled, geen echte low-level IBKR client, geen auto-connect/reconnect loop/persistente session manager, geen account/portfolio sync runtime, geen market-data/FX runtime, geen suggesties/action drafts/orders/broker execution en geen storage schema/migraties.
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

# Project Handover — AI Trading Agent (legacy: Portfolio Outlook Manager)

- Producttrackingstatus: Task 137 is afgerond als planning/documentation-only Milestone B sliceslectie na Task 136. Geselecteerde volgende implementatietaak is Task 138: harden IBKR read-only adapter contracts + deterministic fake-adapter sync fixtures voor cash/positions/open orders/executions. Geen runtimecode, geen API/web behaviorwijziging, geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 135B-R is afgerond als repair-only follow-up na merged-red Task 135B: API Ruff E501 line-too-long failures in IBKR sync validation/testbestanden zijn hersteld met formatting-only wijzigingen; geen runtime/API/storage/migratie/scope-uitbreiding, geen market-data runtime, suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 136 is afgerond als nauwe contract-uitlijning na Task 135B-R: duurzame `/ibkr/sync/status` responses bevatten nu dezelfde Task 135B payload-validatievelden en safetyvelden als de memory/read-status route. Historische duurzame runs zonder opgeslagen payload-validatie-details blijven conservatief `not_available` (geen verzonnen validatiefouten). Geen storage schema/migraties, geen echte TWS/Gateway runtime, geen market-data runtime, geen suggesties, action drafts, orders of broker execution toegevoegd.
- Producttrackingstatus: Task 135A is afgerond als documentatie-only audit/reconciliatie na Task 134B-R2 (PR #326) en herstelde producttrackingdrift naar repository-truth op `main` (markerfix in `current-state`, Milestone B queue/backlog driftfix, auditdocument toegevoegd, handover/history/scope/next-task opnieuw uitgelijnd). Task 135B blijft de volgende implementatiestap in op basis van deze audit. Geen runtime-, API-, web-, storage-, migratie-, netwerk- of berekeningsgedrag gewijzigd; geen echte TWS/Gateway netwerkruntime, geen market-data runtime, geen suggesties, geen action drafts, geen orders en geen fake data toegevoegd.

## Purpose

Dit document zorgt dat nieuwe sessies starten vanuit repository-truth, niet chatgeheugen.

## Verplichte leesvolgorde voor elke nieuwe sessie

1. Source-of-truth productdocs:
 - `docs/product/final-solution-vision.md`
 - `docs/product/release-1-functional-workflow-blueprint.md`
 - 
 - `docs/product/locked-decisions.md`
 - `docs/product/version-1-scope-register.md`
 - `docs/product/version-1-backlog.md`
2. CI-procesregels:
 - 
3. Actuele voortgang:
 - laatste gemergede PR + CI status op main
 - open PR’s en hun CI-status
4. Volgende implementatiestap:
 - 

## Read-only readiness terminologie-startpunt

Voor consistente reviewtaal in nieuwe sessies (documentatie/review guardrails, **geen runtime-unlock**) raadpleeg vroeg:
- `docs/product/read-only-readiness-ui-contract-inventory.md`
- `docs/product/read-only-readiness-pr-checklist.md`

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
- Volgende taak: 

## Producttracking drift-preventieregel (documentation/review discipline)

Wanneer een taak als afgerond wordt vastgelegd in productdocs, moet dezelfde PR altijd expliciet controleren en zo nodig bijwerken:
- titel;
- `Huidige toestand:`-regel;
- task completion-regel;
-;
- `docs/product/version-1-scope-register.md`;
- `docs/product/version-1-backlog.md`;
-.

Aanvullend:
- `next-task.md` mag geen nieuwe drift-only taak plannen tenzij er echte trackingdrift te herstellen is.
- Als de enige noodzakelijke fix een tasknummercorrectie in `current-state.md` is, moet die correctie in dezelfde PR worden meegebundeld en niet als losse volgende taak worden gepland.
- Dit is een documentatie/review-discipline-regel en **geen** geautomatiseerde CI-regel.

## Task 128 workflowpivot
- Gebruik voortaan en voor kortere milestone-gerichte opdrachten.
- Red/green CI discipline volgt.
- Geen auto-merge; human review en manual merge blijven verplicht.

## Task 130P workflow rule (nieuw)
- Task 130P is afgerond als process/documentation-only workflowupdate.
- Geen handmatige owner-testing voor partial, unfinished slices; handmatige testing pas bij volledige Version 1 release candidate.
- Partial features moeten via CI + fake adapters/fixtures/contracttests worden afgedekt.
- Toekomstige taken moeten waar veilig milestone-batches gebruiken binnen strikte safety boundaries.
- Eerdere kleine Task 131-route is vervangen door Task 131B in (tenzij latere inspectie een nog veiligere batch oplevert).

## Task 130Q handover update
- Owner workshop productrichting is nu vergrendeld in (mission-control dashboard, daily operating model, Action Center, Research Desk, structured order drafts, evidence-gated engine).
- Tracking marker drift in is met Task 130Q-R verder gecorrigeerd naar **na Task 130Q-R**.
- Task 131B is afgerond en Task 131B-R heeft de merged-red API statusregressie gerepareerd; volgende implementatierichting is Task 133B (tenzij latere inspectie een veiligere batch oplevert).

- Nieuw in Task 139: status-only inspectie van recente IBKR syncruns via `/ibkr/sync/runs` en detail via `/ibkr/sync/runs/{sync_run_id}`. In-memory history, geen real-runtime toevoegingen.

- Task 145 afgerond: handmatige dependency-free TWS/Gateway read-only runtime status-check boundary toegevoegd (test-only injected fake clients), runtime default uit, geen echte connectivity/broker execution.

- Nieuwe verplichte lockbron: `docs/product/version-1-product-experience-locks.md` (lees vóór user-facing productwerk).
- Producttrackingstatus bijgewerkt: Task 153-L completed; volgende implementatie is Task 155.
