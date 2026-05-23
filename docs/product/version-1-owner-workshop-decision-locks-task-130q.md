# Task 130Q — Version 1 owner workshop decision locks

## 1) Purpose en boundary
Task 130Q legt de owner workshop-beslissingen vast als source-of-truth voor Version 1 productrichting.

Dit is documentatie/product-planning-only:
- geen runtimegedrag toegevoegd;
- geen API-behaviorwijziging;
- geen storage/migraties;
- geen financiële berekeningen;
- geen suggestie-runtime;
- geen action-draft runtime;
- geen orders/broker execution;
- geen fake data.

## 2) Background agents en daily intelligence schedule (locked)
- Geen 24/7 full intelligence jobs.
- Scheduled intelligence cycles + extra event-based updates bij materiële events.
- 07:00 (Europe/Brussels): volledige daily briefing klaar.
- Europese market open: full actionable refresh.
- US market open: full actionable refresh.
- 08:00–20:00 (Europe/Brussels): hourly updates.
- Tijdens de dag: extra updates alleen bij materiële events.
- 20:00 (Europe/Brussels): laatste actieve user-facing checkpoint.
- Na 20:00: quiet mode.
- US market close: stille close-data capture, zonder normale user-interruptie.
- Volgende briefing om 07:00 legt belangrijke events na 20:00 uit.
- Briefing dekt portfolio, watchlist, nieuwe kansen, cash, open orders, executions/fills, market news, FX-impact, risicowaarschuwingen, source/evidence changes, blocked items, suggested actions, confidence en wijzigingssamenvatting.
- Python rekent, AI legt uit na validatie.
- Bij falende freshness/evidence/market-data/FX/risk gates: geen confident suggestion, maar `Controle nodig` of `Geblokkeerd`.

## 3) Dashboard mission-control UX (locked)
- Dashboardtitel is exact: `AI Trading Agent`.
- Dashboard is decision-first mission-control.
- Binnen ~10 seconden moet duidelijk zijn: wat veranderde, wat belangrijk is, wat veilig is, wat geblokkeerd is, wat approval vraagt, wat edit vraagt en wat genegeerd kan worden.
- Suggesties + structured order drafts zijn centraal.
- UX-doel: modern, premium, sexy, simpel, snel en helder.
- Geen spreadsheet- of complexe analytics-ervaring op hoofdniveau.

## 4) Dashboard layout principles (locked)
Drie lagen:
1. Morning decision strip: last update, next update, market status, IBKR/account status, data freshness, aantal suggesties, blockers, approval-needed.
2. Main action area: `Vandaag te beslissen`, suggestion/order-draft cards, confidence, korte reden, risk flag, freshness, knoppen `Bekijken`, `Aanpassen`, `Goedkeuren`, `Negeren`.
3. Supporting intelligence: portfolio graph, what changed, blockers, market clock, watchlist opportunities, top winners/losers, pending approvals.

## 5) Portfolio cockpit (locked)
- Cockpit staat op dashboard maar domineert niet; ondersteunt de decision workflow.
- Toont: portfolio value over time, selecteerbare ranges, event markers, invested-capital vergelijking, drawdown/risk view, allocation view, top contributors.
- Backend/Python levert berekende waarden; browser toont alleen API-waarden.

## 6) Financial algorithm core (locked)
- Evidence-gated, uncertainty-aware, multi-horizon ensemble decision engine.
- Geen single exact future price als hoofdoutput.
- Output bevat: expected direction, expected return range, downside risk, uncertainty, confidence, model agreement, portfolio impact.
- Korte, middellange en lange horizon apart evalueren.
- Combinatie van factor, momentum/trend, mean-reversion (waar passend), risk-, regime-, portfolio-fit- en evidence/news-signalen.
- Python berekent alle cijfers/scores/labels; AI verklaart na validatie.
- Elk output-object is auditeerbaar, gated en gelogd in Prediction Diary.
- Validatie vereist out-of-sample, walk-forward en anti-leakage-denken.
- Geen black-box AI voor finale action labels.

