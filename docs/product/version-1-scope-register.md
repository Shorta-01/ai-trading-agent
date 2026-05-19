# Ai Trading Agent — Version 1 Scope Register

## Purpose

Dit register is de source-of-truth voor alle vergrendelde Version 1-features en hun implementatie-traceability.

- Ai Trading Agent is een **volledig tradingplatform**.
- Version 1 koppelt uitsluitend met een **IBKR paper-only account**.
- De accountmodus beperkt risico; de systeemfunctionaliteit wordt niet afgezwakt.
- De belangrijkste flow is **research en suggesties**.
- Executie is de laatste gecontroleerde stap.
- Alle user-facing UI blijft **eenvoudig Nederlands**.
- Belangrijk gedrag moet configureerbaar zijn in **Instellingen**.
- Dit register moet worden bijgewerkt bij lock, implementatie, wijziging of bewuste defer.

## Traceability rules

### Statusdefinities
- Locked
- Contracted
- Storage planned
- Storage implemented
- API planned
- API implemented
- UI planned
- UI implemented
- Tested
- Complete
- Deferred

### Implementatiekolommen
- Domain
- Storage
- API
- UI
- Tests
- Docs
- Status
- Notes

### Regels
- Een feature is pas complete met vereiste contracts, storage/API/UI/tests/docs waar van toepassing.
- Geen locked feature mag alleen UI-only of docs-only worden gerealiseerd.
- High-risk features moeten tests hebben.
- Financiële en broker-features moeten auditeerbaar zijn.
- AI-research features moeten schema-validatie hebben vóór gebruik.
- User-provided content is **bewijs**, geen instructie.

## Locked Version 1 feature traceability

