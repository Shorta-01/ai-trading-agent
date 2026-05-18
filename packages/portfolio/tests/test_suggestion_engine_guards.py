from datetime import UTC, datetime

import pytest
from portfolio_outlook_domain import (
    ActionSuggestionDraft,
    AdviceAction,
    CandidateSource,
    CandidateStatus,
    SuggestionCandidate,
    SuggestionConfidenceLevel,
    SuggestionDraftStatus,
)
from portfolio_outlook_portfolio import (
    check_candidate_ready_for_suggestion,
    check_suggestion_draft_ready,
    require_candidate_ready_for_suggestion,
    require_suggestion_draft_ready,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def _candidate(**overrides: object) -> SuggestionCandidate:
    payload = {
        "candidate_id": "cand_1",
        "instrument_id": "inst_1",
        "source": CandidateSource.WATCHLIST,
        "status": CandidateStatus.ELIGIBLE_FOR_SUGGESTION,
        "source_reference_ids": ["src_1"],
        "audit_event_ids": ["aud_1"],
        "explanation_nl": "Kandidaat uit watchlist.",
        "created_at": datetime.now(UTC),
    }
    payload.update(overrides)
    return SuggestionCandidate(**payload)


def _draft(**overrides: object) -> ActionSuggestionDraft:
    payload = {
        "suggestion_draft_id": "draft_1",
        "candidate_id": "cand_1",
        "instrument_id": "inst_1",
        "action": AdviceAction.HOLD,
        "status": SuggestionDraftStatus.READY_FOR_REVIEW,
        "confidence": SuggestionConfidenceLevel.NOT_AVAILABLE,
        "gate_result_ids": ["gate_1"],
        "risk_gate_result_id": "risk_1",
        "suggestion_eligibility_check_id": "elig_1",
        "source_reference_ids": ["src_1"],
        "audit_event_ids": ["aud_1"],
        "title_nl": "Actiesuggestie",
        "summary_nl": "Samenvatting",
        "reason_nl": "Waarom",
        "risk_nl": "Risico",
        "next_step_nl": "Volgende stap",
        "created_at": datetime.now(UTC),
    }
    payload.update(overrides)
    return ActionSuggestionDraft(**payload)


def test_candidate_and_draft_guards() -> None:
    assert check_candidate_ready_for_suggestion(_candidate())
    assert not check_candidate_ready_for_suggestion(_candidate(status=CandidateStatus.BLOCKED))
    assert not check_candidate_ready_for_suggestion(_candidate(audit_event_ids=[]))
    assert not check_candidate_ready_for_suggestion(_candidate(source_reference_ids=[]))
    assert check_candidate_ready_for_suggestion(
        _candidate(source=CandidateSource.MANUAL_USER_INPUT, source_reference_ids=[])
    )

    assert check_suggestion_draft_ready(_draft())
    assert not check_suggestion_draft_ready(_draft(status=SuggestionDraftStatus.BLOCKED))
    assert not check_suggestion_draft_ready(_draft(gate_result_ids=[]))
    assert not check_suggestion_draft_ready(_draft(source_reference_ids=[]))


def test_require_helpers_raise() -> None:
    with pytest.raises(InvalidAccountingInputError):
        require_candidate_ready_for_suggestion(_candidate(status=CandidateStatus.BLOCKED))

    with pytest.raises(InvalidAccountingInputError):
        require_suggestion_draft_ready(_draft(gate_result_ids=[]))
