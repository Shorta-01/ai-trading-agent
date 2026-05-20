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

| IBKR open-orders + executions snapshots foundation (Task 76) | Contracted | Storage foundation aanwezig (in-memory foundation) | API implemented | UI implemented (dashboard tellers minimaal) | Runtime pending (echte IBKR connectie) | Read-only; geen ordersubmission/wijziging/cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime |

| Portefeuille read-only snapshot grid (Task 77) | Contracted | N/A | API hergebruikt (Task 75/76) | UI implemented | Runtime pending (echte IBKR connectie) | Read-only; toont opgeslagen snapshots voor posities/cash/open orders/executions; geen ordersubmission/-wijziging/-cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime en geen fake data |

| Watchlist foundation + Volglijst page (Task 78, CI repaired in Task 78B) | Contracted | Storage implemented | API implemented | UI implemented | Runtime pending | Lokaal/manueel, gescheiden van IBKR-portfolio; geen suggesties/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |

| Watchlist-to-Asset-Master identity linking foundation (Task 79) | Contracted | Bestaande storage hergebruikt (`watchlist_items.asset_id`) | API implemented | UI implemented (statusbadge + read-only canonical samenvatting) | Runtime pending | Reference/status-only; geen auto Asset Master create; geen portfolioposities/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |

| Asset Master search/picker UI foundation (Task 80) | Contracted | Bestaande storage hergebruikt (Asset Master records read-only) | API implemented (`GET /assets/master/search`) | UI implemented (Volglijst picker component + koppelen/ontkoppelen) | Runtime pending | Reference/status-only; selecteert alleen bestaande asset-identiteiten; geen auto Asset Master create, geen portfolioposities/suggesties/Decision Packages/action drafts/IBKR-ordergedrag/AI/market-data/forecast runtime; geen fake data |


| IBKR contract identity validation | Core workflow | Planned | Planned | Planned | Runtime pending | Active watchlist requires validated IBKR identity before data/analysis runtime |
| IBKR conid mapping | Core workflow | Planned | Planned | Planned | Runtime pending | Conid mapping required for market data readiness; ticker text alone is insufficient |
| IBKR-contract-based Volglijst activation | Core workflow | Planned | Planned | Planned | Runtime pending | Only resolved IBKR contracts may become active watchlist items |
| System-detected asset candidate resolution | Core workflow | Planned | Planned | Planned | Runtime pending | Detected assets remain candidates until IBKR contract resolution succeeds |
| IBKR watchlist sync | Core workflow | Planned | Planned | Planned | Runtime pending | Import/export later; must stay conid-based with auditable conflicts |
| Data freshness and priority engine | Core workflow | Planned | Planned | Planned | Runtime pending | Hot/warm/cold freshness tiers and readiness states |
| Historical data backfill scheduler | Core workflow | Planned | Planned | Planned | Runtime pending | Pacing-aware backfill queue before serious analysis |
| Market snapshot scheduler | Core workflow | Planned | Planned | Planned | Runtime pending | Latest snapshot scheduler layered with freshness policy |
| Fast alert layer | Core workflow | Planned | Planned | Planned | Runtime pending | Early signal layer on validated identities only |
| AI event trigger layer | Core workflow | Planned | Planned | Planned | Runtime pending | Event-analysis trigger foundation on validated, freshness-aware data |

| IBKR contract search/validation foundation (Task 82) | Contracted | API foundation implemented | Read-only endpoints implemented | UI not converted yet | Runtime pending | Identity/reference-only; safe not-configured behavior; no market-data/historical/scheduler/suggestions/Decision Packages/action drafts/order/AI/forecast runtime |


- Task 83: Volglijst add-flow omgezet naar IBKR contractpicker; actieve creatie vereist gevalideerde IBKR-contractidentiteit. Bestaande losse records zonder contract blijven niet-gevalideerd en niet klaar voor analyse. Geen market-data runtime, historical fetching, schedulers, suggesties, Decision Packages, action drafts, IBKR-ordergedrag, AI runtime, forecast runtime of fake data toegevoegd.
