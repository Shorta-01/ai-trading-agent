from enum import StrEnum


class AssetType(StrEnum):
    CASH = "cash"
    FX = "fx"
    UCITS_ETF = "ucits_etf"
    STOCK = "stock"
    BENCHMARK = "benchmark"
    OTHER = "other"
    TERM_DEPOSIT = "term_deposit"


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
