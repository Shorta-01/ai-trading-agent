import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    AssetType,
    ETFDetails,
    Instrument,
    InstrumentStatus,
    Money,
    Percentage,
)


def test_instrument_requires_required_fields() -> None:
    with pytest.raises(ValidationError):
        Instrument(
            instrument_id="inst1",
            name="",
            currency="EUR",
            asset_type=AssetType.STOCK,
            status=InstrumentStatus.ACTIVE,
        )


def test_etf_details_optional_fields() -> None:
    details = ETFDetails(
        accumulating=True,
        fund_size=Money(amount="1000000", currency="EUR"),
        ter=Percentage(value="0.12"),
    )
    assert details.accumulating is True
    assert details.ter is not None
