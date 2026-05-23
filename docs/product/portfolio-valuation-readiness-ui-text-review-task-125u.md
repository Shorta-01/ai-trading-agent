# Task 125U — Document-first review van read-only portfolio valuation readiness UI-teksten en helpteksten

## 1) Purpose en boundary
Deze taak is **documentatie/preflight-only** voor consistente, eenvoudige Nederlandse UI-teksten rond read-only portfolio valuation readiness.

Expliciete boundary:
- geen runtimegedrag-wijzigingen;
- geen codewijzigingen in API/web runtime;
- geen TypeScript runtime-logic changes;
- geen Python API/model/calculator changes;
- geen storage/migraties;
- geen runtime market-data/latest-price/FX-provider fetch;
- geen suggesties, action drafts, orders of broker execution;
- geen fake kostbasis/P/L/markt/FX/cash/converted-total waarden.

## 2) Huidige UI-tekstinventaris (observatie)
Bronnen gecontroleerd:
- `apps/web/app/page.tsx`
- `apps/web/app/portefeuille/page.tsx`
- `apps/web/components/ValuationTraceDetails.tsx`
- `apps/web/components/PositionPlTraceDetails.tsx`
- `apps/web/lib/apiClient.ts`
- `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py`
- `apps/api/tests/test_portfolio_valuation_readiness_endpoint.py`

Patronen die nu zichtbaar zijn in valuation readiness-oppervlakken:
- Dashboard valuation cards:
  - labels zoals `Totale portefeuillewaarde`, `Cashwaarde`, `Totale marktwaarde`, `Omrekening`.
  - fallback-teksten zoals `Geen veilige totaalwaarde` en `Geen veilige totaalwaarde beschikbaar`.
- Portefeuille valuation totals:
  - labels `Totale portefeuillewaarde`, `Totale marktwaarde`, `Cashwaarde`, `Basismunt`, `Omrekening`, `Toelichting`.
- Conversion trace/details:
  - section-koppen zoals `Controle en herkomst`, `Blokkerende details`, `Ruwe auditdata`.
- Kostbasis en ongerealiseerde P/L tabel:
  - kolommen zoals `Kostbasis`, `Status kostbasis`, `Ongerealiseerde winst/verlies`, `Winst/verlies %`, `Status winst/verlies`, `Ontbrekende invoer`.
- Row-level trace/details:
  - labels rond `Herkomst kostbasis`, `Herkomst winst/verlies`, `Marktsnapshot`, `Prijsmoment`, en trace fallback zoals `Geen tracegegevens beschikbaar`.
- Empty/unavailable states:
  - `Waardering niet beschikbaar`, `Nog geen kostbasis- of winst/verliesgegevens`, `Er worden geen waarden verzonnen`.
- Blocked/control-needed states:
  - `Controle nodig`, `Geblokkeerd`, en blokkerende reason-lijsten (missing/stale/invalid inputs).

Zoekcontrole uitgevoerd op termen:
- `Geen veilige`, `Controle nodig`, `Geblokkeerd`, `trace`, `Kostbasis`, `winst/verlies`, `Omrekening`, `totaalwaarde`, `live`, `realtime`, `N/A`.

## 3) Wording-principes
Voor valuation readiness UI-copy geldt:
- Houd taal eenvoudig Nederlands.
- Vermijd jargon; als onvermijdelijk, geef korte uitleg.
- Geen fake certainty (toon geen schijnzekerheid bij incomplete data).
- Geen `live`/`realtime` wording zonder echte freshness/runtime-garantie.
- Gebruik nooit `ready/klaar`-taal wanneer status `controle nodig` of `geblokkeerd` is.
- Geen adviesimplicatie vanuit valuationwaarden.
- Geen `kopen/verkopen/houden` woordgebruik naast valuation-only velden.
- Toon unavailable nooit als `0`.
- Gebruik geen kale `N/A`.
- Leg altijd kort uit **waarom** een waarde unavailable is.
- Houd onderscheid expliciet tussen:
  - `Niet beschikbaar`;
  - `Controle nodig`;
  - `Geblokkeerd`.

