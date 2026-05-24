# Task 148 — IBKR TWS client dependency decision gate

## 1. Purpose
Deze taak legt een expliciete implementatiebeslissings-gate vast vóórdat enige echte TWS/Gateway client dependency of runtime-connectiviteit wordt toegevoegd.

## 2. Current state after Task 147-R
- Runtime is disabled-by-default.
- Er is geen echte low-level IBKR client.
- Er is geen `ibapi` of `ib_insync` dependency.
- Handmatige read-only status-check endpoint/readiness diagnostics bestaan al.

## 3. What is already built
- Dependency-free adapter boundary, endpoint shells en readiness diagnostics.
- Paper-only/read-only safety gates en blokkeringen.
- Product-tracking en preflight-documentatie voor runtime enablement.

## 4. What is still not built
- Geen echte TWS/Gateway clientintegratie.
- Geen account/portfolio sync runtime.
- Geen auto-connect/reconnect/persistent session manager.
- Geen market-data/FX/suggestions/action drafts/orders/broker execution.

## 5. Decision options
A. `ibapi`  
B. `ib_insync`  
C. Dependency-free boundary langer aanhouden  
D. Dependency-introductie expliciet deferen

## 6. Option A: `ibapi`
Plus: dicht bij officiële IBKR API, minimale abstraction mismatch.  
Min: lifecycle en threading complexer; hogere implementatie-/foutrisico's voor veilige handmatige status-check slice.

## 7. Option B: `ib_insync`
Plus: hogere ergonomie voor request/response-flow en timeoutafhandeling.  
Min: async/event-loop implicaties, extra dependency surface, mogelijk packaging-risico op doelomgevingen.

## 8. Option C: keep dependency-free boundary longer
Plus: nul dependency-risico nu; maximale safety.  
Min: vertraagt verificatie van echte install/import-compatibiliteit.

## 9. Option D: defer real client dependency
Plus: veiligste korte-termijnkeuze als bewijs ontbreekt.  
Min: Milestone B voortgang vertraagt.

## 10. Risk comparison table
| Optie | Install/package risico | Runtime complexiteit | CI impact | Overall risico |
|---|---|---|---|---|
| `ibapi` | Middel | Hoog | Middel | Middel-hoog |
| `ib_insync` | Middel-hoog | Middel | Middel-hoog | Middel-hoog |
| Dependency-free langer | Laag | Laag | Laag | Laag |
| Defer dependency | Laag | Laag | Laag | Laag |

## 11. Safety comparison table
| Optie | No-order safety | Read-only status-check fit | Secret exposure risico |
|---|---|---|---|
| `ibapi` | Goed met harde gates | Goed | Middel |
| `ib_insync` | Goed met harde gates | Goed | Middel |
| Dependency-free langer | Zeer goed | Uitstekend | Laag |
| Defer dependency | Zeer goed | Uitstekend | Laag |

## 12. CI/package compatibility considerations
Eerst install/import preflight op ondersteunde Python/OS matrix; geen runtime connectie in deze fase.

## 13. Raspberry Pi / Linux arm64 considerations
Arm64-compatibiliteit moet expliciet bewezen worden via install/import checks; geen Pi-specifieke applicatielogica toevoegen.

## 14. Runtime lifecycle implications
Een dependency-keuze verandert nog niets aan lifecycle: geen auto-connect, geen reconnect loop, geen persistente session manager.

## 15. Read-only account-mode verification implications
Account-mode verificatie blijft verplicht vóór connectiepoging en moet mismatch/unknown hard blokkeren.

## 16. No-secret/no-raw-config implications
Geen credentials in logs/responses; geen raw broker payload exposure; config masking blijft verplicht.

## 17. Order/suggestion/action safety implications
Zelfs na dependency-selectie blijven orders/suggesties/action drafts strikt buiten scope en hard geblokkeerd.

## 18. Recommended decision
**Selecteer een conservatieve tussenstap: dependency-selectie nog niet definitief vastzetten; eerst Task 149 preflight uitvoeren die `ibapi` en `ib_insync` install/import-compatibiliteit vergelijkt zonder runtime-connectiviteit.**  
Motivatie: veilig, testbaar, en sluit aan op huidige architecturele boundary zonder risico op runtimeverbreding.

## 19. Explicit non-goals
Geen runtime code, geen API/web/storage schemawijzigingen, geen dependency-introductie, geen socket/connectie.

## 20. Required acceptance criteria before adding a dependency
1. Matrix-resultaten voor Python-versie(s) en Linux arm64/x86_64 install/import checks vastgelegd.
2. CI-impact beschreven inclusief lockfile/package policy.
3. Fake-client teststrategie blijft leidend; geen echte netwerkcalls in tests.
4. Security/no-secret logging policy bevestigd voor gekozen library.
5. Documenteerde rollback-stap beschikbaar.

## 21. Required acceptance criteria before any connection attempt
1. Runtime opt-in blijft default `False`.
2. Handmatige trigger-only, geen background/scheduler connect.
3. Timeouts/error mapping en account-mode gates zijn getest.
4. Geen auto-connect/reconnect/persistente sessie.
5. Audit logging voor elke connectiebeslissing aanwezig.

## 22. Required rollback/disable path
- Dependency mag feature-flagged gedeactiveerd blijven.
- Terugval naar dependency-free boundary moet zonder API-contractwijziging mogelijk blijven.
- Bij CI/package regressie: dependency-introductie terugdraaien in dezelfde PR.

## 23. Recommended next task
**Task 149 — Add dependency-selection compatibility preflight for TWS/Gateway client libraries without introducing runtime connectivity.**
