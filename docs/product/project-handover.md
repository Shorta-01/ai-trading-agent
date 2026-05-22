# Project Handover — Portfolio Outlook Manager / Ai Trading Agent

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

- Producttrackingstatus: Task 127R (PR #271) is merged; Task 127R2 rondt de laatste documentatie-contradicties af. Laatste docs locken account-mode-aware productrichting en uitgebreide Task 127 decision-locks. Volgende implementatiestap blijft Task 125D (volgens `next-task.md`).

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
