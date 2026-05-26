# `packages/domain` — portfolio and policy

**Phase:** 1a (reality components)
**Task:** T-001
**Scope:** ten modules in `packages/domain/src/portfolio_outlook_domain/` that define what a portfolio is, what users can configure, and what policies gate suggestions. They sit above the primitives layer (`domain-primitives-and-money.md`) and below the research / runtime layers.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `portfolio.py` — `PortfolioSummary`, `PositionSnapshot`.
- `paper_setup.py` — first-run paper-portfolio setup flow.
- `investment_policy.py` — single `InvestmentPolicyStatement`.
- `eligibility.py` — suggestion-eligibility policy and check + evaluation function.
- `approvals.py` — `ApprovalRequest`, `ApprovalDecision`, `ApprovedAction`.
- `capabilities.py` — `AssetCapability`, `CapabilityCheckResult`.
- `settings.py` — strategy / IBKR / OpenAI / budget / pricing / connection settings (largest module in the package).
- `market_calendar.py` — venues, sessions, tradability assessment.
- `market_data_foundation.py` — market-data identity, snapshot, readiness state machine.
- `audit.py` — `AuditEvent`.

All public symbols are re-exported from `packages/domain/src/portfolio_outlook_domain/__init__.py`. Every model in this group inherits `DomainBaseModel` from `primitives.py:9-10` (so it is frozen), except `capabilities.py` (uses plain `BaseModel`) and `market_data_foundation.py` (uses `@dataclass(frozen=True)`).

## `portfolio.py` — portfolio and position snapshots

**Path:** `packages/domain/src/portfolio_outlook_domain/portfolio.py` (40 lines)

### Public surface

- `PortfolioSummary(DomainBaseModel)` — fields `portfolio_id`, `name`, `base_currency: CurrencyCode`, `mode: PaperLiveMode = PaperLiveMode.PAPER`, `starting_capital: Money`, optional `cash_available`, `invested_value`, `current_value: Money | None`, `created_at: datetime` (`portfolio.py:10-19`).
- `PositionSnapshot(DomainBaseModel)` — fields `portfolio_id`, `instrument_id`, `quantity: Quantity`, optional `average_buy_price`, `current_price`, `current_value`, `unrealized_gain_loss`, `realized_gain_loss: Money | None`, `risk_level: RiskLevel | None`, `advice_action: AdviceAction | None`, `as_of: datetime` (`portfolio.py:28-39`).

### Collaborators

`AdviceAction`, `PaperLiveMode`, `RiskLevel` from `.enums`; `InstrumentId`, `PortfolioId` from `.identifiers`; `CurrencyCode`, `DomainBaseModel`, `Money`, `Quantity` from `.primitives`.

### Notable choices

- Hard paper-only invariant: `@model_validator(mode="after")` rejects any non-`PAPER` mode at construction time (`portfolio.py:21-25`), confirmed by `tests/test_portfolio.py:25-34`.
- All monetary fields on `PositionSnapshot` are nullable — these are snapshots, not computed projections; valuation may not be computable yet.

```python
# portfolio.py:21-25
@model_validator(mode="after")
def validate_mode(self) -> "PortfolioSummary":
    if self.mode is not PaperLiveMode.PAPER:
        raise ValueError("Version 1 is paper-only. PortfolioSummary.mode must be 'paper'.")
    return self
```

## `paper_setup.py` — first-run setup contracts

**Path:** `packages/domain/src/portfolio_outlook_domain/paper_setup.py` (276 lines)

### Public surface

- `PaperCashAccountDefinition` (`paper_setup.py:17-42`).
- `FirstRunPaperPortfolioSetupRequest` (`:45-86`).
- `FirstRunPaperPortfolioSetupPreview` (`:89-122`).
- `PaperPortfolioSetupDefaults` (`:125-175`).
- `PaperPortfolioSetupState` (`:178-201`).
- Factories: `build_default_paper_portfolio_setup_defaults()` (`:204-215`); `build_not_configured_paper_setup_state()` (`:218-228`); `build_first_run_setup_preview(*, request, first_run_setup_preview_id, created_at, source_reference_ids=None, audit_event_ids=None)` (`:231-265`); `paper_setup_ready_for_creation(preview)` (`:268-275`).

