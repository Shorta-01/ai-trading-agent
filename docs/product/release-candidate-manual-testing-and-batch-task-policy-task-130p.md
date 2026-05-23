# Task 130P — Release-candidate manual testing and batch task policy

## 1) Purpose
Task 130P werkt de ontwikkelworkflow bij voor hoe partial features worden getest en hoe volgende taken worden gebundeld.

Dit is een **process/documentation-only** taak.

Task 130P voegt **geen** runtime productgedrag toe en wijzigt geen IBKR runtime, API runtime, web runtime, storage, migraties, sync, market-data runtime, FX runtime, suggesties, action drafts, Decision Packages runtime, orders of broker execution.

## 2) Manual testing policy
- Handmatige user-testing door de projecteigenaar gebeurt pas bij een volledige **Version 1 release candidate**.
- De gebruiker wordt niet gevraagd om half-afgewerkte partial features handmatig te testen.
- Partial features moeten worden afgedekt met CI, unit tests, API tests, web lint/build, fake adapters, fixtures en contracttests.
- IBKR paper-account handmatige testing gebeurt alleen wanneer de volledige Version 1 workflow release-candidate-ready is.

## 3) Release candidate testing definition
Een **Version 1 release candidate** betekent dat minimaal dit geheel release-klaar is:
- IBKR read-only sync end-to-end werkt.
- account-mode/status zichtbaar is.
- portfolio- en cash-zichtbaarheid werkt.
- open orders- en executions-zichtbaarheid werkt.
- market-data en FX readiness aanwezig is.
- evidence/source flow readiness aanwezig is.
- Decision Package readiness aanwezig is.
- suggestion grid readiness aanwezig is.
- action draft flow readiness aanwezig is.
- risk/freshness/source gates actief zijn.
- audit trail compleet is.
- UI in eenvoudig Nederlands staat.
- geen automatische brokeractie bestaat.
- geen submit/modify/cancel zonder expliciete user approval mogelijk is.
- CI groen is op alle zes jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- producttrackingdocs actueel zijn.

## 4) Batch task policy
Toekomstig werk moet waar veilig grotere milestone-batches prefereren.

### Veilig om te bundelen
- één status-boundary + tests + docs;
- één API endpoint-familie + tests;
- één UI-oppervlak + API-client type + tests;
- één read-only adapter boundary + fake-adapter tests;
- producttrackingupdates in dezelfde implementatie-PR;
- gerelateerde Nederlandse helptekst/status-tekst in dezelfde PR.

### Niet veilig om te bundelen
- broker order submission samen met suggesties;
- market-data runtime samen met suggestion engine;
- action drafts samen met broker submission;
- storage migratie samen met niet-gerelateerde UI-overhaul;
- AI runtime samen met final action labels;
- financiële berekeningen zonder dedicated tests;
- meerdere externe integraties in één PR;
- alles wat geld kan bewegen samen met niet-gerelateerd featurewerk.

## 5) Milestone batch examples
### Voorbeeld veilige batch
**"IBKR read-only account/session safety batch"**
- bevat account-mode mapping;
- unknown-status safe handling/wording;
- connection-failed/authentication-required/pacing-limited mapping;
- fake-adapter tests;
- no-secret tests;
- producttrackingupdates.

**Expliciet uitgesloten in deze batch**:
- sync;
- orders;
- market-data runtime;
- suggesties;
- action drafts.

### Voorbeeld onveilige batch
**"IBKR connection + sync + suggestions + action drafts + order submit"**
- mag niet als één PR worden uitgevoerd.

## 6) Testing responsibility split
- Codex/CI test elke PR.
- GitHub CI moet groen blijven.
- Fake adapters dekken externe services die in CI niet beschikbaar zijn.
- Handmatige user-testing wacht op de Version 1 release candidate.
- Rode CI betekent: dezelfde PR fixen vóór merge.
- Groene CI betekent: review + handmatige merge is toegestaan.

## 7) Next planning implication
De kleine Task 131-route wordt vervangen/uitgebreid naar een veiligere milestone-batch:

**Task 131B — Implement IBKR read-only account/session safety batch using the Task 130 session-status boundary, covering account-mode mapping, unknown-status safe wording, connection-failed/authentication-required/pacing-limited status mapping, fake-adapter tests and no-secret/no-fake-data checks, without account/portfolio sync, without market-data runtime, without suggestions, without action drafts and without orders.**

## 8) Note about known Task 130 follow-up
Een PR-reviewcomment meldde dat `unknown` IBKR status niet mag terugvallen op wording van `configured_not_connected`.

Deze correctie hoort in Task 131B.

Task 130P fixt dit niet, tenzij documentatievoltooiing anders onmogelijk zou zijn.