## 4) Standaard wording-catalogus (aanbevolen)
Aanbevolen labels/helpteksten voor toekomstige implementatie:
- **Totale portefeuillewaarde** — help: `Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is.`
- **Totale marktwaarde** — help: `Marktwaarde uit opgeslagen snapshots; geen browserberekening.`
- **Cashwaarde** — help: `Cash uit opgeslagen accountsnapshot; geen verzonnen fallback.`
- **Basismunt** — help: `Valuta waarin totalen worden getoond als omrekening veilig beschikbaar is.`
- **Omrekening** — help: `Status van omzetting naar basismunt op basis van opgeslagen wisselkoersen.`
- **Kostbasis** — help: `Kostbasis uit opgeslagen brokerinput; ontbrekende invoer blijft zichtbaar.`
- **Status kostbasis** — help: `Toont of kostbasis veilig beschikbaar, onduidelijk of geblokkeerd is.`
- **Ongerealiseerde winst/verlies** — help: `Alleen getoond wanneer kostbasis en marktinput veilig beschikbaar zijn.`
- **Winst/verlies %** — help: `Alleen getoond wanneer percentage veilig berekend kan worden.`
- **Status winst/verlies** — help: `Toont of winst/verlies klaar, controle nodig of geblokkeerd is.`
- **Ontbrekende invoer** — help: `Lijst met velden die ontbreken voor veilige waardeweergave.`
- **Controle en herkomst** — help: `Waarom een waarde wel/niet beschikbaar is en uit welke opslagbron ze komt.`
- **Herkomst kostbasis** — help: `Trace van gebruikte kostbasis-invoer.`
- **Herkomst winst/verlies** — help: `Trace van gebruikte winst/verlies-invoer.`
- **Marktsnapshot** — help: `Opslagbron van gebruikte marktprijs.`
- **Prijsmoment** — help: `Tijdstip van de gebruikte opgeslagen prijs.`
- **Ruwe auditdata** — help: `Technische tracevelden voor controle; geen adviessignaal.`

## 5) Missing-input en empty-state checklist
Checklist voor lege/missende staten:
- [ ] geen latest IBKR snapshot
- [ ] geen posities
- [ ] geen cash snapshot
- [ ] ontbrekende market data
- [ ] verouderde market data
- [ ] ontbrekende FX
- [ ] verouderde FX
- [ ] ongeldige FX
- [ ] ontbrekende basismunt
- [ ] ontbrekende average cost
- [ ] ongeldige quantity
- [ ] unsupported shortpositie
- [ ] lege kostbasis-trace
- [ ] lege ongerealiseerde-P/L-trace
- [ ] lege conversion-trace
- [ ] trace-object bestaat maar bevat nested/onleesbare waarden

## 6) Veilige wordingvoorbeelden
- `Geen veilige waarde beschikbaar`
- `Controle nodig`
- `Geblokkeerd`
- `Geen tracegegevens beschikbaar`
- `Alleen opgeslagen gegevens worden getoond`
- `Er worden geen waarden berekend in de browser`
- `Er worden geen waarden verzonnen`

## 7) Onveilige wordingvoorbeelden (verboden)
- `Live waarde`
- `Realtime winst`
- `Actuele marktwaarde` (tenzij freshness/runtime dit echt dekt)
- `Klaar om te kopen`
- `Goed moment om te verkopen`
- `P/L is 0` wanneer waarde unavailable is
- `N/A` zonder uitleg
- elke tekst die advies, suggestie, order-readiness of brokeractie impliceert

## 8) Checklist voor toekomstige implementatietaak
Bij latere code-implementatie van deze catalogus:
- [ ] UI gebruikt alleen bestaande API-aangeleverde waarden.
- [ ] geen browser-side financiële berekeningen.
- [ ] geen JavaScript numeric parsing voor money/P/L-berekeningen.
- [ ] geen API behavior changes.
- [ ] geen runtime fetch.
- [ ] geen fake waarden.
- [ ] geen suggestie/action/order-controls.
- [ ] web lint/build draaien zodra code wijzigt.
- [ ] `docs/product/read-only-readiness-pr-checklist.md` toepassen bij label/helptekstwijzigingen.

## 9) Aanbevolen volgende taak
Aanbevolen volgende smalle implementatiestap:

**Task 125V — Apply the Task 125U wording catalog to the read-only portfolio valuation readiness UI labels/help texts, without changing API behavior, without browser-side financial calculations, without runtime fetch, without suggestions, without action drafts and without orders.**
