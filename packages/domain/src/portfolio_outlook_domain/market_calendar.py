from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from .primitives import DomainBaseModel


class MarketRegion(StrEnum):
    EUROPE = "europe"
    UNITED_STATES = "united_states"
    UNITED_KINGDOM = "united_kingdom"
    GLOBAL = "global"
    UNKNOWN = "unknown"


class ExchangeCode(StrEnum):
    EURONEXT_AMSTERDAM = "euronext_amsterdam"
    EURONEXT_BRUSSELS = "euronext_brussels"
    EURONEXT_PARIS = "euronext_paris"
    EURONEXT_LISBON = "euronext_lisbon"
    EURONEXT_DUBLIN = "euronext_dublin"
    EURONEXT_MILAN = "euronext_milan"
    EURONEXT_OSLO = "euronext_oslo"
    NYSE = "nyse"
    NASDAQ = "nasdaq"
    NYSE_ARCA = "nyse_arca"
    XETRA = "xetra"
    LONDON_STOCK_EXCHANGE = "london_stock_exchange"
    OTHER = "other"
    UNKNOWN = "unknown"


class InstrumentTradingVenueType(StrEnum):
    PRIMARY_EXCHANGE = "primary_exchange"
    ALTERNATIVE_TRADING_SYSTEM = "alternative_trading_system"
    BROKER_ROUTED = "broker_routed"
    OTC = "otc"
    UNKNOWN = "unknown"


class MarketSessionType(StrEnum):
    REGULAR = "regular"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    OPENING_AUCTION = "opening_auction"
    CLOSING_AUCTION = "closing_auction"
    INTRADAY_AUCTION = "intraday_auction"
    TRADING_AT_LAST = "trading_at_last"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"
    HALTED = "halted"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class MarketSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    AUCTION = "auction"
    HALF_DAY = "half_day"
    EXTENDED_HOURS = "extended_hours"
    HALTED = "halted"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class TradabilityStatus(StrEnum):
    TRADABLE = "tradable"
    TRADABLE_WITH_WARNING = "tradable_with_warning"
    NOT_TRADABLE = "not_tradable"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class MarketCalendarDayType(StrEnum):
    FULL_TRADING_DAY = "full_trading_day"
    HALF_TRADING_DAY = "half_trading_day"
    HOLIDAY_CLOSED = "holiday_closed"
    WEEKEND_CLOSED = "weekend_closed"
    SPECIAL_CLOSURE = "special_closure"
    UNKNOWN = "unknown"


class MarketClosureReason(StrEnum):
    WEEKEND = "weekend"
    PUBLIC_HOLIDAY = "public_holiday"
    EXCHANGE_HOLIDAY = "exchange_holiday"
    SPECIAL_EVENT = "special_event"
    TECHNICAL_ISSUE = "technical_issue"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class MarketStatusFreshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class MarketVenue(DomainBaseModel):
    venue_id: str
    exchange_code: ExchangeCode
    display_name: str
    region: MarketRegion
    timezone: str
    venue_type: InstrumentTradingVenueType
    explanation_nl: str

    @field_validator("venue_id", "display_name", "timezone", "explanation_nl")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value


class TradingSessionWindow(DomainBaseModel):
    session_type: MarketSessionType
    status: MarketSessionStatus
    starts_at: datetime
    ends_at: datetime
    timezone: str
    allows_market_orders: bool
    allows_limit_orders: bool
    liquidity_warning_nl: str | None = None
    explanation_nl: str

    @field_validator("timezone", "explanation_nl")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_window(self) -> TradingSessionWindow:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if (
            self.session_type
            in {
                MarketSessionType.PRE_MARKET,
                MarketSessionType.POST_MARKET,
                MarketSessionType.AFTER_HOURS,
            }
            and not self.liquidity_warning_nl
        ):
            raise ValueError("extended-hours sessions require liquidity_warning_nl")
        return self


class MarketCalendarDay(DomainBaseModel):
    venue_id: str
    trading_date: date
    day_type: MarketCalendarDayType
    closure_reason: MarketClosureReason | None = None
    sessions: tuple[TradingSessionWindow, ...] = ()
    source_id: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    published_at: datetime | None = None
    explanation_nl: str

    @field_validator("venue_id", "explanation_nl")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_day(self) -> MarketCalendarDay:
        if (
            self.day_type
            in {MarketCalendarDayType.FULL_TRADING_DAY, MarketCalendarDayType.HALF_TRADING_DAY}
            and not self.sessions
        ):
            raise ValueError("trading day requires at least one session")
        if self.day_type in {
            MarketCalendarDayType.HOLIDAY_CLOSED,
            MarketCalendarDayType.WEEKEND_CLOSED,
            MarketCalendarDayType.SPECIAL_CLOSURE,
        }:
            if any(session.session_type == MarketSessionType.REGULAR for session in self.sessions):
                raise ValueError("closed day cannot contain a regular session")
        return self


