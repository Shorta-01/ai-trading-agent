from datetime import datetime, timezone
from decimal import Decimal
import pytest
from portfolio_outlook_domain import *


def test_ibkr_models():
    i=IBKRInstrumentReference(broker_reference_id='b1', instrument_id='i1', symbol='VWCE', sec_type=IBKRSecurityType.ETF, currency='EUR', multiplier=Decimal('1'), min_tick=Decimal('0.01'), market_data_permission_status=IBKRMarketDataPermissionStatus.UNKNOWN, trading_permission_status=IBKRTradingPermissionStatus.PAPER_ONLY)
    assert i.model_dump()['symbol']=='VWCE'
    with pytest.raises(ValueError): i.model_copy(update={'symbol':'   '})
    with pytest.raises(ValueError): i.model_copy(update={'multiplier':Decimal('-1')})
    IBKROrderReference(broker_order_reference_id='bo1', order_id=None, broker_provider=BrokerProvider.INTERACTIVE_BROKERS, account_mode=BrokerAccountMode.IBKR_PAPER, transmission_status=IBKROrderTransmissionStatus.NOT_SUBMITTED)
    IBKRDataPermissionSnapshot(broker_reference_id='b1', instrument_id='i1', market_data_permission_status=IBKRMarketDataPermissionStatus.UNKNOWN, trading_permission_status=IBKRTradingPermissionStatus.UNKNOWN, checked_at=datetime.now(timezone.utc), explanation_nl='ok')
