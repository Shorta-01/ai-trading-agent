from portfolio_outlook_domain import (
    AssetCapability,
    BlockedReasonCode,
    CapabilityCategory,
    CapabilityCheckResult,
    CapabilityStatus,
)

from .errors import InvalidAccountingInputError


def _capability(
    *,
    category: CapabilityCategory,
    status: CapabilityStatus,
    can_watch: bool,
    can_research: bool,
    can_ai_explain: bool,
    can_generate_action_suggestion: bool,
    can_create_paper_order: bool,
    can_create_paper_transaction: bool,
    can_enter_paper_portfolio: bool,
    explanation_nl: str,
    blocked_reason_codes: list[BlockedReasonCode] | None = None,
) -> AssetCapability:
    return AssetCapability(
        category=category,
        status=status,
        can_watch=can_watch,
        can_research=can_research,
        can_ai_explain=can_ai_explain,
        can_generate_action_suggestion=can_generate_action_suggestion,
        can_create_paper_order=can_create_paper_order,
        can_create_paper_transaction=can_create_paper_transaction,
        can_enter_paper_portfolio=can_enter_paper_portfolio,
        blocked_reason_codes=blocked_reason_codes or [],
        explanation_nl=explanation_nl,
    )


def _check_result(category: CapabilityCategory, allowed: bool) -> CapabilityCheckResult:
    capability = get_asset_capability(category)
    reasons = capability.blocked_reason_codes
    if not allowed and not reasons:
        reasons = [BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1]
    return CapabilityCheckResult(
        category=capability.category,
        allowed=allowed,
        status=capability.status,
        explanation_nl=capability.explanation_nl,
        blocked_reason_codes=reasons,
    )


