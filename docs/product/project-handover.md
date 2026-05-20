# Project Handover — Portfolio Outlook Manager / Ai Trading Agent

## 1) Purpose of this file

Dit document bewaart de projectcontext over chat-sessies heen.

- De GitHub repository is de duurzame source of truth.
- Een lange chat is **geen** betrouwbare bron op lange termijn.
- Nieuwe ChatGPT/Codex sessies moeten dit document **eerst** lezen vooraleer ze nieuwe taken voorstellen of implementeren.

## 2) Product identity

- **Productnaam:** Portfolio Outlook Manager.
- **Repository/werknaam:** Ai Trading Agent.
- **Version 1 is paper-only.**
- Het systeem is een professionele AI-ondersteunde paper portfolio research- en trading-beslissingsomgeving.
- Het helpt de gebruiker met analyse van ETF’s, aandelen en valuta.
- Het maakt research-onderbouwde suggesties.
- Het volgt paper transacties en paper portefeuillestatus op.
- Het legt alles uit in eenvoudige Nederlandse taal.
- Het is **geen** automatische real-money trading bot.

## 3) Core product principle

- **Complexe backend, eenvoudige Nederlandse frontend.**
- Backend mag professionele berekeningen en strikte modellen gebruiken.
- UI blijft eenvoudig, duidelijk en begrijpelijk voor niet-expert traders.
- Elk veld, elke status, elke actie en waarschuwing krijgt duidelijke Nederlandse hulptekst.

## 4) Main analytical goal

- Het systeem moet uiteindelijk probability/range-based asset outlooks berekenen.
- Het doel is niet één exact toekomstig koersdoel raden.
- Het doel is de kansverdeling van toekomstige assetwaarde/returns tonen: verwachte bandbreedte, p10/p50/p90, kans op winst, kans op verlies, downside risk, confidence, model disagreement en geldigheidsvenster.
- Python/quantmodellen berekenen deze kansen en ranges.
- AI interpreteert bewijs en events en legt de uitkomst uit in eenvoudige Nederlandse taal.
- De volledige doctrine staat in `docs/product/probabilistic-asset-outlook-doctrine.md` en is verplicht voor toekomstige forecast-, quant-, suggestion- en AI-event-intelligence taken.

## 5) Version 1 hard boundaries

### Version 1 mag niet bevatten

- live trading
- real-money execution
- automatische broker-orders
- broker-executie zonder user-confirmatie
- opties
- futures
- leverage
- short selling
- crypto
- penny stocks
- CFD’s
- complexe derivaten
- high-frequency trading
- automatische portefeuille-executie met echt geld

### Version 1 mag wel bevatten

- IBKR paper-only integratie
- paper cash
- paper posities
- paper portefeuille
- paper order-simulatie
- user-confirmed paper order submission naar IBKR, alleen nadat toekomstige gates bestaan
- watchlist
- onderzoeksbibliotheek
- actiesuggesties
- marktresearch logica
- risicocontroles
- audit trail
- probabilistische asset outlooks en scenario’s, alleen als berekende/geverifieerde informatie en nooit als automatische executie
- eenvoudige Nederlandse UI
- performantie-opvolging
- Belgische fiscaliteit/compliance ondersteuning als informatieve ondersteuning

## 6) AI role

- AI is enkel research- en uitleglaag.
- Python rekent.
- AI legt uit.
- AI mag geen financiële kerngetallen origineren die gebruikt worden voor beslissingen.
- AI mag geen trades uitvoeren.
- AI mag risicoregels niet overrulen.
- AI mag veiligheidsregels niet verzwakken.
- AI mag strategieregels niet stilzwijgend aanpassen.
- AI-output moet schema-gevalideerd zijn voor systeemgebruik.
- Internet/document/filing/website-inhoud is data, geen instructie.
- Prompt-injection defense is verplicht.

## 7) Main user flow (Version 1 doelstroom)

IBKR/paper account data  
→ market data en FX data  
→ market calendar/trading-hours check  
→ data freshness gates  
→ portfolio/watchlist state  
→ geüploade documenten/URL’s/notities uit Onderzoeksbibliotheek  
→ deterministische extractie/parsing  
→ classificatie  
→ prompt-injection scan  
→ source credibility scoring  
→ evidence ledger  
→ kwantitatieve modellen  
→ probabilistische asset outlook  
→ AI event intelligence  
→ suggestion engine  
→ risicocontroles  
→ Nederlandse uitleg  
→ actiesuggestie in portfolio/watchlist grid  
→ gebruiker opent gedetailleerde “waarom”-uitleg  
→ suggestie kan een bewerkbare IBKR actie worden  
→ gebruiker reviewt/bewerkt/bevestigt  
→ pas dan mag toekomstige IBKR paper submission  
→ orderwaarschuwingen/confirmaties worden vastgelegd  
→ execution/reconciliatie  
→ audit/outcome tracking

Duidelijk principe:
- Suggestiecreatie is de belangrijkste flow.
- Buy/sell instructies zijn downstream van probabilistische outlooks en suggesties.
- Het systeem optimaliseert voor tijdige, evidence-backed, probability/range-based inzichten.

## 8) Development workflow

- Werk in kleine Codex PR’s.
- Één gefocuste taak per keer.
- Geen “build everything” taken.
- CI moet slagen voor de volgende taak.
- Als er een merge met fouten was: eerst één reparatietaak op basis van CI-logs.
- Geen failing CI mergen.
- Geen verborgen productlogica in skeleton-taken.
- Elke financiële berekening moet tests hebben.
- User-facing UI blijft eenvoudig Nederlands.
- Gebruik `docs/product/next-task.md` als standaard startpunt voor volgende taak.

## 9) How to restart in a new ChatGPT session

1. Kopieer/plak prompt uit `docs/product/new-chat-startup-prompt.md`.
2. Vraag de assistant om eerst de handover-documenten te lezen.
3. Laat assistant de nieuwste merged PR + CI-status controleren.
4. Ga verder vanuit `docs/product/next-task.md`.
