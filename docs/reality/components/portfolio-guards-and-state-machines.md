# `packages/portfolio` — guards and state machines

**Phase:** 1a (reality components)
**Task:** T-002
**Scope:** eleven modules in `packages/portfolio/src/portfolio_outlook_portfolio/` that gate access to suggestions, approvals, submissions, paper setup, storage writes, AI explanations, and broker reconciliation; the canonical action-draft state machine; and the package's error hierarchy.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `approval_guards.py` — final-decision check + approved-action builder.
- `suggestion_guards.py` — eligibility + data-quality predicate/require pair.
- `suggestion_engine_guards.py` — candidate-ready + draft-ready guards.
- `execution_guards.py` — execution-mode defaults table + availability check.
- `storage_guards.py` — storage-readiness predicate/require pair.
- `paper_setup_guards.py` — setup-request and preview safety.
- `ai_explanation_guards.py` — output validation including hallucination scan.
- `broker_reconciliation_guards.py` — reconciliation-allows-suggestions gate.
- `action_draft_safety.py` — sizing + orderimpact + dry-run safety checks.
- `action_draft_state_machine.py` — locked 13-state transition table.
- `errors.py` — package exception hierarchy.

The recurring idiom in this group is the **predicate / require pair**: every `require_X` raises, every `check_X` returns bool. Two modules (`ai_explanation_guards.py`, `action_draft_safety.py`) instead return a result dataclass with a `status`/`blocking_reason`/`failures`. `action_draft_state_machine.py` raises its own `InvalidStateTransitionError` (a `ValueError` subclass), not part of the package error hierarchy.

## `approval_guards.py` — final-decision check + approved-action builder

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/approval_guards.py`

### Public surface

- `is_approval_decision_final(decision)` (`:14-21`) — five terminal members: `APPROVED`, `REJECTED`, `EXPIRED`, `BLOCKED`, `WITHDRAWN`.
- `require_approved_decision(*, request, decision)` (`:24-30`) — cross-link by `approval_request_id`, decision must be `APPROVED`, target mode cannot be `BLOCKED_AUTO`.
- `build_approved_action(*, request, decision)` (`:33-51`) — kw-only; constructs `ApprovedAction`. Accepts `PENDING` or `APPROVED` request status (idempotent rebuild allowed). `approved_at` is `decision.decided_at` or wall-clock `datetime.now(UTC)` (`:50`).

### Collaborators

`ApprovalDecision`, `ApprovalDecisionStatus`, `ApprovalRequest`, `ApprovedAction`, `ExecutionMode` from `portfolio_outlook_domain`; `InvalidAccountingInputError` from `.errors`.

### Notable choices

- Three hard-blocks in `require_approved_decision`: request mismatch, non-APPROVED decision, `BLOCKED_AUTO` target (`:25-30`).
- The wall-clock fallback on `approved_at` is the only impurity in any guard module in this group.

```python
# approval_guards.py:24-30
def require_approved_decision(*, request: ApprovalRequest, decision: ApprovalDecision) -> None:
    if decision.approval_request_id != request.approval_request_id:
        raise InvalidAccountingInputError("Approval request mismatch")
    if decision.decision != ApprovalDecisionStatus.APPROVED:
        raise InvalidAccountingInputError("Approval decision must be approved")
    if request.target_execution_mode == ExecutionMode.BLOCKED_AUTO:
        raise InvalidAccountingInputError("blocked_auto is never approvable")
```

## `suggestion_guards.py` — eligibility + data quality

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/suggestion_guards.py`

### Public surface

- `check_suggestion_eligible(check)` / `require_suggestion_eligible(check)` — `ELIGIBLE` or `ELIGIBLE_WITH_WARNINGS` both treated as eligible (`:11-20`).
- `check_data_quality_allows_suggestions(gate)` / `require_data_quality_allows_suggestions(gate)` — delegates to `portfolio_outlook_domain.gate_allows_suggestions` (`:23-31`).

### Collaborators

