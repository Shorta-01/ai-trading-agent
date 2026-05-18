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
