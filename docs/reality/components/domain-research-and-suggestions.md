# `packages/domain` — research and suggestions

**Phase:** 1a (reality components)
**Task:** T-001
**Scope:** nine modules in `packages/domain/src/portfolio_outlook_domain/` that carry research artefacts, data-source policy, data-quality gating, and the candidate-to-suggestion pipeline.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `suggestion_engine.py` — pipeline of candidate → gates → risk → cost → draft.
- `suggestions.py` — `ActionSuggestion` (typed, structured).
- `research.py` — `ResearchRun`, `ResearchReport`, `ResearchFinding`.
- `research_library.py` — user research library (uploads, URLs, notes, classifications).
- `research_suggestions.py` — parallel, string-id-keyed research / suggestion vocabulary; largest in this group.
- `quantitative_research.py` — historical OHLC contracts and probability estimates.
- `data_quality.py` — freshness checks, issues, gates, policy.
- `data_sources.py` — source / policy / requirement / registry.
- `sources.py` — `SourceReference`, archive references.

All models in this group inherit `DomainBaseModel` (`primitives.py:9-10`), so they are frozen. `SafeIdentifier` from `identifiers.py:5-8` enforces `^[A-Za-z0-9_-]+$` on every typed `*Id`; `research_suggestions.py` and `research_library.py` use raw `str` ids instead.

## `suggestion_engine.py` — candidate-to-draft pipeline

**Path:** `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py` (334 lines)

### Public surface

- `SuggestionCandidate` (`:37`) — fields `candidate_id`, `instrument_id`, `source: CandidateSource`, `status: CandidateStatus`, `research_report_id?`, `source_reference_ids: list`, `audit_event_ids: list`, `explanation_nl`, `created_at`.
- `SuggestionGateResult` (`:59`) — `suggestion_gate_result_id`, `gate_type`, `status`, `block_reasons_nl`, `warning_reasons_nl`, `source_reference_ids`, `audit_event_ids`, `explanation_nl`, `checked_at`.
- `RiskGateResult` (`:90`) — `risk_gate_result_id`, `status`, `block_reasons: list[RiskGateBlockReason]`, `warning_reasons_nl`, `explanation_nl`, `checked_at`.
- `CostTaxImpactPlaceholder` (`:116`) — `cost_tax_impact_id`, `status`, `estimated_costs_available`, `estimated_taxes_available`, `explanation_nl`, `checked_at`.
- `SuggestionEngineRun` (`:134`) — `suggestion_engine_run_id`, `status`, `candidate_ids`, `scheduler_job_run_id?`, `started_at`, `completed_at?`, `explanation_nl`.
- `ActionSuggestionDraft` (`:163`) — the heavy aggregate. Fields: `suggestion_draft_id`, `candidate_id`, `instrument_id`, `action: AdviceAction`, `status`, `confidence`, `gate_result_ids`, `risk_gate_result_id`, `cost_tax_impact_id?`, `suggestion_eligibility_check_id`, `source_reference_ids`, `audit_event_ids`, `title_nl`, `summary_nl`, `reason_nl`, `risk_nl`, `next_step_nl`, `created_at`.
- Helpers: `build_passed_gate_result` (`:203`); `build_blocked_gate_result` (`:223`); `gate_result_blocks_suggestion` (`:241`); `risk_gate_blocks_suggestion` (`:245`); `decide_suggestion_draft_outcome` (`:249`); `build_action_suggestion_draft` (`:280`).

### Collaborators

`SuggestionEligibilityCheck` from `.eligibility`; eleven enums from `.enums`; many `*Id` aliases from `.identifiers`; `DomainBaseModel` from `.primitives` (`:1-34`).

### Notable choices

- Dutch audit fields enforced everywhere (`explanation_nl`, `title_nl`, etc. validated non-empty).
- `SuggestionGateResult` cross-checks status vs reasons (`:70-87`): `PASSED` forbids any reasons AND requires sources + audit events; `WARNING` allows only `warning_reasons_nl`; `BLOCKED`/`FAILED` require `block_reasons_nl`.
- `SuggestionCandidate.validate_model` allows missing `source_reference_ids` only when `source is CandidateSource.MANUAL_USER_INPUT` (`:48-56`).
- `ActionSuggestionDraft` forbids constructing with `status=CONVERTED_TO_APPROVAL_REQUEST` or `action=BLOCKED` at creation time (`:185-188`).
- `decide_suggestion_draft_outcome` is a layered short-circuit decision tree: SKIP/FAIL/BLOCK from eligibility, then BLOCK from any gate/risk/cost, then CREATE_WITH_WARNING if any warning bubbles up, else CREATE_DRAFT (`:249-277`).
- `build_action_suggestion_draft` filters `gate_result_ids` to only PASSED/WARNING gates (`:310-314`).

