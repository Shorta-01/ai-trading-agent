from datetime import datetime

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import PaperLiveMode, PortfolioSummary, PositionSnapshot
from portfolio_outlook_domain.enums import AdviceAction, RiskLevel
from portfolio_outlook_domain.primitives import Money, Quantity


def test_position_snapshot_accepts_data_without_calculation() -> None:
    snapshot = PositionSnapshot(
        portfolio_id="p1",
        instrument_id="i1",
        quantity=Quantity(value="2.5"),
        average_buy_price=Money(amount="100", currency="EUR"),
        current_price=Money(amount="110", currency="EUR"),
        risk_level=RiskLevel.MEDIUM,
        advice_action=AdviceAction.HOLD,
        as_of=datetime.utcnow(),
    )
    assert snapshot.quantity.value == Quantity(value="2.5").value


def test_portfolio_summary_rejects_non_paper_mode() -> None:
    with pytest.raises(ValidationError):
        PortfolioSummary(
            portfolio_id="p1",
            name="Demo",
            base_currency="EUR",
            mode=PaperLiveMode.LIVE_READ_ONLY,
            starting_capital=Money(amount="10000", currency="EUR"),
            created_at=datetime.utcnow(),
        )