### Collaborators

`PaperPortfolioBaseCurrency`, `PaperSetupBlockReason`, `PaperSetupMode`, `PaperSetupStatus`, `PaperSetupWarningReason` from `.enums`; `AuditEventId`, `FirstRunSetupPreviewId`, `PaperCashAccountId`, `SourceReferenceId` from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- Strict float rejection on every Decimal field (`paper_setup.py:23-28, 55-60, 136-146`).
- Triple user-confirmation requirement on the request (`:76-86`): all three booleans must be true and `setup_mode` must be `FIRST_RUN`.
- Status invariants: `PREVIEW_READY` forbids block reasons; `BLOCKED`/`FAILED` require them (`:115-121`).
- `build_first_run_setup_preview` hard-codes the cash account id `"paper_cash_main"` and seeds five default warnings: `PREVIEW_NOT_SAVED`, `IBKR_NOT_CONFIGURED`, `OPENAI_NOT_CONFIGURED`, `NO_POSITIONS_YET`, `NO_WATCHLIST_YET` (`:251-257`).
- `PaperPortfolioSetupDefaults.validate_rules` enforces `paper_only_required=True`, `broker_required=False`, `live_trading_allowed=False` — build-time invariants, not just defaults (`:163-175`).
- `FirstRunPaperPortfolioSetupPreview.persisted` must be `False` (`:113-114`) — the file's comment notes "Preview cannot be persisted in this foundation step".

```python
# paper_setup.py:76-86
@model_validator(mode="after")
def validate_confirmations(self) -> "FirstRunPaperPortfolioSetupRequest":
    if self.setup_mode is not PaperSetupMode.FIRST_RUN:
        raise ValueError("setup_mode must be first_run.")
    if not self.user_confirmed_paper_only:
        raise ValueError("paper-only confirmation is required.")
    if not self.user_confirmed_no_real_money:
        raise ValueError("no-real-money confirmation is required.")
    if not self.user_confirmed_no_broker_order:
        raise ValueError("no-broker-order confirmation is required.")
    return self
```

## `investment_policy.py` — IPS

**Path:** `packages/domain/src/portfolio_outlook_domain/investment_policy.py` (37 lines)

### Public surface

- `InvestmentPolicyStatement(DomainBaseModel)` — fields with defaults: `goal`, `risk_profile`, `time_horizon_years: int | None (ge=1)`, `maximum_drawdown_tolerance`, `allowed_asset_types` (default `[CASH, FX, UCITS_ETF, STOCK, BENCHMARK]`), `blocked_asset_types` (default `[OTHER]`), `minimum_cash_reserve` (default `Percentage(value=20)`), `maximum_single_etf_allocation` (default `25`), `maximum_single_stock_allocation` (default `10`), `minimum_holding_period_days: int | None (ge=0)`, and five `allow_*` booleans defaulted to `False` (`investment_policy.py:9-30`).

### Collaborators

`AssetType` from `.enums`; `DomainBaseModel`, `Percentage` from `.primitives`.

### Notable choices

- Single cross-field rule: stock concentration cap must be **strictly less than** ETF cap (`investment_policy.py:32-36`). Equality is rejected.
- Safe-by-default booleans — all "exotic" features (`allow_leverage`, `allow_short_selling`, `allow_options`, `allow_crypto`, `allow_penny_stocks`) disabled. `tests/test_investment_policy.py:8-13` confirms.
- No persistence schema, no identifier — this is a value object embedded elsewhere.

```python
# investment_policy.py:32-36
@model_validator(mode="after")
def validate_allocations(self) -> "InvestmentPolicyStatement":
    if self.maximum_single_stock_allocation.value >= self.maximum_single_etf_allocation.value:
        raise ValueError("Stock allocation must be lower than ETF allocation.")
    return self
```

## `eligibility.py` — eligibility policy and check

**Path:** `packages/domain/src/portfolio_outlook_domain/eligibility.py` (143 lines)

### Public surface