| # | Feature | Why it exists | Domain | Storage | API | UI | Tests | Docs | Status | Notes |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | Research and Suggestion Engine | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 2 | Decision Readiness Gate | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 3 | Conditional suggestions | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 4 | Suggestion validity windows | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 5 | Suggestion lifecycle | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 6 | Suggestion blocked reasons | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 7 | Separate research confidence and action confidence | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 8 | “Why not now?” explanations | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 9 | Shadow suggestion mode | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 10 | Outcome tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 11 | Evidence Ledger | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 12 | Source credibility scoring | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 13 | Source conflict detection | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 14 | Prompt-injection defense | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 15 | AI research output schema validation | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 16 | AI research run tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 17 | AI cost and value dashboard | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 18 | User-fed Research Library | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 19 | User-uploaded files | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 20 | User-added URLs | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 21 | User notes as first-class evidence | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 22 | Multi-year report comparison | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 23 | Research source archive | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 24 | Document extraction pipeline | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 25 | OpenAI File Search / retrieval integration later | V1 governance en betrouwbaarheid | Deferred | Deferred | Deferred | Deferred | Deferred | This register | Deferred | Bewust later; geen V1 runtime verplichting nu. |
| 26 | Market calendar | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Marktkalender-contracten aanwezig; runtime koppeling volgt met officiële brondata. |
| 27 | Trading hours | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Handelssessie-contracten aanwezig; geen live broker/beurs-calls. |
| 28 | Half-day and holiday handling | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Half-day/holiday-contracten aanwezig; kalenderdata-runtime volgt later. |
| 29 | Auction/pre-market/post-market states | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Sessiestaten voor auction/voorbeurs/nabeurs gecontracteerd als safety input. |
| 30 | Catalyst calendar | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 31 | Earnings calendar | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 32 | Annual report / quarterly report calendar | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 33 | Filing event tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 34 | Dividend / ex-dividend events | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 35 | ETF rebalance event awareness | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 36 | Market regime layer | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 37 | Currency conversion rules | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 38 | FX source tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 39 | FX freshness handling | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 40 | Data freshness SLAs | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 41 | No-stale-advice wall | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Stale/unknown marktstatus blokkeert order-readiness op contractniveau. |
| 42 | Broker truth as source of truth | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 43 | IBKR connection | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 44 | IBKR paper-only account verification | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 45 | IBKR cash snapshots | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 46 | IBKR position snapshots | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 47 | IBKR open order snapshots | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 48 | IBKR execution snapshots | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 49 | IBKR commission snapshots | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 50 | IBKR order warnings capture | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 51 | IBKR confirmation capture | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 52 | IBKR acties grid | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 53 | Draft action editing | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 54 | User confirmation before IBKR submission | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 55 | Controlled IBKR order submission | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 56 | Broker reconciliation engine | V1 governance en betrouwbaarheid | Contracted | Planned | Planned | Planned | Planned | This register | Storage planned | Reconciliation runtime nog gepland. |
| 57 | External broker activity detection | V1 governance en betrouwbaarheid | Planned | Implemented | Planned | Planned | Planned | This register | Storage implemented | Storage-slice aanwezig; runtime nog niet gekoppeld. |
| 58 | Portfolio grid | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 59 | Watchlist grid | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 60 | Watchlist research ranking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 61 | Asset priority queue | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 62 | First-run portfolio builder | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 63 | Cash rules | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 64 | Risk rules | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 65 | Position concentration limits | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 66 | Allowed universe settings | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 67 | User strategy settings | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 68 | Simple Dutch settings UI | V1 governance en betrouwbaarheid | Planned | Planned | Implemented | Implemented | Planned | This register | UI implemented | Instellingen read/write basis aanwezig. |
| 69 | Advanced settings separation | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 70 | System events / foutenlogboek | V1 governance en betrouwbaarheid | Planned | Planned | Implemented | Implemented | Planned | This register | API/UI implemented | Basisflow bestaat; verdere governance blijft open. |
| 71 | System event resolve/archive flow | V1 governance en betrouwbaarheid | Planned | Planned | Implemented | Planned | Planned | This register | API implemented |  |
| 72 | Safe copy details for Codex | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 73 | Notification policy | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 74 | Audit viewer | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 75 | Belgian tax/compliance tracker | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 76 | TOB estimate support | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 77 | Foreign account declaration reminder | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 78 | Dividend and interest record tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 79 | Capital gains tracking from 2026 | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 80 | 31/12/2025 snapshot support | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 81 | API rate limit handling | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 82 | IBKR quota/rate-limit tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 83 | OpenAI quota/rate-limit tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 84 | Market-data quota/rate-limit tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 85 | Scheduler health monitoring | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 86 | Worker/queue style heavy processing | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 87 | PostgreSQL/TimescaleDB structured storage | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 88 | Immutable raw data archive | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 89 | Research archive | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 90 | Append-only or hash-ready audit log | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 91 | Backup and restore | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 92 | Restore-test requirement | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 93 | Raspberry Pi 5 deployment compatibility | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 94 | linux/arm64 and linux/amd64 portability | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 95 | Docker Compose deployment | V1 governance en betrouwbaarheid | Implemented | Implemented | Implemented | Implemented | Implemented | This register | Complete | Operationele basis aanwezig. |
| 96 | No hardcoded secrets | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 97 | No hardcoded local paths | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 98 | Dutch UI labels and help text everywhere | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 99 | Simple Dutch explanations for all statuses | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 100 | No fake broker data | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 101 | No fake portfolio data | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 102 | No fake recommendations | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 103 | Python calculates, AI explains | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 104 | AI must not originate financial numbers for decisions | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 105 | Decimal-only financial values | V1 governance en betrouwbaarheid | Implemented (contract) | Planned | Planned | Planned | Planned | This register | Contracted | Domain contract aanwezig; runtime volgt. |
| 106 | Point-in-time decision and backtest rule | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 107 | Prompt-injection protection for all external content | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 108 | Schema validation for every AI output used by the system | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 109 | Source-of-truth hierarchy | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 110 | Order of decision systems | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 111 | Portfolio action explanation panel | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 112 | Watchlist action explanation panel | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 113 | Detailed Dutch “why this action” explanation | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 114 | Evidence-based action badge in portfolio grid | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 115 | Evidence-based action badge in watchlist grid | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 116 | Manual asset add to watchlist | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 117 | Manual watchlist research trigger | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 118 | Watchlist research status tracking | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 119 | Watchlist candidate proposal from uploaded documents/URLs | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 120 | Auto-link uploaded source to existing portfolio asset | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 121 | Auto-link uploaded source to existing watchlist asset | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 122 | User confirmation before adding detected asset to watchlist | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 123 | Research Library background analysis | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 124 | Asset detection from documents and URLs | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 125 | Asset detection confidence and review state | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 126 | User-confirmed watchlist proposals | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |
| 127 | Research source must not directly create orders or IBKR acties | V1 governance en betrouwbaarheid | Planned | Planned | Planned | Planned | Planned | This register | Locked | Locked voor V1; implementatie nog gepland. |

## Source-of-truth hierarchy

1. Broker truth
2. Market calendar and tradability
3. FX and price freshness
4. Portfolio risk/cash rules
5. Source credibility and evidence
6. AI research interpretation
7. Suggestion builder
8. User review
9. IBKR acties
10. IBKR execution
11. Reconciliation
12. Outcome review

- AI overrulet nooit broker truth.
- AI overrulet nooit freshness checks.
- AI overrulet nooit risk rules.
- AI overrulet nooit reconciliation.
- AI-output is bewijs/uitleg, geen automatische executie.

