# Version 1 Task Queue (milestone-gericht)

## Current pivot
- **Task 128 — workflow acceleration** (afgerond): procesdocumentatie + lichte hulpmiddelen om micro-taakfragmentatie te verminderen.

## Milestone A — Valuation readiness closure
- **Purpose**: waardering-readiness afronden met beperkte, waardevolle resterende tekst/contractafstemming.
- **Blocked until**: workflowregels van Task 128 actief gebruikt in nieuwe taken.
- **Non-goals**: geen runtime unlock; geen suggesties; geen orders.
- **Task size guidance**: bundel kleine documentatie- en labelwerkzaamheden waar veilig.
- **Bundling notes**:
  - veilig: UI label/helptekst cleanup + product tracking in één PR;
  - apart houden: wijzigingen die runtime contracten raken.

## Milestone B — IBKR read-only runtime
- **Purpose**: read-only TWS/Gateway status, account-mode verificatie en read-only sync (positions/cash/open orders/executions).
- **Blocked until**: readiness- en safety-guards bevestigd.
- **Non-goals**: geen ordersubmissie/wijziging/cancel.
- **Task size guidance**: grotere veilige milestone-batches binnen één read-only boundary (geen unsafe bundling).
- **Bundling notes**:
  - veilig: één read-only boundary/surface + tests + docs;
  - apart houden: broker-order flows.
- **Testing policy**:
  - partial IBKR slices worden getest via CI/fake adapters/fixtures/contracttests;
  - handmatige IBKR paper-account testing wacht tot volledige Version 1 release candidate.

## Milestone C — Market data + FX runtime foundations
- **Purpose**: provider adapters, latest snapshots, freshness checks.
- **Blocked until**: IBKR read-only basis stabiel.
- **Non-goals**: geen fake prijzen; geen suggesties.
- **Task size guidance**: per adapter/contractlaag.
- **Bundling notes**:
  - veilig: adapter + tests;
  - apart houden: combineren met suggestie-engine.

## Milestone D — Research Library + Evidence Ledger runtime
- **Purpose**: source extraction, URL snapshotting, prompt-injection analyse, credibility scoring en evidence ledger.
- **Blocked until**: opslag/API-fundament voor audit-koppelingen gereed.
- **Non-goals**: geen handelsacties.
- **Task size guidance**: per subsystem (extractie, scoring, ledger).
- **Bundling notes**:
  - veilig: één subsystem + tests;
  - apart houden: koppeling met brokeracties.

## Milestone E — Decision Package foundation
- **Purpose**: storage, API, UI en audit-links voor decision packages.
- **Blocked until**: evidence ledger basis gereed.
- **Non-goals**: geen orderuitvoering.
- **Task size guidance**: contract-first per laag.
- **Bundling notes**:
  - veilig: één API endpoint + tests;
  - apart houden: runtime broker-integratie.

## Milestone F — Model/risk/forecast foundation
- **Purpose**: feature store, risk metrics, baseline model, validatie en model registry.
- **Blocked until**: Decision Package datafundament.
- **Non-goals**: geen automatische acties.
- **Task size guidance**: per model/riskcomponent.
- **Bundling notes**:
  - veilig: metric-module + tests;
  - apart houden: modelruntime combineren met UI-overhaul.

## Milestone G — Suggestion engine
- **Purpose**: deterministische label translator, Suggestions-grid, explanation panels en blockers.
- **Blocked until**: model/risk basis en audittrail aanwezig.
- **Non-goals**: geen orders.
- **Task size guidance**: per suggesteringscomponent.
- **Bundling notes**:
  - veilig: één UI-component + tests;
  - apart houden: broker submission.

## Milestone H — Action draft workflow
- **Purpose**: editable drafts, dry-run en final confirmation (paper/user-approved only).
- **Blocked until**: suggestion engine stabiel + locks.
- **Non-goals**: geen automatische uitvoering.
- **Task size guidance**: per workflowstap.
- **Bundling notes**:
  - veilig: één draft-stap + tests;
  - apart houden: execution integratie.

## Milestone I — Alerts, daily briefing, Prediction Diary
- **Purpose**: notificaties en dagoverzicht met auditkoppeling.
- **Blocked until**: action draft/audit fundament beschikbaar.
- **Non-goals**: geen orderautomatisering.
- **Task size guidance**: per alert/briefingcapability.
- **Bundling notes**:
  - veilig: één alertkanaal + tests;
  - apart houden: brede UI-refactors.

## Milestone J — Version 1 acceptance, deployment, backup/restore
- **Purpose**: release-acceptatie, deploypad, backup + restore-validatie.
- **Blocked until**: milestones A-I voldoende afgerond.
- **Non-goals**: geen scope-expansie naar V2.
- **Task size guidance**: release-readiness per checklistblok.
- **Bundling notes**:
  - veilig: documentatie + verificatiechecks;
  - apart houden: grote functionele toevoegingen.

## Release-candidate-only manual testing policy
- Owner manual testing gebeurt pas op volledige Version 1 release candidate.
- Partial/unfinished slices worden niet handmatig getest door de owner.
- Partial features moeten CI/fake-adapter/fixture/contracttest-dekking hebben.
- Rode CI niet mergen; fix dezelfde PR.


## Task 130Q alignment note
- Milestones voor Dashboard/Action Center/Decision Packages/Suggestion Engine/Research Desk/Prediction Diary volgen de vergrendelde owner workshop richting uit `version-1-owner-workshop-decision-locks-task-130q.md`.
- Runtimevolgorde binnen Milestone B (geauditeerd in Task 135A): Task 133B readiness/preflight gate = voltooid, Task 134B manual sync execution blocking = voltooid, Task 134B-R + 134B-R2 repairs = voltooid; Task 135B is de eerstvolgende implementatiestap binnen read-only veiligheidsgrens.

## Immediate lock-in update
- Task 153-L is afgerond als documentatie/product-lock recovery en moet als afgeronde blocker worden beschouwd vóór verdere user-facing implementatie.
- Eerstvolgende implementatietaak: **Task 155** (real IBKR account-mode-aware read-only account snapshot preflight voor cash/positions, zonder persistence/valuation/market-data/FX/suggestions/action drafts/orders).
