from portfolio_outlook_domain import (
    FirstRunPaperPortfolioSetupPreview,
    FirstRunPaperPortfolioSetupRequest,
    PaperPortfolioBaseCurrency,
    PaperSetupStatus,
)

from .errors import InvalidAccountingInputError


def check_first_run_setup_request_allowed(request: FirstRunPaperPortfolioSetupRequest) -> bool:
    return (
        request.user_confirmed_paper_only
        and request.user_confirmed_no_real_money
        and request.user_confirmed_no_broker_order
        and request.starting_cash > 0
        and request.base_currency is PaperPortfolioBaseCurrency.EUR
    )


def require_first_run_setup_request_allowed(request: FirstRunPaperPortfolioSetupRequest) -> None:
    if not check_first_run_setup_request_allowed(request):
        raise InvalidAccountingInputError("First-run setup request is not allowed.")


def check_setup_preview_safe(preview: FirstRunPaperPortfolioSetupPreview) -> bool:
    return (
        not preview.block_reasons
        and preview.setup_status
        in {PaperSetupStatus.PREVIEW_READY, PaperSetupStatus.READY_TO_CREATE}
        and not preview.persisted
        and preview.request.user_confirmed_paper_only
        and preview.request.user_confirmed_no_real_money
        and preview.request.user_confirmed_no_broker_order
    )


def require_setup_preview_safe(preview: FirstRunPaperPortfolioSetupPreview) -> None:
    if not check_setup_preview_safe(preview):
        raise InvalidAccountingInputError("First-run setup preview is unsafe.")
