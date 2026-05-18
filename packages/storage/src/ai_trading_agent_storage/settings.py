"""Safe database settings helpers for migration planning only."""

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


@dataclass(frozen=True)
class DatabaseConnectionSettings:
    """Safe database connection summary without secret exposure."""

    database_url: str | None
    database_url_configured: bool
    safe_database_label: str
    explanation_nl: str


def _redacted_netloc(split_result: SplitResult) -> str:
    host = split_result.hostname or ""
    port = f":{split_result.port}" if split_result.port is not None else ""
    username = split_result.username

    if username is None:
        return f"{host}{port}"

    if split_result.password is None:
        return f"{username}@{host}{port}"

    return f"{username}:***@{host}{port}"


def redact_database_url(database_url: str | None) -> str:
    """Redact credential secrets in a database URL.

    Returns a Dutch not-configured label when URL is missing.
    """

    if database_url is None or database_url.strip() == "":
        return "Niet ingesteld"

    split_result = urlsplit(database_url)
    if split_result.scheme == "":
        return "Ongeldige database-url"

    redacted = split_result._replace(netloc=_redacted_netloc(split_result))
    return urlunsplit(redacted)


def build_database_connection_settings(database_url: str | None) -> DatabaseConnectionSettings:
    """Build safe, non-connecting storage configuration summary."""

    has_url = database_url is not None and database_url.strip() != ""
    safe_label = redact_database_url(database_url)
    return DatabaseConnectionSettings(
        database_url=database_url,
        database_url_configured=has_url,
        safe_database_label=safe_label,
        explanation_nl=(
            "Databasekoppeling is voorbereid voor latere migraties, "
            "maar de app-runtime gebruikt nog geen actieve databaseverbinding."
        ),
    )
