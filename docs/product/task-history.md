# Task History (concise)

> Opmerking: waar PR-nummers niet betrouwbaar lokaal bevestigd zijn, worden taaknamen gebruikt zonder nummergok.

## Foundation and governance era

- Product scope/guardrails foundations vastgelegd (paper-only, safety boundaries, simple Dutch UI).
- API/worker/web/Docker/CI skeletons opgezet.
- Shared domain/storage package foundations toegevoegd.
- Decimal-first financiële contracten en paper-only constraints vastgelegd.
- Settings/system events/status foundations toegevoegd.

## Storage and broker planning era

- Storage/migratie foundations met Alembic-planning en readiness checks toegevoegd.
- IBKR source-of-truth doctrine en architectuur-ADR’s toegevoegd.
- IBKR adapter-first contract foundations toegevoegd.
- Broker sync/reconciliatie schema slices in opeenvolgende migratiefases voorbereid.

## Research/suggestion architecture era

- Research Engine en Suggestion Engine contracts toegevoegd.
- Suggestion lifecycle en validity-window contract foundations toegevoegd.
- Data freshness, source credibility, prompt-injection defense contracts toegevoegd.
- Market calendar/trading-hours contracts toegevoegd.
- Quant model contract foundations toegevoegd.
- AI Event Intelligence/deep-search contract foundations toegevoegd.
- Evidence Ledger storage foundations toegevoegd.
- Event Signal storage foundations toegevoegd.

## Research Library implementation era

- **Task 56A/56B/56C:** Research Source Archive storage foundations.
- **Task 57:** API foundation + repairs.
- **Task 58:** Nederlandse UI foundation.
- **Task 59:** veilige file upload API + repairs.
- **Task 60:** file upload UI.
- **Task 61A:** extracted text storage foundation.
- **Task 61B:** deterministische TXT/MD/CSV extractie-runtime + repairs voor green CI.
- **Task 62:** gedetailleerde project handover en Version 1 backlog source-of-truth docs.
- **Task 63:** Onderzoeksbibliotheek UI extractie-trigger + extracted-text status display.
- **Task 64:** deterministic document classification contracts/runtime foundation + API endpoint `POST /research/sources/{library_source_id}/classify-deterministic`; classification remains metadata-only and blocked for suggestions.

## Forecasting doctrine lock

- Probabilistische asset-outlook doctrine toegevoegd als productrichting voor toekomstige forecast-, quant-, suggestion- en AI-event-intelligence taken.
- Locked principle: het systeem berekent probability/range-based outlooks, geen fake exact toekomstig koersdoel.
- Locked principle: Python/modelcode berekent kansen, ranges en risico; AI interpreteert bewijs en legt uit.
- Locked principle: forecasts zijn geen orders, geen IBKR acties en bypassen geen gates.

## Current task

- **Task 67:** evidence extraction foundation voor research-bronnen is de volgende aanbevolen kleine taak, tenzij CI eerst een reparatietaak vereist.

- Task 65 afgerond: prompt-injection runtime scanstatus wiring toegevoegd (opslaan + latest ophalen), met conservatieve blokkade voor suggesties in alle gevallen.

- Task 66 afgerond: source credibility assessment status wiring toegevoegd (opslaan + latest ophalen), met conservatieve blokkade: safe_to_use_for_suggestions blijft false en blocks_suggestions blijft true.
- Task 66B afgerond: CI-reparatie na Task 66 (storage ruff formatting + API testverwachtingen bijgewerkt voor credibility-woordkeuze en migratie `0013`), zonder runtime-gedragswijziging; bronnen blijven geblokkeerd voor suggesties.
