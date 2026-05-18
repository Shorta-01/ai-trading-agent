from portfolio_outlook_domain import (
    StorageReadinessCheck,
    storage_allows_paper_setup_persistence,
    storage_allows_transaction_persistence,
)

from .errors import InvalidAccountingInputError


def check_storage_allows_paper_setup_persistence(check: StorageReadinessCheck) -> bool:
    return storage_allows_paper_setup_persistence(check)


def require_storage_allows_paper_setup_persistence(check: StorageReadinessCheck) -> None:
    if not check_storage_allows_paper_setup_persistence(check):
        raise InvalidAccountingInputError("Opslag is nog niet klaar om setup op te slaan.")


def check_storage_allows_transaction_persistence(check: StorageReadinessCheck) -> bool:
    return storage_allows_transaction_persistence(check)


def require_storage_allows_transaction_persistence(check: StorageReadinessCheck) -> None:
    if not check_storage_allows_transaction_persistence(check):
        raise InvalidAccountingInputError("Opslag is nog niet klaar om transacties op te slaan.")
