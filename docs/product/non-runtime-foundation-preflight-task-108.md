# Task 108 — Non-runtime foundation preflight (grote implementatievoorbereiding)

## A) Purpose

Deze preflight bereidt de **eerstvolgende betekenisvolle conservatieve foundationstap** voor zonder runtimegedrag te activeren.
Doel is uit de terugkerende drift-only documentatielus te stappen en precies één bruikbare Task 109 te kiezen die implementatierisico verlaagt.

## B) Source-of-truth references

- `docs/product/current-state.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/locked-decisions.md`
- `docs/product/release-1-functional-workflow-blueprint.md`
- `docs/product/codex-ci-quality-rules.md`
- `docs/product/read-only-readiness-pr-checklist.md`

## C) Candidate foundation areas reviewed

### Research Library
- PDF/DOCX/XLSX/PPTX extraction
- URL fetching + safe snapshotting
- Evidence Ledger API/linking deepening
- evidence review UI
- source freshness/runtime validation prep
- source conflict detection runtime prep
- source-to-asset linking runtime/detection/matching prep

### Core product
- Asset Master runtime deepening prep
- market-data storage/freshness follow-up prep (zonder runtime fetching)
- provider/source metadata design prep
- request-log/pacing/freshness audit design prep
- Decision Package contract/design prep (zonder runtime object creation)
- AI enforcement foundation prep (zonder AI runtime)
- audit viewer foundation prep

### IBKR/paper workflow
- IBKR Gateway skeleton design prep (zonder real connection/runtime)
- account-mode verification design prep (zonder live connection)
- paper action state-machine design prep (zonder actions/orders)

## D) Candidate matrix

| Candidate | Product value | Safety risk | Runtime risk | Dependencies | Why now / why not now | Recommended next-task status |
|---|---|---|---|---|---|---|
| Request-log/pacing/freshness audit storage+API contract preflight (docs-only) | Hoog: verlaagt toekomstige market-data/IBKR integratierisico en CI regressies | Laag | Laag | Bestaande readiness contracts (Task 85-96), locked terminology | Waarom nu: hoge leverage voor meerdere latere runtimeblokken. Waarom niet later: uitstel verhoogt kans op ad-hoc velddrift. | **Recommended next** |
| Evidence Ledger API/linking deepening preflight | Hoog | Laag | Middel | Research source foundations + Task 68 | Waardevol, maar contractomvang groter en sneller overlap met runtime-interpretatie. | Good later |
| Evidence review UI contract preflight | Middel | Laag | Middel | Evidence Ledger API-contracten | Nuttig, maar beter ná scherpere audit-/metadata-contractbasis. | Good later |
| Decision Package schema/design preflight | Hoog | Middel | Middel | Market-data/evidence/portfolio gate contracten | Belangrijk, maar veel cross-module dependencies nog onstabiel. | Blocked until prerequisite |
| IBKR Gateway skeleton design preflight | Hoog | Middel | Middel | Auth/session/account-mode contractkeuzes | Waardevol, maar sterk afhankelijk van pacing/log contractdiscipline. | Good later |
| Account-mode verification design preflight | Middel | Laag | Middel | IBKR gateway skeleton keuzes | Te vroeg zonder centrale gateway contracten. | Blocked until prerequisite |
| Paper action state-machine design preflight | Hoog | Middel | Middel | Decision Package + safety + IBKR reply model | Te vroeg; riskeert premature orderflow-detail zonder basiscontracten. | Too runtime-heavy now |
| URL fetching + safe snapshotting preflight | Hoog | Middel | Hoog | Security/policy + storage/archive contracten | Nuttig maar sneller runtimeadjacent (fetch lifecycle/policies). | Too runtime-heavy now |

## E) Recommended next foundation step

**Task 109 (aanbevolen):**
**Conservatieve storage/API contract preflight voor request logs + provider/source metadata + freshness audit records (documentation/design only).**

Waarom deze keuze:
- maximaliseert implementatiereadiness met minimale runtimeunlock-kans;
- reduceert toekomstige CI-risico's via vroegtijdige contractafbakening;
- ondersteunt zowel market-data als IBKR gateway vervolgwerk zonder fetch/connect/order-gedrag te starten.

## F) Acceptance criteria for recommended Task 109

### Waarschijnlijke files
- `docs/product/next-task.md`
- `docs/product/current-state.md`
- `docs/product/version-1-backlog.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/task-history.md`
- nieuw preflightdoc, bv. `docs/product/request-log-provider-freshness-contract-preflight-task-109.md`
- optioneel: aanvulling in `docs/product/codex-ci-quality-rules.md` (alleen documentatie, geen CI automation)

### Exact boundaries
- Alleen documentatie/design.
- Definieer contractvoorstellen voor:
  - request-log velden (provider, endpoint/doel, pacing-context, correlatie-id, timestamps, outcome status);
  - provider/source metadata velden (source type, provenance, versie, trust/scope);
  - freshness audit record velden (snapshot_time, observed_time, freshness_status, reason_code, audit link).
- Geen code, geen migrations, geen nieuwe tabellen, geen endpoints, geen scheduler/fetch runtime.

### Tests/checks required
- `git diff --check`
- optioneel document-consistency handmatige check tegen:
  - `docs/product/locked-decisions.md`
  - `docs/product/read-only-readiness-pr-checklist.md`

### What must not be added
- Geen runtime market-data fetching
- Geen runtime-fetch
- Geen latest-price fetching
- Geen scheduler/background jobs
- Geen historical fetching
- Geen forecast runtime
- Geen AI runtime
- Geen suggesties
- Geen Decision Packages runtime
- Geen actiedrafts
- Geen IBKR connectie/orders
- Geen fake data

### How to prove no runtime unlock happened
- Diff bevat uitsluitend `docs/product/*` wijzigingen.
- Geen wijzigingen in `apps/*`, `packages/*`, migrations of workflows.
- PR-body bevat expliciete non-runtime bevestiging met bovenstaande lock-termen.

## G) Read-only terminology lock check

Aanbevolen Task 109 respecteert expliciet:
- read-only status;
- metadata/status-only;
- **geen market-data runtime**;
- **geen runtime-fetch**;
- **geen latest-price fetching**;
- **geen analysevrijgave**;
- **geen suggesties**;
- **geen Decision Packages runtime**;
- **geen actiedrafts**;
- **geen orders**;
- **geen fake data**.

## H) Producttracking drift rule check (Task 107)

In Task 108 PR uitgevoerd en bevestigd:
- current-state title checked;
- `Huidige toestand:` line checked;
- task completion line added;
- task-history updated;
- scope-register updated;
- backlog updated;
- next-task updated.
