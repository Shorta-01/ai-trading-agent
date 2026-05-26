# `packages/domain` — primitives and money

**Phase:** 1a (reality components)
**Task:** T-001
**Scope:** seven leaf-level modules in `packages/domain/src/portfolio_outlook_domain/` that form the package's value-type substrate. All other domain modules consume these.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `primitives.py` — `DomainBaseModel`, `Money`, `Percentage`, `Quantity`, `CurrencyCode`.
- `costs.py` — `CostEstimate`, `TotalCostEstimate`.
- `lots.py` — `PaperLot`, `FifoLotAllocation`.
- `identifiers.py` — `SafeIdentifier` and ~80 typed aliases.
- `enums.py` — ~120 `StrEnum` types covering every closed-set value used in the project.
- `instruments.py` — `Instrument`, `ETFDetails`, `InstrumentWithDetails`.
- `term_deposits.py` — `TermDepositInput`, `TermDepositProjection`.

All public symbols are re-exported from the package's `__init__.py` (`packages/domain/src/portfolio_outlook_domain/__init__.py:23,259,262,295,413,468-513`). The dependency graph among these seven modules is one-way and acyclic: `enums.py`, `identifiers.py`, and `primitives.py` are leaves; the other four import only from those three.

## `primitives.py` — the foundation

**Path:** `packages/domain/src/portfolio_outlook_domain/primitives.py` (64 lines)

### Public surface

- `CurrencyCode` — type alias `Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]` (`primitives.py:6`). The regex enforces three uppercase letters; the **allowed-set** check lives on `Money`, not on the alias.
- `DomainBaseModel(BaseModel)` — base for every other domain model. Sets `model_config = ConfigDict(frozen=True)` (`primitives.py:9-10`). This is the project-wide immutability switch.
- `Money(DomainBaseModel)` — fields `amount: Decimal`, `currency: CurrencyCode` (`primitives.py:13-15`). Two validators plus a `display` property (`primitives.py:32-34`).
- `Percentage(DomainBaseModel)` — field `value: Decimal` (`primitives.py:37-38`). Validators reject `float` and require `Decimal.is_finite()` (`primitives.py:40-52`).
- `Quantity(DomainBaseModel)` — `value: Decimal = Field(ge=Decimal("0"))` (`primitives.py:55-56`). Rejects `float` (`primitives.py:58-63`).

### Collaborators

None. Imports are stdlib-only (`decimal.Decimal`, `typing.Annotated`) plus `pydantic` (`primitives.py:1-4`).

### Notable choices

- **Floats are rejected at the door** for `Money.amount`, `Percentage.value`, and `Quantity.value` via `mode="before"` validators that raise on `isinstance(value, float)` (`primitives.py:25-30`, `:40-45`, `:58-63`). Strings and `Decimal` are accepted (test: `packages/domain/tests/test_primitives.py:9-19`).
- `Money.validate_currency_supported` restricts currencies to the closed set `{EUR, USD, GBP, CHF, JPY}` even though the regex would accept any uppercase triple (`primitives.py:19-23`). Lowercase or 2-letter codes are rejected at the regex layer.
- `Money.display` formats as `f"{amount:.2f} {currency}"` — two decimals regardless of the underlying precision (`primitives.py:32-34`; test asserts `"1000.00 EUR"` at `tests/test_primitives.py:28-29`).
- `Percentage` does **not** enforce a range — only "finite" and "no float". Values like `-1` or `1000` pass.

```python
# primitives.py:9-23
class DomainBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Money(DomainBaseModel):
    amount: Decimal
    currency: CurrencyCode

    @field_validator("currency")
    @classmethod
    def validate_currency_supported(cls, value: str) -> str:
        supported = {"EUR", "USD", "GBP", "CHF", "JPY"}
        if value not in supported:
            raise ValueError(f"Unsupported currency code: {value}")
        return value
```

## `costs.py` — cost estimates and totals

**Path:** `packages/domain/src/portfolio_outlook_domain/costs.py` (33 lines)

### Public surface

