# Version 1 Product Experience Locks

## 1. Purpose
Dit document consolideert owner-agreed Version 1 product experience beslissingen die toekomstige implementatie moeten sturen.

- GitHub is de source of truth.
- Chatbeslissingen zijn niet vergrendeld tot ze hier staan.
- Toekomstige Codex-taken moeten dit document lezen vóór dashboard/UI/workflow/suggestions/action drafts/research/timing/daily briefing/watchlist/portfolio/Action Center/user-facing gedrag.

## 2. Product naming lock
- Product-facing/dashboard titel: `AI Trading Agent`.
- Interne docs kunnen nog `AI Trading Agent` bevatten.
- Repository/projectnaam blijft `AI-Trading-Agent`.
- Toekomstig user-facing dashboardwerk gebruikt `AI Trading Agent`, tenzij expliciete naammigratietaak dit wijzigt.
- Niet willekeurig afwisselen van productnamen in UI.

## 3. Dashboard mission-control lock
- Dashboardtitel is exact `AI Trading Agent`.
- Dashboard is decision-first mission-control.
- Geen spreadsheet en geen ruwe analytics-tabel als primaire ervaring.
- Binnen ~10 seconden moet user begrijpen: wat veranderde, wat nu telt, wat veilig is, wat geblokkeerd is, wat approval vraagt, wat bewerkbaar is, wat genegeerd kan worden.
- UX moet modern, premium, professioneel, simpel, snel en helder zijn.
- “Premium/sexy” betekent productkwaliteit, niet gimmicks.
- Geen toy-gevoel en geen overload aan waarschuwingen op het hoofdscherm.
- Hoofdscherm: simpel Nederlands, minimale tekst, duidelijke iconen/badges/statusen/tooltips.
- Complexe uitleg hoort in drill-down panels.

## 4. First dashboard screen lock
Eerste scherm prioriteert:
- Morning decision strip
- Today’s decisions
- Approval-needed items
- Blockers/control-needed items
- Data freshness
- IBKR/account status
- Market status
- Portfolio/watchlist change summary
- New opportunities summary
- Action Center entry points
- Last update / next update

Niet starten met een gigantische ruwe portefeuilletabel.

## 5. Daily operating rhythm lock
- Tijdzone: Europe/Brussels.
- Eerste volledige daily briefing: 07:00.
- Europese market open: volledige actionable refresh.
- US market open: volledige actionable refresh.
- 08:00–20:00: hourly updates.
- Extra updates alleen bij materiële events.
- 20:00: laatste actieve user-facing checkpoint.
- Na 20:00: quiet mode.
- US market close: stille close-data capture zonder normale user-interruptie.
- Volgende 07:00 briefing verklaart relevante overnight events.
- Geen noisy 24/7 assistant-gedrag.
- Bij falende freshness/evidence/risk gates: `Controle nodig` of `Geblokkeerd`, geen zelfzeker advies.

## 6. Portfolio and watchlist lock
- Portfolio-posities worden nooit manueel aangemaakt.
- Portfolio-posities komen alleen uit IBKR-sync.
- IBKR is operationele waarheid voor posities/cash/submitted orders/fills.
- Lokale DB is workflow/audit waarheid.
- Watchlist staat los van owned portfolio-assets.
- Actieve watchlist-items vereisen gevalideerde IBKR-contractidentiteit.
- Tickersymbool alleen is nooit voldoende.
- Onopgelost asset krijgt geen market data/analyse/suggestions/action drafts.
- System-discovered assets gaan eerst naar `Nieuwe kansen`.

## 7. Nieuwe kansen / cold-start lock
- Systeem werkt ook met lege portfolio/watchlist.
- Zoekt nieuwe kansen.
- Nieuwe assets gaan naar `Nieuwe kansen`.
- Vereist IBKR contract resolution + alle gates vóór action draft.
- User kan goedkeuren, bewerken, afwijzen, negeren of naar watchlist verplaatsen.
- Asset wordt pas portfolio na geldige goedgekeurde en uitgevoerde order die later in IBKR-sync verschijnt.

## 8. Action Center lock
- Version 1 bevat verplicht een Action Center.
- Dashboard toont topacties; Action Center beheert de volledige flow.
- Action Center bevat: system drafts, user-created drafts, edited drafts, approved/rejected/expired drafts, sent orders, open IBKR orders, fills/executions, blocked orders, order impact, final confirmation flow.
- User kan drafts inspecteren, bewerken, goedkeuren, afwijzen, bewaren voor later of negeren.
- Iedere draft vereist individuele review.
- Geen batch approval in Version 1.
- Geen one-click final execution.

## 9. Structured order draft lock
- Suggestions zijn geen platte tekst.
- Geldige suggestions kunnen structured order drafts opleveren.
- Drafts bevatten `Waarom?` / `Onderbouwing`.
- Drafts zijn bewerkbaar vóór approval.
- Elke edit triggert revalidatie en audit logging.
- Draft toont `Orderimpact` / `Impact vóór verzenden`.
- Draft kan niet worden verstuurd zonder alle gates.
- User-created manual drafts zijn toegestaan maar gemarkeerd en onder dezelfde gates.