```python
# suggestion_engine.py:70-87
@model_validator(mode="after")
def validate_model(self) -> "SuggestionGateResult":
    if not self.explanation_nl.strip():
        raise ValueError("explanation_nl is verplicht")
    if self.status is SuggestionGateStatus.PASSED:
        if self.block_reasons_nl or self.warning_reasons_nl:
            raise ValueError("passed mag geen redenen hebben")
        if not self.source_reference_ids or not self.audit_event_ids:
            raise ValueError("passed vereist source_reference_ids en audit_event_ids")
```

```python
# suggestion_engine.py:256-277
if eligibility_check.status is SuggestionEligibilityStatus.SKIPPED:
    return SuggestionDraftDecision.SKIP
if eligibility_check.status is SuggestionEligibilityStatus.FAILED:
    return SuggestionDraftDecision.FAIL
if eligibility_check.status is SuggestionEligibilityStatus.BLOCKED:
    return SuggestionDraftDecision.BLOCK
if any(gate_result_blocks_suggestion(gate) for gate in gate_results):
    return SuggestionDraftDecision.BLOCK
```

## `suggestions.py` — structured `ActionSuggestion`

**Path:** `packages/domain/src/portfolio_outlook_domain/suggestions.py` (40 lines)

### Public surface

Single class `ActionSuggestion` (`:10`). Fields: `suggestion_id`, `portfolio_id`, `instrument_id`, `action: AdviceAction`, `status: SuggestionStatus`, `suggested_amount: Money | None`, `suggested_quantity: Quantity | None`, `target_price: Money | None`, `reason_nl`, `risk_level: RiskLevel`, `confidence: Percentage | None`, `data_quality_status: DataQualityStatus`, `created_at`, `expires_at?` (`:10-24`).

### Collaborators

`AdviceAction`, `DataQualityStatus`, `RiskLevel`, `SuggestionStatus` from `.enums`; `InstrumentId`, `PortfolioId`, `SuggestionId` from `.identifiers`; `DomainBaseModel`, `Money`, `Percentage`, `Quantity` from `.primitives` (`:1-7`).

### Notable choices

- Keyed by `SuggestionId` with portfolio/instrument FKs and optional monetary triple (amount / quantity / target_price). Carries `data_quality_status` snapshot — the row records gate state at creation time.
- `validate_reason_nl` enforces non-empty Dutch reason (`:26-31`).
- `validate_blocked_pairing` enforces that `action=BLOCKED` is only allowed alongside `status ∈ {BLOCKED_BY_RISK, BLOCKED_BY_DATA_QUALITY}` (`:33-40`).
- **Naming collision:** this `ActionSuggestion` is *different* from the one in `research_suggestions.py:479`. They share no fields; this one uses `Money` / `Quantity` value objects and structured IDs, while the other uses raw strings and Dutch enums.

```python
# suggestions.py:33-40
@model_validator(mode="after")
def validate_blocked_pairing(self) -> "ActionSuggestion":
    if self.action == AdviceAction.BLOCKED and self.status not in {
        SuggestionStatus.BLOCKED_BY_RISK,
        SuggestionStatus.BLOCKED_BY_DATA_QUALITY,
    }:
        raise ValueError("Blocked action requires a blocked status.")
    return self
```

## `research.py` — research run / report / finding

**Path:** `packages/domain/src/portfolio_outlook_domain/research.py` (86 lines)

### Public surface

- `ResearchRun` (`:22`) — `research_run_id`, `portfolio_id?`, `instrument_id?`, `research_use: ResearchUse`, `status: ResearchReportStatus`, `started_at`, `completed_at?`, `source_reference_ids`, `data_quality_status`, `prompt_template_version?`, `model_name?` (`:22-33`).
- `ResearchReport` (`:42`) — `research_report_id`, `research_run_id`, `instrument_id?`, `status`, `ai_role: AIResearchRole`, `summary_nl`, `opportunity_summary_nl?`, `risk_summary_nl?`, `missing_data_warnings_nl`, `source_reference_ids`, `input_hash?`, `output_hash?`, `created_at`, `data_quality_status`, `prompt_injection_risk` (`:42-57`).
- `ResearchFinding` (`:81`) — `research_report_id`, `label_nl`, `detail_nl`, `source_reference_ids`, `confidence: Percentage?` (`:81-86`).

