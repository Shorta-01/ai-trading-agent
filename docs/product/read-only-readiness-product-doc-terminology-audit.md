# Read-only readiness product-doc terminologie-audit (Task 100)

## A) Purpose

Deze audit controleert **productdocumentatie** (niet UI/API-bronbestanden) op wording die runtime-readiness kan impliceren terwijl runtimecapaciteiten nog niet bestaan.

Doel:
- read-only grenzen conservatief en consistent houden;
- voortijdige runtime-implicaties in productdocs voorkomen;
- duidelijk scheiden tussen huidige status (status/metadata-only) en toekomstige runtimeplannen.

## B) Scope

Geaudit:
- `docs/product/final-solution-vision.md`
- `docs/product/release-1-functional-workflow-blueprint.md`
- `docs/product/current-state.md`
- `docs/product/locked-decisions.md`
- `docs/product/version-1-backlog.md`
- `docs/product/task-history.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/probabilistic-asset-outlook-doctrine.md`
- `docs/product/probabilistic-outlook-scope-addendum.md`
- `docs/product/asset-value-prediction-engine-roadmap.md`
- `docs/product/codex-ci-quality-rules.md`
- `docs/product/read-only-readiness-pr-checklist.md`

Referentiebron gebruikt:
- `docs/product/read-only-readiness-ui-contract-inventory.md` (niet gedupliceerd).

## C) Terms to check

Gecontroleerd op termen die ten onrechte kunnen impliceren dat nu al bestaat:
- live/current/latest prijs;
- market-data runtime;
- runtime-fetch;
- vrijgegeven analyse;
- beschikbare suggesties;
- Decision Packages als runtime-objecten;
- actiedrafts;
- IBKR-ordergedrag;
- AI-advies;
- acceptatie van fake portfolio/broker/market/recommendation data.

## D) Audit table

| Document | Terms / sections reviewed | Status | Change made? | Reason |
|---|---|---|---|---|
| `final-solution-vision.md` | Workflow target-state vs V1 boundary en modulelijst | Safe | Nee | Beschrijft target-state, maar markeert V1-grenzen en nog te bouwen modules expliciet. |
| `release-1-functional-workflow-blueprint.md` | Future workflow termen (suggesties, Decision Package, drafts, orders) | Safe | Nee | Duidelijk als blueprint/target; runtime niet als huidig gedrag geclaimd. |
| `current-state.md` | Header/samenvatting + taskstatusregels | Harmonized | Ja | Stale statusregel “na Task 97” gecorrigeerd en Task 100 auditstatus toegevoegd. |
| `locked-decisions.md` | Vergrendelde scope- en safetybeslissingen | Safe | Nee | Scope- en safetylocks blijven conservatief en read-only consistent. |
| `version-1-backlog.md` | Volgende stap/taakstatus + runtime pending formuleringen | Harmonized | Ja | Stale “Volgende conservatieve stap: Task 97” vervangen door afgeronde Task 100-regel + conservatieve follow-up. |
| `task-history.md` | Meest recente tasksamenvattingen | Harmonized | Ja | Task 100 toegevoegd met documentatie-only scope en expliciete runtime-niet-toegevoegd bevestiging. |
| `version-1-scope-register.md` | Recente taskblokken + “not implemented yet” context | Harmonized | Ja | Task 100 toegevoegd als documentatie/audit-only; stale next-step verwijzing geactualiseerd. |
| `probabilistic-asset-outlook-doctrine.md` | Forecast object/doctrine-taal | Needs future runtime task | Nee | Bevat toekomstige forecasttermen; correct als doctrine (niet als huidige runtime). |
| `probabilistic-outlook-scope-addendum.md` | Scope-addities + statuskolom | Needs future runtime task | Nee | Correct geplande status (“Planned”, “not implemented yet”). |
| `asset-value-prediction-engine-roadmap.md` | Faseroadmap V1.0–V1.8 | Needs future runtime task | Nee | Roadmap is expliciet toekomstig en runtime-pending. |
| `codex-ci-quality-rules.md` | CI- en reviewguardrails voor wordingdrift | Reference-only | Nee | Referentieregels blijven passend; geen termenharmonisatie nodig. |
| `read-only-readiness-pr-checklist.md` | Checklist/rubric termen | Reference-only | Nee | Al consistente termenset; gebruikt als controlebasis. |

## E) Findings

Aangepaste wording/trackings:
- `current-state.md`: stale regel “Huidige toestand: na Task 97” gecorrigeerd en Task 100 toegevoegd als afgeronde documentatie-audit.
- `version-1-backlog.md`: stale “Volgende conservatieve stap: Task 97” verwijderd en vervangen door afgeronde Task 100 + conservatieve volgende stap zonder runtime-start.
- `version-1-scope-register.md`: status aangevuld met Task 100 documentatie-audit/harmonisatie-only.
- `task-history.md`: Task 100 entry toegevoegd met audit/harmonisatiecontext.
- `next-task.md`: Task 101 als conservatieve documentatiefollow-up ingesteld (geen market-data runtime-start).

Geen overige onveilige wording gevonden die runtimecapabilities als reeds actief presenteert buiten bovenstaande tracking-harmonisatie.

## F) Locked wording

Voorkeurspatroon voor read-only wording:
- read-only status
- metadata/status-only
- geen market-data runtime
- geen runtime-fetch
- geen latest-price fetching
- geen analysevrijgave
- geen suggesties
- geen Decision Packages runtime
- geen actiedrafts
- geen orders
- geen fake data