`DataQualityGate`, `SuggestionEligibilityCheck`, `SuggestionEligibilityStatus`, `gate_allows_suggestions` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- Soft-warn allowed: `ELIGIBLE_WITH_WARNINGS` does not block (`:17-20`). The only soft-warn flavor in this group.
- Dutch error messages.

## `suggestion_engine_guards.py` — candidate + draft readiness

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/suggestion_engine_guards.py`

### Public surface

- `check_candidate_ready_for_suggestion(candidate)` / `require_candidate_ready_for_suggestion(candidate)` — status must be `ELIGIBLE_FOR_SUGGESTION`, audit events required, source references required **except** for `MANUAL_USER_INPUT` candidates (`:12-26`).
- `check_suggestion_draft_ready(draft)` / `require_suggestion_draft_ready(draft)` — status `READY_FOR_REVIEW` AND all three evidence arrays non-empty (`:30-44`).

### Collaborators

`ActionSuggestionDraft`, `CandidateSource`, `CandidateStatus`, `SuggestionCandidate`, `SuggestionDraftStatus` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- Status checks use identity `is not` (`:30-36`).
- All three evidence arrays (`source_reference_ids`, `audit_event_ids`, `gate_result_ids`) required to be non-empty for draft readiness.

```python
# suggestion_engine_guards.py:30-36
def check_suggestion_draft_ready(draft: ActionSuggestionDraft) -> bool:
    return (
        draft.status is SuggestionDraftStatus.READY_FOR_REVIEW
        and bool(draft.source_reference_ids)
        and bool(draft.audit_event_ids)
        and bool(draft.gate_result_ids)
    )
```

## `execution_guards.py` — execution-mode defaults + availability

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/execution_guards.py`

### Public surface

- `get_default_execution_targets()` (`:15-89`) — five locked execution modes: `INTERNAL_PAPER`, `IBKR_PAPER`, `IBKR_LIVE_READ_ONLY`, `IBKR_LIVE_MANUAL`, `BLOCKED_AUTO`. Each carries `explanation_nl` (Dutch operator text) and concrete `execution_target_id` strings.
- `check_execution_mode_available(mode, settings)` / `require_execution_mode_available(mode, settings)` (`:93-110`).
- `check_can_submit_order_to_target(target)` (`:112-117`).
- `require_manual_approval_required(target)` (`:119-126`) — conditional: only fires when `can_submit_orders` is true; read-only targets are exempt.

### Collaborators

`ApprovalRequirement`, `BrokerAccountMode`, `BrokerProvider`, `ExecutionMode`, `ExecutionModeSettings`, `ExecutionModeStatus`, `ExecutionTarget`, `ExecutionTargetKind` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- `BLOCKED_AUTO` is hard-disabled in the default table: `status=BLOCKED`, `approval_requirement=BLOCKED`, every `can_*` flag False (`:76-89`).
- `IBKR_LIVE_READ_ONLY` has `approval_requirement=NOT_APPLICABLE` and `can_submit_orders=False` — exempt because it can't place orders (`:45-58`).
- Master switch in availability gate: `approval_required_for_all_orders` must be true for *any* mode to be available (`:94-95`).

```python
# execution_guards.py:93-104
def check_execution_mode_available(mode: ExecutionMode, settings: ExecutionModeSettings) -> bool:
    if mode == ExecutionMode.BLOCKED_AUTO or not settings.approval_required_for_all_orders:
        return False
    if mode == ExecutionMode.INTERNAL_PAPER:
        return bool(settings.allow_internal_paper)
    if mode == ExecutionMode.IBKR_PAPER:
        return bool(settings.allow_ibkr_paper)
    if mode == ExecutionMode.IBKR_LIVE_READ_ONLY:
        return bool(settings.allow_ibkr_live_read_only)
    if mode == ExecutionMode.IBKR_LIVE_MANUAL:
        return bool(settings.allow_ibkr_live_manual)
    return False
```

