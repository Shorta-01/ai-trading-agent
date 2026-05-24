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
