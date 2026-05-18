from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from .enums import (
    BrokerAccountMode,
    BrokerProvider,
    IBKRMarketDataPermissionStatus,
    IBKROrderTransmissionStatus,
    IBKRSecurityType,
    IBKRTradingPermissionStatus,
)
from .identifiers import BrokerOrderReferenceId, BrokerReferenceId, InstrumentId, OrderId
from .primitives import CurrencyCode, DomainBaseModel


class IBKRInstrumentReference(DomainBaseModel):
    broker_reference_id: BrokerReferenceId
    instrument_id: InstrumentId
    conid: str | None = None
    symbol: str
    sec_type: IBKRSecurityType
    exchange: str | None = None
    primary_exchange: str | None = None
    currency: CurrencyCode
    local_symbol: str | None = None
    trading_class: str | None = None
    multiplier: Decimal | None = None
    market_name: str | None = None
    min_tick: Decimal | None = None
    valid_exchanges: list[str] = Field(default_factory=list)
    is_fractional_supported: bool | None = None
    market_data_permission_status: IBKRMarketDataPermissionStatus
    trading_permission_status: IBKRTradingPermissionStatus

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("symbol is required")
        return value

    @field_validator("multiplier", "min_tick")
    @classmethod
    def validate_positive_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Decimal value must be positive")
        return value


class IBKROrderReference(DomainBaseModel):
    broker_order_reference_id: BrokerOrderReferenceId
    order_id: OrderId | None = None
    broker_provider: BrokerProvider
    account_mode: BrokerAccountMode
    ibkr_account_id: str | None = None
    ibkr_order_id: str | None = None
    ibkr_perm_id: str | None = None
    client_id: str | None = None
    transmission_status: IBKROrderTransmissionStatus
    submitted_at: datetime | None = None
    last_status_at: datetime | None = None
    status_message: str | None = None

    @model_validator(mode="after")
    def validate_provider(self) -> "IBKROrderReference":
        if self.broker_provider != BrokerProvider.INTERACTIVE_BROKERS:
            raise ValueError("IBKROrderReference requires interactive_brokers provider")
        return self


class IBKRDataPermissionSnapshot(DomainBaseModel):
    broker_reference_id: BrokerReferenceId
    instrument_id: InstrumentId
    market_data_permission_status: IBKRMarketDataPermissionStatus
    trading_permission_status: IBKRTradingPermissionStatus
    checked_at: datetime
    explanation_nl: str

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation_nl is required")
        return value
