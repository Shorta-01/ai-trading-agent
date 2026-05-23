# Release 1 Functional Workflow Blueprint

## 1) Release 1 product intent

Terminologieguardrail: pre-runtime wording blijft vergrendeld via `docs/product/locked-decisions.md` (sectie **Read-only readiness terminology lock (Task 101)**); dit document beschrijft target-state workflow, geen reeds actieve runtime.


Release 1 is geen gedeeltelijke demo. Release 1 is pas compleet wanneer de volledige workflow end-to-end werkt.

Complete workflowdoel voor Release 1:

IBKR account synchroniseren  
→ portfolio- en watchlist-assets analyseren  
→ auditeerbare suggesties genereren  
→ vooringevulde maar bewerkbare actie-drafts maken  
→ alleen expliciet user-goedgekeurde acties naar IBKR sturen  
→ IBKR-status opvolgen  
→ portfolio/cash opnieuw synchroniseren  
→ volledige auditgeschiedenis bewaren.

GUI-principe:
- De GUI blijft eenvoudig en professioneel in het Nederlands.
- Geen “toy”-gevoel en geen constante waarschuwingstaal op hoofdniveau.
- Normale modus toont enkel een eenvoudige account-modus/status-icoonweergave.

## 2) Portfolio source-of-truth rule

- Portfolio-posities kunnen niet manueel toegevoegd worden.
- Portfolio-posities komen alleen uit IBKR-sync.
- IBKR is operationele waarheid voor:
  - posities
  - cash
  - ingediende orders
  - executions/fills
- Lokale database is workflow- en auditwaarheid voor:
  - suggesties
  - Decision Packages
  - actie-drafts
  - user-edits
  - approvals
  - submitted action records
  - status snapshots
- User wijzigt portfolio door in IBKR te handelen en daarna opnieuw te synchroniseren.
- Systeem moet IBKR-wijzigingen detecteren bij sync.

## 3) Watchlist rule

- De actieve Volglijst moet IBKR-contract-based zijn.
- Elke actieve watchlist-item moet een gevalideerde IBKR-contractidentiteit hebben met minstens:
  - `ibkr_conid`
  - `symbol`
  - `asset class`
  - `exchange` of `primary exchange` waar beschikbaar
  - `currency`
  - `validation status`
  - `validation timestamp`
- Exacte lock: “Every active watchlist item must have a validated IBKR contract identity, including conid, asset class, exchange or primary exchange where available, and currency. Manual add must use IBKR contract search and user selection. System-detected assets must resolve to the correct IBKR contract before they can become active watchlist items. IBKR watchlist sync is allowed, but imported items must be stored with full conid-based identity and all sync conflicts must be auditable. No unresolved asset may receive market data, analysis, suggestions or action drafts.”
- Watchlist-assets mogen manueel toegevoegd worden via dit verplichte pad:
  - IBKR contract search
  - user selecteert exact contract
  - Asset Master link/create path
  - pas dan actief watchlist-item
- System-detected assets starten als kandidaten en mogen pas actief worden na geslaagde IBKR-contractresolutie.
- Ambigue of onopgeloste gedetecteerde assets mogen nooit actieve watchlist-items worden.
- Onopgeloste assets mogen geen market data, analyse, suggesties of action drafts ontvangen.
- Tickertekst alleen is nooit voldoende identiteit voor actieve watchlist, analyse of acties.
- IBKR watchlist import/export is later toegestaan, maar altijd conid-based en auditeerbaar.
- Sync mag geen automatische deleties doen; conflicts moeten zichtbaar en veilig oplosbaar zijn.
- Watchlist-assets blijven gescheiden van werkelijk aangehouden portfolio-assets.
- Watchlist sell-acties mogen enkel wanneer IBKR op dat moment effectief een positie toont.

## 4) IBKR portfolio sync and broker data

Minimale Release 1 syncset:
- actuele posities
- contract-identiteit
- hoeveelheid
- gemiddelde aankoopprijs (indien beschikbaar)
- cash/account values
- actieve orders
- executions/fills

