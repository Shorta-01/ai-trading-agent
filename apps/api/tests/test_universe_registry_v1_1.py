"""Tests for the V1.1 Slice 31 universe-set expansion."""

from __future__ import annotations

import pytest

from portfolio_outlook_api.universe_registry import (
    ALL_5K_EXTRA,
    DEFAULT_UNIVERSE_SET,
    EU600_EXTRA,
    LOCKED_UNIVERSE_SETS,
    UNIVERSE_SET_ALL_5K,
    UNIVERSE_SET_EU600,
    UNIVERSE_SET_SP500,
    UNIVERSE_SET_STARTER_50,
    UniverseEntry,
    locked_universe,
    universe_by_index,
)


def test_locked_universe_sets_are_immutable_frozenset() -> None:
    assert isinstance(LOCKED_UNIVERSE_SETS, frozenset)
    assert LOCKED_UNIVERSE_SETS == {
        UNIVERSE_SET_STARTER_50,
        UNIVERSE_SET_SP500,
        UNIVERSE_SET_EU600,
        UNIVERSE_SET_ALL_5K,
    }


def test_default_set_is_starter_50() -> None:
    """STARTER_50 (Bel20 + AEX) is the new default — large/liquid Belgian
    + Dutch names so the operator gets real ``Nieuwe kansen`` output
    inside the EODHD quota before deciding to opt into the larger sets."""

    assert DEFAULT_UNIVERSE_SET == UNIVERSE_SET_STARTER_50


def test_locked_universe_default_returns_starter_50_set() -> None:
    by_default = locked_universe()
    by_explicit = locked_universe(UNIVERSE_SET_STARTER_50)
    assert by_default == by_explicit


def test_starter_50_is_bel20_plus_aex() -> None:
    """The starter set is the union of Bel20 (20) + AEX (~25) — a
    deliberately-tight set the operator can lean on without large
    EODHD-quota concerns. The actual count depends on whether AEX
    happens to overlap any Bel20 symbol but in practice it doesn't."""

    starter = locked_universe(UNIVERSE_SET_STARTER_50)
    symbols = {e.eodhd_symbol for e in starter}
    assert "ABI.BR" in symbols  # Bel20
    assert "ASML.AS" in symbols  # AEX
    assert 30 <= len(starter) <= 50  # small set by design


def test_locked_universe_rejects_unknown_set_code() -> None:
    with pytest.raises(ValueError, match="universe_set"):
        locked_universe("BOGUS")


def test_eu600_set_includes_uk_swiss_iberia_italy_nordic_additions() -> None:
    entries = locked_universe(UNIVERSE_SET_EU600)
    eodhd_symbols = {e.eodhd_symbol for e in entries}
    # UK FTSE 100
    assert "AZN.LSE" in eodhd_symbols
    assert "HSBA.LSE" in eodhd_symbols
    # Swiss SLI
    assert "NESN.SW" in eodhd_symbols
    assert "ROG.SW" in eodhd_symbols
    # IBEX 35
    assert "ITX.MC" in eodhd_symbols
    # FTSE MIB
    assert "ENI.MI" in eodhd_symbols
    # Stoxx Nordic 30
    assert "NOVO-B.CO" in eodhd_symbols
    assert "EQNR.OL" in eodhd_symbols


def test_eu600_set_strictly_supersets_sp500() -> None:
    sp500 = {e.eodhd_symbol for e in locked_universe(UNIVERSE_SET_SP500)}
    eu600 = {e.eodhd_symbol for e in locked_universe(UNIVERSE_SET_EU600)}
    assert sp500 < eu600
    # EU600_EXTRA is what's added on top.
    assert {e.eodhd_symbol for e in EU600_EXTRA} - sp500 == eu600 - sp500


def test_all_5k_set_strictly_supersets_eu600() -> None:
    eu600 = {e.eodhd_symbol for e in locked_universe(UNIVERSE_SET_EU600)}
    all_5k = {e.eodhd_symbol for e in locked_universe(UNIVERSE_SET_ALL_5K)}
    assert eu600 < all_5k
    # ALL_5K_EXTRA is what's added on top.
    assert {e.eodhd_symbol for e in ALL_5K_EXTRA} - eu600 == all_5k - eu600


def test_locked_universe_deduplicates_by_eodhd_symbol() -> None:
    entries = locked_universe(UNIVERSE_SET_ALL_5K)
    seen = {e.eodhd_symbol for e in entries}
    # Every entry appears exactly once.
    assert len(seen) == len(entries)


def test_universe_entry_country_code_field_present() -> None:
    # New V1.1 §22.4 field — should be on every dataclass instance.
    sample = EU600_EXTRA[0]
    assert isinstance(sample, UniverseEntry)
    assert hasattr(sample, "country_code")
    assert sample.country_code is not None


def test_universe_by_index_respects_set_code() -> None:
    # FTSE100 is part of EU600 + ALL_5K but not SP500.
    assert universe_by_index("FTSE100", set_code=UNIVERSE_SET_SP500) == ()
    eu_ftse = universe_by_index("FTSE100", set_code=UNIVERSE_SET_EU600)
    assert len(eu_ftse) > 0
    assert all(e.index_code == "FTSE100" for e in eu_ftse)


def test_universe_by_index_default_set_returns_sp500_filtered() -> None:
    # BEL20 is in the V1 SP500 set.
    entries = universe_by_index("BEL20")
    assert len(entries) > 0
    assert all(e.index_code == "BEL20" for e in entries)
