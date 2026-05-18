class PortfolioAccountingError(Exception):
    """Base exception for paper accounting helper errors."""


class CurrencyMismatchError(PortfolioAccountingError):
    """Raised when accounting inputs use different currencies."""


class InvalidAccountingInputError(PortfolioAccountingError):
    """Raised when accounting inputs fail deterministic validation."""


class InsufficientLotQuantityError(PortfolioAccountingError):
    """Raised when a lot allocation exceeds the available quantity."""