Verder te onderzoeken en documenteren in een latere taak:
- lot-level data en buy/sell history via IBKR API, Flex Queries, statements of andere officiële route.

Omdat IBKR-data op elk moment kan wijzigen:
- sync-timestamps zijn verplicht
- status-timestamps zijn verplicht.

## 5) Suggestions structure

- Suggesties zijn zelfstandige auditeerbare objecten in een aparte Suggestions-grid.
- Portfolio- en Watchlist-rijen tonen per asset de laatste actieve hoofdsuggestie.
- Suggestions-grid bevat:
  - Actief
  - Verlopen
  - Historiek
- Asset Detail-pagina toont alle suggesties, Decision Packages, evidence, acties en audit trail voor dat asset.
- Meerdere suggesties per asset zijn toegestaan; grid-rijen tonen enkel de belangrijkste actieve suggestie.

## 6) Decision Package core concept

Decision Package is een kernconcept van Release 1.

- Een suggestie is niet enkel een icoon.
- Elke suggestie moet gedragen worden door een Decision Package.
- Decision Package bevat minstens:
  - asset
  - IBKR position snapshot
  - cash en usable-cash snapshot
  - market data snapshot
  - historische prijs-/risicometrics
  - portfolio exposure
  - source evidence
  - AI news/event signals
  - AI risk/opportunity signals
  - AI conflict signals
  - AI dissent check
  - model output
  - risk checks
  - suggested action
  - suggested order draft
  - expiry
  - Nederlandse uitleg
  - audit links
- Decision Packages zijn auditeerbaar en geversioneerd.

## 7) Suggestion quality and explanation

Elke suggestie bevat minstens:
- action label
- confidence
- data quality
- freshness
- risk
- blockers
- expiry
- wat veranderde sinds de vorige suggestie

Uitlegregel:
- Elke suggestie heeft een duidelijke “Waarom?”-uitleg.
- Uitleg moet gegrond zijn in het Decision Package.
- Uitleg mag geen nieuwe feiten verzinnen.

## 8) IBKR Action Center

IBKR Action Center bevat vier tabbladen:
- Systeemvoorstellen
- Mijn eigen orders
- Actief bij IBKR
- Historiek

Gedragsregels:
- Geblokkeerde draft-acties blijven in Te keuren met duidelijk blokkade-icoon en uitleg.
- Te keuren-rijen zijn bewerkbaar tot indiening.
- Actief bij IBKR-rijen zijn vergrendeld en volgen IBKR-status.
- Historiek-rijen zijn read-only met finale status (submitted/cancelled/rejected/filled/expired).
- Alle aangemaakte acties worden lokaal bewaard voor audit en workflow-continuïteit.
- Na submission blijft IBKR operationele waarheid.

## 9) Prefilled action drafts

Vanuit een geldige systemsuggestie kan de user een IBKR-actie-draft maken.

Draft wordt vooringevuld met:
- asset
- buy/sell-richting
- quantity
- order preset
- IBKR order type
- limiet-/trigger-/stop-prijsvelden
- timing
- expiry
- reden
- safety-check status

Regels:
- User mag draft bewerken of verwijderen vóór uitvoering.
- Elke edit herberekent safety checks.
- Audit logt zowel oorspronkelijke systemdraft als user-edits.
- Draft wordt nooit automatisch uitgevoerd.

## 10) Supported human order presets

Belangrijke scope-opmerking: deze sectie beschrijft een toekomstige preset-catalogus. De eerste uitvoerbare user-approved action flow blijft strikt LMT-only. Market orders, bracket orders, stop orders, trailing orders en conditionele orderpresets zijn niet toegestaan in de eerste uitvoerbare flow. Latere uitbreiding van orderpresets vereist aparte validatie, safety gates, user-approval workflow en expliciete product-lock update.

Bedoelde eenvoudige menselijke presets in de toekomstige catalogus:
- Buy with limit price.
- Sell with limit price.
- Buy if price drops to X.
- Sell if price rises to X.
- Sell if price falls to X.
- Execute after date/time.
- Expire after date/time.