- `CostEstimate(DomainBaseModel)` — fields `cost_estimate_id`, `cost_type: CostType`, `amount: Money`, `description_nl: str | None = None` (`costs.py:10-14`). The `_nl` suffix is the project's convention for Dutch-language user-facing text.
- `TotalCostEstimate(DomainBaseModel)` — field `costs: list[CostEstimate]` and method `total_by_currency() -> dict[str, Decimal]` (`costs.py:24-32`).

### Collaborators

- `CostType` from `.enums` (`costs.py:5`)
- `CostEstimateId` from `.identifiers` (`costs.py:6`)
- `DomainBaseModel`, `Money` from `.primitives` (`costs.py:7`)

### Notable choices

- Negative amounts on individual cost lines are explicitly forbidden — `validate_non_negative_amount` raises if `value.amount < Decimal("0")` (`costs.py:16-21`; tested at `tests/test_costs.py:18-24`).
- `total_by_currency` partitions costs **by currency without converting** — each currency gets its own bucket; no FX is performed (`costs.py:27-32`; tested at `tests/test_costs.py:45-60`).

```python
# costs.py:24-32
class TotalCostEstimate(DomainBaseModel):
    costs: list[CostEstimate]

    def total_by_currency(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for cost in self.costs:
            currency = cost.amount.currency
            totals[currency] = totals.get(currency, Decimal("0")) + cost.amount.amount
        return totals
```

## `lots.py` — paper lots and FIFO allocation

**Path:** `packages/domain/src/portfolio_outlook_domain/lots.py` (73 lines)

### Public surface

- `PaperLot(DomainBaseModel)` (`lots.py:11-23`) — represents a position-lot of a paper portfolio. Fields: `lot_id`, `portfolio_id`, `instrument_id`, `buy_transaction_id`, `buy_date: date`, `original_quantity`, `remaining_quantity`, `buy_price`, `buy_currency`, `fees_allocated: Money | None`, `cost_basis: Money`, `status: LotStatus`.
- `FifoLotAllocation(DomainBaseModel)` (`lots.py:60-66`) — allocation of a sell-transaction against a specific buy lot. Fields: `fifo_allocation_id`, `sell_transaction_id`, `lot_id`, `allocated_quantity`, `allocated_cost_basis`, `allocated_at: datetime`.

### Collaborators

`LotStatus` from `.enums` (`lots.py:6`); five IDs from `.identifiers` (`lots.py:7`); `CurrencyCode`, `DomainBaseModel`, `Money`, `Quantity` from `.primitives` (`lots.py:8`).

### Notable choices

- Validation lives in a single `@model_validator(mode="after")` (`lots.py:25-57`) enforcing six invariants on top of the field-level constraints:
  1. `original_quantity > 0` (despite `Quantity` allowing `0` in general).
  2. `0 <= remaining_quantity <= original_quantity`.
  3. `buy_currency == buy_price.currency`.
  4. `cost_basis.currency == buy_price.currency`.
  5. If `fees_allocated` is not None, its currency must match `buy_price`.
  6. **Status–quantity coupling:** `remaining == original` ⇒ `OPEN`; `0 < remaining < original` ⇒ `PARTIALLY_CLOSED`; `remaining == 0` ⇒ `CLOSED`.
- `FifoLotAllocation.validate_allocation` only checks `allocated_quantity > 0` (`lots.py:68-72`); it does **not** check the allocated lot reference, cost-basis sign, or currency.
- `buy_currency` is structurally redundant with `buy_price.currency` (the validator enforces equality). It is stored anyway, presumably for query/index reasons.
- `allocated_at: datetime` carries no timezone constraint — tests pass a naive `datetime(2026, 1, 2, 10, 0, 0)` (`tests/test_lots.py:66`).

