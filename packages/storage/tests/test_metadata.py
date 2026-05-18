from ai_trading_agent_storage.metadata import metadata


def test_metadata_imports_and_has_no_tables() -> None:
    assert metadata is not None
    assert len(metadata.tables) == 0
