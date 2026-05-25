"""Task 131 — asset universe resolver tests."""

from __future__ import annotations

from decimal import Decimal

from portfolio_outlook_worker.forecasting.asset_universe_resolver import (
    resolve_forecast_universe,
)


class _StubWatchlist:
    def __init__(self, rows: tuple[tuple[str, str], ...]) -> None:
        self._rows = rows

    def list_active_conids_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str], ...]:
        return self._rows


class _StubPositions:
    def __init__(
        self, rows: tuple[tuple[str, str, Decimal], ...]
    ) -> None:
        self._rows = rows

    def list_held_positions_for_account(
        self, ibkr_account_id: str  # noqa: ARG002
    ) -> tuple[tuple[str, str, Decimal], ...]:
        return self._rows


# ---- union semantics --------------------------------------------


def test_union_of_watchlist_and_positions_dedupes_by_conid() -> None:
    watchlist = _StubWatchlist(
        (
            ("conid-A", "ASML.AS"),
            ("conid-B", "SAP.DE"),
            ("conid-C", "VWCE"),
        )
    )
    positions = _StubPositions(
        (
            ("conid-B", "SAP.DE", Decimal("5.0")),  # overlap
            ("conid-D", "AAPL", Decimal("10.0")),
        )
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=positions,
    )
    conids = [u.conid for u in universe]
    assert conids == ["conid-A", "conid-B", "conid-C", "conid-D"]


def test_overlap_marks_source_both_and_held_position_true() -> None:
    watchlist = _StubWatchlist((("conid-B", "SAP.DE"),))
    positions = _StubPositions(
        (("conid-B", "SAP.DE", Decimal("5.0")),)
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=positions,
    )
    assert len(universe) == 1
    row = universe[0]
    assert row.source == "both"
    assert row.user_holds_position is True
    assert row.held_quantity == Decimal("5.0")


def test_watchlist_only_marks_source_watchlist_and_not_held() -> None:
    watchlist = _StubWatchlist((("conid-A", "ASML.AS"),))
    positions = _StubPositions(())
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=positions,
    )
    assert len(universe) == 1
    assert universe[0].source == "watchlist"
    assert universe[0].user_holds_position is False
    assert universe[0].held_quantity == Decimal("0")


def test_position_only_marks_source_position_and_held() -> None:
    watchlist = _StubWatchlist(())
    positions = _StubPositions((("conid-D", "AAPL", Decimal("10.0")),))
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=positions,
    )
    assert universe[0].source == "position"
    assert universe[0].user_holds_position is True


# ---- empty + edge cases -----------------------------------------


def test_empty_both_sources_returns_empty_universe() -> None:
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=_StubWatchlist(()),
        position_provider=_StubPositions(()),
    )
    assert universe == ()


def test_unconfirmed_watchlist_universe_is_positions_only() -> None:
    # Unconfirmed = the resolver was given an empty watchlist list.
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=_StubWatchlist(()),
        position_provider=_StubPositions(
            (("conid-X", "TSLA", Decimal("2.0")),)
        ),
    )
    assert len(universe) == 1
    assert universe[0].conid == "conid-X"


def test_watchlist_rows_with_empty_conid_are_skipped() -> None:
    watchlist = _StubWatchlist(
        (
            ("", "BROKEN"),
            ("conid-A", "ASML.AS"),
            ("   ", "WHITESPACE"),
        )
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=_StubPositions(()),
    )
    assert len(universe) == 1
    assert universe[0].conid == "conid-A"


def test_positions_with_zero_or_negative_quantity_are_skipped() -> None:
    positions = _StubPositions(
        (
            ("conid-A", "ASML.AS", Decimal("5.0")),
            ("conid-B", "ZERO", Decimal("0")),
            ("conid-C", "SHORT", Decimal("-3.0")),
        )
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=_StubWatchlist(()),
        position_provider=positions,
    )
    assert {u.conid for u in universe} == {"conid-A"}


# ---- override channel -------------------------------------------


def test_override_bypasses_providers_entirely() -> None:
    watchlist = _StubWatchlist((("conid-A", "ASML.AS"),))
    positions = _StubPositions(
        (("conid-B", "SAP.DE", Decimal("5.0")),)
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=positions,
        override_conids=("OVERRIDE-1", "OVERRIDE-2"),
    )
    assert [u.conid for u in universe] == ["OVERRIDE-1", "OVERRIDE-2"]
    assert all(u.source == "override" for u in universe)
    assert all(u.user_holds_position is False for u in universe)


def test_override_dedupes_preserving_order() -> None:
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=_StubWatchlist(()),
        position_provider=_StubPositions(()),
        override_conids=("A", "B", "A", "C", "B"),
    )
    assert [u.conid for u in universe] == ["A", "B", "C"]


def test_returned_universe_is_sorted_by_conid_for_determinism() -> None:
    watchlist = _StubWatchlist(
        (
            ("conid-Z", "ZUO"),
            ("conid-A", "ASML"),
            ("conid-M", "MSFT"),
        )
    )
    universe = resolve_forecast_universe(
        ibkr_account_id="DU1",
        watchlist_provider=watchlist,
        position_provider=_StubPositions(()),
    )
    assert [u.conid for u in universe] == ["conid-A", "conid-M", "conid-Z"]