```python
# lots.py:25-49
@model_validator(mode="after")
def validate_lot(self) -> "PaperLot":
    if self.original_quantity.value <= Decimal("0"):
        raise ValueError("original_quantity must be greater than zero.")
    if self.remaining_quantity.value < Decimal("0"):
        raise ValueError("remaining_quantity must be zero or positive.")
    if self.remaining_quantity.value > self.original_quantity.value:
        raise ValueError("remaining_quantity cannot exceed original_quantity.")

    if self.buy_currency != self.buy_price.currency:
        raise ValueError("buy_currency must match buy_price currency.")
    if self.cost_basis.currency != self.buy_price.currency:
        raise ValueError("cost_basis currency must match buy_price currency.")
```

## `identifiers.py` — typed string aliases

**Path:** `packages/domain/src/portfolio_outlook_domain/identifiers.py` (101 lines)

### Public surface

A single base alias and ~80 named aliases of that same type. All identifiers are **string aliases**, not distinct classes — there is no type-level discrimination between `PortfolioId` and `InstrumentId` at runtime.

- `SafeIdentifier = Annotated[str, StringConstraints(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]` (`identifiers.py:5-8`).
- Domain IDs (`:10-17`): `PortfolioId`, `InstrumentId`, `TransactionId`, `LotId`, `SuggestionId`, `RunId`, `SourceId`, `AuditEventId`.
- Trade / cost IDs (`:19-24`): `OrderId`, `FillId`, `LedgerEntryId`, `CostEstimateId`, `CorporateActionId`, `FifoAllocationId`.
- Approvals & execution (`:29-39`): `ApprovalRequestId`, `ApprovalDecisionId`, `ExecutionIntentId`, `ExecutionTargetId`, `BrokerReferenceId`, `BrokerOrderReferenceId`, `ResearchRunId`, `ResearchReportId`, `SourceReferenceId`, `RawDataArchiveId`, `ResearchArchiveId`.
- Data sources (`:41-44`): `DataSourceId`, `DataSourcePolicyId`, `DataSourceRequirementId`, `DataSourceRegistryId`.
- Runtime / scheduler (`:46-55`): `RuntimeServiceId`, `RuntimeTopologyId`, `StartupPlanId`, `HealthCheckId`, `BackgroundJobTypeId`, `SchedulerPlanId`, `ScheduledJobId`, `JobRunId`, `RetryPolicyId`, `JobEligibilityCheckId`.
- DQ / eligibility (`:57-60`): `DataQualityGateId`, `SuggestionEligibilityCheckId`, `SuggestionEligibilityPolicyId`, `DataFreshnessCheckId`.
- Suggestion engine (`:62-67`): `CandidateId`, `SuggestionDraftId`, `SuggestionEngineRunId`, `SuggestionGateResultId`, `RiskGateResultId`, `CostTaxImpactId`.
- Settings & API budget (`:69-76`): `SettingsProfileId`, `ExternalIntegrationId`, `SecretReferenceId`, `ApiBudgetPolicyId`, `ApiUsageSummaryId`, `ApiCostEstimateId`, `ModelPricingId`, `ApiConnectionCheckId`.
- Paper setup (`:78-80`): `PaperPortfolioSetupId`, `PaperCashAccountId`, `FirstRunSetupPreviewId`.
- Storage (`:81-89`): `StorageProfileId`, `StorageBackendId`, `StorageReadinessCheckId`, `StorageSchemaVersionId`, `StorageMigrationPlanId`, `StorageRetentionPolicyId`, `BackupPlanId`, `RestoreCheckId`, `PersistedRecordReferenceId`.
- Broker / IBKR (`:91-100`): `BrokerAccountId`, `BrokerSyncRunId`, `BrokerSnapshotId`, `BrokerPositionSnapshotId`, `BrokerCashSnapshotId`, `BrokerExecutionSnapshotId`, `BrokerCommissionSnapshotId`, `BrokerReconciliationReportId`, `BrokerReconciliationDifferenceId`, `ExternalBrokerActivityId`.

### Collaborators

None. Imports only `typing.Annotated` and `pydantic.StringConstraints` (`identifiers.py:1-3`).

### Notable choices

