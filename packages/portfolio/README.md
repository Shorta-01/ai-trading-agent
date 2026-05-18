# portfolio-outlook-portfolio

Dit package bevat **paper accounting calculation helpers** voor Portfolio Outlook Manager.

## Wat dit package wel is
- Pure Python helperfuncties voor deterministische paper accounting-berekeningen.
- Gebaseerd op domeinprimitives (`Money`, `Quantity`, `CostEstimate`, `PaperTransaction`, `PaperLot`).
- Decimal-only via het gedeelde domain package.

## Wat dit package niet doet
- Geen data-opslag of persistentie.
- Geen brokerverbindingen of order-executie.
- Geen aanbevelingen of tradinglogica.
- Geen AI-calls of promptlogica.
- Geen volledige FIFO-lotselectie.
- Geen taxberekeningen.

## Lokale checks
```bash
cd packages/domain
python -m pip install -e .

cd ../portfolio
python -m pip install -e .[dev]
python -m ruff check .
python -m mypy src
python -m pytest -q
```

## Paper ledger service helpers
- Deze helpers maken gevalideerde paper-transacties en cash-ledger entries aan.
- Geen persistentie en geen database.
- Geen broker-executie en geen echte orders.
- Geen aanbevelingen, geen AI en geen market-data calls.
- Decimal-only accounting via gedeelde domeinprimitives.
- Blijft strikt paper-only voor versie 1.

## Paper portfolio snapshot helpers
- Deze helpers berekenen de actuele paper-state op basis van aangeleverde ledger-records.
- Geen persistentie en geen database.
- Geen market prices en geen valuation.
- Geen aanbevelingen, geen AI en geen broker-executie.
- Decimal-only accounting via domeinprimitives.
- Blijft strikt paper-only voor versie 1.


## Portfolio performance and net result helpers
- Berekent totaalresultaat vanaf dag 1 op basis van aangeleverde paper-records.
- Scheidt extra stortingen van beleggingswinst.
- Scheidt opnames van beleggingsverlies.
- Ondersteunt kosten en geschatte taksen in nettoresultaat.
- `current_positions_value` wordt aangeleverd en niet opgehaald.
- Geen database, geen market prices, geen valuation fetching.
- Geen aanbevelingen, geen AI en geen broker-executie.
- Decimal-only accounting via domeinprimitives.
- Blijft strikt paper-only in versie 1.

## Termijnrekening-berekeningshelpers
- Helpers voor looptijd -> maanden, maturiteitsdatum (kalendermaanden met dag-clamp), bruto intrest, netto intrest en verwachte eindwaarde.
- Helpers voor dagen tot maturiteit, statusafleiding en totalen per valuta.
- Pure, deterministische Decimal-only berekeningen zonder API, DB, broker of AI.

## Capability registry helpers
- Deterministische helperlaag voor capability checks per categorie (watch, research, suggestie, paper order/transaction, portfolio toegang).
- Bevat ook `require_*` guard helpers die geblokkeerde categorieën hard stoppen in backendlogica.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.
\n\n## Task 24A update\nIBKR wordt na koppeling de bron van waarheid voor brokerfeiten; lokale data blijft een spiegel voor analyse en audit. Er is nog geen echte IBKR-integratie in deze versie.
