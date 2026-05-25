"""Task 131: resolve the forecast universe for a given account.

The universe is the **union** of:

* every confirmed-watchlist item for the account (active rows in
  ``watchlist_items`` with non-empty ``ibkr_conid``); and
* every position the account currently holds (latest IBKR position
  snapshot with ``quantity > 0``).

Deduplicated by conid. Order is symbol-asc, watchlist first, so that
when both sources surface the same conid the held-quantity flag from
the position snapshot wins.

A separate ``override`` channel exists for testing: when
``FORECAST_OVERRIDE_CONIDS`` is set the resolver returns those conids
directly without consulting storage — used to pin the universe to
specific test fixtures.

Pure resolution logic — no storage I/O happens here. Callers wire
storage adapters via the Protocols below; in tests they're tiny
hand-built fakes. The doctrine lock from Task 130 carries over: no
network calls, no AI, no fabricated data.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ConidWithContext:
    """One asset in the resolved universe.

    The flags here are read by the forecasting step's label
    translator (``user_holds_position``) and the audit row
    (``source`` so the operator can see why the conid was included).
    """

    conid: str
    symbol: str
    source: str  # one of: "watchlist", "position", "both", "override"
    held_quantity: Decimal
    user_holds_position: bool


class WatchlistUniverseProvider(Protocol):
    """Storage adapter exposing confirmed-watchlist conids."""

    def list_active_conids_for_account(
        self, ibkr_account_id: str
    ) -> tuple[tuple[str, str], ...]:
        """Return ``((conid, symbol), ...)`` for active items.

        Implementations skip rows with empty ``ibkr_conid`` — those
        aren't forecastable until the user resolves the contract.
        """
        ...


class PositionUniverseProvider(Protocol):
    """Storage adapter exposing the account's current held positions."""

    def list_held_positions_for_account(
        self, ibkr_account_id: str
    ) -> tuple[tuple[str, str, Decimal], ...]:
        """Return ``((conid, symbol, quantity), ...)`` for held positions.

        Held means ``quantity > 0``. Implementations are responsible
        for resolving the latest snapshot per (account, conid).
        """
        ...


def resolve_forecast_universe(
    *,
    ibkr_account_id: str,
    watchlist_provider: WatchlistUniverseProvider,
    position_provider: PositionUniverseProvider,
    override_conids: tuple[str, ...] | None = None,
) -> tuple[ConidWithContext, ...]:
    """Resolve the deduplicated forecast universe for an account.

    When ``override_conids`` is non-empty the providers are
    bypassed entirely and the override list is returned — used for
    deterministic test scenarios and the ``FORECAST_OVERRIDE_CONIDS``
    env var.
    """

    if override_conids:
        return tuple(
            ConidWithContext(
                conid=conid,
                symbol=conid,
                source="override",
                held_quantity=Decimal("0"),
                user_holds_position=False,
            )
            for conid in _dedup_preserving_order(override_conids)
        )

    watchlist_rows = tuple(
        watchlist_provider.list_active_conids_for_account(ibkr_account_id)
    )
    position_rows = tuple(
        position_provider.list_held_positions_for_account(ibkr_account_id)
    )

    watchlist_conids: dict[str, str] = {}
    for conid, symbol in watchlist_rows:
        if not conid or not conid.strip():
            continue
        watchlist_conids.setdefault(conid, symbol or conid)

    position_data: dict[str, tuple[str, Decimal]] = {}
    for conid, symbol, quantity in position_rows:
        if not conid or not conid.strip():
            continue
        if quantity <= 0:
            continue
        position_data.setdefault(conid, (symbol or conid, quantity))

    all_conids = sorted(set(watchlist_conids.keys()) | set(position_data.keys()))
    universe: list[ConidWithContext] = []
    for conid in all_conids:
        in_watchlist = conid in watchlist_conids
        position_entry = position_data.get(conid)
        if in_watchlist and position_entry is not None:
            symbol, quantity = position_entry
            source = "both"
            held_quantity = quantity
            held = True
        elif in_watchlist:
            symbol = watchlist_conids[conid]
            source = "watchlist"
            held_quantity = Decimal("0")
            held = False
        else:
            assert position_entry is not None  # narrow for type-checker
            symbol, quantity = position_entry
            source = "position"
            held_quantity = quantity
            held = True
        universe.append(
            ConidWithContext(
                conid=conid,
                symbol=symbol,
                source=source,
                held_quantity=held_quantity,
                user_holds_position=held,
            )
        )
    return tuple(universe)


def _dedup_preserving_order(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


__all__ = [
    "ConidWithContext",
    "PositionUniverseProvider",
    "WatchlistUniverseProvider",
    "resolve_forecast_universe",
]
