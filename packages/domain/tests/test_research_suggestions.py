from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain.research_suggestions import (
    ActionSuggestion,
    AIResearchOutput,
    AIResearchRunStatus,
    AIResearchUseStatus,
    CatalystEvent,
    CatalystEventType,
    CatalystImpactLevel,
    FreshnessAssessment,
    FreshnessSla,
    FreshnessStatus,
    PromptInjectionAssessment,
    PromptInjectionRiskLevel,
    ResearchDataType,
    ResearchDocumentType,
    ResearchRun,
    ResearchSourceReference,
    ResearchSourceStatus,
    ResearchSourceType,
    SourceAuthorityCategory,
    SourceCredibilityAssessment,
    SourceCredibilityLevel,
    SuggestionAction,
    SuggestionAuditLink,
    SuggestionConfidence,
    SuggestionOutcomePlaceholder,
    SuggestionOutcomeStatus,
    SuggestionStatus,
    SuggestionTimeSensitivity,
    SuggestionValidityWindow,
    action_label_nl,
    default_credibility_for_source_type,
    default_freshness_slas,
    suggestion_can_be_converted_to_ibkr_action,
)


def test_research_source_requires_non_empty_fields() -> None:
    with pytest.raises(ValueError):
        ResearchSourceReference(
            source_id="",
            source_type=ResearchSourceType.USER_NOTE,
            document_type=ResearchDocumentType.USER_NOTE,
            title="ok",
            uploaded_by_user=True,
            created_at=datetime.now(UTC),
            status=ResearchSourceStatus.NEW,
            explanation_nl="x",
        )


def test_credibility_and_helpers() -> None:
    c = SourceCredibilityAssessment(
        source_id="s1",
        authority_category=SourceAuthorityCategory.BROKER_TRUTH,
        credibility_level=SourceCredibilityLevel.HIGHEST,
        credibility_score=Decimal("99"),
        reason_nl="ok",
        assessed_at=datetime.now(UTC),
    )
    assert isinstance(c.credibility_score, Decimal)
    with pytest.raises(ValueError):
        SourceCredibilityAssessment(
            source_id="s1",
            authority_category=SourceAuthorityCategory.BROKER_TRUTH,
            credibility_level=SourceCredibilityLevel.HIGHEST,
            credibility_score=99.1,
            reason_nl="ok",
            assessed_at=datetime.now(UTC),
        )
    assert (
        default_credibility_for_source_type(ResearchSourceType.BROKER_DATA).credibility_level
        == SourceCredibilityLevel.HIGHEST
    )


def test_freshness_and_prompt_injection_rules() -> None:
    with pytest.raises(ValueError):
        FreshnessSla(
            data_type=ResearchDataType.BROKER_CASH,
            max_age_seconds=0,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=True,
            warning_nl="w",
            explanation_nl="e",
        )
    with pytest.raises(ValueError):
        PromptInjectionAssessment(
            source_id="s",
            risk_level=PromptInjectionRiskLevel.LOW,
            signals=(),
            safe_to_use_as_evidence=True,
            safe_to_use_as_instruction=True,
            assessed_at=datetime.now(UTC),
            explanation_nl="x",
        )
    run = ResearchRun(
        research_run_id="r1",
        asset_symbol="ASML",
        requested_at=datetime.now(UTC),
        status=AIResearchRunStatus.REQUESTED,
        source_ids=("s1",),
        estimated_cost=Decimal("1.23"),
        use_status=AIResearchUseStatus.NOT_USED,
        explanation_nl="x",
    )
    assert isinstance(run.estimated_cost, Decimal)
    slas = {sla.data_type for sla in default_freshness_slas()}
    assert ResearchDataType.AI_RESEARCH in slas


def test_suggestion_contracts() -> None:
    event = CatalystEvent(
        event_id="e1",
        event_type=CatalystEventType.EARNINGS,
        impact_level=CatalystImpactLevel.HIGH,
        known_before_suggestion=True,
        reason_nl="x",
    )
    window = SuggestionValidityWindow(
        valid_from=datetime.now(UTC),
        expires_on_market_close=True,
        expires_on_price_change=False,
        expires_on_event=True,
        related_event_ids=("e1",),
        reason_nl="x",
    )
    audit = SuggestionAuditLink(
        research_run_ids=("r1",),
        source_ids=("s1",),
        freshness_assessment_ids=("f1",),
        catalyst_event_ids=("e1",),
        system_event_ids=("se1",),
        explanation_nl="x",
    )
    suggestion = ActionSuggestion(
        suggestion_id="sg2",
        asset_symbol="ASML",
        action=SuggestionAction.HOUDEN,
        status=SuggestionStatus.ACTIVE,
        confidence=SuggestionConfidence.MEDIUM,
        time_sensitivity=SuggestionTimeSensitivity.SHORT_TERM,
        title_nl="t",
        summary_nl="s",
        reason_nl="r",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        validity_window=window,
        blocked_reasons=(),
        freshness_assessments=(
            FreshnessAssessment(
                data_type=ResearchDataType.AI_RESEARCH,
                status=FreshnessStatus.FRESH,
                checked_at=datetime.now(UTC),
                age_seconds=0,
                max_age_seconds=86400,
                blocks_suggestions=False,
                blocks_orders=False,
                reason_nl="ok",
            ),
        ),
        source_credibility_assessments=(),
        catalyst_events=(event,),
        audit_link=audit,
        can_be_converted_to_ibkr_action=True,
    )
    assert suggestion_can_be_converted_to_ibkr_action(suggestion)
    outcome = SuggestionOutcomePlaceholder(
        suggestion_id="sg2", status=SuggestionOutcomeStatus.PENDING, notes_nl="x"
    )
    assert outcome.status == SuggestionOutcomeStatus.PENDING
    assert action_label_nl(SuggestionAction.KOPEN) == "Kopen"


def test_ai_output_contract_only() -> None:
    output = AIResearchOutput(
        research_run_id="r1",
        asset_symbol="ASML",
        summary_nl="Samenvatting",
        positive_evidence=(),
        negative_evidence=(),
        uncertainties_nl=(),
        catalyst_notes_nl=(),
        risk_notes_nl=(),
        source_ids=("s1",),
        schema_version="1.0",
        generated_at=datetime.now(UTC),
        validation_passed=True,
        explanation_nl="x",
    )
    assert output.validation_passed