- `SuggestionEligibilityPolicy` — `suggestion_eligibility_policy_id`, `policy_name`, six `require_*: bool = True` flags, `explanation_nl` (`eligibility.py:23-38`).
- `SuggestionEligibilityCheck` — `suggestion_eligibility_check_id`, `policy_id`, `instrument_id?`, `data_quality_gate_id`, `status`, `block_reasons`, `warning_reasons`, `source_reference_ids`, `audit_event_ids`, `checked_at`, `explanation_nl` (`:41-86`).
- `build_default_suggestion_eligibility_policy()` (`:89-94`); `evaluate_suggestion_eligibility(...)` (`:97-143`).

### Collaborators

`DataQualityGate` from `.data_quality`; `DataGateDecision`, `SuggestionEligibilityBlockReason`, `SuggestionEligibilityStatus`, `SuggestionEligibilityWarningReason` from `.enums`; six identifier types from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- Status-driven invariants in the check (`:54-86`): `ELIGIBLE` forbids block/warning reasons; `ELIGIBLE_WITH_WARNINGS` requires warnings but no blocks; `BLOCKED` requires block reasons; eligible statuses additionally require non-empty `source_reference_ids` and `audit_event_ids` (traceability enforced at the model level).
- `evaluate_suggestion_eligibility` flow: policy traceability/audit gates first → if any block reasons appear, status is `BLOCKED`; otherwise the `DataGateDecision` is mapped per the cascade below.
- The factory hard-codes the result id as `"eligibility_check_result"` (`:132`).

```python
# eligibility.py:115-129
if block_reasons:
    status = SuggestionEligibilityStatus.BLOCKED
elif data_quality_gate.decision is DataGateDecision.CONTINUE_ALLOWED:
    status = SuggestionEligibilityStatus.ELIGIBLE
elif data_quality_gate.decision is DataGateDecision.CONTINUE_WITH_WARNING:
    status = SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
    warning_reasons.append(SuggestionEligibilityWarningReason.UNKNOWN)
elif data_quality_gate.decision is DataGateDecision.SKIP_JOB:
    status = SuggestionEligibilityStatus.SKIPPED
elif data_quality_gate.decision is DataGateDecision.BLOCK_SUGGESTION:
    status = SuggestionEligibilityStatus.BLOCKED
    block_reasons.append(SuggestionEligibilityBlockReason.DATA_QUALITY_FAILED)
elif data_quality_gate.decision is DataGateDecision.FAIL_JOB:
    status = SuggestionEligibilityStatus.FAILED
    block_reasons.append(SuggestionEligibilityBlockReason.DATA_QUALITY_FAILED)
```

## `approvals.py` — request, decision, approved action

**Path:** `packages/domain/src/portfolio_outlook_domain/approvals.py` (85 lines)

### Public surface

- `ApprovalRequest` — `approval_request_id`, `execution_intent_id`, `portfolio_id`, optional `suggestion_id`, `instrument_id`, `action: AdviceAction`, `requested_amount: Money | None`, `requested_quantity: Quantity | None`, `target_execution_mode: ExecutionMode`, `status: ApprovalDecisionStatus = PENDING`, `explanation_nl`, `created_at`, optional `expires_at` (`approvals.py:17-45`).
- `ApprovalDecision` — `approval_decision_id`, `approval_request_id`, `decision: ApprovalDecisionStatus`, `decided_at`, `decided_by: str`, `reason_nl: str | None` (`:48-67`).
- `ApprovedAction` — derived bundle linking request, decision, intent, portfolio, instrument, action, target mode, `approved_at` (`:70-84`).

### Collaborators

`AdviceAction`, `ApprovalDecisionStatus`, `ExecutionMode` from `.enums`; six identifier types from `.identifiers`; `Money`, `Quantity` from `.primitives`.

### Notable choices

- `ApprovalRequest`: `BLOCKED_AUTO` rejected as target mode (`:41-42`); either `requested_amount` or `requested_quantity` must be provided (`:43-44`). `PENDING` is the only allowed initial status.
- `ApprovalDecision`: `PENDING` decision rejected — a decision must be terminal (`:58-59`); `decided_by` required; `REJECTED`/`BLOCKED` require `reason_nl` (`:62-66`). Tests verify these (`tests/test_approvals.py:52-68`).
- `ApprovedAction`: same `BLOCKED_AUTO` rejection (`:80-83`). Produced only on a positive decision.

