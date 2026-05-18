from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import AuditEvent


def test_audit_event_requires_event_type_and_actor() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            audit_event_id="a1",
            event_type="",
            actor="system",
            created_at=datetime.utcnow(),
            details={},
        )


def test_models_serialize_to_json_compatible_data() -> None:
    event = AuditEvent(
        audit_event_id="a1",
        event_type="suggestion_created",
        actor="system",
        created_at=datetime.utcnow(),
        details={"count": 1, "ratio": Decimal("2.5"), "ok": True},
    )
    payload = event.model_dump(mode="json")
    assert payload["event_type"] == "suggestion_created"
    assert payload["details"]["ratio"] == "2.5"
