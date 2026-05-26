# 0008 — Adopt the action-draft architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/action-draft-state-machine.md`, `docs/intent/dashboard-and-order-flow.md`, doctrine §4, §5, §15.

## Context

T-018 (`action-draft-composition-and-approval.md` reality) needed answers to several coupled questions:

1. What are the action-draft states, and what transitions are allowed?
2. What safety guards must run, when, and which are hard-blocks vs soft-warns?
3. What is the retry policy for transient submission failures?
4. How are recoverable vs unrecoverable rejections distinguished?
5. What is the bulk behaviour (approve / reject / cancel)?
6. What happens to a draft the user edits before approving?
7. What happens to a draft that sits unactioned for too long?

The existing Task 133, 134, 135 product locks answer some of these in scattered places; this decision consolidates them into a single intent surface plus the new bulk-behaviour and edit-as-override semantics surfaced during the review.

## Decision

Adopt the action-draft architecture defined in `docs/intent/action-draft-state-machine.md` (canonical source) and reflected at UX-surface level in `docs/intent/dashboard-and-order-flow.md` §4.3 and §4.4:

- **State machine:** `drafted` → `user-approved` → `submitting` → `ibkr-acknowledged` → `parked` (hand-off to Open orders grid). Terminal branches: `user-rejected`, `withdrawn-by-system`, `failed`.
- **Eleven safety guards** (A–K). Hard-block vs soft-warn classification. Evaluated at creation AND at submission; **submission-time evaluation is authoritative**. Every block audit-logged.
- **Retries:** up to 3 attempts with exponential backoff (1s / 4s / 16s).
- **Recoverable vs unrecoverable rejection** classification is configurable in Category 3 settings; default for unknown codes is unrecoverable (fail closed).
- **Auto-withdrawal** of drafts > 24h in `drafted`.
- **Bulk behaviour:** individual approve / submit; bulk reject / cancel allowed with single shared reason and batch audit event.
- **Edit-as-override:** both original system value and user-edited value recorded per field.

## Alternatives considered

- **Approve-all bulk action.** Rejected: defeats the per-ticket review intent of the two-grid model.
- **Silent overwrite on edit** (just store the user's value). Rejected: violates AGENTS.md "every decision must be logged" — the system-proposed value is information; recording both is essentially free.
- **Unlimited retries on transient failures.** Rejected: a stuck submission would loop forever. 3 attempts + audit failure is the right blast radius.
- **Hard mapping of every IBKR rejection code in v1.** Rejected: the code space is large and IBKR adds new codes. Configurable mapping with fail-closed default is more resilient.

## Consequences

- T-018 reality describes existing action-draft code against this intent.
- T-026 reality (`user-approve-action-draft.md`) walks the UX flow including bulk reject.
- Rejection-classification mapping initial population remains open (doctrine §15) — to be filled during T-018 reality.
- The submission-authoritative-guard principle is a hard rule the worker submission sweep (per Task 134) must respect.