- All identifiers are **structurally identical at runtime** (mypy would treat them as `str`). The aliases serve as documentation, not as nominal types.
- Allowed characters: `A-Za-z0-9_-`. No dots, no colons, no `/`, no UUID curly-brace form. A raw UUID with hyphens passes; canonical UUID with braces does not. Empty strings and whitespace-only strings are rejected (`tests/test_identifiers.py:16-19`).
- The character set is **path-safe and shell-safe** — tested rejections include `"portfolio id"`, `"abc/def"`, `"https://x"`, `"abc\\def"`.

```python
# identifiers.py:5-17
SafeIdentifier = Annotated[
    str,
    StringConstraints(min_length=1, pattern=r"^[A-Za-z0-9_-]+$"),
]

PortfolioId = SafeIdentifier
InstrumentId = SafeIdentifier
TransactionId = SafeIdentifier
LotId = SafeIdentifier
SuggestionId = SafeIdentifier
RunId = SafeIdentifier
SourceId = SafeIdentifier
AuditEventId = SafeIdentifier
```

## `enums.py` — closed value sets

**Path:** `packages/domain/src/portfolio_outlook_domain/enums.py` (1181 lines, ~120 enums)

All declarations are `StrEnum` subclasses (`enums.py:1`). Because `StrEnum` instances *are* strings, every member serialises as its lowercase string value (e.g. `AssetType.CASH == "cash"`).

### Grouped public surface

