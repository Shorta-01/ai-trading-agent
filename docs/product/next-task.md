## Task 75: IBKR portfolio sync engine foundation (recommended)

Doel: na de UI-foundation van Task 74 een conservatieve, read-only IBKR portfolio sync-basis bouwen met audit-first gedrag.

### Waarom nu

- Task 74 leverde een moderne dashboard-shell met veilige empty states, maar runtime-data ontbreekt nog.
- Release 1 blueprint vereist IBKR als operationele waarheid voor posities/cash/orders/executions.
- Zonder sync-engine blijft dashboardinformatie terecht “niet beschikbaar”.

### Scope voor Task 75 (toekomstig)

- Read-only IBKR sync foundation voor posities/cash/accountwaarden en sync-timestamps.
- Audit logging en zichtbare foutstatussen voor mislukte sync-runs.
- Geen orderflow, geen submissions, geen live trading, geen automatische acties.

### Niet doen in Task 75

- Geen market-data runtime.
- Geen suggestion/AI runtime.
- Geen Decision Packages.
- Geen ordergedrag of action drafts.

# Next Task

## Task 76 — IBKR executions/open-orders sync foundation (read-only)

Bouw de volgende conservatieve stap: read-only opslag en API voor executions/fills + open-orders status, zonder order submission.
