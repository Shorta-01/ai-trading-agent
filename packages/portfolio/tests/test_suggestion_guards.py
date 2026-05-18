from datetime import UTC, datetime

import pytest
from portfolio_outlook_domain import (
    DataDomain,
    DataGateDecision,
    DataQualityGate,
    DataQualityGateStatus,
    SuggestionEligibilityStatus,
)

from portfolio_outlook_portfolio import (
    InvalidAccountingInputError,
    check_data_quality_allows_suggestions,
    check_suggestion_eligible,
    require_data_quality_allows_suggestions,
    require_suggestion_eligible,
)


def _check(status: SuggestionEligibilityStatus):
    from portfolio_outlook_domain import SuggestionEligibilityCheck

    return SuggestionEligibilityCheck(
        suggestion_eligibility_check_id="c1",
        policy_id="p1",
        data_quality_gate_id="g1",
        status=status,
        checked_at=datetime.now(UTC),
        explanation_nl="x",
        warning_reasons=[]
        if status is not SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
        else ["unknown"],
        block_reasons=[]
        if status
        in {
            SuggestionEligibilityStatus.ELIGIBLE,
            SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
            SuggestionEligibilityStatus.SKIPPED,
        }
        else ["data_quality_failed"],
        source_reference_ids=["src"],
        audit_event_ids=["aud"],
    )


def _gate(decision: DataGateDecision):
    status_by_decision = {
        DataGateDecision.CONTINUE_ALLOWED: DataQualityGateStatus.PASSED,
        DataGateDecision.CONTINUE_WITH_WARNING: DataQualityGateStatus.WARNING,
        DataGateDecision.SKIP_JOB: DataQualityGateStatus.SKIPPED,
        DataGateDecision.BLOCK_SUGGESTION: DataQualityGateStatus.BLOCKED,
    }
    try:
        status = status_by_decision[decision]
    except KeyError as exc:  # pragma: no cover - defensive for future enum expansion
        raise AssertionError(f"Unsupported test decision: {decision}") from exc

    return DataQualityGate(
        data_quality_gate_id="g1",
        gate_name="g",
        required_domains=[DataDomain.MARKET_DATA],
        status=status,
        decision=decision,
        checked_at=datetime.now(UTC),
        explanation_nl="x",
        source_reference_ids=["src"],
    )


def test_guards() -> None:
    require_suggestion_eligible(_check(SuggestionEligibilityStatus.ELIGIBLE))
    require_suggestion_eligible(_check(SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS))
    for status in [
        SuggestionEligibilityStatus.BLOCKED,
        SuggestionEligibilityStatus.FAILED,
        SuggestionEligibilityStatus.SKIPPED,
    ]:
        with pytest.raises(InvalidAccountingInputError):
            require_suggestion_eligible(_check(status))
    require_data_quality_allows_suggestions(_gate(DataGateDecision.CONTINUE_ALLOWED))
    with pytest.raises(InvalidAccountingInputError):
        require_data_quality_allows_suggestions(_gate(DataGateDecision.BLOCK_SUGGESTION))
    assert check_suggestion_eligible(_check(SuggestionEligibilityStatus.ELIGIBLE))
    assert not check_suggestion_eligible(_check(SuggestionEligibilityStatus.BLOCKED))
    assert check_data_quality_allows_suggestions(_gate(DataGateDecision.CONTINUE_WITH_WARNING))
    assert not check_data_quality_allows_suggestions(_gate(DataGateDecision.SKIP_JOB))