- **Instrument & status:** `AssetType` (`:4-13`, 9 values incl. `CASH`, `UCITS_ETF`, `STOCK`, `TERM_DEPOSIT`, `COMMODITY_ETF_ETC`, `BLOCKED_OR_WATCH_ONLY`); `InstrumentStatus` (`:16-20`); `RiskLevel` (`:23-28`).
- **Advice / suggestion lifecycle:** `AdviceAction` (`:31-41`); `SuggestionStatus` (`:44-52`); `SuggestionDraftStatus` (`:868-874`); `SuggestionGateStatus` (`:877-881`); `SuggestionGateType` (`:884-891`); `RiskGateStatus`/`RiskGateBlockReason` (`:894-910`); `SuggestionConfidenceLevel` (`:913-917`); `SuggestionEngineRunStatus` (`:920-926`); `SuggestionDraftDecision` (`:929-934`).
- **Data quality:** `DataQualityStatus` (`:55-60`); `DataQualityGateStatus` (`:768-774`); `DataQualityIssueType` (`:777-790`); `SuggestionEligibilityStatus`/`BlockReason`/`WarningReason` (`:793-825`); `FreshnessRequirement` (`:828-837`); `DataGateDecision` (`:840-845`).
- **Tax & costs:** `TaxStatus` (`:63-71`); `CostType` (`:136-144`); `CostCurrency` (`:1014-1016`).
- **Mode:** `PaperLiveMode` (`:74-78`); `ExecutionMode` (`:219-224`).
- **Ledger / transactions / orders:** `LedgerEntryType` (`:81-93`); `TransactionSide`/`TransactionStatus` (`:96-110`); `OrderType` (`:113-115`); `OrderStatus` (`:118-127`); `LotStatus` (`:130-133`); `CorporateActionType` (`:147-156`).
- **Term deposits:** `TermDepositTerm` (`:159-163`, four values: 1M / 3M / 6M / 12M); `TermDepositStatus` (`:166-170`); `TermDepositInterestType` (`:173-175`: `FIXED_RATE`, `FIXED_AMOUNT`).
- **Capability & approvals:** `CapabilityCategory` (`:178-195`); `CapabilityStatus` (`:198-201`); `BlockedReasonCode` (`:204-216`); `ApprovalRequirement` (`:325-328`); `ApprovalDecisionStatus` (`:331-337`); `ExecutionIntentStatus` (`:340-348`); `ExecutionTargetKind` (`:317-322`).
- **Scheduler:** `ScheduleCadence` (`:227-238`); `ScheduledJobStatus` (`:241-251`); `JobSkipReason`/`JobBlockReason` (`:254-277`); `RetryBackoffPolicy` (`:280-284`); `JobPriority` (`:287-291`); `JobSafetyImpact` (`:294-299`); `JobResourceLimit` (`:302-306`); `ExecutionModeStatus` (`:309-314`).
- **Broker / IBKR / reconciliation:** `BrokerProvider`, `BrokerAccountMode`, `BrokerSystem`, `BrokerConnectionStatus`, `BrokerSourceOfTruthStatus`, `BrokerSyncMode`, `BrokerSyncStatus`, `BrokerDataKind`, `BrokerActivityOrigin`, `ReconciliationStatus`, `ReconciliationDifferenceKind`, `ReconciliationSeverity`, `BrokerSuggestionPolicy` (`:351-474`); IBKR specifics: `IBKRDataSourceType`, `IBKRSecurityType`, `IBKRMarketDataPermissionStatus`, `IBKRTradingPermissionStatus`, `IBKROrderTransmissionStatus`, `IBKRConnectionMode`, `IBKRApiGatewayKind` (`:477-529`, `:969-980`).
- **Research:** `ResearchReportStatus`, `ResearchSourceType`, `ResearchUse`, `AIResearchRole`, `PromptInjectionRisk` (`:532-581`).
- **Data sources:** `DataProviderKind`, `DataAccessMethod`, `DataCostTier`, `DataUsageStatus`, `DataUsePermission`, `DataFreshnessClass`, `DataFailurePolicy`, `SourceReliabilityTier`, `DataDomain` (`:584-669`).
- **Runtime:** `RuntimeDeploymentTarget`, `RuntimeServiceKind`, `RuntimeServiceStatus`, `RuntimeServiceCriticality`, `StartupPhase`, `StartupDependencyPolicy`, `ServiceFailurePolicy`, `RuntimeResourceProfile`, `ParallelExecutionPolicy`, `RuntimeHealthSeverity` (`:672-765`).
- **Candidates:** `CandidateSource`, `CandidateStatus` (`:848-865`).
- **OpenAI / external integration / budget:** `ExternalIntegrationKind`, `ExternalIntegrationStatus`, `SecretStorageKind`, `SecretStatus`, `OpenAIUsageSource`, `OpenAIModelPurpose`, `BudgetPeriod`, `BudgetStatus`, `ApiConnectionCheckStatus` (`:937-1024`).
- **Paper setup:** `PaperSetupStatus`, `PaperSetupMode`, `PaperPortfolioBaseCurrency` (single value `EUR`, `:1042-1043`), `PaperSetupBlockReason`, `PaperSetupWarningReason` (`:1027-1061`).
- **Storage:** `StorageBackendKind`, `StorageBackendStatus`, `PersistenceMode`, `StorageReadinessStatus`, `StorageBlockReason`, `StorageWarningReason`, `PersistedEntityKind`, `StorageSensitivity`, `RetentionCategory`, `BackupStatus`, `RestoreCheckStatus` (`:1064-1181`).

### Notable choices

- Single design conventions: UPPER_SNAKE_CASE member names; lowercase string values.
- A `BLOCKED` / `UNKNOWN` / `NOT_CONFIGURED` member is present on practically every lifecycle enum (e.g. `RiskLevel.BLOCKED` at `enums.py:28`, `OrderStatus.BLOCKED` at `:127`, `BrokerSyncStatus.BLOCKED` at `:407`, `PaperSetupStatus.BLOCKED` at `:1032`). Blocking is a first-class state across the system.
- `PaperPortfolioBaseCurrency` (`enums.py:1042-1043`) contains a **single value** `EUR = "eur"` — paper portfolios are euro-only by enum design.
- `CostCurrency` (`:1014-1016`) is a **separate enum from `CurrencyCode`** with only `USD`/`EUR` and *lowercase* values. It is used in API-cost / budget tracking, not in `Money`.
- `AssetType` includes a deliberately-blocked member `BLOCKED_OR_WATCH_ONLY` (`:13`) — assets can be marked structurally non-tradeable.

