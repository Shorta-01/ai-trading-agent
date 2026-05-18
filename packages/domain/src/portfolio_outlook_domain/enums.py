from enum import StrEnum


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


class InstrumentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELISTED = "delisted"
    BLOCKED = "blocked"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    BLOCKED = "blocked"


class AdviceAction(StrEnum):
    BUY = "buy"
    SLOWLY_BUY = "slowly_buy"
    HOLD = "hold"
    WATCH = "watch"
    REDUCE = "reduce"
    SELL = "sell"
    AVOID = "avoid"
    KEEP_CASH = "keep_cash"
    NO_ACTION = "no_action"
    BLOCKED = "blocked"


class SuggestionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ACCEPTED = "accepted"
    REJECTED_BY_USER = "rejected_by_user"
    BLOCKED_BY_RISK = "blocked_by_risk"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    CONVERTED_TO_PAPER_ORDER = "converted_to_paper_order"
    NO_ACTION = "no_action"


class DataQualityStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    FAILED = "failed"
    STALE = "stale"
    UNKNOWN = "unknown"


class TaxStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    ESTIMATED = "estimated"
    NEEDS_REVIEW = "needs_review"
    READY_TO_DECLARE = "ready_to_declare"
    DECLARED = "declared"
    PAID = "paid"
    BROKER_HANDLED = "broker_handled"
    PROOF_STORED = "proof_stored"


class PaperLiveMode(StrEnum):
    PAPER = "paper"
    LIVE_READ_ONLY = "live_read_only"
    LIVE_MANUAL_APPROVAL = "live_manual_approval"
    LIVE_AUTOMATION_BLOCKED = "live_automation_blocked"


class LedgerEntryType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    DISTRIBUTION = "distribution"
    FEE = "fee"
    TAX_ESTIMATE = "tax_estimate"
    FX_CONVERSION = "fx_conversion"
    CASH_ADJUSTMENT = "cash_adjustment"
    CORPORATE_ACTION = "corporate_action"
    REBALANCE_ACTION = "rebalance_action"


class TransactionSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class TransactionStatus(StrEnum):
    DRAFT = "draft"
    SUGGESTED = "suggested"
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(StrEnum):
    SUGGESTED = "suggested"
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class LotStatus(StrEnum):
    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"


class CostType(StrEnum):
    BROKER_FEE = "broker_fee"
    TOB_ESTIMATE = "tob_estimate"
    FX_COST = "fx_cost"
    SPREAD_ESTIMATE = "spread_estimate"
    SLIPPAGE_ESTIMATE = "slippage_estimate"
    WITHHOLDING_TAX_ESTIMATE = "withholding_tax_estimate"
    OTHER = "other"
    TERM_DEPOSIT = "term_deposit"


class CorporateActionType(StrEnum):
    DIVIDEND = "dividend"
    DISTRIBUTION = "distribution"
    SPLIT = "split"
    REVERSE_SPLIT = "reverse_split"
    SPECIAL_DIVIDEND = "special_dividend"
    MERGER = "merger"
    SPIN_OFF = "spin_off"
    TICKER_CHANGE = "ticker_change"
    DELISTING = "delisting"


class TermDepositTerm(StrEnum):
    ONE_MONTH = "one_month"
    THREE_MONTHS = "three_months"
    SIX_MONTHS = "six_months"
    TWELVE_MONTHS = "twelve_months"


class TermDepositStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    MATURED = "matured"
    CANCELLED = "cancelled"


class TermDepositInterestType(StrEnum):
    FIXED_RATE = "fixed_rate"
    FIXED_AMOUNT = "fixed_amount"


class CapabilityCategory(StrEnum):
    CASH = "cash"
    TERM_DEPOSIT = "term_deposit"
    UCITS_ETF = "ucits_etf"
    STOCK = "stock"
    FX = "fx"
    BENCHMARK = "benchmark"
    COMMODITY_ETF_ETC = "commodity_etf_etc"
    FUTURES = "futures"
    OPTIONS = "options"
    LEVERAGE = "leverage"
    SHORT_SELLING = "short_selling"
    CRYPTO = "crypto"
    PENNY_STOCK = "penny_stock"
    COMPLEX_DERIVATIVE = "complex_derivative"
    HIGH_FREQUENCY_TRADING = "high_frequency_trading"
    AUTOMATIC_REAL_MONEY_EXECUTION = "automatic_real_money_execution"
    UNKNOWN = "unknown"


