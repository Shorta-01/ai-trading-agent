# IBKR API research (Task 47)

## Reviewed official documentation
- IBKR API software home: https://interactivebrokers.github.io/
- IBKR developer documentation home: https://www.interactivebrokers.com/en/index.php?f=24356
- IBKR Web API docs: https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-doc/
- IBKR Web API v1.0 docs (Client Portal API): https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/
- IBKR TWS API docs: https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/
- TWS account summary docs: https://interactivebrokers.github.io/tws-api/account_summary.html

## Web API vs TWS API
- **Web API**: HTTP-based API family (Web API umbrella, Client Portal API lineage, OAuth direction) suitable for service-style integration and explicit endpoint contracts.
- **TWS API**: socket/event-driven API through TWS or IB Gateway, suited for low-latency streaming workflows and stateful client session handling.

## Suitability for Ai Trading Agent
- Web API is likely a strong fit for backend services that need explicit read/write HTTP contracts.
- TWS API is likely stronger when continuous streaming behavior and event callbacks are required.
- Final choice remains staged: the internal adapter must allow either implementation without changing product logic.

## Required system capabilities for later phases
- account discovery
- account status and session status
- account mode verification (paper vs live)
- cash values (total cash, settled cash, buying power, net liquidation)
- positions
- open orders
- executions/trades and commissions
- market data
- order preview/what-if where available
- controlled order placement
- session health checks
- structured error handling and mapping

## Constraints and implementation notes
- Session/auth requirements differ per API mode and must be validated in spike implementation.
- Market data access depends on account permissions/subscriptions.
- Some values are snapshot-like and cadence/update timing must be verified endpoint-by-endpoint.
- Account access can differ for individual vs advisor/introducing structures.
- Version 1 safety boundary remains paper-only account usage.
- Infrastructure dependency is explicit: Client Portal Gateway/TWS/IB Gateway may be required depending on final approach.

## Open questions before real API calls
1. Which exact endpoint set is authoritative for account mode confirmation in our account type?
2. Which flow is operationally safer in production: Web API path first or TWS path first?
3. What heartbeat/session health signal is most reliable for blocking order actions?
4. Which market-data permission indicators should map to `missing_permission` vs `blocked`?
5. What is the precise refresh cadence we can guarantee for cash/positions/orders/executions?
6. What error categories must trigger immediate order-blocking in risk controls?
7. Which order preview/what-if functionality is available for the selected path?

## Task 47 boundary confirmation
- No real IBKR HTTP calls implemented.
- No TWS/Gateway client instantiation implemented.
- No credential storage added.
- No order submission implemented.
