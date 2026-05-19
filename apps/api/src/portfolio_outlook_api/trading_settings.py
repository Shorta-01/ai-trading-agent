"""Trading settings payload builders and save flow."""

from collections.abc import Callable
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    SaveTradingSettingsRequest,
    SqlAlchemyTradingSettingsRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from portfolio_outlook_domain.settings import (
    AllowedUniverseSettings,
    UserStrategySettings,
    get_allowed_universe_help_texts,
    get_user_strategy_help_texts,
)
from pydantic import BaseModel
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings

ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemyTradingSettingsRepository,
]


class TradingSettingsUpdateInput(BaseModel):
    allowed_universe: AllowedUniverseSettings
    user_strategy: UserStrategySettings
    reason_nl: str | None = None


def _always_blocked_asset_types() -> list[str]:
    allowed_universe = AllowedUniverseSettings()
    return [asset_type.value for asset_type in allowed_universe.blocked_asset_types]


def _help_texts() -> list[dict[str, str]]:
    return [
        help_text.model_dump(mode="json")
        for help_text in (*get_allowed_universe_help_texts(), *get_user_strategy_help_texts())
    ]


def _base_response(*, status_nl: str, message_nl: str, source: str) -> dict[str, object]:
    allowed_universe = AllowedUniverseSettings()
    user_strategy = UserStrategySettings()
    return {
        "title_nl": "Trading instellingen",
        "status_nl": status_nl,
        "settings_source": source,
        "settings_source_nl": (
            "Opgeslagen instellingen" if source == "storage" else "Standaardinstellingen"
        ),
        "settings_loaded_from_storage": source == "storage",
        "storage_available": source == "storage",
        "message_nl": message_nl,
        "allowed_universe": allowed_universe.model_dump(mode="json"),
        "user_strategy": user_strategy.model_dump(mode="json"),
        "help_texts": _help_texts(),
        "always_blocked_asset_types": _always_blocked_asset_types(),
        "safety_summary_nl": (
            "Toegestane beleggingen zijn harde veiligheidsregels. "
            "Mijn strategie bepaalt alleen voorkeur en rangschikking."
        ),
    }


def build_default_trading_settings_response(
    *, status_nl: str, message_nl: str
) -> dict[str, object]:
    return _base_response(status_nl=status_nl, message_nl=message_nl, source="domain_defaults")


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

            response = _base_response(
                status_nl="Opgeslagen actief",
                message_nl="Opgeslagen trading instellingen geladen.",
                source="storage",
            )
            response["allowed_universe"] = read_result.record.allowed_universe
            response["user_strategy"] = read_result.record.user_strategy
            return response
    except StorageConnectionError:
        return build_default_trading_settings_response(
            status_nl="Standaard actief",
            message_nl="Standaardinstellingen geladen door veilige foutafhandeling.",
        )


def update_trading_settings_response(
    payload: TradingSettingsUpdateInput,
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> dict[str, object]:
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemyTradingSettingsRepository

    if not storage_settings.enabled:
        response = _base_response(
            status_nl="Geblokkeerd",
            message_nl="Trading instellingen niet opgeslagen: opslag staat uit.",
            source="domain_defaults",
        )
        return response | {"updated": False, "settings_id": "default"}

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        response = _base_response(
            status_nl="Geblokkeerd",
            message_nl="Trading instellingen niet opgeslagen: database-url ontbreekt.",
            source="domain_defaults",
        )
        return response | {"updated": False, "settings_id": "default"}

    provider = connection_provider_factory(build_database_connection_settings(database_url))
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            request = SaveTradingSettingsRequest(
                settings_id="default",
                updated_at=datetime.now(UTC),
                allowed_universe=payload.allowed_universe.model_dump(mode="json"),
                user_strategy=payload.user_strategy.model_dump(mode="json"),
                source="api",
                status="active",
                explanation_nl=payload.reason_nl or "Instellingen aangepast door gebruiker.",
            )
            repository.save_settings(request)
            response = _base_response(
                status_nl="Opgeslagen",
                message_nl="Trading instellingen opgeslagen.",
                source="storage",
            )
            response["allowed_universe"] = request.allowed_universe
            response["user_strategy"] = request.user_strategy
            return response | {"updated": True, "settings_id": "default"}
    except StoragePersistenceBlockedError:
        response = _base_response(
            status_nl="Geblokkeerd",
            message_nl="Trading instellingen niet opgeslagen: writes geblokkeerd.",
            source="domain_defaults",
        )
        return response | {"updated": False, "settings_id": "default"}
    except StorageConnectionError:
        response = _base_response(
            status_nl="Niet opgeslagen",
            message_nl="Trading instellingen niet opgeslagen door veilige foutafhandeling.",
            source="domain_defaults",
        )
        return response | {"updated": False, "settings_id": "default"}