class MarketStatusAssessment(DomainBaseModel):
    assessment_id: str
    asset_symbol: str | None = None
    venue_id: str
    exchange_code: ExchangeCode
    checked_at: datetime
    as_of_time: datetime
    current_session_type: MarketSessionType
    current_session_status: MarketSessionStatus
    tradability_status: TradabilityStatus
    freshness_status: MarketStatusFreshness
    blocks_suggestions: bool
    blocks_orders: bool
    reason_nl: str
    help_nl: str

    @field_validator("assessment_id", "venue_id", "reason_nl", "help_nl")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_consistency(self) -> MarketStatusAssessment:
        if self.checked_at < self.as_of_time:
            raise ValueError("checked_at must be at or after as_of_time")
        blocking_freshness = {
            MarketStatusFreshness.STALE,
            MarketStatusFreshness.MISSING,
            MarketStatusFreshness.UNKNOWN,
            MarketStatusFreshness.BLOCKED,
        }
        blocking_status = {
            MarketSessionStatus.CLOSED,
            MarketSessionStatus.HALTED,
            MarketSessionStatus.SUSPENDED,
            MarketSessionStatus.UNKNOWN,
        }
        if (
            self.tradability_status in {TradabilityStatus.UNKNOWN, TradabilityStatus.BLOCKED}
            and not self.blocks_orders
        ):
            raise ValueError("unknown/blocked tradability must block orders")
        if self.freshness_status in blocking_freshness and not self.blocks_orders:
            raise ValueError("stale/missing/unknown/blocked freshness must block orders")
        if self.current_session_status in blocking_status and not self.blocks_orders:
            raise ValueError("closed/halted/suspended/unknown sessions must block orders")
        if (
            self.current_session_type
            in {
                MarketSessionType.PRE_MARKET,
                MarketSessionType.POST_MARKET,
                MarketSessionType.AFTER_HOURS,
            }
            and self.tradability_status == TradabilityStatus.TRADABLE
        ):
            raise ValueError("extended-hours sessions cannot be cleanly tradable")
        return self


class MarketCalendarHelpText(DomainBaseModel):
    key: str
    label_nl: str
    help_nl: str


def evaluate_tradability(
    *,
    current_session_status: MarketSessionStatus,
    current_session_type: MarketSessionType,
    freshness_status: MarketStatusFreshness,
    allows_market_orders: bool,
    allows_limit_orders: bool,
) -> TradabilityStatus:
    if freshness_status in {
        MarketStatusFreshness.STALE,
        MarketStatusFreshness.MISSING,
        MarketStatusFreshness.BLOCKED,
    }:
        return TradabilityStatus.BLOCKED
    if freshness_status == MarketStatusFreshness.UNKNOWN:
        return TradabilityStatus.UNKNOWN
    if current_session_status in {MarketSessionStatus.HALTED, MarketSessionStatus.SUSPENDED}:
        return TradabilityStatus.BLOCKED
    if current_session_status == MarketSessionStatus.UNKNOWN:
        return TradabilityStatus.UNKNOWN
    if current_session_status == MarketSessionStatus.CLOSED:
        return TradabilityStatus.NOT_TRADABLE
    if current_session_type in {
        MarketSessionType.PRE_MARKET,
        MarketSessionType.POST_MARKET,
        MarketSessionType.AFTER_HOURS,
    }:
        return (
            TradabilityStatus.TRADABLE_WITH_WARNING
            if allows_limit_orders
            else TradabilityStatus.NOT_TRADABLE
        )
    if current_session_type in {
        MarketSessionType.OPENING_AUCTION,
        MarketSessionType.CLOSING_AUCTION,
        MarketSessionType.INTRADAY_AUCTION,
        MarketSessionType.TRADING_AT_LAST,
    }:
        return (
            TradabilityStatus.TRADABLE_WITH_WARNING
            if (allows_market_orders or allows_limit_orders)
            else TradabilityStatus.UNKNOWN
        )
    if current_session_type == MarketSessionType.UNKNOWN:
        return TradabilityStatus.UNKNOWN
    if not allows_market_orders and not allows_limit_orders:
        return TradabilityStatus.NOT_TRADABLE
    return TradabilityStatus.TRADABLE


