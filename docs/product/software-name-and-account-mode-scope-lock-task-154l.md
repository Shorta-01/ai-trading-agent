# Task 154-L — Software name and account-mode scope lock

## 1. Purpose
This lock corrects repository source-of-truth wording so future tasks consistently use the right software identity and account-mode scope.

## 2. Owner correction
Owner correction accepted and locked on 2026-05-24.

## 3. Software name lock
- Software name: `AI Trading Agent`.
- Repository/project name: `AI-Trading-Agent`.
- `Portfolio Outlook Manager` is legacy/internal/historical only and must not be used as active user-facing software name.
- Future user-facing UI, docs, and task titles use `AI Trading Agent`.

## 4. Account-mode-aware product identity
AI Trading Agent is an account-mode-aware IBKR decision-support and action workflow system.

## 5. Paper mode as safety/testing context, not product identity
- The product is not a paper-only simulator or paper-only product.
- Paper mode is a safety/testing/development context.
- Current implementation slices may still be paper-gated until account-mode verification and action-safety gates are complete.

## 6. Real-money wording boundary
- Real-money account context can be visible as account environment context.
- This task does not implement real-money execution.
- Any expansion requires explicit safety gates, tests, docs, and owner approval.

## 7. Broker action safety boundary
Any broker action remains blocked unless the account environment is verified, all gates pass, the user reviews the action draft, and the user gives explicit final approval.

## 8. Automatic execution prohibition
No automatic broker execution is allowed.

## 9. Required terminology going forward
- account-mode-aware
- paper mode / paper account context
- real-money account context
- account environment
- verified account mode
- user-approved broker action
- manual final confirmation
- paper-gated implementation slice
- disabled-by-default runtime
- no automatic execution

## 10. Terms to avoid
Avoid blanket product wording like:
- paper-only software/product
- paper simulator / training simulator / fake trading system
- only paper trading
- Version 1 is paper-only (as product identity)

## 11. Documents updated
- `AGENTS.md`
- `README.md`
- product source-of-truth docs in `docs/product/*` listed in Task 154-L

## 12. Recommended next task
Task 155 — Add real IBKR account-mode-aware read-only account snapshot preflight for cash and positions without persistence or valuation.

Core wording lock:

AI Trading Agent is an account-mode-aware IBKR decision-support and action workflow system. It is not a paper-only simulator. Paper mode is a safety and testing context, not the product identity. Any broker action remains blocked unless the account environment is verified, all gates pass, the user reviews the action draft, and the user gives explicit final approval. No automatic broker execution is allowed.
