# Ai Trading Agent — Version 1 Scope Register

Zie ook `docs/product/final-solution-vision.md` voor het einddoel.

## Status definitions

- Contracted
- Storage implemented
- API implemented
- UI implemented
- Runtime pending
- Blocked for suggestions

## Traceability (current implemented state)

| Capability | Domain | Storage | API | UI | Runtime status | Suggestion/IBKR/order status |
|---|---|---|---|---|---|---|
| Research source archive | Contracted | Storage implemented | API implemented | UI implemented | Runtime pending (gedeeltelijk) | Blocked for suggestions; geen IBKR/order gedrag |
| Safe file upload | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| TXT/MD/CSV extraction | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| Deterministic document classification | Contracted | Storage implemented | API implemented | UI implemented | Foundation exists | Blocked for suggestions; geen IBKR/order gedrag |
| Prompt-injection scan status | Contracted | Storage implemented | API implemented | UI implemented (status zichtbaar) | **Runtime engine pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Source credibility status | Contracted | Storage implemented | API implemented | UI implemented (status zichtbaar) | **Runtime scoring engine pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Source evidence items (Task 67) | Contracted | Storage implemented | API implemented | UI implemented (status/foundation) | **Evidence runtime verdieping pending** | Blocked for suggestions; geen IBKR/order gedrag |
| Evidence Ledger API/linking (Task 68) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending | Blocked for suggestions; geen IBKR/order gedrag |
| Research Library source pipeline overall | Contracted | Storage/API/UI foundations implemented | API implemented | UI implemented | Full runtime pipeline pending | Blocked for suggestions; geen IBKR/order gedrag |
| Gate outcome/freshness foundation (Task 69) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending | Blocked for suggestions; audit/status-only; geen watchlist/IBKR/order gedrag |
| Source conflict findings (Task 70) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (analysis engine pending; storage/API foundation implemented) | Blocked for suggestions; audit/status-only; geen AI/watchlist/IBKR/order gedrag |
| Asset master identity foundation (Task 71) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (advanced identity validation/mapping pending; foundation is reference/status-only) | Blocked for suggestions; geen watchlist/portfolio/IBKR/order gedrag; geen AI/market-data/forecast runtime |
| Source-to-asset linking foundation (Task 72) | Contracted | Storage implemented | API implemented | UI pending | Runtime pending (asset detection/matching runtime pending) | Blocked for suggestions; audit/reference-only; geen AI/watchlist/portfolio/IBKR/order gedrag |
| CI quality governance rules | Locked | N/A | N/A | N/A | Implemented as mandatory workflow docs | Geen safety gate verzwakking toegestaan |

| Portfolio sync from IBKR | Core workflow | Planned | Planned | UI pending | Runtime pending | Geen runtime-implementatie; IBKR blijft operationele waarheid |
| Watchlist assets (manuele toevoeging, gescheiden van portfolio) | Core workflow | Planned | Planned | Planned | Runtime pending | Suggesties mogelijk na gates; geen automatische orders |
| Decision Package | Core workflow | Planned | Planned | Planned | Runtime pending | Kernobject voor auditbare suggesties; nog niet geïmplementeerd |
| Suggestions grid (Actief/Verlopen/Historiek) | Core workflow | Planned | Planned | Planned | Runtime pending | Portfolio/watchlist toont enkel laatste actieve hoofdsuggestie |
| IBKR Action Center (Te keuren/Actief bij IBKR/Historiek) | Core workflow | Planned | Planned | Planned | Runtime pending | Submission enkel na user approval; geen auto-trading |
| Prefilled action drafts | Core workflow | Planned | Planned | Planned | Runtime pending | Bewerkbaar vóór submit; audit op system-draft + user edits |
| Action safety checks | Core workflow | Planned | Planned | Planned | Runtime pending | Hard checks blokkeren uitvoering bij falen |
| Sync/recompute engine (jobs/events/manual refresh) | Core workflow | Planned | Planned | Planned | Runtime pending | Hybride refreshmodel; nog geen runtime |
| AI analytics layer | Core workflow | Planned | Planned | Planned | Runtime pending | Gestructureerde evidence-signalen; AI maakt geen orders |
| Daily briefing | Core workflow | Planned | Planned | Planned | Runtime pending | Dagelijkse wijzigingssamenvatting met evidence-links |
| Release 1 end-to-end acceptance workflow | Core workflow | Planned | Planned | Planned | Runtime pending | Niet compleet tot volledige keten werkt |

## Hard boundaries (Version 1)

- Geen live trading.
- Geen real-money execution.
- Geen automatische orders.
- Geen IBKR live order flow.
- Suggesties blijven geblokkeerd tot alle gates/runtime engines bestaan.


| Moderne GUI shell + dashboard foundation (Task 74) | Contracted | N/A | N/A | UI implemented | Runtime pending | UI-only foundation; geen IBKR/market-data/suggestion/AI/order runtime; gebruikt veilige empty states zonder fake data |

| IBKR portfolio sync foundation (Task 75) | Contracted | Storage foundation aanwezig | API implemented | UI pending (status wiring minimaal) | Runtime pending (echte IBKR connectie) | Read-only; geen ordersubmission/suggestions/AI/market-data/forecast runtime |