## `storage_guards.py` — storage-readiness pair

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/storage_guards.py`

### Public surface

`check_storage_allows_paper_setup_persistence(check)` / `require_storage_allows_paper_setup_persistence(check)` (`:10-17`); `check_storage_allows_transaction_persistence(check)` / `require_storage_allows_transaction_persistence(check)` (`:19-25`).

### Collaborators

`StorageReadinessCheck`, `storage_allows_paper_setup_persistence`, `storage_allows_transaction_persistence` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- Thin wrappers around domain helpers that lift bool predicates into the `require/check` idiom.
- Dutch error messages: `"Opslag is nog niet klaar om setup op te slaan."`, `"Opslag is nog niet klaar om transacties op te slaan."`.

```python
# storage_guards.py:14-16
def require_storage_allows_paper_setup_persistence(check: StorageReadinessCheck) -> None:
    if not check_storage_allows_paper_setup_persistence(check):
        raise InvalidAccountingInputError("Opslag is nog niet klaar om setup op te slaan.")
```

## `paper_setup_guards.py` — request + preview safety

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/paper_setup_guards.py`

### Public surface

`check_first_run_setup_request_allowed(request)` / `require_first_run_setup_request_allowed(request)` (`:11-24`); `check_setup_preview_safe(preview)` / `require_setup_preview_safe(preview)` (`:26-43`).

### Collaborators

`FirstRunPaperPortfolioSetupPreview`, `FirstRunPaperPortfolioSetupRequest`, `PaperPortfolioBaseCurrency`, `PaperSetupStatus` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- Request check requires **all three** user confirmations true, positive `starting_cash`, and EUR base currency (`:13-17`).
- Preview safety check explicitly requires `not preview.persisted` (`:33`) — re-callable safety net against double-persistence.
- Preview must have empty `block_reasons` and status in `{PREVIEW_READY, READY_TO_CREATE}` (`:29-31`).

```python
# paper_setup_guards.py:11-18
def check_first_run_setup_request_allowed(request: FirstRunPaperPortfolioSetupRequest) -> bool:
    return (
        request.user_confirmed_paper_only
        and request.user_confirmed_no_real_money
        and request.user_confirmed_no_broker_order
        and request.starting_cash > 0
        and request.base_currency is PaperPortfolioBaseCurrency.EUR
    )
```

## `ai_explanation_guards.py` — output validation + hallucination scan

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/ai_explanation_guards.py`

### Public surface

- `LOCKED_RISK_DISCLAIMER_NL: str` (Dutch constant, `:26`).
- Status constants: `EXPLANATION_STATUS_GENERATED`, `EXPLANATION_STATUS_BLOCKED`, `EXPLANATION_STATUS_FAILED` (`:33-35`).
- Blocking-reason constants: `BLOCKING_REASON_HALLUCINATED_NUMBERS`, `BLOCKING_REASON_DISCLAIMER_MISSING`, `BLOCKING_REASON_EMPTY_OUTPUT`, `BLOCKING_REASON_OUTPUT_TOO_LONG` (`:37-40`).
- `ExplanationValidationResult(status, blocking_reason, hallucinated_numbers)` frozen dataclass (`:57-61`).
- `validate_explanation_output(*, output_text, input_evidence_text, max_output_chars, disclaimer=LOCKED_RISK_DISCLAIMER_NL)` (`:112`).

### Collaborators

**No domain imports** — stdlib only (`re`, `dataclasses`). The orchestrator wires inputs; this is a pure validator.

### Notable choices

- "every explanation is bound to a `(decision_package_id, decision_package_content_hash)` pair so a new package version always requires a new explanation" — the binding is enforced by the orchestrator/storage layer, not here (`:8-11`).
- **Hallucination guard:** every numeric token in AI output must also appear in the evidence text. Missing numbers ⇒ BLOCKED (`:146-154`).
- Check ordering (cheapest first): empty → too-long → missing-disclaimer → hallucinated-numbers (`:127-154`).
- Numeric normalization is locale-aware: handles Dutch decimal comma vs thousand separators (`:64-102`).
- Two-alternative regex: thousand-separated first (must have at least one separator), plain integer/decimal second (`:49-54`).
- All four blocking reasons are hard-blocks; no soft-warn flavor. `FAILED` status is exposed but not produced by `validate_explanation_output` (reserved for orchestrator-side errors).
- Returns a result object — does **not** raise. The only result-object guard module besides `action_draft_safety.py`.

```python
# ai_explanation_guards.py:146-159
input_numbers = _extract_numeric_tokens(input_evidence_text)
output_numbers = _extract_numeric_tokens(stripped)
hallucinated = sorted(output_numbers - input_numbers)
if hallucinated:
    return ExplanationValidationResult(
        status=EXPLANATION_STATUS_BLOCKED,
        blocking_reason=BLOCKING_REASON_HALLUCINATED_NUMBERS,
        hallucinated_numbers=tuple(hallucinated),
    )