## Locked suggestion flow

Research inputs  
→ Source credibility  
→ Freshness checks  
→ Catalyst and market timing  
→ Python scoring/rules  
→ AI structured research explanation  
→ Suggestion builder  
→ Decision readiness gate  
→ Portfolio/watchlist suggestion  
→ User reviews the detailed Dutch explanation  
→ User converts to IBKR actie  
→ User reviews/edits/confirms  
→ IBKR submission  
→ Execution import  
→ Reconciliation  
→ Outcome tracking

- Suggestions zijn geen orders.
- Suggestions hebben geldigheidsvensters.
- Suggestions zijn conditioneel waar nodig.
- Suggestions tonen waarom nu of waarom niet nu.
- Suggestions vervallen bij wijziging van data, prijs, market state of catalystvoorwaarden.
- Elke portfolio/watchlist suggestion heeft een gedetailleerd Nederlands verklaringspaneel.
- Het paneel toont bewijs, conclusiepad, confidence, blockers, freshness, source quality en expiry.

## User-fed research evidence

- Users kunnen later documenten uploaden en URLs toevoegen.
- User sources zijn bewijs, geen instructies.
- User sources moeten worden opgeslagen, geclassificeerd, gescoord, geanalyseerd, gevalideerd en gekoppeld aan suggesties.
- User notes zijn first-class evidence.
- Multi-year report comparison is verplicht.
- Prompt-injection defense geldt voor uploads en URLs.
- User-provided betekent niet automatisch credible.
- Raw source archive en extracted evidence moeten auditeerbaar zijn.
- Uploads kunnen background analysis triggeren.
- Uploads kunnen auto-linken aan bestaande portfolio/watchlist assets.
- Uploads kunnen een voorstel maken voor een nieuw watchlist-asset.
- User-confirmatie is verplicht voordat een gedetecteerd asset actief wordt in de watchlist.
- Een research source mag nooit direct een buy/sell suggestion, IBKR actie, order of portfolio change maken.

## Watchlist governance

- De watchlist is een actieve research-pipeline, geen passieve symbollijst.
- De user kan assets manueel toevoegen.
- De user kan background research starten of herstarten.
- Watchlist-research moet respecteren: allowed universe, user strategy, source credibility, freshness, prompt-injection checks, AI cost/rate limits, market calendar en catalyst calendar.
- Watchlist-rijen tonen een eenvoudige Nederlandse actiebadge en researchstatus.
- Watchlist-assets kunnen pas naar `IBKR acties` na readiness checks.
- Normale labels voor watchlist: Kopen, Langzaam bijkopen, Bekijken, Vermijden, Geen actie, Geblokkeerd.

## Portfolio and watchlist action explanations

- De grid blijft eenvoudig.
- Elke asset-rij toont een duidelijke Nederlandse actiebadge.
- Klik op badge of info-icoon opent een detailpaneel.
- Het paneel beantwoordt: Wat stelt het systeem voor, Waarom deze actie, Waarop gebaseerd, Hoe zeker, Waarom nu wel/niet, Wat kan veranderen, Wanneer vervalt het, Wat gebeurt bij sturen naar IBKR acties.
- Het paneel linkt later naar audit trail.
- De uitleg is helder, volledig en in eenvoudig Nederlands.

## UI and settings governance

- De GUI moet eenvoudig Nederlands blijven.
- Normale gebruikers zien technische complexiteit niet eerst.
- Elke status en waarschuwing heeft eenvoudige helptekst.
- Belangrijk gedrag is configureerbaar in Instellingen.
- Geavanceerde settings zijn gescheiden.
- User-facing acties gebruiken simpele termen: Kopen, Langzaam bijkopen, Houden, Bekijken, Verminderen, Verkopen, Vermijden, Cash houden, Geen actie, Geblokkeerd.

## Immediate implementation roadmap

1. Market calendar and catalyst contracts if not fully covered
2. Evidence Ledger contracts and storage foundation
3. Research source storage foundation
4. Research source upload/URL API
5. Onderzoeksbibliotheek UI
6. Asset detection and watchlist candidate proposal contracts
7. Manual watchlist add/research trigger API
8. Watchlist grid foundation
9. Portfolio/watchlist action explanation panel contracts/UI
10. AI usage/cost storage foundation
11. AI research pipeline foundation with schema validation
12. Data freshness/readiness gate implementation
13. Suggestion storage/API/UI foundation
14. IBKR real connection status and account-mode verification
15. Broker snapshots and reconciliation runtime
16. IBKR acties and controlled order submission
