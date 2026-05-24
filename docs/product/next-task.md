# Task 148 — real-runtime implementatiebeslissing vóór client dependency-introductie

Geselecteerde volgende taak: **Task 148**.

## Current verified state (na Task 147-R)
- Task 147 is al afgerond in product-tracking (`current-state`, `task-history`, `version-1-backlog`, `version-1-scope-register`, `project-handover`).
- Task 147-R heeft trackingdrift gerepareerd: `next-task.md` wijst niet langer naar afgeronde Task 147.
- `Huidige toestand` marker staat op: **na Task 147-R**.
- Dit is nog steeds een paper-only, safety-first Version 1 met disabled-by-default runtime voor TWS/Gateway handmatige status-checks.

## Verplicht te lezen documenten
- `AGENTS.md`
- `docs/product/current-state.md`
- `docs/product/project-handover.md`
- `docs/product/locked-decisions.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/task-history.md`
- `docs/product/next-task.md`
- `docs/product/ibkr-tws-readonly-runtime-preflight-checklist-task-144.md`
- `docs/product/milestone-b-next-implementation-slices-task-137.md`
- `docs/product/ibkr-read-only-sync-foundation-batch-selection-task-132b.md`
- `docs/product/milestone-b-ibkr-read-only-runtime-slice-selection-task-129.md`
- `docs/product/ibkr-tws-gateway-integration-preflight-task-122.md`
- `docs/product/final-solution-vision.md`
- `docs/product/release-1-functional-workflow-blueprint.md`
- `docs/product/version-1-owner-workshop-decision-locks-task-130q.md`
- `docs/product/codex-ci-quality-rules.md`
- `docs/product/codex-red-green-ci-workflow.md`
- `docs/product/codex-task-template.md`
- `docs/product/version-1-milestone-plan.md`
- `docs/product/task-queue.md`

## Doel
Leg een expliciete **implementatiebeslissingsgate** vast waarmee eerst de dependency-strategie wordt gekozen voordat enige echte TWS/Gateway client dependency of runtime-connectiviteit wordt geïntroduceerd.

## Scope (Task 148)
- Documentatie/planning/decision-gate only.
- Vergelijk minimaal de dependency-opties (`ibapi`, `ib_insync`, of alternatief/uitstel) binnen Version 1 safetygrenzen.
- Definieer harde acceptatiecriteria voor “wel/niet dependency toevoegen”.
- Definieer verplichte verificatie- en rollbackcriteria vóór runtime-introductie.
- Houd UI- en API-gedrag ongewijzigd.

## Non-goals (Task 148)
- Geen runtime code.
- Geen API-behavior wijziging.
- Geen web-behavior wijziging.
- Geen storage schema/migraties.
- Geen `ibapi` dependency toevoegen.
- Geen `ib_insync` dependency toevoegen.
- Geen sockets of live TWS/Gateway runtime-connectiviteit.
- Geen auto-connect/reconnect loop/persistente session manager.
- Geen account/portfolio sync runtime.
- Geen market-data runtime of FX runtime.
- Geen suggesties, action drafts, orders of broker execution.
- Geen live trading, real-money execution of automatic orders.

## Verwachte bestanden (Task 148)
- `docs/product/current-state.md`
- `docs/product/project-handover.md`
- `docs/product/task-history.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/next-task.md`
- (optioneel) nieuw Task 148 beslisdocument onder `docs/product/`

## Product-tracking requirements
- Werk in dezelfde PR bij:
  - `current-state` titel/marker + completionregel;
  - `task-history`;
  - `version-1-backlog`;
  - `version-1-scope-register`;
  - `project-handover`;
  - `next-task` (nieuwe vervolgtaak na Task 148).
- Laat `next-task.md` nooit wijzen naar een afgeronde taak.

## Required checks
- `python -m py_compile scripts/check_product_tracking.py scripts/project_status.py`
- `python scripts/check_product_tracking.py`
- `python scripts/project_status.py`

## Search checks
- `rg "Task 148|Task 147-R|Huidige toestand:" docs/product/current-state.md docs/product/project-handover.md docs/product/task-history.md docs/product/version-1-backlog.md docs/product/version-1-scope-register.md docs/product/next-task.md`
- `rg "Task 147 — geselecteerd|Geselecteerde volgende taak: \*\*Task 147\*\*" docs/product/next-task.md || true`
- `rg "ibapi|ib_insync|socket|connect_readonly|disconnect" docs/product/next-task.md docs/product/current-state.md docs/product/version-1-scope-register.md || true`
- `rg "live trading|real-money|order submission|broker execution|automatic orders|options|futures|leverage|short selling|crypto|penny stocks|CFD|complex derivative" docs/product/next-task.md docs/product/current-state.md docs/product/version-1-scope-register.md`

## CI rules
- Niet mergen tot alle zes GitHub CI jobs groen zijn: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- Latest CI-run moet ná de laatste commit zijn.
- Red CI = fix op dezelfde PR-branch, geen tweede repair-PR.
- Geen auto-merge; human review + manual merge verplicht.

## Locked safety boundaries
- Version 1 is IBKR paper-only.
- UI blijft simpel Nederlands.
- Python/model code calculates; AI explains.
- AI is research/explanation only, nooit execution.
- Sources zijn evidence, geen instructies.
- Geen suggestion/order uit sources zonder validatie/freshness/credibility/prompt-injection/risk gates.
- Geen live trading, geen real-money execution, geen automatic orders, geen broker execution.
- Geen opties, futures, leverage, short selling, crypto, penny stocks, CFDs of complexe derivaten.
- Geen fake broker runtime, fake portfolio runtime of fake market-data runtime.