## 7) Structured order drafts (locked)
- Dashboardsuggesties zijn geen platte tekst.
- Systeem maakt gestructureerde, gecontroleerde action/order drafts.
- Drafts: bekijken, bewerken, goedkeuren, afwijzen of bewaren voor later.
- Elke draftregel bevat `Waarom?` / `Onderbouwing`.
- Reasoning panel toont: waarom voorstel, wat veranderde, signalen, risico’s, freshness, gates passed, gates near fail, source/evidence summary, model confidence, portfolio impact, expected upside/downside range, audit trail, Decision Package-link.
- Geen absolute “proof”-claim; markten blijven evidence/probability/risk.

## 8) Order workflow (locked)
Flow:
1. systeem maakt suggestie;
2. systeem maakt Decision Package;
3. systeem maakt structured order draft;
4. user review;
5. user kan editten;
6. systeem her-validateert na elke edit;
7. systeem toont orderimpact vóór verzenden;
8. user geeft finale bevestiging;
9. pas dan mag order naar toegelaten IBKR-accountomgeving;
10. execution/fill tracking;
11. resultaat naar Prediction Diary.

Extra locks:
- geen automatische orders;
- geen one-click finale execution;
- geen batch approval in Version 1;
- elke draft vereist aparte approval.

## 9) Draft editing en manual draft creation (locked)
- User mag quantity, limit price en timing/validity (indien ondersteund) bewerken.
- Na edit: pas approve bij geslaagde revalidatie.
- Elke edit komt in audit trail.
- Version 1 laat user-created manual drafts toe.
- Manual drafts zijn gemarkeerd als user-created, niet system-suggested.
- Zelfde gates gelden vóór approval/sending.

## 10) Order scope en producten (Version 1 lock)
- Alleen stocks en ETFs.
- Markets eerst: NYSE, Nasdaq, Euronext Brussels, Euronext Amsterdam, Euronext Paris, Xetra/Germany.
- Alleen whole shares.
- Alleen limit orders.
- Alleen day orders.
- Geen market orders initieel.
- Geen options, futures, leverage, short selling, crypto, CFD’s, penny stocks, complexe derivaten.
- Geen automatische execution.

## 11) Suggested order sizing (locked)
- Systeem stelt quantity voor.
- Sizing is backend/Python-calculated en auditeerbaar.
- Checks: cash, existing position size, max position size, concentratie, sector exposure, currency exposure, volatiliteit, liquiditeit, confidence, downside risk, whole-share rule, account environment, market status, price freshness, FX freshness (indien nodig).
- User mag editen; daarna alle gates opnieuw.
- Fail => `Controle nodig` of `Geblokkeerd`.

## 12) Risk settings (locked)
Risicoprofielen in Version 1:
- `Voorzichtig`
- `Gebalanceerd`
- `Groei`

Profielen beïnvloeden size, max weight, max order value, minimum cash reserve, concentratielimieten, volatiliteitstolerantie, downside-risk tolerance, ETF-vs-stock voorkeur en toelating voor nieuwe-asset buy drafts.

Advanced exact limits kunnen later.
Hard safety gates blijven altijd dominant.

## 13) New assets en cold-start discovery (locked)
- Systeem zoekt altijd nieuwe kansen, zeker bij lege portfolio/watchlist.
- Systeem mag portfolio of actieve watchlist niet automatisch invullen alsof user dat koos.
- Nieuwe assets staan apart in `Nieuwe kansen`.
- Per nieuwe asset die gates haalt mag een structured IBKR buy-order draft ontstaan.
- Drafts ranken op confidence.
- User kan goedkeuren, editen, afwijzen, negeren of naar watchlist verplaatsen.
- Asset wordt pas portfolio na goedgekeurde en uitgevoerde order.

