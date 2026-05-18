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
