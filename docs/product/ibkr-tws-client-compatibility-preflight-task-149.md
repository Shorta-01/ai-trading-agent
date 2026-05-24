# Task 149 — IBKR TWS/Gateway client compatibility preflight (zonder runtime-connectiviteit)

## 1. Purpose
Deze taak levert een documenteerde dependency-selectie compatibiliteitspreflight voor kandidaat TWS/Gateway client libraries (`ibapi`, `ib_insync`) vóór enige dependency-introductie in projectmetadata.

## 2. Current state after Task 148
Task 148 sloot af met een decision gate: eerst compatibiliteitspreflight, daarna pas eventueel een dependency-only introductie. Runtime blijft disabled-by-default en dependency-free.

## 3. Compatibility preflight method
- Documentreview van eerdere productbesluiten en safety boundaries.
- Inspectie van package metadata/public documentatie (zonder runtime connectie).
- Optionele lokale/ephemeral install/import proef in tijdelijke venv (niet committed).
- Geen sockets, geen TWS/Gateway connectiecode, geen runtime imports in productiecode.

## 4. Candidate A: `ibapi`
- **Beschikbaarheid**: public package beschikbaar maar historisch onregelmatige releasecadans.
- **API-alignment**: laag-niveau, dicht bij officiële IB API objecten/events.
- **Dependency footprint**: relatief klein (beperkte extra afhankelijkheden).
- **Testbaarheid**: goed voor strikte boundary-tests met eigen fakes, maar meer boilerplate.
- **Risico**: lagere abstractie betekent hogere integratiecomplexiteit in latere runtime slices.

## 5. Candidate B: `ib_insync`
- **Beschikbaarheid**: public package beschikbaar met gebruiksvriendelijke wrapperlaag.
- **API-alignment**: gebouwd boven IB API-concepten, maar met extra abstraherende laag.
- **Dependency footprint**: zwaarder dan `ibapi` door extra wrappergedrag/async-hulpen.
- **Testbaarheid**: ergonomischer voor async-scenario’s, maar implicit gedrag/event-loop coupling vraagt extra governance.
- **Risico**: hogere kans op framework/event-loop koppelrisico’s in API/worker context.

## 6. Package/install considerations
- Beide kandidaten lijken package-technisch installeerbaar in gangbare Linux/Python omgevingen.
- Geen van beide is in deze taak toegevoegd aan `pyproject.toml` of lockfiles.
- Installatie-geschiktheid moet in volgende taak CI-matig gevalideerd worden.

## 7. Import considerations
- Documentatie/preflight wijst op importeerbaarheid van beide libraries in geïsoleerde context.
- In deze taak geen productie-imports toegevoegd in `apps/` of `packages/`.

## 8. Python version considerations
- Project draait op moderne Python 3.x; beide kandidaten vereisen versiecontrole vóór introductie.
- `ib_insync` event-loop gedrag vereist expliciete compatibiliteitscheck met gebruikte Python-minorversie.

## 9. CI considerations
- Introductie van dependency moet eerst via dependency-only PR met install/import checks per CI job.
- Geen wijziging aan CI dependency-install steps in deze taak.

## 10. Raspberry Pi / Linux arm64 considerations
- Architectuur-onafhankelijke Python packages zijn waarschijnlijk bruikbaar, maar arm64 wheel/sdist pad moet expliciet geverifieerd worden.
- Geen Raspberry Pi-specifieke logic toegevoegd.

## 11. Dependency footprint comparison
- `ibapi`: kleiner footprint, meer eigen integratiewerk.
- `ib_insync`: rijkere ergonomie, maar grotere abstraction surface + event-loop implicaties.

## 12. Runtime lifecycle implications
- Beide kandidaten vereisen later expliciete lifecycle boundary (connect, health, timeout, teardown).
- Deze taak verandert geen runtime lifecycle gedrag.