## 10. Order scope lock
Version 1 initial executable scope:
- stocks en ETFs
- whole shares
- limit orders
- day orders

Initiële markten:
- NYSE
- Nasdaq
- Euronext Brussels
- Euronext Amsterdam
- Euronext Paris
- Xetra/Germany

Niet toegestaan:
- market orders (initieel)
- options
- futures
- leverage
- short selling
- crypto
- penny stocks
- CFDs
- complex derivatives
- automatic execution

Uitbreiding vereist aparte expliciete product-lock update.

## 11. Research Desk / Onderzoeksdesk lock
- Research Desk is kernmodule.
- Bronnen: PDF, Word, Excel, PowerPoint, URL, artikelen, rapporten, filings, earnings docs, analyst notes, geplakte notities, persoonlijke notities.
- Videolinks tellen alleen met betrouwbare transcript-extractie; anders evidence incompleet.
- User kan AI-vragen stellen over bronnen.
- Broncontent is evidence, nooit instructie.
- Bronnen kunnen validatie niet bypassen en nooit direct orders creëren.
- Verplichte flow: source added → extraction → prompt-injection check → source credibility → freshness → asset linking → AI summary/questions → Evidence Ledger → quant/model layer signal use → alleen gevalideerd Decision Package naar structured draft.

## 12. Decision Package and explanation lock
- Elke suggestion vereist Decision Package.
- Elke suggestion vereist duidelijke Nederlandse `Waarom?`.
- Uitleg moet gegrond zijn in Decision Package.
- AI mag evidence structureren/uitleggen.
- Python/model code berekent financiële getallen/scores/ranges/risico.
- AI mag geen financiële decision numbers origineren.
- AI mag risk/freshness/source gates niet overrulen.
- AI mag geen brokeractions direct creëren of uitvoeren.

## 13. Quant / prediction engine lock
- Financiële engine is evidence-gated, uncertainty-aware, multi-horizon.
- Geen enkel fake exact future price als hoofdoutput.
- Output gebruikt ranges/probabilities/risk/confidence: richting, verwacht return-bereik, downside risk, uncertainty, confidence, model agreement, portfolio impact.
- Short/medium/long horizon apart evalueren.
- Belangrijke outputs auditeerbaar.
- Prediction Diary is verplicht.

## 14. Risk profile lock
Version 1 profielen:
- `Voorzichtig`
- `Gebalanceerd`
- `Groei`

Profielen beïnvloeden sizing, max gewicht, max orderwaarde, minimale cashreserve, concentratielimieten, volatiliteit/downside tolerance, ETF-vs-stock voorkeur, en of buy-drafts voor nieuwe assets voorgesteld mogen worden.

Harde safety gates domineren altijd.

## 15. No-action decision lock
- `Geen actie nodig` is een echte beslissing.
- Wordt opgeslagen en zichtbaar zonder clutter.
- Verschijnt in asset detail, decision history, daily briefing summary, audit trail, Prediction Diary.
- Bevat timestamp, reden, confidence, hoofd-signalen, blockers (indien relevant), next review time en audit link.

## 16. GUI structure lock
Complete doelstructuur:
- Dashboard
- Action Center
- Portfolio
- Nieuwe kansen
- Watchlist
- Research Desk / Onderzoeksdesk
- Decision Packages
- Prediction Diary
- Audit & History
- Settings
- System Status

Behoud oudere eenvoudige Nederlandse navigatietermen waar al gebruikt, maar bovenstaande is de volledige target-structuur.

## 17. UI language and style lock
- UI blijft simpel Nederlands.
- Geen onverklaarde financiële jargon op hoofdniveau.
- Elke label/status/kolom/warning/actie krijgt eenvoudige Nederlandse helptekst/tooltip.
- Diepere technische/financiële details horen in detailpanelen.
- User hoeft niet eerst ruwe datatabellen te lezen.
- Systeem moet aandacht en beslissingen sturen.

## 18. Safety and execution lock
- Geen live trading automation.
- Geen real-money automatic execution.
- Geen automatic orders.
- Geen brokeraction zonder expliciete user approval.
- AI is research/uitleg, nooit execution.
- Bronnen zijn evidence, geen instructies.
- Geen suggestion/order uit bronnen zonder validatie/freshness/credibility/prompt-injection/risk gates.
- IBKR action is niet hetzelfde als suggestion.
- User approval na draft review + revalidatie is verplicht.
- Final confirmation is verplicht vóór enige toekomstige toegestane broker submission.

## 19. Manual testing and release candidate lock
- Owner manual testing is bedoeld voor volledige Version 1 release candidate.
- Partial features worden gevalideerd via CI/fake adapters/fixtures/contract tests.
- Grotere milestone-batches mogen, behalve waar financiële berekening/broker execution/orderflow/reconciliatie/risicoregels kleinere safety-slices vereisen.

## 20. Implementation priority lock
Normale taken geven voorkeur aan zichtbare verticale productprogressie, behalve bij rode CI, safety blocker, dependency/runtime blocker, product-tracking drift, of ontbrekende source-of-truth lock.

