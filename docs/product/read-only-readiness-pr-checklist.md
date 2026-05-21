# Read-only readiness PR checklist en term-review rubric (Task 99)

## A) Purpose

Deze checklist voorkomt dat UI/API wording capaciteiten suggereert die nog niet bestaan.

Doel:
- read-only grenzen consequent bewaken;
- wording-risico's vroeg detecteren;
- voorkomen dat labels/helpteksten/contractvelden impliceren dat runtime-capaciteiten al actief zijn.

## B) When to use

Gebruik deze checklist bij **elke PR** die minstens één van onderstaande onderdelen raakt:
- `apps/web/app/`
- `apps/web/components/`
- `apps/web/lib/apiClient.ts`
- `apps/api/src/portfolio_outlook_api/`
- `docs/product/read-only-readiness-ui-contract-inventory.md`
- UI-gerichte Nederlandse labels, status-tekst of help-tekst
- API response fields, Pydantic model descriptions of TypeScript client contracts

## C) Mandatory reviewer checklist

- [ ] Raakt de PR UI/API labels, help-tekst, status-tekst of response-contracten?
- [ ] Zo ja: heeft de auteur de read-only readiness inventory gecontroleerd?
- [ ] Zijn onveilige termen afwezig of expliciet ontkend?
- [ ] Vermijdt de tekst implicaties over live/current/latest prijzen?
- [ ] Vermijdt de tekst implicaties over market-data runtime of runtime-fetch?
- [ ] Vermijdt de tekst implicaties over analysevrijgave?
- [ ] Vermijdt de tekst implicaties over suggesties, Decision Packages, actiedrafts of orders?
- [ ] Blijven readiness-booleans waar van toepassing conservatief?
- [ ] Bevestigt de PR-body expliciet dat er geen runtime unlock is bij wording/contract-only wijzigingen?

## D) Term-review rubric

### Allowed terms
- Read-only status
- Nog geen runtime
- Niet beschikbaar
- Geblokkeerd
- Geen analysevrijgave
- Suggesties geblokkeerd
- Geen actiedrafts
- Geen orders
- Metadata/status-only
- Wacht op toekomstige runtime-stap

### Allowed only when explicitly negated
- live price
- current price
- latest price
- market data ready
- analysis ready
- suggestions ready
- action draft ready
- order ready
- actuele prijs
- live prijs
- laatste prijs
- analyse klaar
- suggestie klaar
- actie klaar
- order klaar

### Forbidden in current pre-runtime UI/API wording
Elke formulering die zegt of suggereert dat het systeem **nu al** beschikt over:
- live market data;
- actieve analyse;
- beschikbare suggesties;
- actieve Decision Packages;
- gereedstaande actiedrafts;
- uitvoerbare orders;
- AI-advies.

## E) Required PR-body wording

Plak onderstaande tekst in toekomstige PR-bodies wanneer dit van toepassing is:

> “Read-only readiness review: checked. This PR does not add market-data runtime, runtime-fetch, latest-price fetching, scheduler/background jobs, forecast runtime, AI runtime, suggestions, Decision Packages, action drafts, orders, or fake data.”

## F) Escalation rule

Als een toekomstige PR **bewust** runtime-capaciteiten wil introduceren, volstaat deze checklist niet.

Die PR moet expliciet:
- productdocs updaten;
- safety gates benoemen en uitbreiden;
- teststrategie en testdekking toevoegen;
- `docs/product/next-task.md` scope en rationale bijwerken.


## G) Locked decision referentie (Task 101)

Na checklist-review, verifieer de vergrendelde termenset in `docs/product/locked-decisions.md` (sectie **Read-only readiness terminology lock (Task 101)**). Gebruik daarnaast de productdoc-audit voor cross-doc context: `docs/product/read-only-readiness-product-doc-terminology-audit.md`.
