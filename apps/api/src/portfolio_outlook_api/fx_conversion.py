"""Historische FX-conversie naar EUR (V1.2 §BB).

Doelen:

* Trade-rapport in EUR ipv lokale munt door de dagkoers van de
  transactiedag te gebruiken.
* Wanneer geen koers beschikbaar is (provider has no data, weekend
  zonder fallback, currency niet ondersteund), faillen we cleanly
  terug op lokale munt + een note voor de accountant.

Gebruikt de bestaande ``fx_rates`` tabel met provider="eodhd". De
``get_nearest_rate`` lookup pakt de meest recente koers op of vóór
de doel-datum — dat is wat een accountant ook doet voor weekend-
transacties.

Pure functies + één I/O-helper. Caller injecteert een storage
provider in tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ai_trading_agent_storage import SqlAlchemyFxRateRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FxRateLookup:
    """Result van een (currency, date) → EUR conversie-lookup."""

    rate_to_eur: Decimal
    rate_date: date
    provider: str
    requested_date: date


def _resolve_provider() -> str:
    return "eodhd"


def _try_get_lookup(
    repo: SqlAlchemyFxRateRepository,
    *,
    currency: str,
    on_date: date,
) -> FxRateLookup | None:
    """Return rate-to-EUR voor 1 unit van ``currency`` op ``on_date``.

    We zoeken eerst ``EUR/{currency}`` (standaard EODHD-format) en
    inverteren. Als dat faalt, proberen we ``{currency}/EUR`` direct.
    """

    if currency.upper() == "EUR":
        return FxRateLookup(
            rate_to_eur=Decimal(1),
            rate_date=on_date,
            provider="eur-identity",
            requested_date=on_date,
        )

    provider = _resolve_provider()
    # EODHD heeft typisch EUR als base voor EUR/USD, EUR/GBP, etc.
    record = repo.get_nearest_rate(
        base_currency="EUR",
        quote_currency=currency.upper(),
        as_of_date=on_date,
        provider=provider,
    )
    if record is not None and record.rate > 0:
        return FxRateLookup(
            rate_to_eur=Decimal(1) / record.rate,
            rate_date=record.as_of_date,
            provider=provider,
            requested_date=on_date,
        )
    # Fallback: directe quote.
    record = repo.get_nearest_rate(
        base_currency=currency.upper(),
        quote_currency="EUR",
        as_of_date=on_date,
        provider=provider,
    )
    if record is not None and record.rate > 0:
        return FxRateLookup(
            rate_to_eur=record.rate,
            rate_date=record.as_of_date,
            provider=provider,
            requested_date=on_date,
        )
    return None


class FxConverter:
    """Stateful FX-converter die rates cacht per (currency, date).

    Vermijdt dubbel-lookups wanneer 100 fills allemaal op dezelfde
    datum staan. Niet thread-safe — de API-routes openen elk een
    eigen converter binnen één checked_connection scope.
    """

    def __init__(self, repo: SqlAlchemyFxRateRepository) -> None:
        self._repo = repo
        self._cache: dict[tuple[str, date], FxRateLookup | None] = {}

    def to_eur(
        self, *, amount: Decimal, currency: str, on_date: date
    ) -> tuple[Decimal | None, FxRateLookup | None]:
        """Convert ``amount`` in ``currency`` op ``on_date`` naar EUR.

        Returns ``(eur_amount, lookup)`` of ``(None, None)`` wanneer
        geen koers beschikbaar is.
        """

        key = (currency.upper(), on_date)
        if key not in self._cache:
            self._cache[key] = _try_get_lookup(
                self._repo, currency=currency, on_date=on_date
            )
        lookup = self._cache[key]
        if lookup is None:
            return None, None
        return amount * lookup.rate_to_eur, lookup


__all__ = ["FxConverter", "FxRateLookup"]