return ExplanationValidationResult(
    status=EXPLANATION_STATUS_GENERATED,
    blocking_reason=None,
    hallucinated_numbers=(),
)
```

## `broker_reconciliation_guards.py` — reconciliation gate

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/broker_reconciliation_guards.py`

### Public surface

`check_reconciliation_allows_suggestions(report)` / `require_reconciliation_allows_suggestions(report)` (`:12-23`); `check_no_blocking_reconciliation_differences(differences)` (`:25-30`).

### Collaborators

`BrokerReconciliationDifference`, `BrokerReconciliationReport`, `ReconciliationStatus`, plus domain helpers `has_blocking_reconciliation_differences` and `reconciliation_blocks_suggestions` from `portfolio_outlook_domain`; `.errors`.

### Notable choices

- Conjunction: report must (a) not block suggestions, (b) be `CLEAN` status, **and** (c) carry `can_create_suggestions=True` (`:13-15`).
- Notable absence: no `require_no_blocking_reconciliation_differences` — the differences predicate is intended for UI inspection rather than as a hard gate at this layer.

```python
# broker_reconciliation_guards.py:12-15
def check_reconciliation_allows_suggestions(report: BrokerReconciliationReport) -> bool:
    if reconciliation_blocks_suggestions(report):
        return False
    return report.status is ReconciliationStatus.CLEAN and report.can_create_suggestions
```