### Collaborators

`AIResearchRole`, `DataQualityStatus`, `PromptInjectionRisk`, `ResearchReportStatus`, `ResearchUse` from `.enums`; multiple ID aliases from `.identifiers`; `DomainBaseModel`, `Percentage` from `.primitives` (`:5-19`).

### Notable choices

- Both `input_hash` and `output_hash` on `ResearchReport` (`:53-54`) model deterministic provenance / dedup hashes (`str | None`; no algorithm fixed). `ResearchRun` FK-links to portfolio / instrument and an array of `source_reference_ids`.
- Three-table shape: run → report → finding (findings carry only `research_report_id` FK, no own id).
- `ResearchRun.validate_completed`: status `COMPLETED` requires `completed_at` to be set (`:35-39`).
- `ResearchReport.validate_report` cross-validates AI safety: `prompt_injection_risk == BLOCKED` must pair with status `BLOCKED_BY_POLICY`; `data_quality_status == FAILED` cannot be `COMPLETED` (`:66-78`).
- This `ResearchRun` is a **different model** from the `ResearchRun` in `research_suggestions.py:418` (which uses raw `str` IDs and tracks token / cost).

```python
# research.py:66-78
@model_validator(mode="after")
def validate_report(self) -> "ResearchReport":
    if (
        self.prompt_injection_risk == PromptInjectionRisk.BLOCKED
        and self.status != ResearchReportStatus.BLOCKED_BY_POLICY
    ):
        raise ValueError("blocked prompt injection requires blocked_by_policy status")
    if (
        self.data_quality_status == DataQualityStatus.FAILED
        and self.status == ResearchReportStatus.COMPLETED
    ):
        raise ValueError("failed data quality cannot be completed")
```

## `research_library.py` — user research library

**Path:** `packages/domain/src/portfolio_outlook_domain/research_library.py` (520+ lines)

### Public surface

Enums (all `StrEnum`): `ResearchLibrarySourceKind` (`:17`); `ResearchLibrarySourceStatus` (`:25`, 13 values); `ResearchLibraryClassificationStatus` (`:41`); `ResearchExtractionStatus` (`:49`); `ResearchAnalysisStatus` (`:58`); `ResearchDocumentSetType` (`:189`); `DocumentClassificationConfidence` (`:229`); `DeterministicDocumentCategory` (`:267`, 9 categories incl. `ANNUAL_REPORT`, `QUARTERLY_REPORT`, `ETF_FACTSHEET`, `MARKET_DATA_EXPORT`, `UNKNOWN`); `DeterministicClassificationMethod` (`:279`); `ResearchLibraryReadinessStatus` (`:383`).

Models: `ResearchLibrarySource` (`:68`); `UploadedResearchFileMetadata` (`:102`); `ResearchUrlMetadata` (`:137`); `UserResearchNote` (`:164`); `ResearchDocumentSet` (`:199`); `ResearchDocumentClassification` (`:236`); `DeterministicDocumentClassificationResult` (`:284`); `ResearchLibrarySourceReadiness` (`:393`); `ResearchLibraryHelpText` (`:490`).

Functions: `classify_document_deterministically(...)` (`:298`); `evaluate_research_library_source_readiness(...)` (`:404`); `get_research_library_help_texts()` (`:496`).

### Collaborators

Imports five symbols from `.research_suggestions` (`PromptInjectionAssessment`, `PromptInjectionRiskLevel`, `ResearchDocumentType`, `ResearchSourceType`, `SourceCredibilityAssessment`, `SourceCredibilityLevel`) (`:7-14`). Does **not** use the typed `*Id` aliases from `.identifiers` — `library_source_id` is a plain `str` (`:69`).

### Notable choices