class CapabilityStatus(StrEnum):
    ALLOWED = "allowed"
    WATCH_ONLY = "watch_only"
    BLOCKED = "blocked"


class BlockedReasonCode(StrEnum):
    NOT_ALLOWED_IN_VERSION_1 = "not_allowed_in_version_1"
    COMPLEX_DERIVATIVE = "complex_derivative"
    LEVERAGE_NOT_ALLOWED = "leverage_not_allowed"
    SHORT_SELLING_NOT_ALLOWED = "short_selling_not_allowed"
    CRYPTO_NOT_ALLOWED = "crypto_not_allowed"
    PENNY_STOCK_NOT_ALLOWED = "penny_stock_not_allowed"
    HFT_NOT_ALLOWED = "hft_not_allowed"
    REAL_MONEY_EXECUTION_BLOCKED = "real_money_execution_blocked"
    REQUIRES_FUTURE_EXPLICIT_APPROVAL = "requires_future_explicit_approval"
    UNKNOWN_OR_UNSUPPORTED = "unknown_or_unsupported"
    OIL_PRODUCT_EXTRA_RISK = "oil_product_extra_risk"
    DIRECT_COMMODITY_OR_FUTURE_BLOCKED = "direct_commodity_or_future_blocked"


class ExecutionMode(StrEnum):
    INTERNAL_PAPER = "internal_paper"
    IBKR_PAPER = "ibkr_paper"
    IBKR_LIVE_READ_ONLY = "ibkr_live_read_only"
    IBKR_LIVE_MANUAL = "ibkr_live_manual"
    BLOCKED_AUTO = "blocked_auto"


class ScheduleCadence(StrEnum):
    MANUAL = "manual"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_15_MINUTES = "every_15_minutes"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    EVENT_DRIVEN = "event_driven"
    DISABLED = "disabled"


class ScheduledJobStatus(StrEnum):
    PLANNED = "planned"
    ELIGIBLE = "eligible"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"
    DISABLED = "disabled"


class JobSkipReason(StrEnum):
    SERVICE_UNHEALTHY = "service_unhealthy"
    DATA_STALE = "data_stale"
    DATA_MISSING = "data_missing"
    SOURCE_NOT_ALLOWED = "source_not_allowed"
    MARKET_CLOSED = "market_closed"
    OUTSIDE_SCHEDULE = "outside_schedule"
    RESOURCE_LIMIT = "resource_limit"
    DEPENDENCY_NOT_READY = "dependency_not_ready"
    MANUAL_PAUSE = "manual_pause"
    DISABLED = "disabled"
    NOT_APPLICABLE = "not_applicable"


class JobBlockReason(StrEnum):
    REQUIRED_SERVICE_UNHEALTHY = "required_service_unhealthy"
    REQUIRED_DATA_MISSING = "required_data_missing"
    DATA_QUALITY_FAILED = "data_quality_failed"
    SOURCE_USAGE_NOT_ALLOWED = "source_usage_not_allowed"
    RISK_POLICY_BLOCK = "risk_policy_block"
    EXECUTION_MODE_BLOCK = "execution_mode_block"
    MISSING_AUDIT_LINK = "missing_audit_link"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    SYSTEM_NOT_READY = "system_not_ready"


class RetryBackoffPolicy(StrEnum):
    NONE = "none"
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL = "exponential"
    MANUAL_ONLY = "manual_only"


class JobPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class JobSafetyImpact(StrEnum):
    READ_ONLY = "read_only"
    MAY_UPDATE_RESEARCH = "may_update_research"
    MAY_UPDATE_PORTFOLIO_STATE = "may_update_portfolio_state"
    MAY_CREATE_SUGGESTIONS = "may_create_suggestions"
    AUDIT_ONLY = "audit_only"


class JobResourceLimit(StrEnum):
    RASPBERRY_PI_SAFE = "raspberry_pi_safe"
    QUEUE_REQUIRED = "queue_required"
    EXTERNAL_WORKER_RECOMMENDED = "external_worker_recommended"
    BLOCKED_ON_RASPBERRY_PI = "blocked_on_raspberry_pi"


class ExecutionModeStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"
    REQUIRES_SETUP = "requires_setup"
    REQUIRES_EXPLICIT_ACTIVATION = "requires_explicit_activation"


