# Next Task

## Task 125F — Read-only vervolg: opgeslagen FX snapshot-contract inventaris en readiness-koppeling zonder runtime fetch

Task 125E heeft cash/FX readiness metadata toegevoegd aan valuation readiness, maar zonder FX-rate opslag of conversieberekening.

Volgende veilige slice:
- documenteer en implementeer alleen read-only detectie van eventueel bestaande opgeslagen FX-rate snapshots (indien aanwezig in storage-contracten);
- geen FX runtime fetch, geen market-data runtime, geen suggestions/action drafts/orders;
- behoud expliciete Geblokkeerd/Controle nodig status wanneer FX-input ontbreekt.