- Each entity is a 1:1 row keyed by its `library_source_id` (str). `UploadedResearchFileMetadata.file_hash_sha256` (`:108`) is the canonical SHA-256 for upload dedup. `ResearchUrlMetadata.snapshot_hash_sha256` (`:143`) is a content snapshot hash.
- `ResearchDocumentSet.library_source_ids` is a `tuple[str, ...]` (frozen + hashable; ordering preserved) (`:204`). `DeterministicDocumentClassificationResult.matched_signals` is also a tuple.
- `_validate_dates` on `ResearchLibrarySource` enforces `updated_at >= created_at` and `archived_at >= created_at` (`:93-99`).
- `UploadedResearchFileMetadata._positive_optional_int` requires `file_size_bytes` and `page_count` to be strictly positive when present (`:129-134`).
- `ResearchUrlMetadata._valid_http_status` constrains to `[100, 599]` (`:156-161`).
- `ResearchDocumentSet._validate_set` rejects empty `library_source_ids`, duplicate fiscal years, and bounds fiscal year to `1900-2200` (`:217-226`).
- `ResearchDocumentClassification._low_confidence_needs_review`: LOW or UNKNOWN confidence forces `needs_user_review=True` (`:257-264`).
- `classify_document_deterministically` is **metadata-only by design**: it matches case-insensitive keywords against `title + original_file_name` and optionally extracted text, but always returns `can_be_used_in_research=False`, `can_be_used_in_suggestions=False`, `blocks_suggestions=True`, `needs_user_review=True` regardless of category (`:365-380`). Pure audit signal.
- `evaluate_research_library_source_readiness` is a multi-stage gate: archived/rejected/failed → `FAILED`; high/blocked prompt injection → `BLOCKED`; pending extraction → `WAITING_FOR_EXTRACTION`; pending analysis → `WAITING_FOR_ANALYSIS`; otherwise `READY` with `can_be_used_in_suggestions` only if no review needed and credibility not `BLOCKED` (`:415-487`).

```python
# research_library.py:365-380
return DeterministicDocumentClassificationResult(
    library_source_id=library_source_id,
    category=category,
    method=method,
    matched_signals=tuple(signals),
    confidence=confidence,
    can_be_used_in_research=False,
    can_be_used_in_suggestions=False,
    blocks_suggestions=True,
    needs_user_review=True,
    reason_nl=(
        "Deterministische classificatie is alleen metadata voor audit. "
        "Deze bron blijft geblokkeerd voor suggesties tot latere validatiegates."
    ),
```

## `research_suggestions.py` — parallel string-id research/suggestion layer

**Path:** `packages/domain/src/portfolio_outlook_domain/research_suggestions.py` (~660 lines — largest in this group)

### Public surface

Enums: `ResearchSourceType` (`:10`, 17 values); `ResearchDocumentType` (`:29`, 19 values incl. `SEC_10K`/`10Q`/`8K`/`20F`/`40F`/`6K`); `ResearchSourceStatus` (`:51`); `SourceCredibilityLevel` (`:63`); `SourceAuthorityCategory` (`:72`); `ResearchDataType` (`:85`, 15 values); `FreshnessStatus` (`:103`); `PromptInjectionRiskLevel` (`:111`); `PromptInjectionSignalType` (`:119`); `AIResearchRunStatus` (`:131`); `AIResearchUseStatus` (`:140`); `CatalystEventType` (`:149`); `CatalystImpactLevel` (`:167`); `SuggestionAction` (`:174`, Dutch values: `kopen`, `langzaam_bijkopen`, `houden`, …); `SuggestionStatus` (`:187`); `SuggestionConfidence` (`:197`); `SuggestionTimeSensitivity` (`:204`); `SuggestionBlockedReason` (`:212`, 27 values); `SuggestionOutcomeStatus` (`:241`).

Models: `ResearchSourceReference` (`:251`); `SourceCredibilityAssessment` (`:309`); `FreshnessSla` (`:325`); `FreshnessAssessment` (`:341`); `PromptInjectionSignal` (`:360`); `PromptInjectionAssessment` (`:367`); `AIResearchEvidenceItem` (`:388`); `AIResearchOutput` (`:401`); `ResearchRun` (`:418`); `CatalystEvent` (`:448`); `SuggestionValidityWindow` (`:460`); `SuggestionAuditLink` (`:470`); `ActionSuggestion` (`:479`); `SuggestionOutcomePlaceholder` (`:509`).

Functions: `default_credibility_for_source_type` (`:517`); `default_freshness_slas` (`:577`); `action_label_nl` (`:630`); `blocked_reason_label_nl` (`:645`); `freshness_status_label_nl` (`:649`); `source_credibility_label_nl` (`:653`); `suggestion_is_blocked` (`:657`); `suggestion_can_be_converted_to_ibkr_action` (`:661`).

### Collaborators

Only `.primitives.DomainBaseModel` (`:7`). Intentionally self-contained — does **not** import `.identifiers`, `.enums`, or `.research`.

### Notable choices