```python
# approvals.py:56-67
@model_validator(mode="after")
def validate_decision(self) -> "ApprovalDecision":
    if self.decision == ApprovalDecisionStatus.PENDING:
        raise ValueError("ApprovalDecision cannot be pending")
    if not self.decided_by.strip():
        raise ValueError("decided_by is required")
    if self.decision in {
        ApprovalDecisionStatus.REJECTED,
        ApprovalDecisionStatus.BLOCKED,
    } and not (self.reason_nl and self.reason_nl.strip()):
        raise ValueError("reason_nl is required for rejected/blocked decisions")
    return self
```

## `capabilities.py` — asset capabilities

**Path:** `packages/domain/src/portfolio_outlook_domain/capabilities.py` (73 lines)

### Public surface

- `AssetCapability(BaseModel)` — `category: CapabilityCategory`, `status: CapabilityStatus`, seven `can_*` booleans (`can_watch`, `can_research`, `can_ai_explain`, `can_generate_action_suggestion`, `can_create_paper_order`, `can_create_paper_transaction`, `can_enter_paper_portfolio`), `blocked_reason_codes: list[BlockedReasonCode]`, `explanation_nl` (`capabilities.py:6-17`).
- `CapabilityCheckResult(BaseModel)` — `category`, `allowed: bool`, `status`, `explanation_nl`, `blocked_reason_codes` (`:59-64`).

### Collaborators

`BlockedReasonCode`, `CapabilityCategory`, `CapabilityStatus` from `.enums`. No identifier or primitive imports.

### Notable choices

- Both models use plain `BaseModel` (mutable) — **inconsistent** with the rest of the package, which uses `DomainBaseModel`.
- Status-specific behaviour matrix in `AssetCapability.validate_rules` (`:19-56`):
  - `ALLOWED` requires watch/research/ai-explain on and rejects any `blocked_reason_codes`.
  - `WATCH_ONLY` requires watch/research/ai-explain on but forbids the four action-related booleans; requires `blocked_reason_codes`.
  - `BLOCKED` forbids the four action booleans; requires `blocked_reason_codes` (watch/research/ai_explain may be off).
- `CapabilityCheckResult` requires `blocked_reason_codes` whenever `allowed is False` (`:66-72`).

```python
# capabilities.py:30-42
if self.status is CapabilityStatus.WATCH_ONLY:
    if not self.can_watch or not self.can_research or not self.can_ai_explain:
        raise ValueError("watch_only categorie moet watch/research/ai uitleg toelaten")
    if self.can_generate_action_suggestion:
        raise ValueError("watch_only categorie mag geen actiesuggestie toelaten")
    if self.can_create_paper_order:
        raise ValueError("watch_only categorie mag geen paper order toelaten")
    if self.can_create_paper_transaction:
        raise ValueError("watch_only categorie mag geen paper transactie toelaten")
    if self.can_enter_paper_portfolio:
        raise ValueError("watch_only categorie mag niet in paper portefeuille")
    if not self.blocked_reason_codes:
        raise ValueError("watch_only categorie vereist blocked_reason_codes")
```

## `settings.py` — settings, secrets, budgets

**Path:** `packages/domain/src/portfolio_outlook_domain/settings.py` (834 lines — largest module in the package)

### Public surface

Constants: `_MILLION = Decimal("1000000")` (`:36`); `_ENV_VAR_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")` (`:37`); `_VERSION_1_BLOCKED_ASSET_TYPES` tuple of 8 strings (`:39-48`).

Local `StrEnum`s (not in `enums.py`): `AllowedAssetType` (`:51-57`), `BlockedAssetType` (`:59-67`), `PortfolioGoal` (`:70-73`), `StrategyRiskLevel` (`:76-79`), `AssetMixPreference` (`:82-85`), `RegionPreference` (`:88-92`), `SectorPreference` (`:95-102`), `CurrencyPreference` (`:105-108`), `AssetPermissionStatus` (`:111-114`).

