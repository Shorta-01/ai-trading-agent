"""Read-only trading settings payload for UI consumption."""

from portfolio_outlook_domain.settings import (
    AllowedUniverseSettings,
    UserStrategySettings,
    get_allowed_universe_help_texts,
    get_user_strategy_help_texts,
)


def build_trading_settings_response() -> dict[str, object]:
    allowed_universe = AllowedUniverseSettings()
    user_strategy = UserStrategySettings()

    return {
        "title_nl": "Trading instellingen",
        "message_nl": (
            "Deze instellingen bepalen wat het systeem mag onderzoeken en "
            "wat bij je strategie past."
        ),
        "allowed_universe": allowed_universe.model_dump(mode="json"),
        "user_strategy": user_strategy.model_dump(mode="json"),
        "help_texts": [
            help_text.model_dump(mode="json")
            for help_text in (
                *get_allowed_universe_help_texts(),
                *get_user_strategy_help_texts(),
            )
        ],
        "always_blocked_asset_types": [
            asset_type.value for asset_type in allowed_universe.blocked_asset_types
        ],
        "safety_summary_nl": (
            "Toegestane beleggingen zijn harde veiligheidsregels. "
            "Mijn strategie bepaalt alleen voorkeur en rangschikking."
        ),
    }