- All IDs are raw `str` (e.g. `source_id`, `suggestion_id`, `research_run_id`, `evidence_id`, `event_id`) — schema-less identifiers compared to `suggestions.py` / `research.py`.
- Most aggregate fields use `tuple[..., ...]` rather than `list[...]` (`AIResearchOutput.positive_evidence`, `ActionSuggestion.blocked_reasons`, `SuggestionValidityWindow.related_event_ids`, etc.) — combined with `frozen=True` this makes models fully hashable and deterministic to serialise.
- `SourceCredibilityAssessment.credibility_score` and `ResearchRun.estimated_cost` use `Decimal` (floats actively rejected — `:317-322` and `:433-438`).
- `PromptInjectionAssessment._validate_safety` enforces a hard rule: `safe_to_use_as_instruction` is **always rejected** ("external research content can never be used as instruction"); HIGH/BLOCKED risk also blocks evidence use (`:376-385`).
- `ResearchSourceReference._validate_reference` (`:277-306`) has a subtle dead branch (`ResearchSourceType.WEBPAGE if False else ResearchSourceType.UNKNOWN` at `:281` — `WEBPAGE` is a `ResearchDocumentType` not `ResearchSourceType`; the `if False` short-circuit looks like leftover code).
- `ActionSuggestion._validate_action`: `GEBLOKKEERD` action requires non-empty `blocked_reasons`; convertible suggestions cannot carry blocked reasons (`:500-506`).
- `default_credibility_for_source_type` returns a hard-coded mapping with deterministic Decimal scores (BROKER_DATA → 99, EXCHANGE_CALENDAR → 97, OFFICIAL_FILING → 88, COMPANY_REPORT → 85, ANALYST_COMMENTARY → 55, BLOG_OR_FORUM → 20, fallback → 40) and stamps `assessed_at=datetime.now(UTC)` (`:517-574`).
- `default_freshness_slas` ships canonical SLAs: broker cash/positions 300 s, market price 120 s, FX 600 s, AI research 86 400 s (1 d), action suggestion 3 600 s (`:577-627`).
- **Critical class-name collisions with other modules:** `ResearchRun` (also in `research.py:22`), `ActionSuggestion` (also in `suggestions.py:10`), `SuggestionStatus` (also in `.enums`), `SuggestionAction` ≠ `AdviceAction`.

```python
# research_suggestions.py:376-385
@model_validator(mode="after")
def _validate_safety(self) -> "PromptInjectionAssessment":
    if self.safe_to_use_as_instruction:
        raise ValueError("external research content can never be used as instruction")
    if (
        self.risk_level in {PromptInjectionRiskLevel.HIGH, PromptInjectionRiskLevel.BLOCKED}
        and self.safe_to_use_as_evidence
    ):
        raise ValueError("high/blocked injection risk cannot be safe evidence")
    return self
```

```python
# research_suggestions.py:520-540
ResearchSourceType.BROKER_DATA: (
    SourceAuthorityCategory.BROKER_TRUTH,
    SourceCredibilityLevel.HIGHEST,
    Decimal("99"),
    "Brokergegevens gelden als waarheid voor accountstatus.",
),
ResearchSourceType.EXCHANGE_CALENDAR: (
    SourceAuthorityCategory.OFFICIAL_EXCHANGE,
    SourceCredibilityLevel.HIGHEST,
    Decimal("97"),
    "Officiële beurskalender is leidend voor handelsbeschikbaarheid.",
),
```

## `quantitative_research.py` — OHLC and probability contracts

**Path:** `packages/domain/src/portfolio_outlook_domain/quantitative_research.py` (137 lines)

Module docstring: `"Quantitative research domain contracts (no runtime execution)."` (`:1`).

### Public surface

- Enums: `MarketDataProvider` (`:13`, `IBKR` + `UNKNOWN`); `HistoricalDataType` (`:18`, `TRADES` + `UNKNOWN`); `HistoricalBarSize` (`:23`, `ONE_DAY` + `UNKNOWN`); `RegularTradingHoursMode` (`:28`, `REGULAR_TRADING_HOURS_ONLY` + `UNKNOWN`).
- Models: `HistoricalDataRequestSpec` (`:33`); `HistoricalMarketBar` (`:60`); `ActionProbabilityEstimate` (`:100`); `QuantitativeResearchHelpText` (`:113`).
- `get_quantitative_research_help_texts()` (`:119`) — returns a single help-text tuple about "Verwachte bandbreedte / Dit is een scenario, geen zekerheid."

### Collaborators

`DomainBaseModel` from `.primitives`; `SuggestionAction` from `.research_suggestions` (`:9-10`).

### Notable choices

