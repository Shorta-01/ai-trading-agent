from pydantic import field_validator

from .enums import AssetType, InstrumentStatus
from .identifiers import InstrumentId
from .primitives import CurrencyCode, DomainBaseModel, Money, Percentage


class Instrument(DomainBaseModel):
    instrument_id: InstrumentId
    name: str
    ticker: str | None = None
    isin: str | None = None
    exchange: str | None = None
    country: str | None = None
    currency: CurrencyCode
    asset_type: AssetType
    status: InstrumentStatus
    sector: str | None = None
    industry: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name is required")
        return value


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