## 13. Async/event-loop implications
- `ibapi`: callback/threading patroon, minder directe asyncio-koppeling.
- `ib_insync`: sterkere asyncio/event-loop afhankelijkheid; extra risico op loop-conflicten in API/worker.

## 14. Read-only status-check fit
- Beide kandidaten passen in principe op handmatige read-only status-check boundary.
- `ibapi` sluit beter aan op minimale, expliciet gecontroleerde boundary zonder extra runtime-ergonomie.

## 15. Account-mode verification fit
- Beide kandidaten kunnen account-mode signalen ondersteunen via latere adaptermapping.
- Geen van beide vereist nu runtime-account sync.

## 16. Error/timeout mapping fit
- `ibapi` biedt ruwe error-events die direct op bestaande reason-codes gemapt kunnen worden.
- `ib_insync` biedt hogere abstractie maar vereist zorgvuldige mapping om semantiek niet te verliezen.

## 17. No-secret/no-raw-config exposure rules
- Ongewijzigd: geen secrets in logs/API, geen raw broker payload exposure.
- Deze taak voegt geen nieuwe runtime oppervlakken toe.

## 18. Order/suggestion/action safety implications
- Beide kandidaten blijven buiten uitvoeringsscope zolang alleen dependency-preflight wordt gedaan.
- Geen order/suggestie/action runtime toegevoegd; safety booleans blijven blocked.

## 19. Compatibility matrix
| Criterium | `ibapi` | `ib_insync` | Opmerking |
|---|---|---|---|
| Package beschikbaarheid | Go | Go | Public package beschikbaar |
| Python compatibiliteit | Voorwaardelijk Go | Voorwaardelijk Go | Verifieer exacte minorversie in Task 150 |
| CI install/import risico | Lager | Middel | `ib_insync` extra loop/abstraction risico |
| Linux x86_64 | Waarschijnlijk Go | Waarschijnlijk Go | Formeel valideren in CI |
| Linux arm64/RPi | Voorwaardelijk Go | Voorwaardelijk Go | Wheel/sdist pad nog valideren |
| Dependency footprint | Gunstig | Minder gunstig | `ibapi` compacter |
| Typing/testability | Neutraal-Go | Neutraal-Go | `ibapi` meer boilerplate; `ib_insync` meer implicit gedrag |
| Async/event-loop impact | Gunstig | Risicovoller | `ib_insync` loop-coupling |
| Official API alignment | Sterk | Goed | `ibapi` dichter op officiële laag |
| Read-only status-check fit | Sterk | Goed | beiden bruikbaar |

## 20. Go/no-go recommendation
**Aanbeveling: conditionele Go voor `ibapi` als veiligste volgende kandidaat, met nog géén dependency-introductie in Task 149.**

Reden: kleinste footprint, laagste event-loop coupling, en beste fit met huidige conservative read-only boundarystrategie.

## 21. Required acceptance criteria before dependency introduction
Voor een volgende dependency-only introductietaak (Task 150):
1. CI preflight moet per package-job install/import checks groen tonen.
2. Python-minorcompatibiliteit expliciet bevestigd.
3. arm64/RPi installpad expliciet gerapporteerd (go/no-go).
4. Geen runtime imports in productieflow.
5. Geen connectiepogingen/sockets tijdens checks.

## 22. Required rollback strategy
Bij CI/install regressie in dependency-only PR:
- dependency-change volledig terugdraaien (metadata-only rollback),
- `next-task.md` terugzetten op dependency-free boundary hardening,
- geen runtime changes combineren met rollback.

## 23. Recommended next task
**Task 150 — Add selected TWS/Gateway client dependency install/import CI preflight without runtime connectivity (voorkeurkandidaat: `ibapi`).**

## Evidence note (Task 149 execution)
- Deze taak is documentatie/preflight-only.
- Lokale/ephemeral install/import checks zijn in deze taak **niet uitgevoerd**; keuze is gebaseerd op documentatie/metadata-risicovergelijking en bestaande project safety boundaries.