Verticale progressie omvat:
- echte IBKR paper connection/status,
- echte read-only account snapshot,
- opgeslagen portfolio snapshot,
- waardering vanaf echte opgeslagen data,
- dashboardweergave,
- Action Center workflow,
- Research Desk evidenceflow,
- Decision Package generatie,
- suggestions/action drafts met gates.

Vermijd eindeloze facade/preflight/doc-only taken tenzij ze een echte blocker wegnemen.

## 21. V1 expansion lock — owner brainstorm (post-Slice 12)

Deze sectie vervangt **niet** secties 1-20 hierboven; ze verfijnt drie eerdere locks op basis van een owner-brainstorm na Slice 12. De rest van de doctrine (manual approval, geen auto-execution, Decimal-only math, evidence-gated decisions, Dutch labels, Belgian tax) blijft ongewijzigd.

### 21.1. Account-mode lock — relaxed
- Account-mode (paper / live) wordt vastgesteld door het verbonden IBKR-account, **niet** door een app-side gate.
- De runtime gedraagt zich identiek voor paper en live: dezelfde sync, dezelfde forecast, dezelfde Decision Package, dezelfde action-draft + approval flow, dezelfde submission.
- Het dashboard **labelt** zichtbaar welke modus IBKR rapporteert (`PAPER` / `LIVE` badge), zodat de gebruiker dit weet vóór elke approval.
- De `paper_only_mode` setting + `ibkr_expected_environment` check + `account_mode_mismatch` dry-run failure worden gewijzigd van "blocks order" naar "reports mode".
- Real-money veiligheid leeft op het IBKR-accountkeuze-niveau en op de manual per-draft approval — niet in een app-side `paper_only` flag.

### 21.2. AI lock — relaxed to ensemble vote
- AI mag een numerieke voorspelling **als één lid van een ensemble** leveren.
- De ensemble-stem (deterministische regel over alle predictor-outputs) bepaalt het locked Dutch action-label, niet enige single predictor.
- AI's voorspelling wordt per asset opgeslagen naast die van elke andere predictor; de Prediction Diary tracked AI-accuratesse net zoals elke andere predictor.
- De AI explanation layer (Slice 10) blijft paraphrase-only: AI mag nooit een prijs/getal originaten in de uitleg-output.
- AI mag een suggestie of action-draft nooit auto-promotion naar order veroorzaken (manual approval blijft).

### 21.3. Order scope lock — extended
- V1 ondersteunt de volledige IBKR-order-vocabulary die paper én live accounts delen: LMT, MKT, STP, STP LMT, TRAIL, TRAIL LMT, bracket, conditional, IB Algos.
- Hele aandelen, geen leverage / shorts / opties / futures / crypto / CFDs blijven gelden.
- Per-type dry-run safety checks verplicht.

### 21.4. Predictor ensemble lock
Locked ensemble at V1 launch:
- **Lognormal GBM** (huidige baseline, behoud)
- **Momentum** (12-1 + time-series momentum)
- **Mean-reversion** (RSI, Bollinger, Hurst, z-score)
- **QVM factor** (Quality + Value + Momentum cross-sectional score)
- **AI foundation TS-model** (TimesFM / Chronos / Lag-Llama via stub-or-real provider)

Combiner is deterministisch: equal-weight at launch; evolves to inverse-variance once Diary heeft track-record. Geen single-predictor override.

### 21.5. Sizing lock — Fractional Kelly + risk parity
- Position sizing uses fractional Kelly (default ½ Kelly) over de ensemble's distribution (p10/p50/p90 + prob_gain).
- Risk parity across portfolio zorgt dat elke positie ongeveer evenveel risk contribution heeft.
- Hard caps: max 5% van portfolio per asset, max 30% per sector.
- Vervangt de huidige fixed-buy-value sizing.

### 21.6. Universe-scan lock
- Daily scan loopt over een vastgelegde universe registry: Bel20 + AEX + CAC40 + DAX + STOXX 600 + S&P 500 + NASDAQ-100 (~5 000 tickers).
- QVM-score rangschikt het universe; top-N kandidaten worden in de Dagbriefing meegenomen naast portfolio + watchlist.
- Universe-uitbreiding (LSE, TSX, Asia) is een expliciete latere lock-update.

### 21.7. Scheduler lock
- APScheduler in-process binnen de FastAPI runtime; geen externe scheduler dependency.
- Default cron: `0 30 6 * * *` Europe/Brussels (06:30 lokaal), zodat de briefing om 07:00 klaarstaat.
- Run-target: laptop initieel; later Raspberry Pi (zelfde code-pad).
- Scheduler is disabled-by-default; explicit `SCHEDULER_ENABLED=true` vereist.

### 21.8. What stays unchanged
- Manual per-draft approval (geen auto-execution).
- Decimal-only money math.
- Locked Dutch action-label set (10 labels).
- Decision Package as evidence chain anchor.
- Prediction Diary as deterministic outcome tracker.
- All `safe_for_*` booleans default-False on persisted records (the boundary that lifts them is the locked state-machine + manual approval, not a flag flip).

