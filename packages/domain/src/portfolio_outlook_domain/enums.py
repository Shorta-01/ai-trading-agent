from enum import StrEnum


class AssetType(StrEnum):
    CASH = "cash"
    FX = "fx"
    UCITS_ETF = "ucits_etf"
    STOCK = "stock"
    BENCHMARK = "benchmark"
    OTHER = "other"


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
