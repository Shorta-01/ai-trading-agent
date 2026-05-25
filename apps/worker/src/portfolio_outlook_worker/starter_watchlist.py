"""Task 128: locked starter-watchlist seed.

The seed runs at most once per ``ibkr_account_id`` (idempotency
enforced by the ``cold_start_seed_audit`` table's ``UNIQUE`` on
``ibkr_account_id``). Starter set v1 — locked by the Task 128
brainstorm 2026-05-25:

* 5 broad UCITS ETFs: SXR8, VWCE, EQQQ, EXSA, AGGH.
* 5 European blue chips: ASML.AS, MC.PA, NOVO-B.CO, SAP.DE, SHEL.L.
* 2 sector ETFs: WTEC, IS3N.

The seed function resolves each entry's IBKR ``conid`` via the
existing AssetListing storage (the lookup table mapping conid →
asset_id was populated by Task 93/94's identity flow). Unresolvable
conids are logged into the ``failed_conids_json`` field of the
seed-audit row; the remaining set still seeds.

Doctrine: safety booleans hard-False; orchestrator never bypasses
the unconfirmed gate; no advice generation runs as part of the
seed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    ColdStartAlreadySeededError,
    ColdStartSeedAuditEntry,
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistConfirmationAuditRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    WatchlistConfirmationAuditEntry,
    WatchlistConfirmationStateRecord,
    WatchlistItemSeedRecord,
)

logger = logging.getLogger(__name__)


SEED_VERSION = "v1"


@dataclass(frozen=True)
class StarterAsset:
    """Locked starter-set entry; resolved to AssetListing at seed time."""

    symbol: str
    exchange: str
    currency: str
    security_type: str
    name: str
    ibkr_conid_hint: str | None = None


# Locked v1 starter set — 12 UCITS-eligible candidates curated for
# the cold-start onboarding. Symbols match IBKR's primary-listing
# convention (Xetra / Euronext / LSE / Borsa Italiana / Copenhagen).
STARTER_WATCHLIST_V1: tuple[StarterAsset, ...] = (
    # ---- broad UCITS ETFs ----
    StarterAsset(
        symbol="SXR8",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="iShares Core S&P 500 UCITS",
    ),
    StarterAsset(
        symbol="VWCE",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="Vanguard FTSE All-World UCITS",
    ),
    StarterAsset(
        symbol="EQQQ",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="Invesco Nasdaq-100 UCITS",
    ),
    StarterAsset(
        symbol="EXSA",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="iShares Stoxx 600 UCITS",
    ),
    StarterAsset(
        symbol="AGGH",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="Xtrackers Global Aggregate Bond UCITS",
    ),
    # ---- European blue chips ----
    StarterAsset(
        symbol="ASML",
        exchange="AEB",
        currency="EUR",
        security_type="STK",
        name="ASML Holding (Euronext)",
    ),
    StarterAsset(
        symbol="MC",
        exchange="SBF",
        currency="EUR",
        security_type="STK",
        name="LVMH Moet Hennessy Louis Vuitton (Paris)",
    ),
    StarterAsset(
        symbol="NOVO-B",
        exchange="CPH",
        currency="DKK",
        security_type="STK",
        name="Novo Nordisk B (Copenhagen)",
    ),
    StarterAsset(
        symbol="SAP",
        exchange="XETRA",
        currency="EUR",
        security_type="STK",
        name="SAP SE (Xetra)",
    ),
    StarterAsset(
        symbol="SHEL",
        exchange="LSE",
        currency="GBP",
        security_type="STK",
        name="Shell plc (London)",
    ),
    # ---- sector UCITS ETFs ----
    StarterAsset(
        symbol="WTEC",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="WisdomTree Cybersecurity UCITS",
    ),
    StarterAsset(
        symbol="IS3N",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        name="iShares MSCI World Healthcare UCITS",
    ),
)


class AssetListingResolverProtocol(Protocol):
    """Subset of the AssetListing repo the seed needs.

    Returns ``None`` when no validated listing exists for the
    (symbol, exchange) pair so the seed function can log the failure
    without raising.
    """

    def find_listing(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
    ) -> object | None: ...


@dataclass(frozen=True)
class SeedResult:
    """Return value from :func:`seed_starter_watchlist`."""

    already_seeded: bool
    seeded_count: int
    failed_symbols: tuple[str, ...]


def seed_starter_watchlist(
    *,
    ibkr_account_id: str,
    seed_audit_repo: SqlAlchemyColdStartSeedAuditRepository,
    watchlist_seed_repo: SqlAlchemyWatchlistItemSeedRepository,
    confirmation_state_repo: SqlAlchemyWatchlistConfirmationStateRepository,
    confirmation_audit_repo: SqlAlchemyWatchlistConfirmationAuditRepository,
    listing_resolver: AssetListingResolverProtocol | None = None,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> SeedResult:
    """Seed the locked starter set into ``watchlist_items``.

    The function is idempotent — if the seed-audit row already
    exists for ``ibkr_account_id`` it returns ``already_seeded=True``
    without touching the watchlist.

    Per-asset failure handling: when ``listing_resolver`` is supplied
    and a starter asset can't be resolved to an AssetListing, the
    seed continues with the rest and records the failure in the
    audit row. When ``listing_resolver`` is ``None`` the seed
    proceeds without identity validation (the watchlist row carries
    a ``None`` ``asset_id``).
    """

    if not ibkr_account_id:
        raise ValueError("ibkr_account_id is required for the seed")

    # Idempotency: prior seed exists → return early.
    existing = seed_audit_repo.find_by_account_id(ibkr_account_id)
    if existing is not None:
        return SeedResult(
            already_seeded=True,
            seeded_count=existing.seeded_count,
            failed_symbols=tuple(),
        )

    now = now_provider()
    seeded = 0
    failed: list[str] = []

    for asset in STARTER_WATCHLIST_V1:
        asset_id: str | None = None
        if listing_resolver is not None:
            listing = listing_resolver.find_listing(
                symbol=asset.symbol,
                exchange=asset.exchange,
                currency=asset.currency,
            )
            if listing is None:
                failed.append(asset.symbol)
                continue
            asset_id = getattr(listing, "asset_id", None)
        record = WatchlistItemSeedRecord(
            watchlist_item_id=f"wi_{uuid4().hex}",
            ibkr_account_id=ibkr_account_id,
            asset_id=asset_id,
            symbol=asset.symbol,
            name=asset.name,
            exchange=asset.exchange,
            currency=asset.currency,
            security_type=asset.security_type,
            status="active",
            source="cold_start_seed",
            is_starter_seed=True,
            seed_version=SEED_VERSION,
            created_at=now,
            updated_at=now,
        )
        try:
            watchlist_seed_repo.append(record)
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to insert starter row for %s; continuing.",
                asset.symbol,
            )
            failed.append(asset.symbol)
            continue
        seeded += 1

    # Try to record the seed-audit row. If it already exists (race),
    # report as already-seeded without raising.
    try:
        seed_audit_repo.append(
            ColdStartSeedAuditEntry(
                seeded_at=now,
                ibkr_account_id=ibkr_account_id,
                seeded_count=seeded,
                failed_conids_json=json.dumps(failed),
                seed_version=SEED_VERSION,
            )
        )
    except ColdStartAlreadySeededError:
        return SeedResult(
            already_seeded=True,
            seeded_count=seeded,
            failed_symbols=tuple(failed),
        )

    # Initialise the confirmation state row + audit transition.
    confirmation_state_repo.upsert(
        WatchlistConfirmationStateRecord(
            ibkr_account_id=ibkr_account_id,
            state="unconfirmed",
            last_updated_at=now,
        )
    )
    confirmation_audit_repo.append(
        WatchlistConfirmationAuditEntry(
            event_at=now,
            ibkr_account_id=ibkr_account_id,
            from_state="absent",
            to_state="unconfirmed",
            actor="system",
            row_count_at_event=seeded,
            details_json=json.dumps(
                {"seed_version": SEED_VERSION, "failed": failed}
            ),
        )
    )

    return SeedResult(
        already_seeded=False,
        seeded_count=seeded,
        failed_symbols=tuple(failed),
    )


__all__ = [
    "SEED_VERSION",
    "STARTER_WATCHLIST_V1",
    "AssetListingResolverProtocol",
    "SeedResult",
    "StarterAsset",
    "seed_starter_watchlist",
]
