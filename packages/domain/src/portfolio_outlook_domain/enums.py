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
    INTERNAL_PAPER = "internal_paper"
    IBKR_PAPER = "ibkr_paper"
    IBKR_LIVE = "ibkr_live"


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
