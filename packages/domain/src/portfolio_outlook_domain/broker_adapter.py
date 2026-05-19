from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator

from .primitives import DomainBaseModel


class BrokerProvider(StrEnum):
    IBKR = "ibkr"


class BrokerEnvironment(StrEnum):
    PAPER = "paper"
    LIVE = "live"
    UNKNOWN = "unknown"


class BrokerConnectionStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ESTABLISHED = "established"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    FAILED = "failed"


class BrokerAccountModeStatus(StrEnum):
    CONFIRMED_PAPER = "confirmed_paper"
    CONFIRMED_LIVE = "confirmed_live"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class BrokerDataFreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    UNKNOWN = "unknown"


class BrokerPermissionStatus(StrEnum):
    ALLOWED = "allowed"
    MISSING_PERMISSION = "missing_permission"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class _BrokerDecimalModel(DomainBaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def reject_float_values(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float values are not allowed in broker contracts; use Decimal.")
        return value


class BrokerIntegrationSettings(DomainBaseModel):
    ibkr_enabled: bool = False
    ibkr_provider: BrokerProvider = BrokerProvider.IBKR
    ibkr_expected_environment: BrokerEnvironment = BrokerEnvironment.PAPER
    ibkr_account_id_hint: str | None = None
    ibkr_gateway_url: str | None = None
    ibkr_connection_timeout_seconds: int = 10
    ibkr_status_check_enabled: bool = True


class BrokerConnectionSnapshot(DomainBaseModel):
    broker_provider: BrokerProvider
    status: BrokerConnectionStatus
    account_mode_status: BrokerAccountModeStatus = BrokerAccountModeStatus.UNKNOWN
    can_submit_orders: bool = False
    checked_at: datetime
    status_nl: str
    message_nl: str


class BrokerAccountIdentity(DomainBaseModel):
    broker_provider: BrokerProvider
    account_id: str
    display_name: str | None = None


class BrokerAccountModeCheck(DomainBaseModel):
    broker_provider: BrokerProvider
    account_id: str
    environment: BrokerEnvironment = BrokerEnvironment.UNKNOWN
    status: BrokerAccountModeStatus = BrokerAccountModeStatus.UNKNOWN
    can_submit_orders: bool = False
    reason_nl: str
    checked_at: datetime


class BrokerCashSnapshot(_BrokerDecimalModel):
    broker_provider: BrokerProvider
    account_id: str
    currency: str
    total_cash_value: Decimal
    settled_cash: Decimal
    buying_power: Decimal
    net_liquidation: Decimal
    source_timestamp: datetime
    received_at: datetime
    freshness_status: BrokerDataFreshnessStatus
    raw_source_reference: str | None = None


class BrokerPositionSnapshot(_BrokerDecimalModel):
    broker_provider: BrokerProvider
    account_id: str
    conid: str | None = None
    symbol: str
    asset_type: str
    exchange: str | None = None
    currency: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    source_timestamp: datetime
    received_at: datetime
    freshness_status: BrokerDataFreshnessStatus


class BrokerOpenOrderSnapshot(_BrokerDecimalModel):
    broker_provider: BrokerProvider
    account_id: str
    order_reference: str
    symbol: str
    side: str
    quantity: Decimal
    order_type: str
    limit_price: Decimal | None = None
    submitted_at: datetime
    status: str


class BrokerExecutionSnapshot(_BrokerDecimalModel):
    broker_provider: BrokerProvider
    account_id: str
    execution_id: str
    order_reference: str
    symbol: str
    quantity: Decimal
    price: Decimal
    commission: Decimal | None = None
    currency: str
    executed_at: datetime


class BrokerAdapterError(DomainBaseModel):
    code: str
    message_nl: str
    blocked: bool = False


class BrokerAdapterHealth(DomainBaseModel):
    broker_provider: BrokerProvider
    connection_status: BrokerConnectionStatus
    account_mode_status: BrokerAccountModeStatus = BrokerAccountModeStatus.UNKNOWN
    can_submit_orders: bool = False
    checked_at: datetime
    errors: list[BrokerAdapterError] = Field(default_factory=list)
