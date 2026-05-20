# Version 1 Backlog (source of truth)

Statuswaarden: Not started / Contracted / Storage foundation / API foundation / UI foundation / Runtime pending / Complete.

## 1) Onderzoeksbibliotheek / Research Library

- **Status:** In progress (Storage foundation + API foundation + UI foundation; runtime deels pending).
- **Why it matters:** Dit is de primaire user-fed evidence-ingang voor suggestiekwaliteit.
- **Completed/foundation:** metadata-archief, veilige upload, upload-UI, TXT/MD/CSV extractie, UI extractie-trigger + extracted-text status, deterministische documentclassificatie contracts/runtime foundation.
- **Still missing:** PDF/DOCX/XLSX/PPTX extractie, eventuele OCR, prompt-injection runtime scan, source credibility scoring runtime, evidence extraction, multi-year vergelijking-runtime, URL fetching + veilige snapshotting, asset detectie + watchlist proposal flow.
- **Next likely tasks:** prompt-injection runtime scan contract wiring; daarna source credibility/evidence foundations.
- **Safety notes:** Alles blijft “evidence only”; geen directe suggestie/order-generatie.

## 2) Evidence Ledger

- **Status:** Storage foundation.
- **Why it matters:** Suggesties moeten bewijsbaar en navolgbaar blijven.
- **Still missing:** runtime API evidence-items, source→evidence links, credibility/freshness metadata, review-UI, lifecycle, evidence→suggestion links.
- **Next likely tasks:** API foundation voor evidence listing + linking contracts.
- **Safety notes:** Geen advies zonder auditeerbaar bewijs.

## 3) Watchlist

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Watchlist is actieve research-pipeline.
- **Still missing:** storage/API/UI grid, manual asset add, start-research actie, source-linked candidates, user-confirm voor gedetecteerde assets, action badge + explanation panel.
- **Next likely tasks:** watchlist storage/API basis of koppeling met onderzoeksflow.
- **Safety notes:** Geen bypass van gates via manuele toevoeging.

## 4) Portfolio

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Portefeuille is kernweergave voor beslissingen.
- **Still missing:** storage/API/UI grid, gecombineerde asset-rijen, lots in detailweergave, summary cards, Decimal P/L, FX-conversie + freshness, action badge + uitlegpaneel.
- **Next likely tasks:** portfolio storage/API basis.
- **Safety notes:** Geen floatberekeningen; alles auditeerbaar.

## 5) IBKR read-only integratie

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Broker truth is required voor betrouwbare paperstaat.
- **Still missing:** officiële API-methodereview, account mode verificatie, cash/posities/contracts/prices/open orders/executions/commissies, warning capture, rate limits.
- **Next likely tasks:** read-only adapter runtime foundation.
- **Safety notes:** Nog geen order submission.

## 6) IBKR acties / toekomstige paper submission

- **Status:** Not started.
- **Why it matters:** Gecontroleerde brug tussen suggestie en uitvoering.
- **Still missing:** aparte editable IBKR acties-grid, suggestion→action conversie, user edit/confirm, warning capture, paper-only submission gate, execution reconciliatie, audit trail.
- **Next likely tasks:** data model + UI concept voor acties-grid.
- **Safety notes:** Suggestie is nooit automatisch order.

## 7) Market data en calendar

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Geen actionable advies zonder marktstatus/versheid.
- **Still missing:** market calendar runtime, open/closed/half-day/auction/pre-market states, providerkeuze, historical prices, corporate actions, FX-rates, freshness SLA-runtime, stale-data blockers.
- **Next likely tasks:** kalender-provider en freshness checker design; daarna market-data storage foundation.
- **Safety notes:** Geen stale advice.

## 8) Quantitative models

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Python-calculatiekern voor beslissingskwaliteit.
- **Still missing:** technical indicators, volatility/risk/drawdown modellen, valuation/factor modellen, probability ranges, ensemble scoring, backtesting/walk-forward, model confidence, explainable output.
- **Next likely tasks:** eerste model-slice + teststrategie, maar pas na voldoende data/feature foundations.
- **Safety notes:** Elke financiële berekening getest.

## 9) Probabilistic Asset Outlook

