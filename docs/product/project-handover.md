# Project Handover — Portfolio Outlook Manager / Ai Trading Agent

- Producttrackingstatus: Task 133B is afgerond met minimale IBKR read-only sync readiness/preflight status gate; Task 133B-R heeft daarna de ontbrekende Task 133B scope-register trackingnotitie gerepareerd en de product-tracking checker verhard; Task 134B is afgerond met execution blocking op handmatige sync; volgende stap is Task 135B in `docs/product/next-task.md`.

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
