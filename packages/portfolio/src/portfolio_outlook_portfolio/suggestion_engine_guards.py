from portfolio_outlook_domain import (
    ActionSuggestionDraft,
    CandidateSource,
    CandidateStatus,
    SuggestionCandidate,
    SuggestionDraftStatus,
)

from .errors import InvalidAccountingInputError


def check_candidate_ready_for_suggestion(candidate: SuggestionCandidate) -> bool:
    if candidate.status is not CandidateStatus.ELIGIBLE_FOR_SUGGESTION:
        return False
    if not candidate.audit_event_ids:
        return False
    if candidate.source is not CandidateSource.MANUAL_USER_INPUT and not candidate.source_reference_ids:
        return False
    return True


def require_candidate_ready_for_suggestion(candidate: SuggestionCandidate) -> None:
    if not check_candidate_ready_for_suggestion(candidate):
        raise InvalidAccountingInputError("Kandidaat is niet klaar voor suggestie.")


def check_suggestion_draft_ready(draft: ActionSuggestionDraft) -> bool:
    return (
        draft.status is SuggestionDraftStatus.READY_FOR_REVIEW
        and bool(draft.source_reference_ids)
        and bool(draft.audit_event_ids)
        and bool(draft.gate_result_ids)
    )


def require_suggestion_draft_ready(draft: ActionSuggestionDraft) -> None:
    if not check_suggestion_draft_ready(draft):
        raise InvalidAccountingInputError("Actiesuggestie-draft is niet klaar voor beoordeling.")