- All price fields use `mode="before"` validators to **reject floats** (`:77-82`, `:105-110`).
- `HistoricalDataRequestSpec.validate_date_order` requires `end_at > start_at` strictly (`:53-57`).
- `HistoricalMarketBar.validate_bar_order` requires `bar_end_at > bar_start_at` AND `high_price >= low_price` (`:91-97`).
- `trade_count` validation: `None` allowed, but if present must be `>= 0` (`:84-89`).
- Enums are deliberately near-empty (only one real value + `UNKNOWN`) — module is shaped for future expansion.

```python
# quantitative_research.py:77-82
@field_validator("open_price", "high_price", "low_price", "close_price", mode="before")
@classmethod
def reject_float_price(cls, value: object) -> object:
    if isinstance(value, float):
        raise ValueError("float is not allowed")
    return value
```

```python
# quantitative_research.py:91-97
@model_validator(mode="after")
def validate_bar_order(self) -> "HistoricalMarketBar":
    if self.bar_end_at <= self.bar_start_at:
        raise ValueError("bar_end_at must be after bar_start_at")
    if self.high_price < self.low_price:
        raise ValueError("high_price must be >= low_price")
    return self
```

## `data_quality.py` — freshness checks, gates, policy

**Path:** `packages/domain/src/portfolio_outlook_domain/data_quality.py` (181 lines)

### Public surface

- `DataFreshnessCheck` (`:18`) — `data_freshness_check_id`, `data_domain`, `requirement: FreshnessRequirement`, `observed_at?`, `checked_at`, `status: DataQualityGateStatus`, `issue_types: list`, `explanation_nl`.
- `DataQualityIssue` (`:48`) — `issue_type`, `data_domain`, `severity: RuntimeHealthSeverity`, `source_reference_id?`, `message_nl`, `blocks_suggestions: bool`.
- `DataQualityGate` (`:70`) — `data_quality_gate_id`, `gate_name`, `required_domains`, `freshness_checks`, `issues`, `source_reference_ids`, `status`, `decision: DataGateDecision`, `checked_at`, `explanation_nl`.
- `DataQualityPolicy` (`:109`) — `suggestion_critical_domains`, `warning_only_domains`, `accepted_warning_reasons`, `explanation_nl`.
- Helpers: `build_passed_data_quality_gate` (`:127`); `build_blocked_data_quality_gate` (`:151`); `gate_blocks_suggestions` (`:175`); `gate_allows_suggestions` (`:181`).

### Collaborators

Multiple enums from `.enums` (`DataDomain`, `DataGateDecision`, `DataQualityGateStatus`, `DataQualityIssueType`, `FreshnessRequirement`, `RuntimeHealthSeverity`, `SuggestionEligibilityWarningReason`); `DataFreshnessCheckId`, `DataQualityGateId`, `SourceReferenceId` from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- `DataQualityGate` is a row with embedded lists (`freshness_checks`, `issues`, `source_reference_ids`).
- Hard-coded sentinel IDs `"data_quality_gate_passed"` / `"data_quality_gate_blocked"` used by the builders (`:138`, `:162`) — not unique per run (probably intended for tests/factories rather than persistence).
- `DataQualityGate.validate_gate` enforces three-way consistency between `status`, `decision`, and issue blocking (`:82-106`): any issue with `blocks_suggestions=True` requires gate status `BLOCKED`/`FAILED` AND decision `BLOCK_SUGGESTION`/`FAIL_JOB`; `PASSED` + `CONTINUE_ALLOWED` requires non-empty `source_reference_ids`.
- `DataQualityIssue.validate_issue` enforces that `CRITICAL` severity must block, and `SOURCE_NOT_TRACEABLE` issue type must always block (`:56-67`).
- `DataFreshnessCheck.validate_check`: `requirement=IMMEDIATE` with `observed_at=None` cannot be `PASSED` (`:39-44`).
- `DataQualityPolicy.validate_policy` rejects overlap between `suggestion_critical_domains` and `warning_only_domains` (`:115-124`).

```python
# data_quality.py:93-106
blocking_issue = any(issue.blocks_suggestions for issue in self.issues)
if blocking_issue:
    if self.status not in {DataQualityGateStatus.BLOCKED, DataQualityGateStatus.FAILED}:
        raise ValueError("blocking issue vereist blocked of failed status")
    if self.decision not in {DataGateDecision.BLOCK_SUGGESTION, DataGateDecision.FAIL_JOB}:
        raise ValueError("blocking issue vereist block_suggestion of fail_job")
if (
    self.decision is DataGateDecision.BLOCK_SUGGESTION
    and self.status is not DataQualityGateStatus.BLOCKED
):
    raise ValueError("block_suggestion vereist blocked status")
if not self.source_reference_ids and self.decision is DataGateDecision.CONTINUE_ALLOWED:
    raise ValueError("continue_allowed vereist source traceability")
```