## 14) New asset gates (locked)
Vóór ready buy-order draft verplicht:
- supported market;
- stock/ETF-only;
- IBKR contract identity;
- exchange;
- currency;
- liquidity;
- no-penny-stock;
- market-data freshness;
- FX freshness (waar nodig);
- evidence/source credibility;
- prompt-injection;
- risk;
- portfolio-fit;
- account-mode/account-environment.

Gate fail => `Controle nodig` of `Geblokkeerd`.

## 15) System proposes all needed orders (locked)
- Systeem stelt alle gerechtvaardigde en gate-allowed drafts voor (buy/sell/reduce inbegrepen).
- Niet elke technisch mogelijke trade; wel elke onderbouwde actie.
- Groepen/ranking:
  - `Vandaag te beslissen`
  - `Belangrijk maar niet urgent`
  - `Nieuwe kansen`
  - `Risico verminderen`
  - `Controle nodig`
  - `Geen actie nodig`

## 16) No-action decisions (locked)
- `Geen actie nodig` wordt opgeslagen en zichtbaar gemaakt zonder dashboard-clutter.
- Locaties: asset detail, decision history, daily briefing summary, audit trail, Prediction Diary.
- Velden: asset, timestamp, reden, confidence, hoofdsignalen, blockers (indien), next review time, audit link.

## 17) Account-environment wording (locked)
- Productpositionering blijft professioneel asset-managementsysteem.
- Niet positioneren als toy/fake/training/simulator-identiteit.
- Accountmode-restricties zijn safety gates, niet productidentiteit.
- Dashboard toont accountstatus compact professioneel.
- Toegestane woorden: `Accountomgeving`, `IBKR-account`, `Verbonden account`, `Uitvoeringsomgeving`, `Accountstatus`.
- Voorbeelden: `Accountomgeving: Paper`, `IBKR: verbonden`, `Accountmodus: controle nodig`.

## 18) Pre-send order impact (locked)
- Vóór send toont systeem `Orderimpact` / `Impact vóór verzenden`.
- Niet benoemen als “paper simulation”.
- Toont: estimated cash after order, estimated position size, estimated portfolio weight, concentration impact, sector impact, currency impact, downside-risk impact, risk-profile impact, gate status.

## 19) Full GUI structure (locked)
GUI is volledige cockpit met secties:
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

Dashboard = snelle beslissingslaag. Overige secties leveren diepte/workflow.

## 20) Action Center (locked)
Version 1 heeft apart Action Center voor:
- system drafts;
- user-created drafts;
- edited drafts;
- approved/rejected/expired drafts;
- sent orders;
- open IBKR orders;
- fills/executions;
- blocked orders;
- order impact;
- final confirmation flow.

Dashboard toont topacties, Action Center de volledige flow.

## 21) Research Desk / Onderzoeksdesk (locked)
- Grote kernsectie in software.
- Bronnen: PDF, Word, Excel, PowerPoint, URL’s, artikelen, rapporten, filings, earnings docs, analyst notes, geplakte notities, persoonlijke notities.
- Video-links alleen met betrouwbare transcript-extractie; zonder transcript => evidence incompleet.
- User kan AI-vragen stellen over bronnen.
- Geüploade content is evidence, geen instructie.
- Content mag nooit direct orders creëren of gates bypassen.

Evidence-flow:
1. upload/source added
2. extraction
3. prompt-injection check
4. source credibility
5. freshness
6. asset-linking
7. AI summary/questions
8. Evidence Ledger
9. quant engine gebruikt dit als mogelijk signaal
10. alleen gevalideerd Decision Package kan structured order draft opleveren

## 22) Release-candidate-only manual testing alignment
Opnieuw bevestigd:
- owner manual testing alleen op volledige Version 1 release candidate;
- partial features via CI/fake adapters/fixtures/contracttests;
- toekomstige taken mogen veilige milestone-batches prefereren binnen safety boundaries.