def get_market_calendar_help_texts() -> tuple[MarketCalendarHelpText, ...]:
    return (
        MarketCalendarHelpText(
            key="market_open", label_nl="Markt open", help_nl="De markt is nu geopend."
        ),
        MarketCalendarHelpText(
            key="market_closed", label_nl="Markt gesloten", help_nl="De markt is nu gesloten."
        ),
        MarketCalendarHelpText(
            key="half_trading_day",
            label_nl="Halve handelsdag",
            help_nl="Kortere handelsuren dan normaal.",
        ),
        MarketCalendarHelpText(
            key="pre_market",
            label_nl="Voorbeurs",
            help_nl="Voorbeurshandel heeft vaak minder liquiditeit.",
        ),
        MarketCalendarHelpText(
            key="post_market",
            label_nl="Nabeurs",
            help_nl="Nabeurshandel heeft vaak minder liquiditeit.",
        ),
        MarketCalendarHelpText(
            key="opening_auction",
            label_nl="Openingsveiling",
            help_nl="Openingsveiling kan extra prijsschommelingen geven.",
        ),
        MarketCalendarHelpText(
            key="closing_auction",
            label_nl="Slotveiling",
            help_nl="Slotveiling kan extra prijsschommelingen geven.",
        ),
        MarketCalendarHelpText(
            key="halted",
            label_nl="Handel gepauzeerd",
            help_nl="Handel is tijdelijk gepauzeerd op de beurs.",
        ),
        MarketCalendarHelpText(
            key="suspended",
            label_nl="Handel geschorst",
            help_nl="Handel is geschorst en orders zijn niet uitvoerbaar.",
        ),
        MarketCalendarHelpText(
            key="market_status_unknown",
            label_nl="Marktstatus onbekend",
            help_nl="Onbekende marktstatus blokkeert uitvoerbaarheid.",
        ),
        MarketCalendarHelpText(
            key="tradable",
            label_nl="Verhandelbaar",
            help_nl="Order kan binnen deze sessie normaal worden geplaatst.",
        ),
        MarketCalendarHelpText(
            key="tradable_with_warning",
            label_nl="Verhandelbaar met waarschuwing",
            help_nl="Order kan mogelijk, maar let op liquiditeit en spreads.",
        ),
        MarketCalendarHelpText(
            key="not_tradable",
            label_nl="Niet verhandelbaar",
            help_nl="Deze sessie laat nu geen normale uitvoering toe.",
        ),
        MarketCalendarHelpText(
            key="blocked", label_nl="Geblokkeerd", help_nl="Veiligheidsregels blokkeren uitvoering."
        ),
        MarketCalendarHelpText(
            key="market_calendar_freshness",
            label_nl="Marktstatus versheid",
            help_nl="De marktstatus bepaalt of een suggestie of actie nu uitvoerbaar is.",
        ),
        MarketCalendarHelpText(
            key="exchange_timezone",
            label_nl="Beurstijdzone",
            help_nl="Alle tijden worden in de tijdzone van de beurs geïnterpreteerd.",
        ),
    )


def default_market_venue_catalog() -> tuple[MarketVenue, ...]:
    return (
        MarketVenue(
            venue_id="euronext_brussels",
            exchange_code=ExchangeCode.EURONEXT_BRUSSELS,
            display_name="Euronext Brussels",
            region=MarketRegion.EUROPE,
            timezone="Europe/Brussels",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van Euronext Brussels zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="euronext_amsterdam",
            exchange_code=ExchangeCode.EURONEXT_AMSTERDAM,
            display_name="Euronext Amsterdam",
            region=MarketRegion.EUROPE,
            timezone="Europe/Amsterdam",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van Euronext Amsterdam zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="euronext_paris",
            exchange_code=ExchangeCode.EURONEXT_PARIS,
            display_name="Euronext Paris",
            region=MarketRegion.EUROPE,
            timezone="Europe/Paris",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van Euronext Paris zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="nyse",
            exchange_code=ExchangeCode.NYSE,
            display_name="NYSE",
            region=MarketRegion.UNITED_STATES,
            timezone="America/New_York",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van NYSE zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="nasdaq",
            exchange_code=ExchangeCode.NASDAQ,
            display_name="Nasdaq",
            region=MarketRegion.UNITED_STATES,
            timezone="America/New_York",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van Nasdaq zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="nyse_arca",
            exchange_code=ExchangeCode.NYSE_ARCA,
            display_name="NYSE Arca",
            region=MarketRegion.UNITED_STATES,
            timezone="America/New_York",
            venue_type=InstrumentTradingVenueType.ALTERNATIVE_TRADING_SYSTEM,
            explanation_nl="Identiteit van NYSE Arca zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="xetra",
            exchange_code=ExchangeCode.XETRA,
            display_name="Xetra",
            region=MarketRegion.EUROPE,
            timezone="Europe/Berlin",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van Xetra zonder live handelsuren.",
        ),
        MarketVenue(
            venue_id="lse",
            exchange_code=ExchangeCode.LONDON_STOCK_EXCHANGE,
            display_name="London Stock Exchange",
            region=MarketRegion.UNITED_KINGDOM,
            timezone="Europe/London",
            venue_type=InstrumentTradingVenueType.PRIMARY_EXCHANGE,
            explanation_nl="Identiteit van London Stock Exchange zonder live handelsuren.",
        ),
    )
