# Next Task

## Task 78 — Watchlist foundation and read-only watchlist page (recommended)

Bouw een conservatieve watchlist foundation en read-only Volglijst-pagina met manuele watchlist-items, duidelijk gescheiden van IBKR-portfolio-posities.

### Waarom nu

- Na Task 77 is de Portefeuille nu zichtbaar op basis van read-only IBKR snapshots.
- De volgende veilige workflowstap is een aparte watchlist voor researchprioriteiten zonder ordergedrag.

### Scope voor Task 78

- Storage/API/UI foundation voor manueel beheerde watchlist-items.
- Read-only Volglijst-grid met eenvoudige Nederlandse empty/error/loading states.
- Duidelijke scheiding tussen IBKR-owned portfolio-posities en lokale watchlist-items.

### Niet doen in Task 78

- Geen echte IBKR-connectieruntime.
- Geen ordersubmission, orderwijziging of ordercancel.
- Geen action drafts of IBKR Action Center runtime.
- Geen suggesties, Decision Packages, AI runtime, market-data runtime of forecast runtime.
- Geen fake broker/portfolio/order/execution/suggestiedata.