## `action_draft_safety.py` — sizing + orderimpact + dry-run

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py`

### Public surface

**Constants:**
- `DEFAULT_BUY_VALUE_EUR = Decimal("1000")`, `DEFAULT_TOP_UP_PCT = Decimal("0.25")`, `DEFAULT_REDUCE_PCT = Decimal("0.25")` (`:27-29`).
- `LOCKED_ALLOWED_EXCHANGES` (frozenset of 15 venue codes) (`:31-50`).
- `LOCKED_ORDER_TYPE = "LMT"`; `LOCKED_ORDER_TYPES = {"LMT","MKT","STP","STP_LMT","TRAIL","TRAIL_LMT","BRACKET"}`; `LOCKED_TIF = "DAY"`; `LOCKED_ACTION_SIDES = {"BUY","SELL"}` (`:52-57`).
- `ACTIONABLE_LABELS_BUY = {"Kopen","Langzaam bijkopen"}`; `ACTIONABLE_LABELS_SELL = {"Verminderen","Verkopen"}` (`:63-66`).

**Dataclasses (all frozen):** `DraftSourceContext` (`:73-111`); `DraftConditionCheck` (`:114-129`); `DraftSizing` (`:132-167`); `Orderimpact` (`:170-184`); `DryRunResult(status, failures: tuple[str, ...])` (`:187-192`).

**Public functions:** `derive_action_draft_sizing(context, *, default_buy_value_in_quote_currency, top_up_pct, reduce_pct) -> DraftSizing` (`:295`); `compute_orderimpact(context, sizing, *, belgian_tob_security_class) -> Orderimpact` (`:388`); `run_dry_run_safety_checks(context, sizing, orderimpact) -> DryRunResult` (`:461`).

### Collaborators

`.belgian_tax` (`compute_tob`, `TobSecurityClass`, `:23`); lazy `.kelly_sizing` imports inside `_kelly_fraction` / `_kelly_apply_caps` (`:271, :287`). No domain imports — stdlib + sibling-only.

### Notable choices

- "the persisted record additionally keeps `safe_for_*=False` so this slice can never feed a broker submission even if the dry-run passes" — submission safety is a separate persisted flag, not this code (`:469-473`).
- **Sizing logic** (`:295-382`):
  - Label gating: only the four actionable labels produce drafts; anything else returns `status="blocked"` with `blocking_reason="not_actionable_label"` (`:312-320`).
  - Missing market price always blocks (no guessing).
  - `Kopen` uses fractional-Kelly + risk-parity caps when ensemble fields present; falls back to `DEFAULT_BUY_VALUE_EUR` otherwise (`:214-259, :334-352`).
  - `Langzaam bijkopen` with zero held quantity falls back to default-sized buy; otherwise 25% of held, floor 1 share (`:354-364`).
  - `Verkopen` sells the full held quantity; `Verminderen` is 25% of held, floor 1 share (`:376-382`).
  - Whole-share floor only; fractional shares forbidden (`:198-203`).
- **Dry-run failure codes** (all hard-blocks producing string codes the orchestrator maps to Dutch UI): `missing_ibkr_conid`, `missing_account_mode`, `missing_exchange`, `unsupported_exchange`, `market_data_not_fresh`, `fx_not_fresh`, `cash_comparison_unavailable`, `buy_value_exceeds_usable_cash`, `sell_quantity_exceeds_held`, `invalid_quantity`, `invalid_limit_price` (`:483-538`).
- Per-order-type and CONDITIONAL/TIF gates extend the failure code set (`_append_per_order_type_failures` / `_append_tif_and_conditional_failures`, `:561-678`).
- **Account-mode mismatch is no longer blocking** — only `missing_account_mode` blocks. Comment: "the connected IBKR account decides paper vs. live, not an app-side gate" (`:486-495`).
- A sizing-blocked input short-circuits; only the sizing's `blocking_reason` is returned (`:477-481`).
- Returns a result object — second result-object guard module.

### Mapping to the eleven A-K safety guards from `docs/intent/action-draft-state-machine.md`

| Intent ID | Intent name | Implemented here? | Where |
|-----|------|------|----|
| A | account-mode-match (hard-block) | **No** — explicitly relaxed; only `missing_account_mode` blocks | `:486-495` |
| B | connection-up | **No** — orchestrator concern | n/a |
| C | account-id-match | **No** — `DraftSourceContext` carries no `ibkr_account_id` | n/a |
| D | market-hours | **No** — exchange whitelist enforced (`unsupported_exchange`) but no session-hours check | `:497-501` (whitelist only) |
| E | duplicate-in-flight | **No** — needs cross-draft inspection | n/a |
| F | cash-sufficient | **Yes** — `buy_value_exceeds_usable_cash` + `cash_comparison_unavailable` | `:516-522` |
| G | position-sufficient | **Yes** — `sell_quantity_exceeds_held` | `:524-527` |
| H | cooldown (60s) | **No** — needs prior-draft timestamps | n/a |
| I | daily-limit | **No** — needs daily counter | n/a |
| J | drawdown | **No** — needs PnL series | n/a |
| K | fomo-drift | **No** — needs creation-time price snapshot | n/a |

Additional gates present here but not in the A-K list: market-data freshness (`market_data_not_fresh`), FX freshness (`fx_not_fresh`), exchange whitelist (`unsupported_exchange`), label / quantity / price sanity, full per-order-type and CONDITIONAL/TIF gates. The module covers F and G plus a broader set of correctness checks; the operational A/B/C/D/E/H/I/J/K guards remain orchestrator responsibilities.

```python
# action_draft_safety.py:475-507
failures: list[str] = []

if sizing.status != "ready":
    return DryRunResult(
        status="failed",
        failures=(sizing.blocking_reason or "sizing_blocked",),
    )

if not context.ibkr_conid.strip():
    failures.append("missing_ibkr_conid")

actual = (context.account_mode or "").strip().lower()
if not actual:
    failures.append("missing_account_mode")

primary = (context.primary_exchange or context.exchange or "").strip().upper()
if not primary:
    failures.append("missing_exchange")