Models: `SettingHelpText` (`:117-127`), `AllowedUniverseSettings` (`:130-139`), `UserStrategySettings` (`:142-182`), `AssetPermission` (`:185-188`), `PortfolioSettings` (`:303-328`), `SecretReference` (`:331-370`), `IBKRConnectionSettings` (`:373-419`), `OpenAIIntegrationSettings` (`:422-468`), `OpenAIModelPricing` (`:471-502`), `ApiBudgetPolicy` (`:505-542`), `ApiUsageSummary` (`:545-603`), `ApiCostEstimate` (`:606-640`), `ApiConnectionCheck` (`:643-657`), `SettingsProfile` (`:660-684`).

Functions: `evaluate_asset_permission` (`:191-239`); `get_allowed_universe_help_texts()` / `get_user_strategy_help_texts()` (`:242-290`); `strategy_settings_summary_nl` (`:293-300`); `build_default_settings_profile` (`:687-744`); `ibkr_settings_ready_for_paper` (`:747-758`); `openai_settings_ready` (`:761-770`); `estimate_openai_cost` (`:773-801`); `calculate_budget_status` (`:804-818`); `remaining_budget_eur` (`:821-825`); `connection_check_blocks_jobs` (`:828-833`).

### Collaborators

Twelve enums from `.enums`; thirteen identifier types from `.identifiers`; `CurrencyCode`, `DomainBaseModel`, `Money`, `Percentage` from `.primitives`.

### Notable choices

- `PortfolioSettings.starting_paper_capital` default is `Money(amount=Decimal("10000"), currency="EUR")` (`:304`).
- `PortfolioSettings.validate_paper_mode_and_percentages` enforces paper-only and `first_run_minimum_cash_reserve + first_run_maximum_invested ≤ 100%` (`:318-328`); first-run defaults are 40 % reserve / 60 % invested, normal reserve 20 %.
- `UserStrategySettings.user_buffer_eur` is annotated as a Task-133 product lock (`:153-156`): subtracted from `available_funds` during BUY draft sizing; default `Decimal("0")`, must be ≥ 0.
- `SecretReference.validate_env_name` rejects values starting with `sk-` and a heuristic against single-token `SECRET`-named values (`:348-357`). `validate_model` requires env-var name when storage is `ENVIRONMENT_VARIABLE`, and forbids `AVAILABLE` status combined with `configured=False` (`:359-370`).
- `IBKRConnectionSettings`: `allow_live_order_transmission=True` always rejected; `paper_account_required` must be True; if enabled, `connection_mode` cannot be `NOT_CONFIGURED`/`DISABLED`, gateway must be configured, and `host`/`port`/`client_id` are all required (`:395-419`).
- `OpenAIModelPricing` requires `min_length=1` on both `source_reference_ids` and `audit_event_ids` (`:479-480`) — every pricing row carries traceability.
- `ApiBudgetPolicy.validate_model`: warning threshold ≤ critical threshold; enabled budgets require `budget_amount_eur > 0` (`:528-542`).
- `ApiUsageSummary` enforces `total_tokens == input + cached_input + output` (`:591-592`) and `period_end > period_start`.
- `estimate_openai_cost` uses `cached_input_usd_per_1m_tokens` if set, else falls back to the regular input price (`:782`). Cost id is timestamp-derived: `f"cost_{model_pricing_id}_{calculated_at:%Y%m%d%H%M%S}"`.
- `calculate_budget_status` returns `NOT_CONFIGURED` when policy disabled, `BLOCKED` when cost meets/exceeds and `block_when_exceeded=True`, otherwise `EXCEEDED`/`CRITICAL`/`WARNING`/`OK` thresholds (`:804-818`).

```python
# settings.py:395-419
@model_validator(mode="after")
def validate_model(self) -> "IBKRConnectionSettings":
    if self.allow_live_order_transmission:
        raise ValueError("Live order transmission is niet toegestaan in deze build.")
    if not self.paper_account_required:
        raise ValueError("paper_account_required moet true zijn.")
    if self.port is not None and not 1 <= self.port <= 65535:
        raise ValueError("Port moet tussen 1 en 65535 liggen.")
    if self.client_id is not None and self.client_id < 0:
        raise ValueError("client_id moet >= 0 zijn.")
    ...
```