- **Status:** Locked doctrine / Runtime pending.
- **Why it matters:** Dit is de kern van de toekomstige forecastlaag: het systeem moet probability/range-based asset outlooks berekenen in plaats van één zogezegd exact toekomstig koersdoel.
- **Source of truth:** `docs/product/probabilistic-asset-outlook-doctrine.md` en `docs/product/probabilistic-outlook-scope-addendum.md`.
- **Still missing:** asset master, market data storage, adjusted/unadjusted price history, FX/freshness, point-in-time data, feature store, forecast target definitions, baseline probability model, backtesting/walk-forward validation, probability calibration, model registry, scenario engine, portfolio-level probability/risk.
- **Next likely tasks:** na prompt-injection/source-credibility/evidence gates: add asset-master and market-data foundations before building any advanced forecast runtime.
- **Safety notes:** Forecasts zijn geen orders; Python/modelcode berekent kansen/ranges; AI legt uit en interpreteert bewijs.

## 10) AI Event Intelligence

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Externe events moeten gecontroleerd in context komen.
- **Still missing:** deep search/news/filing agent, source collection, structured event-signalen, expiry, asset/sector mapping, confidence/relevance scoring, event→suggestion integratie, OpenAI cost tracking, prompt-injection defense runtime.
- **Next likely tasks:** event signal runtime-contract naar API/worker pad.
- **Safety notes:** AI-signalen zijn input, geen directe trades.

## 11) Suggestion Engine

- **Status:** Contracted / Runtime pending.
- **Why it matters:** Dit is de kernwaarde van het product.
- **Still missing:** readiness gates, blocked/conditional suggesties, buy/hold/sell/watch/avoid/cash-hold logica, validity windows, expiry, risk checks, evidence links, quant+AI combinatie, Nederlandse uitleg, action badge/details, outcome tracking.
- **Next likely tasks:** runtime orchestration skeleton + blocked reasons output.
- **Safety notes:** Geen advies zonder kwaliteit/freshness gates.

## 12) Audit viewer

- **Status:** Not started.
- **Why it matters:** Gebruiker/reviewer moet beslisgeschiedenis kunnen reconstrueren.
- **Still missing:** storage/API/UI viewer, data-known-at-time, bronreferenties, calculatietrace, AI-uitlegtrace, user-action trace.
- **Next likely tasks:** audit query API-contract.
- **Safety notes:** Audit is verplicht voor vertrouwen.

## 13) AI cost dashboard

- **Status:** Not started.
- **Why it matters:** Kostenbeheersing en waarde-evaluatie.
- **Still missing:** OpenAI usage, token counts, model, kostenschatting, research value, cost per asset/suggestie/run.
- **Next likely tasks:** cost-metrics storage contract.
- **Safety notes:** Geen verborgen AI-kosten.

## 14) Notifications

- **Status:** Not started.
- **Why it matters:** Belangrijke events zichtbaar zonder spam.
- **Still missing:** beleid, onderscheid user-notificaties vs systeemevents, anti-spam regels.
- **Next likely tasks:** notificatiebeleid als ADR/docs + contract.
- **Safety notes:** Fouten moeten zichtbaar zijn.

## 15) Belgische tax/compliance

- **Status:** Not started.
- **Why it matters:** Informatieondersteuning voor Belgische context.
- **Still missing:** modulefoundation, TOB-schattingen, dividend/rente records, bronheffing, meerwaardetracking vanaf 2026, 31/12/2025 snapshot, accountant export, proof archive.
- **Next likely tasks:** storage/domain basis voor fiscale records.
- **Safety notes:** Informatief; geen vervanging professioneel advies.

## 16) Deployment/backups

- **Status:** Foundation aanwezig, productie-runtime pending.
- **Why it matters:** Betrouwbaarheid en herstelbaarheid.
- **Still missing:** production compose-profiel, restore-geteste backups, encryptie, health checks, Raspberry Pi deployment docs, portable AMD64/ARM64 validatie.
- **Next likely tasks:** backup/restore runbook.
- **Safety notes:** Backup niet vertrouwen zonder hersteltest.

- Task 65 afgerond: prompt-injection runtime scanstatus wiring toegevoegd (opslaan + latest ophalen), met conservatieve blokkade voor suggesties in alle gevallen.