```python
# enums.py:4-13
class AssetType(StrEnum):
    CASH = "cash"
    FX = "fx"
    UCITS_ETF = "ucits_etf"
    STOCK = "stock"
    BENCHMARK = "benchmark"
    OTHER = "other"
    TERM_DEPOSIT = "term_deposit"
    COMMODITY_ETF_ETC = "commodity_etf_etc"
    BLOCKED_OR_WATCH_ONLY = "blocked_or_watch_only"
```

## `instruments.py` — instrument and ETF details

**Path:** `packages/domain/src/portfolio_outlook_domain/instruments.py` (47 lines)

### Public surface

- `Instrument(DomainBaseModel)` (`instruments.py:8-19`) — required `instrument_id`, `name`, `currency`, `asset_type`, `status`; optional `ticker`, `isin`, `exchange`, `country`, `sector`, `industry`.
- `ETFDetails(DomainBaseModel)` (`instruments.py:29-41`) — a flat bundle of optional ETF-specific fields: `accumulating`, `domicile`, `replication_method`, `fund_size: Money | None`, `ter: Percentage | None`, `tracking_difference: Percentage | None`, `listing_currency`, `exposure_currency`, `currency_hedged`, `tob_tax_category`, `benchmark_index`, `provider`. **Every field is optional.**
- `InstrumentWithDetails(DomainBaseModel)` (`instruments.py:44-46`) — composes `instrument: Instrument` and `etf_details: ETFDetails | None`.

### Collaborators

`AssetType`, `InstrumentStatus` from `.enums` (`instruments.py:3`); `InstrumentId` from `.identifiers` (`:4`); `CurrencyCode`, `DomainBaseModel`, `Money`, `Percentage` from `.primitives` (`:5`).

### Notable choices

- The only validator is `validate_name`, which rejects empty/whitespace-only names (`instruments.py:21-26`; tested at `tests/test_instruments.py:14-22`).
- `tob_tax_category` is a free-string field (`:40`) — TOB is the Belgian transaction tax; the category is not enum-typed here, suggesting it is filled by a categoriser elsewhere.
- `ETFDetails` distinguishes `listing_currency` from `exposure_currency` — explicit awareness that the trading currency and underlying-exposure currency can differ.
- `replication_method` is `str | None`, not enum-typed.

```python
# instruments.py:29-46
class ETFDetails(DomainBaseModel):
    accumulating: bool | None = None
    domicile: str | None = None
    replication_method: str | None = None
    fund_size: Money | None = None
    ter: Percentage | None = None
    tracking_difference: Percentage | None = None
    listing_currency: CurrencyCode | None = None
    exposure_currency: CurrencyCode | None = None
    currency_hedged: bool | None = None
    tob_tax_category: str | None = None
    benchmark_index: str | None = None
    provider: str | None = None


class InstrumentWithDetails(DomainBaseModel):
    instrument: Instrument
    etf_details: ETFDetails | None = None
```

## `term_deposits.py` — fixed-term deposits

**Path:** `packages/domain/src/portfolio_outlook_domain/term_deposits.py` (114 lines)

### Public surface

- `TermDepositInput(DomainBaseModel)` (`term_deposits.py:11-24`) — user-supplied term-deposit definition. Fields: `term_deposit_id`, `portfolio_id`, `bank_name`, `name`, `principal: Money`, `start_date: date`, `term: TermDepositTerm`, `interest_type: TermDepositInterestType`, `gross_interest_rate: Percentage | None`, `gross_interest_amount: Money | None`, `costs: Money`, `estimated_taxes: Money`, `status: TermDepositStatus`.
- `TermDepositProjection(DomainBaseModel)` (`term_deposits.py:77-92`) — computed projection. Fields: `term_deposit_id`, `portfolio_id`, `bank_name`, `name`, `principal`, `start_date`, `maturity_date`, `term`, `gross_interest`, `costs`, `estimated_taxes`, `net_interest`, `expected_maturity_value`, `days_until_maturity: int`, `status`.

### Collaborators

`TermDepositInterestType`, `TermDepositStatus`, `TermDepositTerm` from `.enums` (`term_deposits.py:6`); `PortfolioId`, `TermDepositId` from `.identifiers` (`:7`); `DomainBaseModel`, `Money`, `Percentage` from `.primitives` (`:8`).