```python
# settings.py:782-801
cached_price = pricing.cached_input_usd_per_1m_tokens or pricing.input_usd_per_1m_tokens
input_cost = (Decimal(input_tokens) / _MILLION) * pricing.input_usd_per_1m_tokens
cached_cost = (Decimal(cached_input_tokens) / _MILLION) * cached_price
output_cost = (Decimal(output_tokens) / _MILLION) * pricing.output_usd_per_1m_tokens
estimated_usd = input_cost + cached_cost + output_cost
estimated_eur = None
if eur_usd_exchange_rate is not None:
    estimated_eur = estimated_usd / eur_usd_exchange_rate
```

## `market_calendar.py` — venues, sessions, tradability

**Path:** `packages/domain/src/portfolio_outlook_domain/market_calendar.py` (465 lines)

### Public surface

Local `StrEnum`s (also not in `enums.py`): `MarketRegion`, `ExchangeCode` (14 codes incl. all major Euronext venues + NYSE/Nasdaq/Xetra/LSE) (`:11-33`); `InstrumentTradingVenueType`, `MarketSessionType` (12 values incl. `OPENING_AUCTION`, `CLOSING_AUCTION`, `TRADING_AT_LAST`), `MarketSessionStatus`, `TradabilityStatus` (5 values), `MarketCalendarDayType`, `MarketClosureReason`, `MarketStatusFreshness` (`:36-102`).

Models: `MarketVenue` (`:105-119`); `TradingSessionWindow` (`:122-154`); `MarketCalendarDay` (`:157-191`); `MarketStatusAssessment` (`:194-252`); `MarketCalendarHelpText` (`:255-258`).

Functions: `evaluate_tradability(...)` (`:261-308`); `get_market_calendar_help_texts()` returns 16-entry tuple (`:311-387`); `default_market_venue_catalog()` returns 8 venues (Brussels/Amsterdam/Paris/NYSE/Nasdaq/NYSE Arca/Xetra/LSE) (`:390-464`).

### Collaborators

`DomainBaseModel` from `.primitives` only — no enum or identifier imports from the rest of the package.

### Notable choices

- `TradingSessionWindow` requires `ends_at > starts_at` and demands a Dutch `liquidity_warning_nl` for any pre/post/after-hours session (`:140-154`).
- `MarketCalendarDay` requires at least one session on full/half trading days and forbids a `REGULAR` session on closed days (`:176-191`).
- `MarketStatusAssessment._validate_consistency` enforces a *blocks-orders* invariant: any unknown/blocked tradability, stale/missing/unknown/blocked freshness, or closed/halted/suspended/unknown session status must set `blocks_orders=True`; pre/post/after-hours sessions cannot be cleanly `TRADABLE` (`:217-252`).
- `evaluate_tradability` is a tiered rule cascade — freshness checked first (stale/missing/blocked → `BLOCKED`; unknown → `UNKNOWN`), then session status (halted/suspended → `BLOCKED`; closed → `NOT_TRADABLE`), then session type (extended hours → `TRADABLE_WITH_WARNING` iff limit orders allowed; auctions → `TRADABLE_WITH_WARNING` if any order type allowed) (`:261-308`).

```python
# market_calendar.py:269-292
if freshness_status in {
    MarketStatusFreshness.STALE,
    MarketStatusFreshness.MISSING,
    MarketStatusFreshness.BLOCKED,
}:
    return TradabilityStatus.BLOCKED
if freshness_status == MarketStatusFreshness.UNKNOWN:
    return TradabilityStatus.UNKNOWN
if current_session_status in {MarketSessionStatus.HALTED, MarketSessionStatus.SUSPENDED}:
    return TradabilityStatus.BLOCKED
if current_session_status == MarketSessionStatus.UNKNOWN:
    return TradabilityStatus.UNKNOWN
if current_session_status == MarketSessionStatus.CLOSED:
    return TradabilityStatus.NOT_TRADABLE
```

## `market_data_foundation.py` — market-data identity, snapshot, readiness

**Path:** `packages/domain/src/portfolio_outlook_domain/market_data_foundation.py` (167 lines)

This module is the boundary between the domain layer and market-data providers. It uses `@dataclass(frozen=True)` and a `Protocol`, not pydantic — distinct from every other module in this group.

