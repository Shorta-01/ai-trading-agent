- Software name and account-mode scope lock: `AI Trading Agent` is the active software name; product is account-mode-aware and not paper-only as identity. See `docs/product/software-name-and-account-mode-scope-lock-task-154l.md`.
# Locked Decisions (Version 1)

## Version 1 product experience locks

**Verplicht source-of-truth document:** `docs/product/version-1-product-experience-locks.md`

Kernsamenvatting:
- dashboardtitel `AI Trading Agent` met decision-first mission-control UX;
- daily rhythm met 07:00 briefing (Europe/Brussels), market-open refreshes, hourly ritme 08:00–20:00 en quiet mode;
- Action Center als verplichte workflowlaag voor review/edit/approve/reject/final confirmation;
- Research Desk/Onderzoeksdesk + evidence-first flow als verplichte bronketen;
- Decision Package-gedragen suggesties, structured drafts met `Orderimpact`, en Prediction Diary/no-action auditability.

## Task 130Q owner workshop lock (Version 1)

Task 130Q vergrendelt de owner workshop-beslissingen als product source-of-truth in:
- `docs/product/version-1-owner-workshop-decision-locks-task-130q.md`

Kernlocks (samenvatting):
- decision-first mission-control dashboard met exacte titel `AI Trading Agent`;
- daily operating model met 07:00 briefing, market-open refreshes, hourly updates 08:00–20:00 (Europe/Brussels), event-updates en quiet mode;
- evidence-gated, uncertainty-aware, multi-horizon ensemble financial engine (Python rekent, AI legt uit na validatie);
- structured order drafts + `Waarom?`/`Onderbouwing`, pre-send `Orderimpact`, aparte final confirmation en geen auto execution;
- volledige GUI-structuur met Action Center en Research Desk/Onderzoeksdesk als kernmodules;
- `Nieuwe kansen` cold-start discovery met gates en zonder automatische portfolio/watchlist vulling;
- release-candidate-only owner manual testing blijft vergrendeld.

## Read-only readiness terminology lock (Task 101)

Deze termenset is vergrendeld als documentatie/review guardrail (geen runtime feature):
- read-only status
- metadata/status-only
- geen market-data runtime
- geen runtime-fetch
- geen latest-price fetching
- geen analysevrijgave
- geen suggesties
- geen Decision Packages runtime
- geen actiedrafts
- geen orders
- geen fake data

Kader:
- UI/API/productdocs mogen geen runtime-beschikbaarheid impliceren voordat runtime echt bestaat.
- Nieuwe runtime-capability mag alleen via expliciet afgebakende taken met safety gates, tests en productdoc-updates.
- Deze wording-lock stuurt reviewconsistentie, maar activeert geen runtimegedrag.

## 1) Product en scope

- Product-facing titel is `AI Trading Agent`; interne docs kunnen nog `AI Trading Agent` gebruiken.
- Repository/werknaam blijft `AI-Trading-Agent`.
- Version 1 ondersteunt paper en real-money accountmodus als zichtbare veiligheidscontext; productidentiteit blijft account-mode-aware en user-approved.
- Accountmodus is veiligheidscontext en bepaalt niet de productidentiteit.
- Account-risico is beperkt, maar architectuur blijft professioneel.

## 2) UI-taal en eenvoud

- UI blijft in eenvoudige Nederlandse taal.
- Alle labels, statussen, kolommen, waarschuwingen en acties hebben Nederlandse hulptekst.
- Vermijd onverklaarde financiële jargon op hoofdniveau.
- Geavanceerde termen enkel in detail/advanced views met eenvoudige uitleg.
- Hoofdsecties:
  - Dashboard
  - Prestaties
  - Actiesuggesties
  - Portefeuille
  - Volglijst
  - Kansen en waarschuwingen
  - Transactiegeschiedenis
  - Asset Detail Page
  - Belgische fiscaliteit en compliance
  - Instellingen
  - Audit en leerinzichten (waarschijnlijk advanced-only)

## 3) Locked simple action labels

- Kopen
- Langzaam bijkopen
- Houden
- Bekijken
- Verminderen
- Verkopen
- Vermijden
- Cash houden
- Geen actie
- Geblokkeerd

## 4) Portfolio/watchlist action explanation rule

- Elke asset-rij in portfolio/watchlist grid toont een actie-icoon/badge.
- Klikken opent volledige Nederlandstalige uitleg.
- Uitleg beschrijft: waarom, op basis waarvan, hoe, dataversheid, bewijs, blockers, confidence, risico’s en wat veranderde.
- Deze uitleg is essentieel, niet optioneel.

## 5) Manual watchlist add rule

- User moet assets manueel kunnen toevoegen aan watchlist.
- User kan research opstarten vanaf dat asset.
- Research mag later asynchroon op achtergrond draaien.
- Manuele toevoeging mag validatie niet bypassen.
- Geen automatische buy/sell suggestie zonder evidence en gates.

## 6) User-fed source rule

