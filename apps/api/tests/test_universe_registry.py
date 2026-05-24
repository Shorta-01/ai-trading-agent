"""Tests for the V1 universe registry (Slice 17)."""

from __future__ import annotations

from portfolio_outlook_api.universe_registry import (
    AEX,
    BEL20,
    CAC40,
    DAX40,
    NASDAQ100_EXTRA,
    SP100,
    UniverseEntry,
    locked_universe,
    universe_by_index,
)


def test_each_index_has_a_meaningful_minimum_size() -> None:
    assert len(BEL20) >= 20
    assert len(AEX) >= 23
    assert len(CAC40) >= 35
    assert len(DAX40) >= 35
    assert len(SP100) >= 90
    assert len(NASDAQ100_EXTRA) >= 50


def test_locked_universe_dedupes_overlapping_tickers() -> None:
    universe = locked_universe()
    eodhd_symbols = [e.eodhd_symbol for e in universe]
    assert len(eodhd_symbols) == len(set(eodhd_symbols))


def test_locked_universe_covers_all_indices() -> None:
    universe = locked_universe()
    seen_indices = {e.index_code for e in universe}
    assert {"BEL20", "AEX", "CAC40", "DAX40", "SP100"}.issubset(seen_indices)


def test_universe_by_index_filters_correctly() -> None:
    bel20 = universe_by_index("BEL20")
    assert all(e.index_code == "BEL20" for e in bel20)
    assert len(bel20) >= 20


def test_every_entry_has_a_well_formed_eodhd_symbol() -> None:
    for entry in locked_universe():
        assert "." in entry.eodhd_symbol, entry.eodhd_symbol
        assert entry.symbol  # non-empty
        assert entry.index_code  # non-empty


def test_universe_entries_are_frozen_dataclasses() -> None:
    entry = UniverseEntry(
        symbol="X", eodhd_symbol="X.US", index_code="SP100", sector=None
    )
    try:
        entry.symbol = "Y"  # type: ignore[misc]
    except (AttributeError, TypeError):
        return
    raise AssertionError("UniverseEntry should be frozen")
