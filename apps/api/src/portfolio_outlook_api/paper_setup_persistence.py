from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from ai_trading_agent_storage import (
    CreatePaperPortfolioSetupRequest,
    SqlAlchemyPaperPortfolioSetupRepository,
    StorageConnectionError,
    StorageConnectionNotReadyError,
    StorageConnectionProvider,
)
from ai_trading_agent_storage.settings import DatabaseConnectionSettings
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings
from portfolio_outlook_api.paper_setup import (
    SETUP_STATUS_FIRST_RUN,
    SETUP_STATUS_PREVIEW_READY,
    SetupPreviewInput,
)


@dataclass(frozen=True)
class PaperSetupPersistenceResult:
    response: dict[str, object]
    blocked: bool


ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[[Connection, object], SqlAlchemyPaperPortfolioSetupRepository]
DateTimeProvider = Callable[[], datetime]
IdProvider = Callable[[], str]


def persist_first_run_paper_setup(
    payload: SetupPreviewInput,
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory = StorageConnectionProvider,
    repository_factory: RepositoryFactory = SqlAlchemyPaperPortfolioSetupRepository,
    now_provider: DateTimeProvider = lambda: datetime.now(UTC),
    id_provider: IdProvider = lambda: f"paper-setup-{uuid4()}",
) -> PaperSetupPersistenceResult:
    if not storage_settings.enabled:
        return PaperSetupPersistenceResult(
            response={
                "setup_status": "blocked",
                "persisted": False,
                "message_nl": "Opslag staat uit. Opslaan is geblokkeerd.",
            },
            blocked=True,
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return PaperSetupPersistenceResult(
            response={
                "setup_status": "blocked",
                "persisted": False,
                "message_nl": "Database-url ontbreekt. Opslaan is geblokkeerd.",
            },
            blocked=True,
        )

    provider = connection_provider_factory(DatabaseConnectionSettings(database_url=database_url))

    try:
        with provider.checked_connection(require_writable=True) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            setup_id = id_provider()
            created_at = now_provider()
            write_result = repository.create_setup(
                CreatePaperPortfolioSetupRequest(
                    setup_id=setup_id,
                    portfolio_name=payload.portfolio_name,
                    base_currency=payload.base_currency,
                    starting_cash_amount=Decimal(payload.starting_cash),
                    status=SETUP_STATUS_FIRST_RUN,
                    created_at=created_at,
                    explanation_nl="Eerste paper setup opgeslagen via API.",
                )
            )

            return PaperSetupPersistenceResult(
                response={
                    "setup_status": SETUP_STATUS_PREVIEW_READY,
                    "setup_mode": SETUP_STATUS_FIRST_RUN,
                    "persisted": write_result.success,
                    "setup_id": setup_id,
                    "title_nl": "Paper setup opgeslagen",
                    "summary_nl": "Je paper setup is veilig opgeslagen.",
                    "help_nl": "Alleen paper trading. Echte orders blijven uit.",
                    "message_nl": "Opslaan gelukt.",
                },
                blocked=False,
            )
    except StorageConnectionNotReadyError:
        return PaperSetupPersistenceResult(
            response={
                "setup_status": "blocked",
                "persisted": False,
                "message_nl": "Writes zijn geblokkeerd door migratie-readiness.",
            },
            blocked=True,
        )
    except StorageConnectionError:
        return PaperSetupPersistenceResult(
            response={
                "setup_status": "blocked",
                "persisted": False,
                "message_nl": "Databaseverbinding mislukt. Opslaan is geblokkeerd.",
            },
            blocked=True,
        )