elif primary not in LOCKED_ALLOWED_EXCHANGES:
    failures.append("unsupported_exchange")
```

## `action_draft_state_machine.py` — 13-state transition table

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_state_machine.py`

### Public surface

- `class ActionDraftState(StrEnum)` with 13 members: `DRAFT, SAFETY_CHECKED, USER_APPROVED, SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING, FILLED, CANCELLED, REJECTED, RECONCILED, EXPIRED, FAILED` (`:37-50`).
- `ALLOWED_TRANSITIONS: dict[ActionDraftState, frozenset[ActionDraftState]]` (`:54-117`).
- `TERMINAL_STATES = {RECONCILED, EXPIRED, FAILED}` (`:120-126`).
- `LIVE_AT_BROKER_STATES = {SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING}` (`:129-136`).
- `class InvalidStateTransitionError(ValueError)` (`:139`).
- `is_transition_allowed(*, from_state, to_state)` (`:143`); `require_transition_allowed(*, from_state, to_state)` (`:151`); `coerce_state(value: str) -> ActionDraftState` (`:163`).

### Collaborators

**None.** Stdlib only (`enum.StrEnum`, `typing.Final`).

### Notable choices

- Transition table: `dict[State, frozenset[State]]`. Anything not in the map is forbidden by default. Terminal states map to `frozenset()` (`:111-117`).
- **Three terminal states** (`:120-126`):
  - `RECONCILED` — happy-path after IBKR-side terminal state (FILLED/CANCELLED/REJECTED) reconciles
  - `EXPIRED` — dry-run validity window closed pre-submission
  - `FAILED` — orchestrator error pre-placement
- **Edit-as-override:** `SAFETY_CHECKED → DRAFT` and `USER_APPROVED → DRAFT` allowed (re-edit downgrades). Docstring: "Every transition is one-way except DRAFT⇆SAFETY_CHECKED⇆USER_APPROVED" (`:26-28`).
- `WORKING` is documented as an alias for `REPLY_CONFIRMED` ("same semantics — IBKR has accepted", `:14-16`). They share most outgoing transitions but `REPLY_CONFIRMED` can transition into `WORKING` while `WORKING` cannot loop back (`:94-110`).
- `FAILED` is reachable from every non-terminal state (`:55-110`) — universal escape hatch.
- `SUBMITTED` cannot go directly to `CANCELLED`; only to `AWAITING_IBKR_REPLY`, `REJECTED`, or `FAILED` (`:78-84`). Cancellation requires having heard from IBKR.
- **Reconciliation choke-point:** `FILLED`, `CANCELLED`, `REJECTED` each have exactly one successor — `RECONCILED` (`:111-113`). IBKR-terminal states must be reconciled before they become final.
- Error class is `ValueError` subclass, not `PortfolioAccountingError` — module is intentionally independent of the package's accounting-error hierarchy (`:139-140`). `coerce_state` re-raises unknown-state `ValueError` as `InvalidStateTransitionError` with `from exc` chaining (`:170-173`).

```python
# action_draft_state_machine.py:78-93
ActionDraftState.SUBMITTED: frozenset(
    {
        ActionDraftState.AWAITING_IBKR_REPLY,
        ActionDraftState.REJECTED,
        ActionDraftState.FAILED,
    }
),
ActionDraftState.AWAITING_IBKR_REPLY: frozenset(
    {
        ActionDraftState.REPLY_CONFIRMED,
        ActionDraftState.WORKING,
        ActionDraftState.REJECTED,
        ActionDraftState.CANCELLED,
        ActionDraftState.FAILED,
    }
),
```

