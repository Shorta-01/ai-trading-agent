from datetime import datetime

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    ActionSuggestion,
    AdviceAction,
    DataQualityStatus,
    RiskLevel,
    SuggestionStatus,
)


def test_action_suggestion_requires_reason_nl() -> None:
    with pytest.raises(ValidationError):
        ActionSuggestion(
            suggestion_id="s1",
            portfolio_id="p1",
            instrument_id="i1",
            action=AdviceAction.HOLD,
            status=SuggestionStatus.ACTIVE,
            reason_nl="  ",
            risk_level=RiskLevel.LOW,
            data_quality_status=DataQualityStatus.OK,
            created_at=datetime.utcnow(),
        )


def test_blocked_action_requires_blocked_status() -> None:
    with pytest.raises(ValidationError):
        ActionSuggestion(
            suggestion_id="s1",
            portfolio_id="p1",
            instrument_id="i1",
            action=AdviceAction.BLOCKED,
            status=SuggestionStatus.ACTIVE,
            reason_nl="Geblokkeerd door risico.",
            risk_level=RiskLevel.BLOCKED,
            data_quality_status=DataQualityStatus.FAILED,
            created_at=datetime.utcnow(),
        )
