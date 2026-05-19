# ADR 0002: IBKR source-of-truth and broker sync schema planning

- Status: Accepted
- Date: 2026-05-18

## Context
AI-Trading-Agent is paper-only in version 1, but the system already defines IBKR as the future broker integration boundary and requires strict auditability, point-in-time reconstruction, and explicit reconciliation behavior. The current storage foundation only includes `paper_portfolio_setups`, `paper_cash_accounts`, and `audit_events`.

Task 24A established the architecture rule that IBKR becomes the source of truth for broker-side facts after connection. Task 24B now needs an implementation-ready schema design for broker mirror and reconciliation storage before any migration is created.

## Decision
1. IBKR is the source of truth for broker-side facts once connected.
2. AI-Trading-Agent stores a local broker mirror for analysis, audit, explanation, and suggestion gating.
3. Broker sync data must be stored as point-in-time snapshots with explicit timestamps (`imported_at`, `observed_at`, `checked_at`, `detected_at` depending on table role).
4. Direct IBKR activity that was not initiated by AI-Trading-Agent must be represented explicitly as external broker activity.
5. Reconciliation differences must be stored explicitly and must not be silently corrected.
6. Blocking or critical reconciliation differences must block suggestions.
7. The next storage migration will add broker sync and reconciliation tables for accounts, sync runs, snapshots, reports, differences, and external activity.
8. No schema migration is implemented in this PR.

## Consequences
- The next migration PR can implement broker-sync schema without ambiguity.
- Source-of-truth behavior is preserved: broker facts are mirrored, not replaced by local assumptions.
- Suggestion safety can later depend on reconciliation outcomes and stale snapshot detection.
- Audit links and source references are designed now so later runtime features remain traceable.
- This PR introduces no runtime persistence, no IBKR API calls, and no credentials handling implementation.

## Alternatives considered
- **Local portfolio as source of truth:** rejected because it can drift from real broker facts and weakens reconciliation discipline.
- **Manual-only portfolio tracking:** rejected because it cannot guarantee traceable broker-fact parity once broker integration exists.
- **Import only current positions without executions:** rejected because missing execution and commission context harms auditability and difference diagnosis.
- **Store broker data without reconciliation reports:** rejected because mismatch handling would remain implicit and unsafe for suggestions.
- **IBKR as source of truth with local mirror and reconciliation:** chosen because it supports auditability, explicit mismatch handling, and safe suggestion gating.

## Follow-up tasks
1. Create the next Alembic migration revision implementing the planned broker sync tables.
2. Add SQLAlchemy metadata mappings for the new tables in `packages/storage`.
3. Add repository interfaces and adapters for broker sync snapshots and reconciliation records.
4. Add validation and checks for stale snapshot detection and suggestion-blocking behavior.
5. Add IBKR configuration/status persistence fields (without storing secrets) and bootstrap preview flow.
6. Add broker snapshot import adapter skeleton and reconciliation engine foundation.