class ExecutionTargetKind(StrEnum):
    INTERNAL_PAPER_SIMULATOR = "internal_paper_simulator"
    IBKR_PAPER_ACCOUNT = "ibkr_paper_account"
    IBKR_LIVE_READ_ONLY = "ibkr_live_read_only"
    IBKR_LIVE_MANUAL = "ibkr_live_manual"
    BLOCKED_AUTOMATIC_EXECUTION = "blocked_automatic_execution"


class ApprovalRequirement(StrEnum):
    ALWAYS_REQUIRED = "always_required"
    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"


class ApprovalDecisionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ExecutionIntentStatus(StrEnum):
    DRAFT = "draft"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    CONVERTED_TO_ORDER = "converted_to_order"


class BrokerProvider(StrEnum):
    NONE = "none"
    INTERACTIVE_BROKERS = "interactive_brokers"


class BrokerAccountMode(StrEnum):
    UNKNOWN = "unknown"
    PAPER = "paper"
    LIVE = "live"
    SIMULATED = "simulated"
    DISABLED = "disabled"
    INTERNAL_PAPER = "internal_paper"
    IBKR_PAPER = "ibkr_paper"
    IBKR_LIVE = "ibkr_live"


class BrokerSystem(StrEnum):
    IBKR = "ibkr"


class BrokerConnectionStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrokerSourceOfTruthStatus(StrEnum):
    NOT_AVAILABLE = "not_available"
    BROKER_AUTHORITATIVE = "broker_authoritative"
    LOCAL_PREVIEW_ONLY = "local_preview_only"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RECONCILIATION_FAILED = "reconciliation_failed"
    BLOCKED = "blocked"


class BrokerSyncMode(StrEnum):
    NOT_CONFIGURED = "not_configured"
    MANUAL_CHECK = "manual_check"
    BOOTSTRAP_FROM_IBKR = "bootstrap_from_ibkr"
    PERIODIC_SNAPSHOT = "periodic_snapshot"
    EVENT_UPDATE = "event_update"
    HISTORY_BACKFILL = "history_backfill"
    RECONCILIATION_ONLY = "reconciliation_only"


class BrokerSyncStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrokerDataKind(StrEnum):
    ACCOUNT_IDENTITY = "account_identity"
    CASH_BALANCE = "cash_balance"
    POSITION = "position"
    EXECUTION = "execution"
    COMMISSION = "commission"
    ORDER_STATUS = "order_status"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    WITHHOLDING_TAX = "withholding_tax"
    STATEMENT = "statement"
    CORPORATE_ACTION = "corporate_action"
    OTHER = "other"


class BrokerActivityOrigin(StrEnum):
    AI_TRADING_AGENT_SUGGESTION = "ai_trading_agent_suggestion"
    USER_APPROVED_AI_ORDER = "user_approved_ai_order"
    DIRECT_IBKR_ORDER = "direct_ibkr_order"
    IMPORTED_IBKR_HISTORY = "imported_ibkr_history"
    IMPORTED_IBKR_POSITION = "imported_ibkr_position"
    IMPORTED_IBKR_CASH = "imported_ibkr_cash"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    UNKNOWN = "unknown"


class ReconciliationStatus(StrEnum):
    NOT_AVAILABLE = "not_available"
    CLEAN = "clean"
    DIFFERENCES_FOUND = "differences_found"
    BLOCKED = "blocked"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class ReconciliationDifferenceKind(StrEnum):
    MISSING_LOCAL_POSITION = "missing_local_position"
    MISSING_BROKER_POSITION = "missing_broker_position"
    POSITION_QUANTITY_MISMATCH = "position_quantity_mismatch"
    AVERAGE_COST_MISMATCH = "average_cost_mismatch"
    CASH_BALANCE_MISMATCH = "cash_balance_mismatch"
    MISSING_LOCAL_EXECUTION = "missing_local_execution"
    DIRECT_BROKER_EXECUTION = "direct_broker_execution"
    COMMISSION_MISMATCH = "commission_mismatch"
    CURRENCY_BALANCE_MISMATCH = "currency_balance_mismatch"
    UNSUPPORTED_ASSET_TYPE = "unsupported_asset_type"
    STALE_BROKER_SNAPSHOT = "stale_broker_snapshot"
    STALE_LOCAL_MIRROR = "stale_local_mirror"
    UNKNOWN = "unknown"


class ReconciliationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"
    CRITICAL = "critical"