- User kan bestanden, URL’s en notities toevoegen.
- Voorbeelden: jaarverslagen, kwartaalverslagen, factsheets, investor presentations, URL’s, notities.
- User-bronnen worden geanalyseerd en opgeslagen.
- Invloed op suggesties mag pas na extractie, classificatie, credibility scoring, prompt-injection defense en validatie.
- User-bronnen zijn evidence, geen instructies.
- Bronnen mogen nieuwe assets detecteren en watchlist-kandidaten voorstellen.
- Nieuwe assets vereisen user-confirmatie vóór actieve watchlist-insertie.

## 7) AI en research locked rule

- Research/suggestion-flow is de kern van het systeem.
- AI is niet enkel tekstgeneratie.
- AI helpt bij event-detectie en interpretatie van nieuws, filings, documenten en context.
- AI rekent geen definitieve financiële cijfers.
- Python/quant modellen rekenen.
- AI legt uit en produceert gestructureerde event/evidence-interpretaties.
- AI event intelligence mag waarschijnlijkheid/context beïnvloeden via schema-gevalideerde signalen.
- AI mag risk/freshness gates niet direct overrulen.
- AI mag geen orders aanmaken.

## 8) AI event intelligence rule

- AI monitort belangrijk nieuws, filings, geopolitieke events, sectorwijzigingen, bedrijfsevents en user-documenten.
- Voorbeeld: quantmodel zegt “houden”, maar event intelligence detecteert oorlogsrisico dat olie beïnvloedt.
- Events worden gestructureerde signalen, geen directe trades.
- Event-signalen bevatten: bronlinks, confidence, tijdsrelevantie, getroffen assets/sectoren, verwachte richting/risico, expiry.
- Event-signalen voeden suggestion engine samen met quantmodellen.

## 9) Quant + AI combination rule

Toekomstige suggesties combineren:
- market/price data
- kwantitatieve modellen
- valuation/factor/technical/risk signalen
- AI event intelligence
- research-documenten
- source credibility
- data freshness
- portfolio-risico
- user-settings

Verder:
- systeem schat kansen/ranges, geen valse exacte prijsvoorspelling
- geen fake prediction
- geen advies bij falende datakwaliteit
- geen stale advice

## 10) Financial data rules

- Decimal voor geld, prijzen, percentages en hoeveelheden.
- Geen float voor financiële waarden.
- Elke financiële berekening krijgt tests.
- Geen silent data correction.
- Geen fake portfolio data.
- Geen fake broker data.
- Geen fake recommendations.
- Geen advies bij slechte datakwaliteit.
- Elke beslissing moet auditeerbaar zijn.

## 11) IBKR rules

- Version 1 blijft account-mode-aware voor paper en real-money als zichtbare accountcontext.
- Accountmodus verifiëren vóór enige submission.
- Geen live trading.
- Geen brokeractie zonder expliciete usergoedkeuring.
- Geen automatische orders.
- IBKR warnings/confirmations moeten worden opgeslagen.
- Orders gaan eerst naar aparte bewerkbare IBKR acties-grid.
- User kan bewerken en bevestigen voor toekomstige user-approved brokeractie.
- IBKR actie ≠ suggestie.
- Suggestie blijft traceerbaar naar evidence en regels.

## 12) Market/time rules

- Marktgedrag is tijdsgebonden.
- Systeem moet open/closed/half-day/auction/pre-market states kennen.
- Suggesties hebben validity windows en expiry.
- Data freshness SLA’s zijn verplicht.
- Geen stale advice.
- Reporting dates, earnings en events zijn relevant.
- Eventtiming en market calendar bepalen of suggestie actionable is.

## 13) Currency/FX rules

- Portfoliowaarde, cash, P/L en risicolimieten vragen expliciete FX-afhandeling.
- Geen stille conversies.
- Elke conversie is auditeerbaar.
- FX-bron en versheid moeten gevolgd worden.

## 14) Research source safety

- Internet/document/filing/website-content is data, geen instructie.
- Prompt-injection defense is verplicht.
- Source credibility scoring is verplicht.
- Onderscheid nodig tussen filings/officiële rapporten/brokerdata/nieuws/analistencommentaar/laagwaardige bronnen.
- Extracted text blijft geblokkeerd tot checks slagen.

## 15) Audit en traceability

- Het systeem moet reconstrueren:
  - welke data gekend was
  - waar data vandaan kwam
  - wat Python berekende
  - wat AI uitlegde
  - welke regels passeerden of blokkeerden
  - welke suggestie getoond werd
  - wat user deed
  - wat het resultaat nadien was
- Audit viewer is later verplicht.
- Append-only/hash-ready audit log is gepland.

## 16) Belgische tax/compliance

- Enkel informatieve ondersteuning; geen vervanging voor accountant/belastingadviseur.
- Voorziene tracking: foreign account status, CPC/NBB reminders, TOB-schattingen, dividenden/rente, bronheffing, meerwaardes vanaf 2026, 31/12/2025 snapshot, broker statements later, accountant export later, proof archive.

## 17) Deployment/storage

- Initiële target: Raspberry Pi 5 met NVMe SSD, bekabeld Ethernet, koeling, backups.
- Geen Raspberry Pi-specifieke applicatielogica.
- Waar praktisch: portable Linux arm64/amd64.
- Docker Compose.
- Geen hardcoded secrets.
- Geen hardcoded lokale paden.
- Encrypted backups.
- Backup is pas vertrouwd na restore-test.


