# Codex Task Template (herbruikbaar)

## Repository en project
- Repository:
- Project:

## Taaktitel
- Task XXX —

## Current verified state
- Laatste gemergede PR:
- Open PR's:
- Laatste geverifieerde CI-run:
- Status zes verplichte jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`):

## Source-of-truth docs to read
- `AGENTS.md`
- `docs/product/project-handover.md`
- `docs/product/current-state.md`
- `docs/product/locked-decisions.md`
- `docs/product/version-1-backlog.md`
- `docs/product/next-task.md`
- `docs/product/task-history.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/codex-ci-quality-rules.md`

## Goal
- 

## Scope
- 

## Non-goals
- 

## Expected changed files
- 

## Required checks
- Repository-searches / relevante lokale checks:
- Extra checks bij codewijzigingen (ruff/mypy/pytest etc.):

## Product tracking updates
- Update in dezelfde PR minimaal:
  - `docs/product/current-state.md`
  - `docs/product/task-history.md`
  - `docs/product/version-1-backlog.md`
  - `docs/product/version-1-scope-register.md`
  - `docs/product/next-task.md`
  - `docs/product/project-handover.md` (indien nodig)

## Red/green CI rule
- Green CI = review + merge toegestaan.
- Red CI = niet mergen; fix in dezelfde PR; rerun tot groen.
- Reeds rood op main gemerged = één gerichte repair-PR.

## Locked CI discipline
- Niet mergen zonder zes groene jobs: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- Laatste CI-check moet na laatste commit gebeuren.
- Geen auto-merge.
- Human review + manual merge verplicht.

## Locked formatting and line-length rule
- Python moet voldoen aan repo Ruff-config.
- Geen E501 line-too-long.
- Gebruik multiline dicts/calls waar nodig.

## Locked contract-drift rule
- Contractwijziging = alle tests/fakes/fixtures/types in dezelfde PR bijwerken.
- Zoek op oud contractgebruik voor afronding.

## Safety boundaries (altijd herhalen)
- Geen live trading.
- Geen automatic trading.
- Geen broker action zonder expliciete user approval.
- Geen fake data.
- Geen stale advice.
- Python/model code calculates.
- AI explains.
- UI blijft simpel Nederlands.
- Geen suggestions/action drafts/orders tenzij expliciet in scope.
- Geen runtime fetch tenzij expliciet in scope.

## Manual testing policy
- Vraag de gebruiker niet om partial unfinished features handmatig te testen.
- Partial features moeten automated tests bevatten, inclusief fake-adapter tests waar externe integraties meespelen.
- Handmatige user-testing gebeurt bij volledige Version 1 release candidate.
- Als een taak tóch handmatige testing vóór release candidate vereist, moet dat expliciet gemotiveerd en vooraf goedgekeurd zijn.


## Task 130Q reminder lock
- Respecteer `docs/product/version-1-owner-workshop-decision-locks-task-130q.md`.
- Geen taak mag dashboard/order/evidence/account-environment/AI-calculation boundaries verzwakken.
- Partial features vereisen geautomatiseerde tests (CI/fake adapters/fixtures/contracttests).
- Owner manual testing gebeurt alleen op volledige release candidate.
