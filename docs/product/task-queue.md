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
- **Task size guidance**: verticale slices per read-only endpoint of sync-component.
- **Bundling notes**:
  - veilig: één endpoint + tests;
  - apart houden: broker-order flows.

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
