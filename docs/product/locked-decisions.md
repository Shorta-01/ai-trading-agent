# Locked Decisions (Version 1)

## 1) Product en scope

- Portfolio Outlook Manager is de productnaam.
- Ai Trading Agent is de repository/werknaam.
- Version 1 is paper-only.
- Paper-only verzwakt de functionele ambitie niet.
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

- Version 1 verbindt enkel met IBKR paper account zodra runtime bestaat.
- Accountmodus verifiëren vóór enige submission.
- Geen live trading.
- Geen real-money execution.
- Geen automatische orders.
- IBKR warnings/confirmations moeten worden opgeslagen.
- Orders gaan eerst naar aparte bewerkbare IBKR acties-grid.
- User kan bewerken en bevestigen voor toekomstige paper-executie.
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

Deze lock wijzigt geen bestaande veiligheidsgrenzen: Version 1 blijft paper-only, zonder live trading, real-money execution of automatische orders.