### Public surface

- `MarketDataFetchStatus(StrEnum)` — 12 values incl. `SUCCESS`, `NOT_CONFIGURED`, `MISSING_IDENTITY`, `IDENTITY_NOT_VALIDATED`, `PROVIDER_PERMISSION_MISSING`, `PACING_LIMITED`, `NO_SNAPSHOT`, `PROVIDER_ERROR`, `STORAGE_ERROR`, `STALE_SNAPSHOT`, `SNAPSHOT_AVAILABLE`, `PROVIDER_NOT_CONFIGURED` (`:10-22`).
- `MarketDataIdentity` (`@dataclass(frozen=True)`) — `ibkr_conid: str`, `identity_validated: bool` (`:25-28`).
- `MarketDataSnapshot` — 17 fields covering symbol, currency, three timestamps (`requested_at`, `received_at`, optional `provider_as_of`, `stored_at`), provider metadata (`provider_code`, `provider_environment`, `provider_account_mode`), `data_domain`, `request_kind`, `source_type`, and four optional `Decimal` price fields (`last_price`, `bid_price`, `ask_price`, `day_change_percent`) (`:31-49`).
- `MarketDataFetchResult` — `status`, optional `snapshot`, `message_nl` (`:52-56`).
- `MarketDataProviderPort(Protocol)` — single method `fetch_latest_snapshot(identity) -> MarketDataFetchResult` (`:59-60`).
- `block_if_identity_invalid(identity) -> MarketDataFetchResult | None` (`:63-76`).
- `MarketDataFreshnessStatus`, `MarketDataValuationReadinessStatus`, `MarketDataPriceBasis` enums (`:79-100`).
- `MarketDataReadinessPolicy` — `fresh_within: timedelta = 15 min`, `near_stale_within: timedelta = 30 min` (`:103-106`).
- `MarketDataReadinessEvaluation` — `freshness_status`, `valuation_readiness_status`, `price_basis`, `usable_price: Decimal | None`, `snapshot_age_seconds: int | None` (`:109-115`).
- `evaluate_market_data_readiness(*, snapshot, now, policy) -> MarketDataReadinessEvaluation` (`:118-166`).

### Collaborators

Pure stdlib only (`dataclasses`, `datetime`, `decimal`, `enum`, `typing.Protocol`). No imports from elsewhere in the package — this is a pure boundary module.

### Notable choices

- Dataclasses + Protocol rather than pydantic — allows duck-typed adapters without runtime model overhead.
- `block_if_identity_invalid` uses `.strip()` to treat whitespace-only conids as missing (`:64-69`).
- `evaluate_market_data_readiness` computes age from `provider_as_of or received_at or stored_at` (`:132`), clamps negative ages to 0 (`:134-135`), picks `LAST` price basis if available, else `MIDPOINT` of bid/ask, else `UNAVAILABLE`; stale snapshots always block valuation even if a price is present (`:144-159`).

```python
# market_data_foundation.py:144-160
if snapshot.last_price is not None:
    basis = MarketDataPriceBasis.LAST
    price = snapshot.last_price
elif snapshot.bid_price is not None and snapshot.ask_price is not None:
    basis = MarketDataPriceBasis.MIDPOINT
    price = (snapshot.bid_price + snapshot.ask_price) / Decimal("2")
else:
    basis = MarketDataPriceBasis.UNAVAILABLE
    price = None

if freshness is MarketDataFreshnessStatus.STALE:
    readiness = MarketDataValuationReadinessStatus.BLOCKED_STALE_SNAPSHOT
elif price is None:
    readiness = MarketDataValuationReadinessStatus.BLOCKED_MISSING_PRICE
else:
    readiness = MarketDataValuationReadinessStatus.READY_FOR_VALUATION_PREVIEW
```

## `audit.py` — audit event

**Path:** `packages/domain/src/portfolio_outlook_domain/audit.py` (29 lines)

### Public surface

