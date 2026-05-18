import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    AssetCapability,
    BlockedReasonCode,
    CapabilityCategory,
    CapabilityCheckResult,
    CapabilityStatus,
)


def _base(status: CapabilityStatus) -> dict:
    return {
        "category": CapabilityCategory.STOCK,
        "status": status,
        "can_watch": True,
        "can_research": True,
        "can_ai_explain": True,
        "can_generate_action_suggestion": True,
        "can_create_paper_order": True,
        "can_create_paper_transaction": True,
        "can_enter_paper_portfolio": True,
        "blocked_reason_codes": [],
        "explanation_nl": "Toegestaan.",
    }


def test_capability_contracts_and_checks() -> None:
    AssetCapability(**_base(CapabilityStatus.ALLOWED))
    watch = _base(CapabilityStatus.WATCH_ONLY) | {
        "can_generate_action_suggestion": False,
        "can_create_paper_order": False,
        "can_create_paper_transaction": False,
        "can_enter_paper_portfolio": False,
        "blocked_reason_codes": [BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1],
    }
    AssetCapability(**watch)
    blocked = watch | {
        "status": CapabilityStatus.BLOCKED,
        "can_watch": False,
        "can_research": False,
    }
    AssetCapability(**blocked)

    with pytest.raises(ValidationError):
        AssetCapability(**(_base(CapabilityStatus.ALLOWED) | {"explanation_nl": " "}))
    with pytest.raises(ValidationError):
        AssetCapability(
            **(
                _base(CapabilityStatus.ALLOWED)
                | {"blocked_reason_codes": [BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1]}
            )
        )
    with pytest.raises(ValidationError):
        AssetCapability(**(watch | {"can_create_paper_order": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(watch | {"can_create_paper_transaction": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(watch | {"can_enter_paper_portfolio": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(blocked | {"can_generate_action_suggestion": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(blocked | {"can_create_paper_order": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(blocked | {"can_create_paper_transaction": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(blocked | {"can_enter_paper_portfolio": True}))
    with pytest.raises(ValidationError):
        AssetCapability(**(watch | {"blocked_reason_codes": []}))
    with pytest.raises(ValidationError):
        AssetCapability(**(blocked | {"blocked_reason_codes": []}))

    ok = CapabilityCheckResult(
        category=CapabilityCategory.STOCK,
        allowed=True,
        status=CapabilityStatus.ALLOWED,
        explanation_nl="ok",
        blocked_reason_codes=[],
    )
    assert isinstance(ok.model_dump(), dict)
    with pytest.raises(ValidationError):
        CapabilityCheckResult(
            category=CapabilityCategory.CRYPTO,
            allowed=False,
            status=CapabilityStatus.WATCH_ONLY,
            explanation_nl="nee",
            blocked_reason_codes=[],
        )