Aanvullend:
- Market order hoort niet bij de eerste uitvoerbare flow en is in Release 1-initiële uitvoering niet toegestaan.
- Eventuele market-order ondersteuning kan pas in latere fase na aparte validatie en expliciete product-lock update.
- UI gebruikt eenvoudige presets en vertaalt deze naar gevalideerde IBKR-ordervelden binnen de actieve scope-lock.

## 11) Execution workflow

Volledige workflow:

Suggestion  
→ user maakt vooringevulde actie-draft  
→ draft verschijnt in Te keuren  
→ user bewerkt/verwijdert/keurt goed  
→ safety checks draaien overal  
→ user klikt uitvoeren  
→ backend hercontroleert safety  
→ actie wordt naar IBKR gestuurd  
→ rij wordt vergrendeld  
→ IBKR-status update rij  
→ portfolio-sync ververst posities/cash  
→ finale status verschijnt in Historiek  
→ audit trail blijft volledig.

## 12) Safety checks

Harde checks:
- Buy value mag user max-buy-transactielimiet niet overschrijden.
- Buy value mag usable IBKR cash niet overschrijden.
- Sell quantity mag IBKR-positiehoeveelheid niet overschrijden.
- FX moet vers zijn bij valuta-verschil.
- Account status/mode moet gekend zijn.
- Data freshness moet slagen.
- Zowel draft-checks als backend-checks moeten slagen.

Checks draaien wanneer:
- draft gecreëerd wordt
- user draft wijzigt
- sync cash/posities/orders wijzigt
- settings wijzigen
- vlak voor uitvoering

Faalde checks blokkeren uitvoering.

## 13) Usable cash

Definitie usable cash:

IBKR available cash  
minus actieve buy-orders  
minus goedgekeurde/ingediende maar niet-finale buy-acties  
minus optionele user cash buffer.

Regel:
- Buy-readiness gebruikt usable cash, niet enkel ruwe cash.

## 14) Sync and refresh model

Release 1 gebruikt een hybride refreshmodel:
- IBKR-subscriptions waar nuttig
- scheduled jobs voor cash, posities, open orders, statussen, executions, market data, history en suggestion expiry
- event-driven herberekening bij IBKR-wijzigingen, market-wijzigingen, uploads, bronverwerking, AI-analytics, settings en tijd

Manuele knoppen:
- Synchroniseren met IBKR
- Data vernieuwen
- Suggesties opnieuw berekenen
- Alles opnieuw berekenen

Regel:
- Draft-statussen moeten automatisch updaten na sync of settingswijzigingen.

## 15) AI analytics layer

AI is in Release 1 een gestructureerde analytics-laag, geen black-box trading brain.

AI-modules:
- News Monitor
- Filing & Report Analyzer
- Source Credibility Analyzer
- Conflict Detector
- AI Dissent Checker
- Explanation Writer

AI-outputs:
- AI Source Analysis
- AI Evidence Signal
- AI Event Signal
- AI Risk Signal
- AI Opportunity Signal
- AI Conflict Signal
- AI Dissent Signal
- AI Explanation Draft

Voor elke AI-output geldt:
- source-linked
- evidence-linked waar mogelijk
- asset-linked waar mogelijk
- schema-valid
- geversioneerd
- getimestamped
- auditeerbaar
- geblokkeerd voor suggesties tot gates slagen

AI mag niet:
- orders creëren
- naar IBKR submitten
- gates bypassen
- prijzen verzinnen
- probabiliteiten verzinnen
- portfolio-waardes verzinnen
- finale financiële waardes berekenen
- geüploade tekst als instructies gebruiken

## 16) User uploads as first-class triggers

Upload-workflow:

Upload  
→ extractie  
→ classificatie  
→ prompt-injection scan  
→ credibility check  
→ AI source analysis  
→ evidence creation  
→ asset linking  
→ event/conflict detectie  
→ betrokken suggesties stale markeren  
→ Decision Packages herberekenen  
→ actie-drafts hervalideren.

