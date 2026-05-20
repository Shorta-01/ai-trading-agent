# Next Task

## Task 77 — Portfolio read-only grid from IBKR snapshots (recommended)

Bouw een read-only portefeuillegrid die uitsluitend de opgeslagen IBKR snapshots toont (posities, cash, open orders, executions/fills), met eenvoudige Nederlandse UI en auditvriendelijke timestamps.

### Waarom nu

- Task 75 en Task 76 leveren read-only broker snapshots maar de gebruikerswaarde in de portefeuilleweergave is nog beperkt.
- Een conservatieve read-only grid levert zichtbare waarde zonder ordergedrag of suggestion-runtime.

### Scope voor Task 77

- Read-only portefeuille-overzicht vanuit bestaande snapshot-opslag.
- Duidelijke empty/error states en sync-timestamp weergave.
- Geen bewerkbare rijen en geen orderknoppen.

### Niet doen in Task 77

- Geen ordersubmission, orderwijziging of ordercancel.
- Geen action drafts of IBKR Action Center runtime.
- Geen suggesties, Decision Packages, AI runtime, market-data runtime of forecast runtime.
- Geen fake broker/order/execution data.
