# portfolio-outlook-domain

Dit package bevat alleen **gedeelde domeincontracten** voor Portfolio Outlook Manager.

## Wat dit package wel is
- Gevalideerde Pydantic-modellen en enums.
- Stabiele data-structuren voor API, workers en auditopslag.
- Financiële primitieve types op basis van `Decimal`.

## Wat dit package expliciet niet doet
- Geen tradinglogica.
- Geen AI-calls of promptlogica.
- Geen brokerintegratie.
- Geen database- of ORM-code.

## Waarom `Decimal`
Geld, aantallen, prijzen en percentages gebruiken `Decimal` om afrondingsproblemen van `float` te vermijden.

## Tests lokaal draaien
```bash
cd packages/domain
python -m pip install -e .[dev]
python -m ruff check .
python -m mypy src
python -m pytest -q
```

## Paper ledger and accounting contracts
- Alleen contracten (datavormen en validatie), geen accounting engine.
- Nog geen FIFO-verkoopallocatie-algoritme.
- Nog geen database/ORM-opslag.
- Geen broker-executie.
- Paper-only afbakening blijft actief.
- Financiële waarden blijven Decimal-only via `Money`, `Quantity` en `Percentage`.
