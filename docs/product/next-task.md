# Next Task

## Task 125E — Read-only vervolg: waarderingsstatus verrijken met cash/FX readiness zonder runtime fetch

Task 125D leverde read-only portfolio valuation readiness op basis van duurzame IBKR snapshots met expliciete blocking bij ontbrekende of verouderde marktdata.

Volgende veilige slice:
- read-only cash/FX readiness velden toevoegen aan hetzelfde contract;
- geen market-data runtime, geen suggestions, geen action drafts, geen orders/execution;
- ontbrekende inputs expliciet als Geblokkeerd/Controle nodig blijven tonen.