Bij materiële impact moeten betrokken suggesties/actiedrafts naar:
- Controle nodig
- Geblokkeerd
- Verlopen
- of herberekende actieve suggestie.

## 17) Daily portfolio/watchlist briefing

Dagelijkse briefing bevat:
- wat vandaag veranderde
- getroffen portfolio/watchlist-assets
- gewijzigde suggesties
- actie-drafts die review nodig hebben
- gedetecteerde risico’s/kansen
- bronnen/evidence die de verandering veroorzaakten
- links naar bron, evidence, AI-signaal, Decision Package, suggestie en actie-draft.

## 18) Release 1 acceptance workflow

Release 1 is niet compleet totdat deze keten werkt:

IBKR sync  
→ portfolio geladen  
→ market data geladen  
→ geüploade/user-source kan verwerkt worden  
→ AI analytics-signalen gemaakt  
→ Decision Package gemaakt  
→ suggestie gegenereerd  
→ suggestie zichtbaar in Portfolio/Watchlist en Suggestions-grid  
→ vooringevulde actie-draft gemaakt  
→ user bewerkt draft  
→ safety checks slagen  
→ user voert uit  
→ IBKR ontvangt actie  
→ IBKR-status update  
→ fill/execution geregistreerd  
→ portfolio opnieuw gesynchroniseerd  
→ actie in Historiek  
→ audit trail volledig.

## 19) Implementatiestatus (duidelijkheid)

Deze blueprint beschrijft vergrendelde functionele ontwerpwaarheid voor Release 1.

- Dit document claimt niet dat deze runtime-functionaliteit al bestaat.
- Deze workflowonderdelen blijven implementatiewerk voor toekomstige taken.
- Task 73 in deze PR is documentatie-only en start geen runtime-implementatie.

## 20) Staged internal execution path (Task 88J, documentation-only)

Release 1 workflow wordt intern gefaseerd: V1.0 foundations → V1.1 baseline forecasting → V1.2 AI text-to-feature → V1.3 challengers → V1.4 AI uitleg/RAG → V1.5 dissent challenger → V1.6 monitoring/drift → V1.7 Decision Package + deterministic translator → V1.8 account-mode-aware user-approved broker action workflow.

Runtime-regel: suggestions, action drafts en user-approved brokeracties blijven geblokkeerd tot V1.7 gates + Decision Package bestaan en gevalideerd zijn. Zie `docs/product/asset-value-prediction-engine-roadmap.md`.

## 21) Task 130Q daily operating model lock

Dagritme (Europe/Brussels):
- 07:00 volledige briefing;
- Europese market open refresh;
- US market open refresh;
- elk uur updates tussen 08:00 en 20:00;
- extra updates alleen bij materiële events;
- 20:00 laatste actieve checkpoint + quiet mode;
- US close capture gebeurt stil; volgende 07:00 briefing verklaart late events.

## 22) Task 130Q dashboard → Action Center execution flow lock

Verplichte flow: Dashboard beslissing → Action Center draftbeheer → `Orderimpact` / `Impact vóór verzenden` → final confirmation → pas daarna user-approved brokerverzending. Geen one-click execution, geen batch approval en geen auto-execution in Version 1.

## 23) Task 130Q new-asset cold-start flow lock

Nieuwe kansen blijven apart van portfolio/watchlist en vereisen volledige gates (identity, market, liquidity, freshness, evidence, prompt-injection, risk, portfolio fit, account environment) vóór een ready buy-draft. Zonder geslaagde gates alleen `Controle nodig` of `Geblokkeerd`.

## 24) Task 130Q Research Desk evidence flow lock

Research Desk/Onderzoeksdesk ondersteunt documenten/URL’s/notities als evidence-input. Evidence doorloopt extraction, prompt-injection check, credibility, freshness en asset-linking vóór gebruik in quant-engine signalering. Geüploade content is nooit directe orderinstructie en kan geen gates bypassen.