- `AuditEvent(DomainBaseModel)` — `audit_event_id: AuditEventId`, `event_type: str`, `actor: str`, `created_at: datetime`, optional FK-style ids (`related_portfolio_id`, `related_instrument_id`, `related_suggestion_id`), three optional hash fields (`input_hash`, `output_hash`, `previous_event_hash`), `details: dict[str, str | int | Decimal | bool | None]` (`audit.py:10-21`).

### Collaborators

`AuditEventId`, `InstrumentId`, `PortfolioId`, `SuggestionId` from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- Minimal validation: only `event_type` and `actor` must be non-empty (`audit.py:23-28`); everything else permits `None`. The most permissive model in the package by design.
- Three hash fields (`input_hash`, `output_hash`, `previous_event_hash`) imply a Merkle-style chain across events, though no chaining logic lives in this module.
- `details` value union excludes float and lists/dicts — only flat primitives plus `Decimal`. Test confirms `Decimal` is stringified when `mode="json"` is used (`tests/test_audit.py:21-31`).

```python
# audit.py:10-28
class AuditEvent(DomainBaseModel):
    audit_event_id: AuditEventId
    event_type: str
    actor: str
    created_at: datetime
    related_portfolio_id: PortfolioId | None = None
    related_instrument_id: InstrumentId | None = None
    related_suggestion_id: SuggestionId | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    previous_event_hash: str | None = None
    details: dict[str, str | int | Decimal | bool | None]

    @field_validator("event_type", "actor")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field is required")
        return value
```

## Cross-cutting observations

- **Frozen-by-default** for every pydantic model in this group except `capabilities.AssetCapability` and `capabilities.CapabilityCheckResult`, which use plain `BaseModel` (`capabilities.py:6, :59`). `market_data_foundation.py` uses `@dataclass(frozen=True)` instead.
- **Decimal-only money and percentages.** Float rejection is universal at the primitives layer (`primitives.py:25-30`, `:40-45`, `:58-63`); modules in this group inherit it via field types.
- **Dutch-language user-facing strings.** Every model carries an `explanation_nl` (or `help_nl` / `title_nl` / `summary_nl` / `reason_nl` / `message_nl` / `label_nl`) and validators enforce non-empty content.
- **Paper-only enforcement** is hard-coded at multiple type layers: `PortfolioSummary.validate_mode` (`portfolio.py:21-25`), `PortfolioSettings.validate_paper_mode_and_percentages` (`settings.py:318-322`), `IBKRConnectionSettings` rejecting `allow_live_order_transmission=True` (`settings.py:397-398`), `PaperPortfolioSetupDefaults.validate_rules` (`paper_setup.py:163-175`).
- **Traceability invariants.** Non-trivial states require non-empty `source_reference_ids` / `audit_event_ids`: `SuggestionEligibilityCheck` (`eligibility.py:68-86`), `OpenAIModelPricing` (`settings.py:479-480`), `ApiUsageSummary` (`settings.py:561, 598-602`).
- **Two enum locations.** Some enums live in `.enums`; `settings.py` and `market_calendar.py` each define their own local `StrEnum`s for module-internal vocabularies. The split is by ownership (general vs. settings-only / calendar-only), not by mistake — these enums are not consumed outside their parent modules.

## Open questions / uncertainty

- `capabilities.py`'s use of plain `BaseModel` (not `DomainBaseModel`) means `AssetCapability` and `CapabilityCheckResult` are mutable. Whether this is intentional or an oversight is not clear from the file (no comment, no test asserting mutability).
- `audit.py`'s three hash fields imply a chain, but no module under `packages/domain` produces or verifies the chain. The chain logic must live elsewhere (likely `apps/api` or `packages/storage`); confirming this is out of scope for this Phase 1a doc.
- `settings.py` defines local enums (e.g. `AllowedAssetType`, `PortfolioGoal`) that overlap with `enums.AssetType` and `enums.PaperPortfolioBaseCurrency`. Whether the duplication is by-design (settings-specific vocabularies) or candidate for consolidation will be assessed by Phase 1b architecture review.
- `market_data_foundation.MarketDataReadinessPolicy` defaults of `fresh_within=15min` / `near_stale_within=30min` (`:103-106`) are presented as policy thresholds with no comment on derivation; whether these match the intent in `docs/intent/decision-package.md` "critical vs non-critical inputs" is out of scope here.
