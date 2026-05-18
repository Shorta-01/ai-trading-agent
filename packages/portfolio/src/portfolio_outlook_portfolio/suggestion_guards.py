from portfolio_outlook_domain import (
    DataQualityGate,
    SuggestionEligibilityCheck,
    SuggestionEligibilityStatus,
    gate_allows_suggestions,
)

from .errors import InvalidAccountingInputError


def require_suggestion_eligible(check: SuggestionEligibilityCheck) -> None:
    if not check_suggestion_eligible(check):
        raise InvalidAccountingInputError("Suggestie is niet eligible.")


def check_suggestion_eligible(check: SuggestionEligibilityCheck) -> bool:
    return check.status in {
        SuggestionEligibilityStatus.ELIGIBLE,
        SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
    }


def require_data_quality_allows_suggestions(gate: DataQualityGate) -> None:
    if not check_data_quality_allows_suggestions(gate):
        raise InvalidAccountingInputError("Datakwaliteit laat geen suggestie toe.")


def check_data_quality_allows_suggestions(gate: DataQualityGate) -> bool:
    return bool(gate_allows_suggestions(gate))
