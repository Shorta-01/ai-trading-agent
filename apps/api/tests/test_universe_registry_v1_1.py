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


def test_default_set_is_sp500() -> None:
    """V1.2 §BS / GAPS.md P1-4: SP500 is de default zodat de
    orchestrator-scan op een breed US large-cap universum draait
    (~325 namen) i.p.v. de eerdere STARTER_50 (45 namen alleen
    Bel20+AEX). CLAUDE.md §5 vraagt namelijk ~3500 namen voor de
    autonome scan; SP500 is een pragmatische tussenstop. Operator
    kan handmatig STARTER_50 / EU600 / ALL_5K kiezen."""

    from portfolio_outlook_api.universe_registry import UNIVERSE_SET_SP500

    assert DEFAULT_UNIVERSE_SET == UNIVERSE_SET_SP500


def test_locked_universe_default_returns_sp500_set() -> None:
    from portfolio_outlook_api.universe_registry import UNIVERSE_SET_SP500

    by_default = locked_universe()
    by_explicit = locked_universe(UNIVERSE_SET_SP500)
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


# ---- Multi-select index-code composition --------------------------------


def test_locked_index_codes_lists_all_thirteen_markets() -> None:
    """The operator-pickable index-code set must enumerate every index
    the registry actually carries — otherwise the UI multi-select would
    hide markets that the underlying ``compose_universe_from_index_codes``
    can already build."""

    from portfolio_outlook_api.universe_registry import (
        LOCKED_INDEX_CODES,
        UNIVERSE_SET_ALL_5K,
        locked_universe,
    )

    indices_in_data = {e.index_code for e in locked_universe(UNIVERSE_SET_ALL_5K)}
    assert indices_in_data == LOCKED_INDEX_CODES


def test_compose_universe_from_index_codes_single_market() -> None:
    from portfolio_outlook_api.universe_registry import (
        compose_universe_from_index_codes,
    )

    bel20 = compose_universe_from_index_codes(("BEL20",))
    assert len(bel20) == 20
    assert all(e.index_code == "BEL20" for e in bel20)


def test_compose_universe_from_index_codes_multiple_markets_deduped() -> None:
    """Picking BEL20 + AEX should produce the union (20 + 25 = 45)."""

    from portfolio_outlook_api.universe_registry import (
        compose_universe_from_index_codes,
    )

    union = compose_universe_from_index_codes(("BEL20", "AEX"))
    assert len(union) == 45
    seen_codes = {e.index_code for e in union}
    assert seen_codes == {"BEL20", "AEX"}


def test_compose_universe_from_index_codes_returns_empty_for_empty_input() -> None:
    from portfolio_outlook_api.universe_registry import (
        compose_universe_from_index_codes,
    )

    assert compose_universe_from_index_codes(()) == ()


def test_parse_index_codes_accepts_comma_list_strips_whitespace() -> None:
    from portfolio_outlook_api.universe_registry import parse_index_codes

    assert parse_index_codes("BEL20, AEX ,CAC40") == ("BEL20", "AEX", "CAC40")


def test_parse_index_codes_deduplicates() -> None:
    from portfolio_outlook_api.universe_registry import parse_index_codes

    assert parse_index_codes("BEL20,AEX,BEL20") == ("BEL20", "AEX")


def test_parse_index_codes_rejects_unknown_code() -> None:
    from portfolio_outlook_api.universe_registry import parse_index_codes

    with pytest.raises(ValueError, match="NOTACODE"):
        parse_index_codes("BEL20,NOTACODE")
