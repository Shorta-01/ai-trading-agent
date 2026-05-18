from pydantic import BaseModel, Field, model_validator

from .enums import BlockedReasonCode, CapabilityCategory, CapabilityStatus


class AssetCapability(BaseModel):
    category: CapabilityCategory
    status: CapabilityStatus
    can_watch: bool
    can_research: bool
    can_ai_explain: bool
    can_generate_action_suggestion: bool
    can_create_paper_order: bool
    can_create_paper_transaction: bool
    can_enter_paper_portfolio: bool
    blocked_reason_codes: list[BlockedReasonCode] = Field(default_factory=list)
    explanation_nl: str

    @model_validator(mode="after")
    def validate_rules(self) -> "AssetCapability":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl mag niet leeg zijn")

        if self.status is CapabilityStatus.ALLOWED:
            if not self.can_watch or not self.can_research or not self.can_ai_explain:
                raise ValueError("allowed categorie moet watch/research/ai uitleg toelaten")
            if self.blocked_reason_codes:
                raise ValueError("allowed categorie mag geen blocked_reason_codes hebben")

        if self.status is CapabilityStatus.WATCH_ONLY:
            if not self.can_watch or not self.can_research or not self.can_ai_explain:
                raise ValueError("watch_only categorie moet watch/research/ai uitleg toelaten")
            if self.can_generate_action_suggestion:
                raise ValueError("watch_only categorie mag geen actiesuggestie toelaten")
            if self.can_create_paper_order:
                raise ValueError("watch_only categorie mag geen paper order toelaten")
            if self.can_create_paper_transaction:
                raise ValueError("watch_only categorie mag geen paper transactie toelaten")
            if self.can_enter_paper_portfolio:
                raise ValueError("watch_only categorie mag niet in paper portefeuille")
            if not self.blocked_reason_codes:
                raise ValueError("watch_only categorie vereist blocked_reason_codes")

        if self.status is CapabilityStatus.BLOCKED:
            if self.can_generate_action_suggestion:
                raise ValueError("blocked categorie mag geen actiesuggestie toelaten")
            if self.can_create_paper_order:
                raise ValueError("blocked categorie mag geen paper order toelaten")
            if self.can_create_paper_transaction:
                raise ValueError("blocked categorie mag geen paper transactie toelaten")
            if self.can_enter_paper_portfolio:
                raise ValueError("blocked categorie mag niet in paper portefeuille")
            if not self.blocked_reason_codes:
                raise ValueError("blocked categorie vereist blocked_reason_codes")

        return self


class CapabilityCheckResult(BaseModel):
    category: CapabilityCategory
    allowed: bool
    status: CapabilityStatus
    explanation_nl: str
    blocked_reason_codes: list[BlockedReasonCode] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_result(self) -> "CapabilityCheckResult":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl mag niet leeg zijn")
        if not self.allowed and not self.blocked_reason_codes:
            raise ValueError("blocked_reason_codes zijn verplicht als allowed false is")
        return self