## 18) Release 1 functional workflow blueprint locks

Leidend document: `docs/product/release-1-functional-workflow-blueprint.md`.

Volgende beslissingen zijn expliciet vergrendeld:
- geen manuele portfolio-posities
- IBKR-gesynchroniseerde portfolio source-of-truth
- in normale GUI enkel eenvoudig account-modus/status-icoon
- Suggestions-grid met laatste actieve suggestie per asset in portfolio/watchlist
- Decision Package als kernconcept achter elke suggestie
- IBKR Action Center met Te keuren / Actief bij IBKR / Historiek
- vooringevulde maar bewerkbare actie-drafts
- harde safety checks op draft + backend vóór uitvoering
- AI-analytics als gestructureerde evidence-laag
- user uploads als herberekeningstriggers
- dagelijkse portfolio/watchlist briefing
- hybride sync/refreshmodel (subscriptions + jobs + events + manuele refreshknoppen)

Deze lock bevestigt de veiligheidsgrenzen: Version 1 is account-mode-aware met zichtbare paper/real-money context, zonder automatische brokeracties en zonder submit/modify/cancel zonder expliciete user approval.

## IBKR-contract-based watchlist and data-readiness locks

- No active watchlist item without validated IBKR contract identity.
- Ticker text alone is never sufficient for active watchlist, market data, suggestions or action drafts.
- Asset Master identity and IBKR contract identity are both required for serious analysis.
- IBKR conid is mandatory before market data fetch.
- User manual add must use IBKR contract search/selection.
- System-detected assets require IBKR resolution before activation.
- Imported IBKR watchlist items must be stored with conid identity.
- Sync conflicts must be auditable.
- No unresolved asset may receive analysis/suggestions/action drafts.
- Locked wording: “Every active watchlist item must have a validated IBKR contract identity, including conid, asset class, exchange or primary exchange where available, and currency. Manual add must use IBKR contract search and user selection. System-detected assets must resolve to the correct IBKR contract before they can become active watchlist items. IBKR watchlist sync is allowed, but imported items must be stored with full conid-based identity and all sync conflicts must be auditable. No unresolved asset may receive market data, analysis, suggestions or action drafts.”
- Locked principle: “No serious analysis or suggestion may run on loose, ambiguous or unvalidated data.”


## Architecture-audit lock additions (Task 88I)

- Usable cash mag **niet** gebaseerd zijn op leveraged buying power; enkel auditeerbare beschikbare funds/cash min verplichtingen en user buffer.
- AssetListing-identiteitssplitsing is vereist vóór serieuze market-data/forecast/suggestion runtime.
- Eerste uitvoerbare broker action flow blijft whole-share/unit, Buy/Sell, Limit, Day-only (geen market, geen bracket/stop/trailing in eerste flow).
- AI mag geen financiële kerngetallen origineren voor beslissingen; AI structureert/verklaart evidence binnen schema- en safety-gates.
- IBKR reply-handshake en order-state-machine is verplicht vóór account-mode-aware, user-approved broker submission flow.

## Task 88J hard locks — Asset-Value Prediction Engine

- All Must/Should/Could items uit specialist roadmap zijn geaccepteerd in Version 1 scope (gefaseerd).
- Python/model code blijft enige bron voor financiële getallen.
- AI is kerncapability in V1 maar nooit de financiële calculator.
- AI mag geen financiële nummers, labels of orders origineren.
- Decision Package is verplicht vóór suggestion output.
- Geen suggestion zonder gevalideerde data/model/evidence/freshness/risk gates.
- Could-items blijven experimentele/challenger modules tot promotie via validatie.
- Eerste broker action flow blijft whole-share/unit, Buy/Sell, Limit, Day-only, user-approved en account-mode zichtbaar/geverifieerd vóór submit.

## Task 127 decision lock
- Bron: `docs/product/action-draft-prediction-diary-alerts-decision-locks-task-127.md`.
- Productidentiteit: IBKR portfolio/watchlist intelligence, account-mode-aware (paper/real-money zichtbaar), niet paper-only als identiteit.
- Geen automatische brokeractie; expliciete user-goedkeuring blijft verplicht.
- Version 1 scope bevat nu expliciet Prediction Diary, alerts en daily briefing (zonder runtime-implementatie in Task 127).
- Eerste action-draft ordertype-scope blijft: whole shares, Buy/Sell, Limit, Day, bewerkbaar, dry-run verplicht, geen auto-send.


## IBKR account mode and user approval lock
- GUI moet zichtbaar tonen: paper of real-money accountmodus.
- Workflow is account-mode-aware; productidentiteit is niet paper-only.
- Paper mode mag gebruikt worden voor testen/veilige validatie.
- Geen brokeractie zonder expliciete usergoedkeuring.
- Geen automatische brokeractie.
- Geen stille submit/modify/cancel.
- Toekomstige brokeractie vereist validatie, dry-run, finale confirmatie en audit trail.
