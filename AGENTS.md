# Development Guardrails

## Product safety boundaries
- Version 1 is paper-only.
- Do not implement live trading.
- Do not add broker execution in version 1.
- Do not add IBKR live order flow.

## Architecture and implementation rules
- No business logic in UI.
- No hardcoded secrets.
- No hardcoded tickers in core logic.
- No Raspberry Pi-specific application logic.
- Do not add external API calls without documented adapter and test strategy.

## Data, audit, and reliability rules
- No silent data correction.
- Every decision must be logged.
- No advice without audit trail.
- All data must be backed up and restorable.
- A backup is not trusted until restore is tested.
- Jobs must be idempotent.
- Scheduled job failures must be visible.

## AI and calculation rules
- Every financial calculation must have tests.
- Every AI output must be schema-validated.
- AI may not override risk rules.

## UI language and clarity rules
- Keep UI Dutch and simple.
- Every UI field must have simple Dutch help text.
