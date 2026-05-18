from datetime import datetime

from portfolio_outlook_domain import PositionSnapshot
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
