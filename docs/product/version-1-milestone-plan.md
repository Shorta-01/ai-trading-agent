# Version 1 Milestone Plan (samenvatting)

Dit document groepeert resterend werk in grotere, beheersbare werkpakketten. Het is compacter dan `version-1-backlog.md`.

## Milestones
- A: Valuation readiness closure (read-only afronding)
- B: IBKR read-only runtime foundation
- C: Market data + FX runtime foundations
- D: Research Library + Evidence Ledger runtime
- E: Decision Package foundation
- F: Model/risk/forecast foundation
- G: Suggestion engine
- H: Action draft workflow (paper/user-approved)
- I: Alerts + daily briefing + Prediction Diary
- J: Version 1 acceptance + deployment + backup/restore

## Waar bundelen veilig is
- documentatie + product tracking;
- UI label/helptekst cleanup;
- één component + tests;
- één API endpoint + tests;
- één storage contract + migratie + tests.

## Waar bundelen niet veilig is
- storage migratie + ongerelateerde UI overhaul;
- market-data runtime + suggestions;
- AI runtime + action labels;
- Decision Package runtime + broker actions;
- broker submission + suggestion engine;
- financiële berekeningen zonder tests.

## Praktische bundelregel
Bundel alleen werk dat:
1. dezelfde safety-boundary deelt;
2. in één CI-cyclus goed te reviewen is;
3. geen contractdrift over meerdere subsystemen verspreidt.

Als één van deze drie niet geldt, splits de taak.