## `data_sources.py` — sources, policies, registry

**Path:** `packages/domain/src/portfolio_outlook_domain/data_sources.py` (~250 lines)

### Public surface

- `DataSourcePolicy` (`:27`) — `data_source_policy_id`, `usage_status`, `reliability_tier`, `allowed_uses`, `requires_manual_review`, `requires_license_review`, `legal_review_status_nl`, `notes_nl`.
- `DataSourceRequirement` (`:61`) — `data_source_requirement_id`, `name`, `data_domain`, `use_permission`, `freshness_class`, `failure_policy`, `notes_nl`.
- `DataSourceDefinition` (`:86`) — `data_source_id`, `name`, `provider_kind`, `data_domains`, `access_method`, `cost_tier`, `policy: DataSourcePolicy`, `source_url?`, `raw_data_archive_id?`, `research_archive_id?`, `notes_nl`.
- `DataSourceRegistry` (`:128`) — `data_source_registry_id`, `created_at`, `sources: list[DataSourceDefinition]`, `requirements: list[DataSourceRequirement]`.
- Helpers: `can_use_source_for` (`:145`); `requires_block_when_missing` (`:149`); `find_sources_for_domain` (`:153`); `build_default_data_source_registry(created_at)` (`:160`) — returns 18 hard-coded sources and 3 hard-coded requirements.

### Collaborators

Nine enums from `.enums`; identifier aliases for archive/source/policy/requirement/registry IDs from `.identifiers`; `DomainBaseModel` from `.primitives` (`:5-24`).

### Notable choices

- `DataSourceDefinition.validate_source_url` rejects URLs containing `apikey=`, `token=`, `secret=` substrings (case-insensitive) — guard against committing credentials (`:99-109`).
- `DataSourcePolicy.validate_policy` couples policy state to permissions (`:37-58`): `BLOCKED` status forbids `allowed_uses`; `REVIEW_REQUIRED` requires at least one of the review flags; granting `SUGGESTION_ELIGIBILITY` requires `usage_status ∈ {ALLOWED, ALLOWED_WITH_LIMITS}` AND `reliability_tier ∉ {UNKNOWN, UNVERIFIED}`.
- `DataSourceDefinition.validate_source` forbids `PUBLIC_NEWS` / `PUBLIC_WEBSITE` provider kinds from being usable for `SUGGESTION_ELIGIBILITY` (`:117-124`).
- `DataSourceRequirement.validate_requirement` forbids `IGNORE_IF_OPTIONAL` failure policy on `SUGGESTION_ELIGIBILITY` or `PORTFOLIO_VALUATION` uses (`:70-82`).
- Registry-level validation deduplicates source IDs and requirement IDs (`:134-142`). The `build_default_data_source_registry` function provides seed data for 18 well-known sources (IBKR contract/account/order/market, SEC EDGAR, ECB, FRED, ETF factsheet, KID/KIID, ETF holdings, exchange public, press releases, public news, central bank announcements, manual input, internal ledger, internal research, public website, paid vendor placeholder).

```python
# data_sources.py:99-109
@field_validator("source_url")
@classmethod
def validate_source_url(cls, value: str | None) -> str | None:
    if value is None:
        return value
    if not value.strip():
        raise ValueError("source_url mag niet leeg zijn")
    lowered = value.lower()
    if "apikey=" in lowered or "token=" in lowered or "secret=" in lowered:
        raise ValueError("source_url mag geen secrets bevatten")
    return value
```

## `sources.py` — source and archive references

**Path:** `packages/domain/src/portfolio_outlook_domain/sources.py` (75 lines)

### Public surface

- `SourceReference` (`:10`) — `source_reference_id`, `source_type: ResearchSourceType`, `title`, `publisher?`, `url?`, `retrieved_at`, `source_published_at?`, `content_hash?`, `raw_data_archive_id?`, `data_quality_status`, `prompt_injection_risk`.
- `RawDataArchiveReference` (`:38`) — `raw_data_archive_id`, `source_type`, `storage_path`, `content_hash`, `received_at`, `data_time?`, `schema_version`, `data_quality_status`.
- `ResearchArchiveReference` (`:58`) — `research_archive_id`, `research_run_id`, `storage_path`, `content_hash`, `created_at`, `schema_version`.