class BrokerSuggestionPolicy(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_WARNING = "allow_with_warning"
    BLOCK_UNTIL_RECONCILED = "block_until_reconciled"
    BLOCK_UNTIL_IBKR_CONFIGURED = "block_until_ibkr_configured"
    BLOCK_UNTIL_MANUAL_REVIEW = "block_until_manual_review"


class IBKRDataSourceType(StrEnum):
    WEB_API_PORTFOLIO = "web_api_portfolio"
    TWS_POSITIONS = "tws_positions"
    TWS_EXECUTIONS = "tws_executions"
    TWS_COMMISSIONS = "tws_commissions"
    FLEX_STATEMENT = "flex_statement"
    MANUAL_PLACEHOLDER = "manual_placeholder"
    NOT_CONFIGURED = "not_configured"


class IBKRSecurityType(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    CASH = "cash"
    FOREX = "forex"
    BOND = "bond"
    FUND = "fund"
    COMMODITY_ETF_ETC = "commodity_etf_etc"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"


class IBKRMarketDataPermissionStatus(StrEnum):
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"
    SUBSCRIBED = "subscribed"
    DELAYED = "delayed"
    MISSING_SUBSCRIPTION = "missing_subscription"
    MISSING_PERMISSION = "missing_permission"
    UNAVAILABLE = "unavailable"


class IBKRTradingPermissionStatus(StrEnum):
    UNKNOWN = "unknown"
    PERMITTED = "permitted"
    PAPER_ONLY = "paper_only"
    READ_ONLY = "read_only"
    NOT_PERMITTED = "not_permitted"
    BLOCKED_BY_SYSTEM = "blocked_by_system"


class IBKROrderTransmissionStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED_TO_PAPER = "submitted_to_paper"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ResearchReportStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_BY_DATA_QUALITY = "blocked_by_data_quality"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    SUPERSEDED = "superseded"


class ResearchSourceType(StrEnum):
    IBKR_ACCOUNT_DATA = "ibkr_account_data"
    IBKR_MARKET_DATA = "ibkr_market_data"
    IBKR_ORDER_DATA = "ibkr_order_data"
    IBKR_EXECUTION_DATA = "ibkr_execution_data"
    IBKR_STATEMENT = "ibkr_statement"
    COMPANY_REPORT = "company_report"
    ETF_FACTSHEET = "etf_factsheet"
    KID_KIID = "kid_kiid"
    FILING = "filing"
    NEWS = "news"
    ANALYST_SUMMARY = "analyst_summary"
    MACRO_DATA = "macro_data"
    CENTRAL_BANK_DATA = "central_bank_data"
    WEBSITE = "website"
    MANUAL_INPUT = "manual_input"
    OTHER = "other"


class ResearchUse(StrEnum):
    MARKET_CONTEXT = "market_context"
    CANDIDATE_DISCOVERY = "candidate_discovery"
    ASSET_DEEP_RESEARCH = "asset_deep_research"
    RISK_REVIEW = "risk_review"
    PERFORMANCE_REVIEW = "performance_review"
    SUGGESTION_EXPLANATION = "suggestion_explanation"
    SELF_LEARNING_REVIEW = "self_learning_review"


class AIResearchRole(StrEnum):
    RESEARCH_INPUT = "research_input"
    EXPLANATION = "explanation"
    REJECTED_INPUT = "rejected_input"
    BLOCKED_INPUT = "blocked_input"


class PromptInjectionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class DataProviderKind(StrEnum):
    BROKER_OFFICIAL = "broker_official"
    REGULATOR_OFFICIAL = "regulator_official"
    CENTRAL_BANK_OFFICIAL = "central_bank_official"
    GOVERNMENT_OFFICIAL = "government_official"
    ISSUER_OFFICIAL = "issuer_official"
    EXCHANGE_OFFICIAL = "exchange_official"
    COMPANY_OFFICIAL = "company_official"
    PUBLIC_NEWS = "public_news"
    PUBLIC_WEBSITE = "public_website"
    INTERNAL_SYSTEM = "internal_system"
    MANUAL_INTERNAL = "manual_internal"
    PAID_VENDOR = "paid_vendor"


class DataAccessMethod(StrEnum):
    BROKER_INTERFACE = "broker_interface"
    PUBLIC_API = "public_api"
    PUBLIC_FILE_DOWNLOAD = "public_file_download"
    PUBLIC_WEBSITE = "public_website"
    VENDOR_API = "vendor_api"
    INTERNAL_SYSTEM = "internal_system"
    MANUAL_ENTRY = "manual_entry"


class DataCostTier(StrEnum):
    FREE = "free"
    BROKER_INCLUDED = "broker_included"
    PAID = "paid"
    INTERNAL = "internal"


class DataUsageStatus(StrEnum):
    ALLOWED = "allowed"
    ALLOWED_WITH_LIMITS = "allowed_with_limits"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class DataUsePermission(StrEnum):
    RESEARCH_CONTEXT = "research_context"
    PORTFOLIO_VALUATION = "portfolio_valuation"
    SUGGESTION_ELIGIBILITY = "suggestion_eligibility"
    AUDIT_EVIDENCE = "audit_evidence"


class DataFreshnessClass(StrEnum):
    NEAR_REAL_TIME = "near_real_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DataFailurePolicy(StrEnum):
    BLOCK_OPERATION = "block_operation"
    WARN_AND_LOG = "warn_and_log"
    IGNORE_IF_OPTIONAL = "ignore_if_optional"


class SourceReliabilityTier(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class DataDomain(StrEnum):
    INSTRUMENT_REFERENCE = "instrument_reference"
    ACCOUNT_POSITION = "account_position"
    ORDER_EXECUTION = "order_execution"
    MARKET_DATA = "market_data"
    COMPANY_FUNDAMENTAL = "company_fundamental"
    MACRO_DATA = "macro_data"
    FX_DATA = "fx_data"
    ETF_REFERENCE = "etf_reference"
    LEGAL_DISCLOSURE = "legal_disclosure"
    HOLDINGS_DATA = "holdings_data"
    COMPANY_EVENT = "company_event"
    NEWS_SIGNAL = "news_signal"
    POLICY_EVENT = "policy_event"
    MANUAL_OVERRIDE = "manual_override"
    PORTFOLIO_ANALYTICS = "portfolio_analytics"
    RESEARCH_OUTPUT = "research_output"
    AUDIT_LOG = "audit_log"
    RESEARCH_CONTEXT = "research_context"


class RuntimeDeploymentTarget(StrEnum):
    RASPBERRY_PI_5 = "raspberry_pi_5"
    LINUX_ARM64 = "linux_arm64"
    LINUX_AMD64 = "linux_amd64"
    STRONGER_PC = "stronger_pc"
    UNKNOWN = "unknown"


class RuntimeServiceKind(StrEnum):
    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    DATABASE = "database"
    DATA_SOURCE_UPDATER = "data_source_updater"
    RESEARCH_WORKER = "research_worker"
    AI_RESEARCH_QUEUE = "ai_research_queue"
    IBKR_ADAPTER = "ibkr_adapter"
    AUDIT_LOGGER = "audit_logger"
    BACKUP_SERVICE = "backup_service"
    HEALTH_MONITOR = "health_monitor"
    WEB_FRONTEND = "web_frontend"
    REVERSE_PROXY = "reverse_proxy"
    UNKNOWN = "unknown"


class RuntimeServiceStatus(StrEnum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    DISABLED = "disabled"
    BLOCKED = "blocked"


class RuntimeServiceCriticality(StrEnum):
    REQUIRED = "required"
    IMPORTANT = "important"
    OPTIONAL = "optional"
    FUTURE = "future"


class StartupPhase(StrEnum):
    CONFIGURATION = "configuration"
    STORAGE = "storage"
    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    ADAPTERS = "adapters"
    BACKGROUND_JOBS = "background_jobs"
    MONITORING = "monitoring"
    READY = "ready"


class StartupDependencyPolicy(StrEnum):
    MUST_START_BEFORE = "must_start_before"
    SHOULD_START_BEFORE = "should_start_before"
    INDEPENDENT = "independent"
    OPTIONAL_AFTER_READY = "optional_after_ready"


class ServiceFailurePolicy(StrEnum):
    BLOCK_SUGGESTIONS = "block_suggestions"
    ALLOW_READ_ONLY = "allow_read_only"
    ALLOW_EXISTING_DATA_WITH_WARNING = "allow_existing_data_with_warning"
    DISABLE_OPTIONAL_FEATURE = "disable_optional_feature"
    STOP_SERVICE = "stop_service"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


class RuntimeResourceProfile(StrEnum):
    LIGHTWEIGHT = "lightweight"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTERNAL_OR_STRONGER_MACHINE_RECOMMENDED = (
        "external_or_stronger_machine_recommended"
    )


class ParallelExecutionPolicy(StrEnum):
    NOT_PARALLEL = "not_parallel"
    PARALLEL_SAFE = "parallel_safe"
    QUEUE_REQUIRED = "queue_required"
    SCHEDULED_ONLY = "scheduled_only"
    EXTERNAL_WORKER_RECOMMENDED = "external_worker_recommended"


class RuntimeHealthSeverity(StrEnum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DataQualityGateStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNKNOWN = "unknown"


class DataQualityIssueType(StrEnum):
    MISSING_DATA = "missing_data"
    STALE_DATA = "stale_data"
    DELAYED_DATA = "delayed_data"
    PARTIAL_DATA = "partial_data"
    INCONSISTENT_DATA = "inconsistent_data"
    SOURCE_NOT_ALLOWED = "source_not_allowed"
    SOURCE_NOT_TRACEABLE = "source_not_traceable"
    PERMISSION_MISSING = "permission_missing"
    SERVICE_UNHEALTHY = "service_unhealthy"
    CALCULATION_FAILED = "calculation_failed"
    PROMPT_INJECTION_RISK = "prompt_injection_risk"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    UNKNOWN = "unknown"


class SuggestionEligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    ELIGIBLE_WITH_WARNINGS = "eligible_with_warnings"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


class SuggestionEligibilityBlockReason(StrEnum):
    DATA_QUALITY_FAILED = "data_quality_failed"
    REQUIRED_DATA_MISSING = "required_data_missing"
    DATA_TOO_STALE = "data_too_stale"
    SOURCE_NOT_ALLOWED = "source_not_allowed"
    SOURCE_NOT_TRACEABLE = "source_not_traceable"
    REQUIRED_SERVICE_UNHEALTHY = "required_service_unhealthy"
    CAPABILITY_BLOCKED = "capability_blocked"
    RISK_POLICY_BLOCKED = "risk_policy_blocked"
    EXECUTION_MODE_BLOCKED = "execution_mode_blocked"
    AI_RESEARCH_BLOCKED = "ai_research_blocked"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    AUDIT_LINK_MISSING = "audit_link_missing"
    UNKNOWN = "unknown"


class SuggestionEligibilityWarningReason(StrEnum):
    DELAYED_DATA = "delayed_data"
    PARTIAL_DATA = "partial_data"
    NON_CRITICAL_SOURCE_MISSING = "non_critical_source_missing"
    STALE_BUT_ACCEPTABLE = "stale_but_acceptable"
    RESEARCH_ONLY_SOURCE_USED = "research_only_source_used"
    MANUAL_INPUT_USED = "manual_input_used"
    LOW_CONFIDENCE = "low_confidence"
    UNKNOWN = "unknown"


class FreshnessRequirement(StrEnum):
    IMMEDIATE = "immediate"
    SAME_DAY = "same_day"
    PREVIOUS_CLOSE = "previous_close"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_QUARTER = "last_quarter"
    LATEST_AVAILABLE = "latest_available"
    STATIC_REFERENCE = "static_reference"
    MANUAL_REVIEW = "manual_review"


class DataGateDecision(StrEnum):
    CONTINUE_ALLOWED = "continue_allowed"
    CONTINUE_WITH_WARNING = "continue_with_warning"
    SKIP_JOB = "skip_job"
    BLOCK_SUGGESTION = "block_suggestion"
    FAIL_JOB = "fail_job"


class CandidateSource(StrEnum):
    PORTFOLIO_REVIEW = "portfolio_review"
    WATCHLIST = "watchlist"
    WEEKLY_DISCOVERY = "weekly_discovery"
    MANUAL_USER_INPUT = "manual_user_input"
    AI_RESEARCH_REPORT = "ai_research_report"
    SCHEDULER_JOB = "scheduler_job"
    IBKR_REFERENCE_DATA = "ibkr_reference_data"
    OTHER = "other"


class CandidateStatus(StrEnum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    ELIGIBLE_FOR_SUGGESTION = "eligible_for_suggestion"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SuggestionDraftStatus(StrEnum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"
    CONVERTED_TO_APPROVAL_REQUEST = "converted_to_approval_request"
    CANCELLED = "cancelled"


class SuggestionGateStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"


class SuggestionGateType(StrEnum):
    CAPABILITY = "capability"
    DATA_QUALITY = "data_quality"
    ELIGIBILITY = "eligibility"
    RISK = "risk"
    COST_TAX = "cost_tax"
    AUDIT = "audit"
    POLICY = "policy"


class RiskGateStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"


class RiskGateBlockReason(StrEnum):
    CONCENTRATION_LIMIT = "concentration_limit"
    ASSET_CLASS_LIMIT = "asset_class_limit"
    CASH_LIMIT = "cash_limit"
    CAPABILITY_BLOCKED = "capability_blocked"
    DATA_QUALITY_FAILED = "data_quality_failed"
    EXECUTION_MODE_BLOCKED = "execution_mode_blocked"
    POLICY_BLOCKED = "policy_blocked"
    UNKNOWN = "unknown"


class SuggestionConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NOT_AVAILABLE = "not_available"


class SuggestionEngineRunStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    BLOCKED = "blocked"
    FAILED = "failed"


class SuggestionDraftDecision(StrEnum):
    CREATE_DRAFT = "create_draft"
    CREATE_WITH_WARNING = "create_with_warning"
    BLOCK = "block"
    SKIP = "skip"
    FAIL = "fail"


class ExternalIntegrationKind(StrEnum):
    IBKR = "ibkr"
    OPENAI = "openai"
    OTHER = "other"


class ExternalIntegrationStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    BLOCKED = "blocked"


class SecretStorageKind(StrEnum):
    ENVIRONMENT_VARIABLE = "environment_variable"
    LOCAL_GITIGNORED_FILE = "local_gitignored_file"
    EXTERNAL_SECRET_MANAGER_FUTURE = "external_secret_manager_future"
    NOT_CONFIGURED = "not_configured"


class SecretStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    REFERENCE_CONFIGURED = "reference_configured"
    AVAILABLE = "available"
    MISSING = "missing"
    INVALID = "invalid"
    BLOCKED = "blocked"


class IBKRConnectionMode(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PAPER_ONLY = "paper_only"
    PAPER_READINESS = "paper_readiness"
    DISABLED = "disabled"


class IBKRApiGatewayKind(StrEnum):
    TWS = "tws"
    IB_GATEWAY = "ib_gateway"
    NOT_CONFIGURED = "not_configured"


class OpenAIUsageSource(StrEnum):
    LOCAL_ESTIMATE = "local_estimate"
    OPENAI_USAGE_API_FUTURE = "openai_usage_api_future"
    OPENAI_COSTS_API_FUTURE = "openai_costs_api_future"
    MANUAL_IMPORT = "manual_import"
    UNKNOWN = "unknown"


class OpenAIModelPurpose(StrEnum):
    DEEP_RESEARCH = "deep_research"
    SIMPLE_EXPLANATION = "simple_explanation"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    FALLBACK = "fallback"
    NOT_CONFIGURED = "not_configured"


class BudgetPeriod(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"


class BudgetStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class CostCurrency(StrEnum):
    USD = "usd"
    EUR = "eur"


class ApiConnectionCheckStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    BLOCKED = "blocked"


class PaperSetupStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PREVIEW_READY = "preview_ready"
    READY_TO_CREATE = "ready_to_create"
    CREATED = "created"
    BLOCKED = "blocked"
    FAILED = "failed"


class PaperSetupMode(StrEnum):
    FIRST_RUN = "first_run"
    RESET_PREVIEW = "reset_preview"
    IMPORT_PREVIEW = "import_preview"


class PaperPortfolioBaseCurrency(StrEnum):
    EUR = "eur"


class PaperSetupBlockReason(StrEnum):
    INVALID_STARTING_CASH = "invalid_starting_cash"
    UNSUPPORTED_CURRENCY = "unsupported_currency"
    LIVE_TRADING_NOT_ALLOWED = "live_trading_not_allowed"
    BROKER_CONNECTION_NOT_REQUIRED = "broker_connection_not_required"
    PERSISTENCE_NOT_AVAILABLE = "persistence_not_available"
    MISSING_AUDIT_REFERENCE = "missing_audit_reference"
    UNKNOWN = "unknown"


class PaperSetupWarningReason(StrEnum):
    PREVIEW_NOT_SAVED = "preview_not_saved"
    IBKR_NOT_CONFIGURED = "ibkr_not_configured"
    OPENAI_NOT_CONFIGURED = "openai_not_configured"
    NO_POSITIONS_YET = "no_positions_yet"
    NO_WATCHLIST_YET = "no_watchlist_yet"


class StorageBackendKind(StrEnum):
    NOT_CONFIGURED = "not_configured"
    POSTGRES = "postgres"
    TIMESCALEDB = "timescaledb"
    IMMUTABLE_ARCHIVE = "immutable_archive"
    RESEARCH_ARCHIVE = "research_archive"
    AUDIT_LOG = "audit_log"
    LOCAL_FILE_FUTURE = "local_file_future"
    OTHER = "other"


class StorageBackendStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PLANNED = "planned"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    BLOCKED = "blocked"


class PersistenceMode(StrEnum):
    NOT_AVAILABLE = "not_available"
    READ_ONLY = "read_only"
    WRITE_PREVIEW_ONLY = "write_preview_only"
    WRITE_ENABLED = "write_enabled"
    DISABLED = "disabled"


class StorageReadinessStatus(StrEnum):
    NOT_READY = "not_ready"
    READY_FOR_PREVIEW = "ready_for_preview"
    READY_FOR_PERSISTENCE = "ready_for_persistence"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    FAILED = "failed"


class StorageBlockReason(StrEnum):
    BACKEND_NOT_CONFIGURED = "backend_not_configured"
    SCHEMA_NOT_READY = "schema_not_ready"
    MIGRATION_REQUIRED = "migration_required"
    BACKUP_NOT_CONFIGURED = "backup_not_configured"
    RESTORE_NOT_TESTED = "restore_not_tested"
    AUDIT_STORAGE_MISSING = "audit_storage_missing"
    SECRET_STORAGE_UNSAFE = "secret_storage_unsafe"
    PERMISSION_MISSING = "permission_missing"
    DATA_INTEGRITY_RISK = "data_integrity_risk"
    UNKNOWN = "unknown"


class StorageWarningReason(StrEnum):
    PREVIEW_ONLY = "preview_only"
    BACKUP_NOT_TESTED = "backup_not_tested"
    RETENTION_POLICY_MISSING = "retention_policy_missing"
    ARCHIVE_NOT_CONFIGURED = "archive_not_configured"
    LOCAL_ONLY = "local_only"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    UNKNOWN = "unknown"


class PersistedEntityKind(StrEnum):
    PAPER_SETUP = "paper_setup"
    PAPER_CASH_ACCOUNT = "paper_cash_account"
    PAPER_CASH_MOVEMENT = "paper_cash_movement"
    PAPER_TRANSACTION = "paper_transaction"
    POSITION_LOT = "position_lot"
    WATCHLIST_ITEM = "watchlist_item"
    ACTION_SUGGESTION = "action_suggestion"
    APPROVAL_DECISION = "approval_decision"
    SOURCE_REFERENCE = "source_reference"
    AI_RESEARCH_RECORD = "ai_research_record"
    DATA_QUALITY_CHECK = "data_quality_check"
    SCHEDULER_JOB_RUN = "scheduler_job_run"
    SETTINGS_PROFILE = "settings_profile"
    API_USAGE_SUMMARY = "api_usage_summary"
    AUDIT_EVENT = "audit_event"
    TAX_RECORD = "tax_record"
    BACKUP_RECORD = "backup_record"
    OTHER = "other"


class StorageSensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET_REFERENCE_ONLY = "secret_reference_only"
    PROHIBITED_SECRET_VALUE = "prohibited_secret_value"


class RetentionCategory(StrEnum):
    SHORT_TERM_OPERATIONAL = "short_term_operational"
    PORTFOLIO_LIFETIME = "portfolio_lifetime"
    AUDIT_LIFETIME = "audit_lifetime"
    TAX_LIFETIME = "tax_lifetime"
    RESEARCH_ARCHIVE = "research_archive"
    IMMUTABLE_RAW_ARCHIVE = "immutable_raw_archive"
    USER_CONFIG = "user_config"
    SECRET_REFERENCE_METADATA = "secret_reference_metadata"


class BackupStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PLANNED = "planned"
    CONFIGURED = "configured"
    LAST_BACKUP_OK = "last_backup_ok"
    LAST_BACKUP_FAILED = "last_backup_failed"
    RESTORE_TESTED = "restore_tested"
    BLOCKED = "blocked"


class RestoreCheckStatus(StrEnum):
    NOT_TESTED = "not_tested"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
