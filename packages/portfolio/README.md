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
