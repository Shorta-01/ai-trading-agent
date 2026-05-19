"""Read-only trading settings payload for UI consumption."""

from collections.abc import Callable

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    SqlAlchemyTradingSettingsRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from portfolio_outlook_domain.settings import (
    AllowedUniverseSettings,
    UserStrategySettings,
    get_allowed_universe_help_texts,
    get_user_strategy_help_texts,
)
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings

ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemyTradingSettingsRepository,
]


def _always_blocked_asset_types() -> list[str]:
    allowed_universe = AllowedUniverseSettings()
    return [asset_type.value for asset_type in allowed_universe.blocked_asset_types]


def build_default_trading_settings_response(
    *,
    status_nl: str,
    message_nl: str,
) -> dict[str, object]:
    allowed_universe = AllowedUniverseSettings()
    user_strategy = UserStrategySettings()
    always_blocked = _always_blocked_asset_types()

    return {
        "title_nl": "Trading instellingen",
        "status_nl": status_nl,
        "settings_source": "domain_defaults",
        "settings_source_nl": "Standaardinstellingen",
        "settings_loaded_from_storage": False,
        "storage_available": False,
        "message_nl": message_nl,
        "allowed_universe": allowed_universe.model_dump(mode="json"),
        "user_strategy": user_strategy.model_dump(mode="json"),
        "help_texts": [
            help_text.model_dump(mode="json")
            for help_text in (
                *get_allowed_universe_help_texts(),
                *get_user_strategy_help_texts(),
            )
        ],
        "always_blocked_asset_types": always_blocked,
        "safety_summary_nl": (
            "Toegestane beleggingen zijn harde veiligheidsregels. "
            "Mijn strategie bepaalt alleen voorkeur en rangschikking."
        ),
    }


def build_trading_settings_response(
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> dict[str, object]:
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemyTradingSettingsRepository

    if not storage_settings.enabled:
        return build_default_trading_settings_response(
            status_nl="Standaard actief",
            message_nl="Standaardinstellingen geladen. Opslag staat uit.",
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return build_default_trading_settings_response(
            status_nl="Standaard actief",
            message_nl="Standaardinstellingen geladen. Database-url ontbreekt.",
        )

    provider = connection_provider_factory(build_database_connection_settings(database_url))
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            read_result = repository.get_settings("default")
            if not read_result.found or read_result.record is None:
                return build_default_trading_settings_response(
                    status_nl="Standaard actief",
                    message_nl=(
                        "Standaardinstellingen geladen. "
                        "Er zijn nog geen opgeslagen instellingen."
                    ),
                ) | {"storage_available": True}

            always_blocked = _always_blocked_asset_types()
            return {
                "title_nl": "Trading instellingen",
                "status_nl": "Opgeslagen actief",
                "settings_source": "storage",
                "settings_source_nl": "Opgeslagen instellingen",
                "settings_loaded_from_storage": True,
                "storage_available": True,
                "message_nl": "Opgeslagen trading instellingen geladen.",
                "allowed_universe": read_result.record.allowed_universe,
                "user_strategy": read_result.record.user_strategy,
                "help_texts": [
                    help_text.model_dump(mode="json")
                    for help_text in (
                        *get_allowed_universe_help_texts(),
                        *get_user_strategy_help_texts(),
                    )
                ],
                "always_blocked_asset_types": always_blocked,
                "safety_summary_nl": (
                    "Toegestane beleggingen zijn harde veiligheidsregels. "
                    "Mijn strategie bepaalt alleen voorkeur en rangschikking."
                ),
            }
    except StorageConnectionError:
        return build_default_trading_settings_response(
            status_nl="Standaard actief",
            message_nl="Standaardinstellingen geladen door veilige foutafhandeling.",
        )
