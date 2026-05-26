# Development Guardrails

> **Top-level doctrine:** `docs/intent/_trading-system-doctrine.md` (locked 2026-05-26; adoption record: `docs/decisions/0002-trading-system-doctrine.md`).
> Where this file conflicts with the doctrine, the doctrine wins.

## Product safety boundaries
- AI Trading Agent is a full trading system that submits user-approved orders to IBKR (paper or real-money account, treated identically). See doctrine §1–§3.
- The system never submits an order without explicit user approval. The two-grid / two-approval lifecycle (suggested grid → IBKR parked → market) defined in doctrine §4 is mandatory.
- IBKR is the single source of truth for positions, cash, orders, and fills (doctrine §2). The system never holds an authoritative state that contradicts IBKR.

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
