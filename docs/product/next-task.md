# Next Task

## Aanbevolen volgende implementatieslice

**Task 125D (of equivalent): read-only portfolio valuation preparation op basis van duurzame IBKR snapshots.**

Doel:
- expliciete blocked/missing-market-data status toevoegen voor waarderingsvoorbereiding;
- geen market-data runtime, geen suggesties, geen orders, geen fake prijzen;
- safety- en auditgrenzen behouden.

## Waarom nu
Task 126 heeft de lange-termijn algoritmeroadmap vastgelegd. De veiligste directe vervolgstap blijft een kleine foundation-slice dicht bij huidige status (read-only, audit-first, non-runtime unlock).

## Product decision pending (niet in deze taak)
Er is een vastgelegde richtingsconflict-notitie: mogelijk bredere eindrichting dan paper-only versus huidige Version-1 paper-only lock. Dit vereist later een aparte expliciete productbeslissingstaak; geen runtimewijziging nu.