## `errors.py` — exception hierarchy

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/errors.py`

### Public surface

- `class PortfolioAccountingError(Exception)` — base (`:1-2`).
- `class CurrencyMismatchError(PortfolioAccountingError)` (`:5-6`).
- `class InvalidAccountingInputError(PortfolioAccountingError)` (`:9-10`).
- `class InsufficientLotQuantityError(PortfolioAccountingError)` (`:13-14`).

### Collaborators

None — single-file hierarchy with no imports.

### Notable choices

- Two-level hierarchy: one base, three sibling subclasses. No deeper nesting.
- All eight predicate/guard modules in this group that raise do so **only** with `InvalidAccountingInputError`. Failure-discrimination is by message string, not exception type.
- `CurrencyMismatchError` and `InsufficientLotQuantityError` are not raised by any of the 11 reviewed modules in this set — they belong to the money/accounting modules (`portfolio-money-and-accounting.md`).
- `action_draft_state_machine.InvalidStateTransitionError` is **not** part of this hierarchy — subclasses `ValueError` directly.
- `ai_explanation_guards` and `action_draft_safety` return result dataclasses with status/failure codes instead of raising.

```python
# errors.py:1-14
class PortfolioAccountingError(Exception):
    """Base exception for paper accounting helper errors."""


class CurrencyMismatchError(PortfolioAccountingError):
    """Raised when accounting inputs use different currencies."""


class InvalidAccountingInputError(PortfolioAccountingError):
    """Raised when accounting inputs fail deterministic validation."""


class InsufficientLotQuantityError(PortfolioAccountingError):
    """Raised when a lot allocation exceeds the available quantity."""
```

## Cross-cutting observations

- **Three distinct failure idioms coexist:**
  1. raise `InvalidAccountingInputError` (modules 1-6 and 8).
  2. raise `InvalidStateTransitionError` (module 10).
  3. return a `*Result` dataclass with stable string codes (modules 7 and 9).
- **Predicate/require pairing** is the dominant pattern: every `require_X` is backed by a public `check_X`. Result-object modules are the only exceptions.
- **Hard-block dominance:** of the modules that raise, all failures are hard-block. The only explicit soft-warn concept appears in `suggestion_guards` where `ELIGIBLE_WITH_WARNINGS` is treated as eligible. The intent doc's guard J (drawdown) is hard/soft per `docs/intent/action-draft-state-machine.md` but `action_draft_safety.py` does not implement guard J at all.
- **A-K guard coverage:** of the eleven safety guards specified in `docs/intent/action-draft-state-machine.md`, only F (cash-sufficient) and G (position-sufficient) are implemented in `action_draft_safety.py`. Guards A, B, C, D, E, H, I, J, K are not present in any of the 11 reviewed modules and are orchestrator responsibilities.
- **Dutch operator strings** appear in modules 2, 3, 4, 5, 7, 8 (error messages and `explanation_nl`). Module 7's `LOCKED_RISK_DISCLAIMER_NL` is the canonical Dutch disclaimer.
- **No I/O across all 11 modules** — pure-Python, deterministic, no `datetime.now()` except `approval_guards.build_approved_action` (`approval_guards.py:50`).

## Open questions / uncertainty

- The A-K → reality gap: `action_draft_safety.py` implements only F and G of the eleven intent-doc guards. Whether A/B/C/D/E/H/I/J/K live in `apps/api` orchestration (per `docs/intent/action-draft-state-machine.md` §6's "submission-time evaluation is authoritative" rule) is out of scope for Phase 1a; Phase 1c gap-analysis will assess.
- `action_draft_safety.py`'s relaxation of account-mode-match (`:486-495`) departs from `docs/intent/action-draft-state-machine.md` §6 Guard A which specifies it as a hard-block. The doctrine §3 ("paper and real are first-class") may justify the relaxation; this Phase 1a doc only records the code state.
- `broker_reconciliation_guards.py` has only a `check_*` form for `no_blocking_reconciliation_differences`, no `require_*`. Whether this is by-design (UI inspection only) or oversight is out of scope.
- `ai_explanation_guards.LOCKED_RISK_DISCLAIMER_NL` is referenced as a `LOCKED_*` constant; whether it has changed (or is intended to change) across releases is not visible from this file.
- `action_draft_state_machine.WORKING` and `REPLY_CONFIRMED` carrying "same semantics" but asymmetric outgoing transitions (`:14-16, :94-110`) raises a small modelling question: why two states for the same semantic? The code does not explain; Phase 1b architecture review may.
