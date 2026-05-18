import pytest
from pydantic import BaseModel, ValidationError

from portfolio_outlook_domain.identifiers import PortfolioId


class _IdModel(BaseModel):
    value: PortfolioId


def test_identifier_accepts_safe_characters() -> None:
    model = _IdModel(value="portfolio_1-abc")
    assert model.value == "portfolio_1-abc"


@pytest.mark.parametrize("value", ["", "portfolio id", "abc/def", "https://x", "abc\\def"])
def test_identifier_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(ValidationError):
        _IdModel(value=value)
