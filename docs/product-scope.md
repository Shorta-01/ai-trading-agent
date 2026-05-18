# Product Scope

## Productdoel
Portfolio Outlook Manager ondersteunt gebruikers bij professionele, auditeerbare paper-beleggingsbeslissingen met eenvoudige Nederlandse uitleg.

## Scope versie 1
- Alleen paper portfolio.
- Startkapitaal instelbaar, standaard €10.000 EUR.
- Actiesuggesties, monitoring, logging, audit en prestatie-opvolging.
- Geen live broker-executie, geen real-money orders.

## Productmodi
### 1) First-run Portfolio Builder Mode
Bij lege portfolio: opbouwplan met gefaseerde inzet (max 50-60% initieel), minimale cashreserve van 40%, focus op beperkte set liquide kernassets.

### 2) Normal Portfolio Review Mode
Periodieke evaluatie van bestaande paper-portfolio, watchlist, kansen, risico en no-action discipline (zoals “Geen actie”, “Houden”, “Cash houden”).

### 3) Intraday Opportunity Watcher
Gerichte monitoring van belangrijke assets en signalen (standaard elke 15 minuten), met gerichte heranalyse bij triggers.

### 4) Weekly Deep Discovery
Wekelijkse diepgaande discovery van nieuwe kwaliteitskandidaten en watchlist-opschoning.

### 5) Monthly Performance Review
Maandelijkse evaluatie van rendement, benchmarkvergelijking, risico en kwaliteit van aanbevelingen.

## UI-principe: eenvoudige Nederlandse interface
De hoofdinterface gebruikt eenvoudige termen en vermijdt onverklaarde vakjargon op hoofdniveau.

## Vereiste voor niet-expert gebruiker
De interface moet ook voor een niet-expert begrijpelijk zijn met duidelijke Nederlandse hulpteksten per veld/status/actie.

## Mijn termijnrekeningen (nieuw, paper-only)
- Aparte portefeuillezone: **Mijn termijnrekeningen** voor manueel ingegeven termijnrekeningen.
- Dit zijn contractgebaseerde assets (geen marktverhandelde posities).
- Ondersteunde standaardlooptijden: 1 maand, 3 maanden, 6 maanden en 1 jaar.
- Blijft apart zichtbaar van ETF's, aandelen en valuta in de UI, maar telt wel mee in totale portefeuillewaarde en performance vanaf dag 1.

## Asset capability registry (nieuw)
- Backend hanteert per categorie een capabilitystatus: **Toegestaan**, **Alleen opvolgen**, of **Geblokkeerd**.
- Toegestaan in versie 1: cash, termijnrekeningen, UCITS ETF, aandelen, FX, benchmark-data en commodity ETF/ETC.
- Alleen opvolgen: futures, opties, leverage, short selling, crypto, penny stocks, complexe derivaten en high-frequency trading.
- Geblokkeerd: automatische real-money uitvoering als systeemcapability.
- Watch-only of geblokkeerde categorieën mogen voor context/educatie gevolgd worden maar mogen geen papieren orders, transacties of portefeuilleposities aanmaken in versie 1.
- Grondstoffenblootstelling is alleen toegestaan via eenvoudige gereguleerde ETF/ETC-producten; directe futures en complexe/geleveragde commodityproducten blijven geblokkeerd.
