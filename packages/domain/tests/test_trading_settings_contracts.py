from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    AllowedAssetType,
    AllowedUniverseSettings,
    AssetPermissionStatus,
    BlockedAssetType,
    UserStrategySettings,
    evaluate_asset_permission,
    get_allowed_universe_help_texts,
    get_user_strategy_help_texts,
)


def test_default_allowed_universe_allows_etfs() -> None:
    permission = evaluate_asset_permission(AllowedAssetType.ETF, AllowedUniverseSettings())
    assert permission.allowed is True
    assert permission.status is AssetPermissionStatus.ALLOWED


def test_default_allowed_universe_allows_stocks() -> None:
    permission = evaluate_asset_permission(AllowedAssetType.STOCK, AllowedUniverseSettings())
    assert permission.allowed is True


def test_version1_blocked_asset_types_always_blocked() -> None:
    settings = AllowedUniverseSettings()
    for blocked in BlockedAssetType:
        permission = evaluate_asset_permission(blocked, settings)
        assert permission.allowed is False
        assert permission.status is AssetPermissionStatus.BLOCKED


def test_disabled_etfs_not_allowed() -> None:
    settings = AllowedUniverseSettings(allow_etfs=False)
    permission = evaluate_asset_permission(AllowedAssetType.ETF, settings)
    assert permission.allowed is False


def test_disabled_stocks_not_allowed() -> None:
    settings = AllowedUniverseSettings(allow_stocks=False)
    permission = evaluate_asset_permission(AllowedAssetType.STOCK, settings)
    assert permission.allowed is False


def test_currencies_watch_only_not_buy_ready() -> None:
    settings = AllowedUniverseSettings(allow_currencies_watch_only=True)
    permission = evaluate_asset_permission(AllowedAssetType.CURRENCY, settings)
    assert permission.allowed is False
    assert permission.status is AssetPermissionStatus.WATCH_ONLY


def test_unknown_unsupported_asset_type_is_blocked() -> None:
    permission = evaluate_asset_permission("unknown_asset", AllowedUniverseSettings())
    assert permission.allowed is False
    assert permission.status is AssetPermissionStatus.BLOCKED


def test_default_strategy_percentages_are_decimal() -> None:
    settings = UserStrategySettings()
    assert isinstance(settings.max_position_pct, Decimal)
    assert isinstance(settings.min_cash_reserve_pct, Decimal)


def test_strategy_percentages_reject_float() -> None:
    with pytest.raises(ValidationError):
        UserStrategySettings(max_position_pct=10.5)


def test_strategy_negative_percentage_rejected() -> None:
    with pytest.raises(ValidationError):
        UserStrategySettings(min_cash_reserve_pct=Decimal("-1"))


def test_strategy_over_100_percentage_rejected() -> None:
    with pytest.raises(ValidationError):
        UserStrategySettings(max_position_pct=Decimal("101"))


def test_preferred_and_avoided_sectors_can_be_stored() -> None:
    settings = UserStrategySettings(
        preferred_sectors=("technology",),
        avoided_sectors=("energy",),
    )
    assert len(settings.preferred_sectors) == 1
    assert len(settings.avoided_sectors) == 1


def test_all_settings_have_dutch_help_texts_non_empty() -> None:
    all_help_texts = get_allowed_universe_help_texts() + get_user_strategy_help_texts()
    assert all_help_texts
    for item in all_help_texts:
        assert item.label_nl.strip()
        assert item.help_nl.strip()


def test_default_settings_keep_version1_blocked_assets_blocked() -> None:
    settings = AllowedUniverseSettings()
    blocked_values = {item.value for item in settings.blocked_asset_types}
    assert blocked_values == {
        "options",
        "futures",
        "leverage",
        "short_selling",
        "crypto",
        "penny_stocks",
        "cfds",
        "complex_derivatives",
    }


def test_contracts_do_not_generate_buy_sell_recommendations() -> None:
    model_fields = set(UserStrategySettings.model_fields.keys())
    assert "recommendation" not in model_fields
    assert "buy_action" not in model_fields
    assert "sell_action" not in model_fields
