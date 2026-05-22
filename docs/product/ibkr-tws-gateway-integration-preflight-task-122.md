# Task 122 — IBKR TWS/Gateway integration preflight

## Scope
Task 122 levert alleen preflight/design + read-only sessiestatuscontract. Geen orderruntime, geen live trading, geen automatische acties.

## Bronnen (official/credible)
- IBKR Campus TWS API docs: https://ibkrcampus.com/campus/ibkr-api-page/trader-workstation-api/
- IBKR TWS API connectivity/nextValidId: https://interactivebrokers.github.io/tws-api/connection.html
- IBKR order flow callbacks (design only): https://interactivebrokers.github.io/tws-api/order_submission.html
- IBKR orders/open-order callbacks: https://interactivebrokers.github.io/tws-api/orders.html
- Python Decimal docs: https://docs.python.org/3/library/decimal.html

## Beslissing: API pad
- **Eerste integratiepad: IBKR TWS API via TWS/IB Gateway**, niet Client Portal API.
- Reden: langlopende, callback-gebaseerde status/sync flow (account/positions/open orders/executions/market data) sluit beter aan op worker-gedreven sync met audit trail.
- Client Portal API blijft optioneel voor latere evaluatie, niet voor Task 122.

## Runtime-eigenaarschap
- Aanbevolen: **worker-proces** beheert later de persistente IBKR-verbinding.
- API blijft read-only contract/statuslaag + handmatige trigger-endpoints.
- Geen auto-connect bij startup.

## Paper-only & safety
- Paper-only enforcement blijft hard: account_mode moet paper zijn.
- Bij wrong account mode: status `connected_wrong_account_mode`, sync/actions/orders geblokkeerd.
- Read-only verplicht voor pre-sync fasen.

## Vereiste configuratievelden
- `enabled` (default false)
- `host`
- `port`
- `client_id`
- `readonly` (default true)
- `account_mode` (default paper)
- `market_data_type` (live/frozen/delayed/delayed_frozen via `reqMarketDataType`)
- timeout/retry instellingen (later runtime)

## Geplande read-only sync-calls (latere taken)
1. `reqAccountSummary` (cash/account values)
2. `reqPositions`
3. `reqOpenOrders` / `reqAllOpenOrders`
4. `reqExecutions`
5. `reqMktData` snapshot

## Ordergerelateerde callbacks (alleen design nu)
- `nextValidId`
- `placeOrder`
- `openOrder`
- `orderStatus`
- executions/fills callbacks

## Niet in Task 122
- Geen `placeOrder` runtime
- Geen order-endpoints
- Geen automatische execution; account mode detectie/status verplicht
- Geen scheduler/background fetch runtime

## Foutmapping (NL status)
Voorbeeldmapping:
- `not_configured` → “IBKR niet geconfigureerd”
- `configured_not_connected` → “IBKR geconfigureerd, nog niet verbonden”
- `connected_wrong_account_mode` → “Verkeerde accountmodus”
- `connection_failed` → “Verbinding mislukt”
- `authentication_required` → “Aanmelding vereist”
- `pacing_limited` → “IBKR pacing-limiet bereikt”

## Logging/secrets
- Geen credentials/account secrets in API responses of logs.
- Alleen booleans/statuscodes/veilig NL help-tekst.

## CI/teststrategie zonder echte IBKR
- Contracttests tegen placeholder/disabled implementatie.
- Geen echte TWS/Gateway nodig.
- Geen netwerkafhankelijkheid in unit/API tests.

## Voorwaarden vóór paper-order submission (later)
1. Stabiele sessiebeheerlaag + reconnect/pacing/errorstrategie
2. Read-only sync volledig en auditbaar
3. Cash/risk/safety checks hard enforced
4. Action draft + user approval workflow
5. Daarna pas account-mode-aware (paper/real-money status zichtbaar) LMT submit pad
