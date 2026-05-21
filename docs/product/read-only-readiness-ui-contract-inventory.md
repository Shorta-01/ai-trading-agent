# Read-only readiness UI/API contract inventory (Task 98)

## A) Doel

Deze inventaris voorkomt wording-drift in UI- en API-contracten die ten onrechte runtime-capaciteiten kunnen impliceren voordat die bestaan.

Doel van dit document:
- read-only grenzen expliciet en consistent houden;
- verwarrende termen vroeg signaleren;
- toekomstige runtime-taken beschermen tegen voortijdige claims over market data, analyse, suggesties, Decision Packages, actiedrafts of orders.

## B) Scope

Deze inventaris dekt minimaal:
- Dashboard
- Portefeuille
- Volglijst
- Suggesties
- IBKR Acties
- Onderzoek
- Historiek
- Instellingen
- API-clientcontracten in `apps/web/lib/apiClient.ts`
- readiness-gerelateerde API-modellen/routes in `apps/api/src/portfolio_outlook_api/`

## C) Huidige veilige labels/patronen (goedgekeurd)

Goedgekeurde Nederlandse read-only patronen:
- "Read-only status"
- "Nog geen runtime"
- "Niet beschikbaar"
- "Geblokkeerd"
- "Geen analysevrijgave"
- "Suggesties geblokkeerd"
- "Geen actiedrafts"
- "Geen orders"
- "Metadata/status-only"
- "Wacht op toekomstige runtime-stap"

Aanvullende veilige patronen die al in code/docs zichtbaar zijn:
- "Geen market-data runtime"
- "Geen runtime-fetch"
- "Snapshotmetadata beschikbaar" (alleen als statusmetadata, niet als prijsclaim)

## D) Onveilige wording-patronen (verboden tenzij expliciet ontkend)

Niet gebruiken zonder expliciete negatie/afbakening:
- "market data ready"
- "analysis ready"
- "suggestions ready"
- "action draft ready"
- "order ready"
- "live price"
- "current price"
- "latest price"
- "runtime active"
- "AI advice"
- "recommendation available"

Nederlandse equivalenten met hetzelfde risico:
- "actuele prijs"
- "live prijs"
- "laatste prijs"
- "analyse klaar"
- "suggestie klaar"
- "actie klaar"
- "order klaar"

Interpretatieregel:
- Dergelijke termen mogen alleen voorkomen als ze ondubbelzinnig ontkend worden (bijv. "geen live/current marktprijs").

## E) Inventaristabel

| Area / scherm / contract | Geïnspecteerde files | Huidige status | Safe today? | Reden | Follow-up nodig? |
|---|---|---|---|---|---|
| Dashboard | `apps/web/app/page.tsx` | Read-only statusbadges + geblokkeerde suggestie/AI-runtime messaging | Ja | Teksten benoemen expliciet dat suggestie- en AI-runtime nog niet bestaan | Nee |
| Portefeuille | `apps/web/app/portefeuille/page.tsx` | Read-only snapshotweergave met veilige empty states | Ja | Geen claims over live prijzen/suggesties/orders; status blijft snapshot/empty-state georiënteerd | Nee |
| Volglijst | `apps/web/app/volglijst/page.tsx` | Read-only readinesslabels via API-contractvelden | Ja | Focus op status/readiness i.p.v. runtime-claims; boundaries liggen in API-teksten | Nee |
| Suggesties | `apps/web/app/suggesties/page.tsx` | Scherm aanwezig (read-only placeholderstijl) | Ja | Geen runtime unlock-terminologie gevonden in gezochte risicopatronen | Nee |
| IBKR Acties | `apps/web/app/ibkr-acties/page.tsx` | Scherm aanwezig (read-only/placeholder fase) | Ja | Geen order-readiness claims aangetroffen in risicopatronen | Nee |
| Onderzoek | `apps/web/app/onderzoek/page.tsx` | Scherm aanwezig (foundationstatus) | Ja | Geen misleidende runtime-claims aangetroffen in risicopatronen | Nee |
| Historiek | `apps/web/app/historiek/page.tsx` | Scherm aanwezig (foundationstatus) | Ja | Geen misleidende readinessclaims aangetroffen in risicopatronen | Nee |
| Instellingen | `apps/web/app/instellingen/page.tsx` | Scherm aanwezig (foundationstatus) | Ja | Geen risicovolle "ready/live/current" claims aangetroffen | Nee |
| API-clientcontracten | `apps/web/lib/apiClient.ts` | Clientcontracten aanwezig; geen risicovolle readiness-termen gevonden in inspectie | Ja | Geen unsafe readiness-labels in gezochte patronen; contractlaag blijft neutraal | Nee |
| Readiness response-contracten | `apps/api/src/portfolio_outlook_api/market_data_readiness.py` | Sterke read-only boundary-teksten (incl. expliciete ontkenning live/current prijs) | Ja | Teksten verankeren "geen runtime-fetch/analyse/suggesties/actiedrafts/orders" | Nee |
| Watchlist readiness mapping | `apps/api/src/portfolio_outlook_api/watchlist.py` | AssetListing-status met read-only boundarytekst | Ja | Gevalideerde listing blijft expliciet read-only zonder runtimevrijgave | Nee |
| Status-routes readiness/snapshots | `apps/api/src/portfolio_outlook_api/status_routes.py` | Read-only routes en helpteksten voor snapshots/status | Ja | Endpointteksten benoemen read-only snapshotkarakter; geen runtime unlock | Nee |

## F) Conservatieve hardening-kandidaten voor later

Geen directe verplichte labelfixes gevonden in deze audit.

Conservatieve follow-upkandidaten (documentatie/contractlaag, geen runtimewerk):
1. Voeg bij toekomstige nieuwe UI-schermen standaard een korte "read-only grens" helptekstcomponent toe met vaste goedgekeurde zinnen.
2. Voeg een lichte lint/checklistregel toe in PR-template om onveilige termen (zoals "live/current/latest price" zonder negatie) expliciet te reviewen.
3. Houd `market_data_readiness.py` aan als centrale bron voor boundary-teksten zodat UI-contractconsumptie consistent blijft.

## Task 98 scopebevestiging

Deze taak is documentatie/inventaris-only:
- geen runtime market-data fetching;
- geen latest-price fetching;
- geen scheduler/background jobs;
- geen forecast runtime;
- geen AI runtime;
- geen suggesties/Decision Packages/actiedrafts/orders;
- geen fake market/broker/recommendation data.

## G) PR-review checklist koppeling (Task 99)

De inventaris blijft de inhoudelijke referentiebron voor veilige read-only wording per scherm/contract.

Gebruik voor PR-reviews aanvullend: `docs/product/read-only-readiness-pr-checklist.md`.
- De inventaris = bron van termen/patronen en scopecontext.
- De checklist = compacte reviewer-tool vóór merge.
