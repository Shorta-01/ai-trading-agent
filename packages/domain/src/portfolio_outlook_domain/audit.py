from datetime import datetime
from decimal import Decimal

from pydantic import field_validator

from .identifiers import AuditEventId, InstrumentId, PortfolioId, SuggestionId
from .primitives import DomainBaseModel


class AuditEvent(DomainBaseModel):
    audit_event_id: AuditEventId
    event_type: str
    actor: str
    created_at: datetime
    related_portfolio_id: PortfolioId | None = None
    related_instrument_id: InstrumentId | None = None
    related_suggestion_id: SuggestionId | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    previous_event_hash: str | None = None
    details: dict[str, str | int | Decimal | bool | None]

    @field_validator("event_type", "actor")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field is required")
        return value