### Collaborators

`DataQualityStatus`, `PromptInjectionRisk`, `ResearchSourceType` from `.enums`; four identifier aliases from `.identifiers`; `DomainBaseModel` from `.primitives` (`:1-7`). Note: this `ResearchSourceType` lives in `.enums`, distinct from the one in `research_suggestions.py:10`.

### Notable choices

- Each is a row keyed by its own `*Id`. `content_hash` is the canonical content-addressable pointer for archive rows. `storage_path` is the blob-store/file-system path.
- `SourceReference.raw_data_archive_id` is an optional FK linking citation to its archived raw bytes.
- `RawDataArchiveReference.validate_required_strings` enforces non-empty AND scans for `token=`, `apikey`, `secret` substrings in `storage_path` / `content_hash` / `schema_version` — same secret-leak guard pattern as `data_sources.py` (`:48-55`).
- `ResearchArchiveReference` validates required strings but **does not** apply the secret-leak scan (`:66-71`) — asymmetric with `RawDataArchiveReference`.
- `SourceReference.validate_optional_nonempty` enforces that optional `url`/`content_hash` cannot be empty strings (None or non-empty) (`:30-35`).

```python
# sources.py:48-55
@field_validator("storage_path", "content_hash", "schema_version")
@classmethod
def validate_required_strings(cls, value: str) -> str:
    if not value.strip():
        raise ValueError("required string field cannot be empty")
    if "token=" in value.lower() or "apikey" in value.lower() or "secret" in value.lower():
        raise ValueError("storage/content fields must not contain secrets")
    return value
```

## Cross-cutting observations

- **Two parallel "domain layers" coexist.** A typed layer using `.identifiers` `*Id` aliases + `.enums` (used by `suggestion_engine.py`, `suggestions.py`, `research.py`, `data_quality.py`, `data_sources.py`, `sources.py`) and a string-id layer using its own enums (used by `research_suggestions.py`, `research_library.py`, `quantitative_research.py`). The latter is largely self-contained.
- **Class-name collisions across files** (same name, different shape):
  - `ActionSuggestion`: `suggestions.py:10` vs `research_suggestions.py:479`.
  - `ResearchRun`: `research.py:22` vs `research_suggestions.py:418`.
  - `ResearchSourceType`: `.enums` (used by `sources.py:5`) vs `research_suggestions.py:10`.
- **All models frozen** via `DomainBaseModel = BaseModel + ConfigDict(frozen=True)` (`primitives.py:9-10`). Combined with `tuple[...]` collections in `research_suggestions.py` / `research_library.py`, those models are hashable.
- **Float-rejection is a recurring contract.** Prices, money amounts, credibility scores, probability scores, and estimated costs all explicitly reject `float` in `mode="before"` validators (`primitives.py:25-29`, `research_suggestions.py:317-322`, `research_suggestions.py:433-438`, `quantitative_research.py:77-82`, `quantitative_research.py:105-110`).
- **Secret-substring guards** in `data_sources.py:107-108` and `sources.py:53-54`, but **missing from `ResearchArchiveReference`** (`sources.py:66-71`).
- **Dutch (`*_nl`) explanation fields are mandatory** across nearly every model — explicit audit/UX requirement encoded in validators.
- **Provenance plumbing is dense:** `SourceReferenceId` arrays, `AuditEventId` arrays, `input_hash`/`output_hash` on reports, `content_hash` on archive refs, `file_hash_sha256` / `snapshot_hash_sha256` on library uploads, `matched_signals` tuples on deterministic classifications.

## Open questions / uncertainty

- The two parallel research/suggestion layers (typed vs string-id) appear to address different use cases — confirming the intent of the duplication (whether one is meant to deprecate the other) requires Phase 1b architecture review.
- `research_suggestions.py:281` contains `if False else ResearchSourceType.UNKNOWN` — looks like dead code path. Whether this is intentional placeholder or leftover refactor is unclear from the file alone.
- `ResearchArchiveReference` (`sources.py:58-72`) is asymmetric with `RawDataArchiveReference` (`:38-55`) — only the latter scans for secrets in storage paths. Whether this is a deliberate choice or an oversight is unclear; would be a Phase 1d finding if classified as risky.
- `DataQualityGate` builders use hard-coded sentinel IDs `"data_quality_gate_passed"` / `"data_quality_gate_blocked"` (`data_quality.py:138`, `:162`). Whether downstream code persists these as-is or generates per-run IDs is out of scope for this Phase 1a doc.
