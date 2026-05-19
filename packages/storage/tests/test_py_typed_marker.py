from importlib import resources


def test_py_typed_marker_exists() -> None:
    marker = resources.files("ai_trading_agent_storage").joinpath("py.typed")
    assert marker.is_file()