def get_default_asset_capabilities() -> dict[CapabilityCategory, AssetCapability]:
    A = CapabilityStatus.ALLOWED
    W = CapabilityStatus.WATCH_ONLY
    B = CapabilityStatus.BLOCKED
    return {
        CapabilityCategory.CASH: _capability(
            category=CapabilityCategory.CASH,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl="Cash is toegestaan in versie 1.",
        ),
        CapabilityCategory.TERM_DEPOSIT: _capability(
            category=CapabilityCategory.TERM_DEPOSIT,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl="Termijnrekeningen zijn toegestaan in versie 1.",
        ),
        CapabilityCategory.UCITS_ETF: _capability(
            category=CapabilityCategory.UCITS_ETF,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl="Dit product is toegestaan voor de papieren portefeuille in versie 1.",
        ),
        CapabilityCategory.STOCK: _capability(
            category=CapabilityCategory.STOCK,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl="Aandelen zijn toegestaan in versie 1.",
        ),
        CapabilityCategory.FX: _capability(
            category=CapabilityCategory.FX,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl="Valuta zijn toegestaan in versie 1.",
        ),
        CapabilityCategory.BENCHMARK: _capability(
            category=CapabilityCategory.BENCHMARK,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            explanation_nl="Benchmarkdata is toegestaan voor vergelijking, niet voor orders.",
        ),
        CapabilityCategory.COMMODITY_ETF_ETC: _capability(
            category=CapabilityCategory.COMMODITY_ETF_ETC,
            status=A,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=True,
            can_create_paper_order=True,
            can_create_paper_transaction=True,
            can_enter_paper_portfolio=True,
            explanation_nl=(
                "Grondstoffen via gereguleerde ETF/ETC zijn toegestaan; "
                "olie blijft extra risicovol."
            ),
        ),
        CapabilityCategory.FUTURES: _capability(
            category=CapabilityCategory.FUTURES,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[
                BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1,
                BlockedReasonCode.DIRECT_COMMODITY_OR_FUTURE_BLOCKED,
            ],
            explanation_nl="Futures zijn niet toegestaan in versie 1 en blijven alleen opvolgbaar.",
        ),
        CapabilityCategory.OPTIONS: _capability(
            category=CapabilityCategory.OPTIONS,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[
                BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1,
                BlockedReasonCode.COMPLEX_DERIVATIVE,
            ],
            explanation_nl="Opties zijn niet toegestaan in versie 1 en blijven alleen opvolgbaar.",
        ),
        CapabilityCategory.LEVERAGE: _capability(
            category=CapabilityCategory.LEVERAGE,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.LEVERAGE_NOT_ALLOWED],
            explanation_nl="Leverage is niet toegestaan in versie 1 en blijft alleen opvolgbaar.",
        ),
        CapabilityCategory.SHORT_SELLING: _capability(
            category=CapabilityCategory.SHORT_SELLING,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.SHORT_SELLING_NOT_ALLOWED],
            explanation_nl=(
                "Short selling is niet toegestaan in versie 1 en blijft alleen opvolgbaar."
            ),
        ),
        CapabilityCategory.CRYPTO: _capability(
            category=CapabilityCategory.CRYPTO,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.CRYPTO_NOT_ALLOWED],
            explanation_nl=(
                "Crypto is niet toegestaan als belegging in versie 1 en blijft alleen opvolgbaar."
            ),
        ),
        CapabilityCategory.PENNY_STOCK: _capability(
            category=CapabilityCategory.PENNY_STOCK,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.PENNY_STOCK_NOT_ALLOWED],
            explanation_nl=(
                "Penny stocks zijn niet toegestaan in versie 1 en blijven alleen opvolgbaar."
            ),
        ),
        CapabilityCategory.COMPLEX_DERIVATIVE: _capability(
            category=CapabilityCategory.COMPLEX_DERIVATIVE,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.COMPLEX_DERIVATIVE],
            explanation_nl=(
                "Complexe derivaten zijn niet toegestaan in versie 1 en blijven alleen opvolgbaar."
            ),
        ),
        CapabilityCategory.HIGH_FREQUENCY_TRADING: _capability(
            category=CapabilityCategory.HIGH_FREQUENCY_TRADING,
            status=W,
            can_watch=True,
            can_research=True,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.HFT_NOT_ALLOWED],
            explanation_nl=(
                "High-frequency trading is niet toegestaan in versie 1 en blijft alleen opvolgbaar."
            ),
        ),
        CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION: _capability(
            category=CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION,
            status=B,
            can_watch=False,
            can_research=False,
            can_ai_explain=True,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.REAL_MONEY_EXECUTION_BLOCKED],
            explanation_nl=(
                "Automatische uitvoering met echt geld is volledig geblokkeerd in versie 1."
            ),
        ),
        CapabilityCategory.UNKNOWN: _capability(
            category=CapabilityCategory.UNKNOWN,
            status=B,
            can_watch=False,
            can_research=False,
            can_ai_explain=False,
            can_generate_action_suggestion=False,
            can_create_paper_order=False,
            can_create_paper_transaction=False,
            can_enter_paper_portfolio=False,
            blocked_reason_codes=[BlockedReasonCode.UNKNOWN_OR_UNSUPPORTED],
            explanation_nl=(
                "Onbekende productcategorie is niet ondersteund in versie 1 en blijft geblokkeerd."
            ),
        ),
    }


def get_asset_capability(category: CapabilityCategory) -> AssetCapability:
    capabilities = get_default_asset_capabilities()
    return capabilities.get(category, capabilities[CapabilityCategory.UNKNOWN])


def check_can_watch(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(category, get_asset_capability(category).can_watch)


def check_can_research(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(category, get_asset_capability(category).can_research)


def check_can_generate_action_suggestion(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(
        category,
        get_asset_capability(category).can_generate_action_suggestion,
    )


def check_can_create_paper_order(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(category, get_asset_capability(category).can_create_paper_order)


def check_can_create_paper_transaction(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(
        category,
        get_asset_capability(category).can_create_paper_transaction,
    )


def check_can_enter_paper_portfolio(category: CapabilityCategory) -> CapabilityCheckResult:
    return _check_result(
        category,
        get_asset_capability(category).can_enter_paper_portfolio,
    )


def require_can_create_paper_order(category: CapabilityCategory) -> None:
    result = check_can_create_paper_order(category)
    if not result.allowed:
        raise InvalidAccountingInputError(
            f"Papieren order niet toegestaan voor '{category.value}': {result.explanation_nl}"
        )


def require_can_create_paper_transaction(category: CapabilityCategory) -> None:
    result = check_can_create_paper_transaction(category)
    if not result.allowed:
        raise InvalidAccountingInputError(
            f"Papieren transactie niet toegestaan voor '{category.value}': {result.explanation_nl}"
        )