### Notable choices

- **Discriminated interest model.** `interest_type` selects which of the two interest fields must be populated and which must be `None`. The cross-field rule is enforced in `validate_interest_and_currency_rules` (`term_deposits.py:47-74`):
  - `FIXED_RATE` ⇒ `gross_interest_rate` required (non-negative), `gross_interest_amount` must be `None`.
  - `FIXED_AMOUNT` ⇒ `gross_interest_amount` required (non-negative, same currency as principal), `gross_interest_rate` must be `None`.
- **Currency homogeneity.** Inputs require `costs.currency` and `estimated_taxes.currency` to match `principal.currency` (`:49-52`). Projections require all six Money fields to share a single currency, checked via a set-cardinality test (`:102-111`).
- `principal` must be **strictly positive** (`:33-38`), while `costs` and `estimated_taxes` must be `>= 0`.
- `TermDepositProjection.maturity_date` must be **strictly after** `start_date`, and `days_until_maturity >= 0` (`:94-100`). `net_interest` may be negative — the test asserts `net_interest.amount == -12` with no validation error (`tests/test_term_deposits.py:90,95`), so cost-heavy term deposits can produce a loss projection legitimately.
- The `TermDepositTerm` enum is closed to four discrete terms (1/3/6/12 months); there is no notion of arbitrary day counts at the input layer.

```python
# term_deposits.py:94-113
@model_validator(mode="after")
def validate_projection_rules(self) -> "TermDepositProjection":
    if self.maturity_date <= self.start_date:
        raise ValueError("maturity_date must be after start_date.")

    if self.days_until_maturity < 0:
        raise ValueError("days_until_maturity cannot be negative.")

    currencies = {
        self.principal.currency,
        self.gross_interest.currency,
        self.costs.currency,
        self.estimated_taxes.currency,
        self.net_interest.currency,
        self.expected_maturity_value.currency,
    }
    if len(currencies) != 1:
        raise ValueError("All Money values must use the same currency as principal.")

    return self
```

## Cross-cutting observations

- **Dependency graph (one-way, no cycles):** `enums.py` / `identifiers.py` / `primitives.py` are leaves. `costs.py`, `lots.py`, `instruments.py`, `term_deposits.py` each import from those three and nothing else within the package.
- **Money model:** there is no `+` / `-` / `*` operator overloading on `Money`. Aggregation lives in callers (e.g. `TotalCostEstimate.total_by_currency` at `costs.py:27-32`). There is no FX conversion in any of the seven files.
- **Frozen everywhere:** `DomainBaseModel(model_config=ConfigDict(frozen=True))` (`primitives.py:9-10`) propagates immutability to all six other modules' models. Combined with no float in `Money` / `Percentage` / `Quantity`, the package has a "value-object with Decimal money" character.
- **Belgian-flavoured fingerprints:** `CostType.TOB_ESTIMATE` (`enums.py:138`); `ETFDetails.tob_tax_category` (`instruments.py:40`); `CostEstimate.description_nl` (`costs.py:14`); paper portfolios euro-only (`enums.py:1042-1043`).

## Open questions / uncertainty

- `Percentage` has no range constraint by design — whether the `> 100` and `< 0` cases are intentional permissive behaviour or an oversight is unclear from the code alone. Both are observed in tests for the calling modules (e.g. `Percentage(value=Decimal("-12"))` is not constructed in `tests/test_primitives.py`; documenting this would require Phase 1c gap analysis).
- `lots.PaperLot.allocated_at` and `FifoLotAllocation.allocated_at` accept naive datetimes; whether the system normalises to UTC at a boundary or relies on caller discipline is not visible from `lots.py` alone (would need cross-module tracing during T-007 / T-011).
- `identifiers.SafeIdentifier` aliases are nominally distinct but structurally identical — whether downstream code relies on the nominal distinction (e.g. via `cast` or static checking) is out of scope for this doc.
