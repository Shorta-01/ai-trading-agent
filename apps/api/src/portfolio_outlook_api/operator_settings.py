"""Operator-instellingen → orchestrator scoring inputs (V1.2 §BD).

CLAUDE.md belofte: de UI laat de operator alle doctrine-knoppen
zetten op ``/instellingen``. Tot deze module er was las de
``orchestrator_scoring_leg`` echter ``_DEFAULT_TRADING_SETTINGS``
hardgecodeerd in plaats van wat de operator opslaat in
``trading_settings.user_strategy_json``. Hierdoor draaide de live
beslissing op een ándere drempel dan wat de operator op de UI zag.

Deze module sluit die loop:

* :func:`load_operator_trading_settings` leest de actieve
  ``UserStrategySettings`` uit storage en mapt ze op de
  ``TradingSettingsSnapshot`` shape die de orchestrator consumeert.
* Bij ontbrekende rij of leesfout valt het naadloos terug op de
  doctrine-defaults (CLAUDE.md §3 sizing, §6.1 target, §7.1
  confidence) zodat een verse install gewoon werkt.
* Het optionele ``profit_target_net_pct`` overlay uit §AZ
  (``runtime_config``) wordt apart toegepast — operator kan dus de
  knop "winstdoel" los van het volledige strategy-blob bijstellen.

Pure storage-IO; geen netwerk, geen LLM. Doctrine-locks blijven
intact: deze module zet geen ``safe_for_*`` flags en doet geen
gokwerk wanneer storage stilstaat.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyTradingSettingsRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from portfolio_outlook_worker.forecasting.orchestrator_candidate_provider import (
    TradingSettingsSnapshot,
)

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.profit_target import (
    DOCTRINE_DEFAULT_PCT,
    get_profit_target_pct,
)

logger = logging.getLogger(__name__)


# Doctrine defaults (CLAUDE.md §3, §6.1, §7.1, §7.2, §7.3). Deze
# blijven de fallback wanneer de operator nog niets heeft opgeslagen.
#
# Audit-correctie 2026-06-16:
#   * ``min_position_eur`` van €25.000 → €5.000 conform §3
#     ("Minimum €5.000 per positie — TOB-efficient").
#   * ``max_sector_pct`` blijft schema-wise bestaan voor backwards
#     compat met persisted records + bestaande UI-velden, maar
#     krijgt nu de doctrine-correcte default ``100`` (= geen cap)
#     per §7.3 ("Geen harde cap — sector-verdeling wordt INFO").
DOCTRINE_DEFAULTS = TradingSettingsSnapshot(
    target_net_pct=DOCTRINE_DEFAULT_PCT,
    confidence_threshold_pct=Decimal("70"),
    min_position_eur=Decimal("5000"),
    max_position_eur=Decimal("100000"),
    total_budget_eur=Decimal("1000000"),
    min_market_cap_eur=Decimal("5000000000"),
    max_annual_volatility_pct=Decimal("30"),
    max_sector_pct=Decimal("100"),
    fat_tail_factor=Decimal("1.15"),
    earnings_block_days=5,
    news_buy_bias_max_boost_pct=Decimal("5"),
)


@dataclass(frozen=True)
class OperatorSettingsResolution:
    """Resultaat van één strategy-lookup.

    Naast de snapshot dragen we een korte audit-string met de bron
    (``operator`` / ``doctrine-default`` / ``storage-unavailable``)
    zodat de scoring-leg dit kan loggen in zijn detail-text — de
    operator kan dan op de Audit-pagina zien of zijn /instellingen-
    edit ook echt doorgewerkt heeft.
    """

    snapshot: TradingSettingsSnapshot
    source: str
    profit_target_overridden: bool


def _coerce_decimal(value: Any, default: Decimal) -> Decimal:
    """Best-effort parse. JSON-blobs in storage roundtrippen Decimal
    typisch als string; ints en floats komen ook voor afhankelijk van
    de provider. We vallen netjes terug op ``default`` zodat één rotte
    waarde nooit de hele snapshot kantelt."""

    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _snapshot_from_strategy_blob(blob: dict[str, Any]) -> TradingSettingsSnapshot:
    """Map de JSON-blob van ``user_strategy_json`` op de orchestrator-
    snapshot. Onbekende velden negeren we; ontbrekende velden vallen
    terug op de doctrine-default. Dit maakt forward-compat: nieuwe
    operator-velden breken de orchestrator niet en omgekeerd kan de
    UI een nieuw veld toevoegen zonder dat de orchestrator crasht.
    """

    return TradingSettingsSnapshot(
        target_net_pct=_coerce_decimal(
            blob.get("trading_target_net_pct"),
            DOCTRINE_DEFAULTS.target_net_pct,
        ),
        confidence_threshold_pct=_coerce_decimal(
            blob.get("trading_confidence_threshold_pct"),
            DOCTRINE_DEFAULTS.confidence_threshold_pct,
        ),
        min_position_eur=_coerce_decimal(
            blob.get("trading_min_position_eur"),
            DOCTRINE_DEFAULTS.min_position_eur,
        ),
        max_position_eur=_coerce_decimal(
            blob.get("trading_max_position_eur"),
            DOCTRINE_DEFAULTS.max_position_eur,
        ),
        total_budget_eur=_coerce_decimal(
            blob.get("trading_total_budget_eur"),
            DOCTRINE_DEFAULTS.total_budget_eur,
        ),
        min_market_cap_eur=_coerce_decimal(
            blob.get("trading_min_market_cap_eur"),
            DOCTRINE_DEFAULTS.min_market_cap_eur,
        ),
        max_annual_volatility_pct=_coerce_decimal(
            blob.get("trading_max_annual_volatility_pct"),
            DOCTRINE_DEFAULTS.max_annual_volatility_pct,
        ),
        max_sector_pct=_coerce_decimal(
            blob.get("trading_max_sector_pct"),
            DOCTRINE_DEFAULTS.max_sector_pct,
        ),
        fat_tail_factor=_coerce_decimal(
            blob.get("trading_fat_tail_factor"),
            DOCTRINE_DEFAULTS.fat_tail_factor,
        ),
        earnings_block_days=_coerce_int(
            blob.get("trading_earnings_block_days"),
            DOCTRINE_DEFAULTS.earnings_block_days,
        ),
        news_buy_bias_max_boost_pct=_coerce_decimal(
            blob.get("trading_news_buy_bias_max_boost_pct"),
            DOCTRINE_DEFAULTS.news_buy_bias_max_boost_pct,
        ),
    )


def _apply_profit_target_override(
    snapshot: TradingSettingsSnapshot,
) -> tuple[TradingSettingsSnapshot, bool]:
    """De §AZ ``profit_target_net_pct`` runtime_config overlay heeft
    voorrang op het strategy-blob — operator kan dus de winstdoel-
    drempel snel bijstellen zonder zijn hele strategie te bewerken.
    Wanneer geen overlay is ingesteld (``DOCTRINE_DEFAULT_PCT``)
    blijft de waarde uit de strategy staan."""

    override = get_profit_target_pct()
    if override == DOCTRINE_DEFAULT_PCT:
        return snapshot, False
    if override == snapshot.target_net_pct:
        return snapshot, False
    return (
        TradingSettingsSnapshot(
            target_net_pct=override,
            confidence_threshold_pct=snapshot.confidence_threshold_pct,
            min_position_eur=snapshot.min_position_eur,
            max_position_eur=snapshot.max_position_eur,
            total_budget_eur=snapshot.total_budget_eur,
            min_market_cap_eur=snapshot.min_market_cap_eur,
            max_annual_volatility_pct=snapshot.max_annual_volatility_pct,
            max_sector_pct=snapshot.max_sector_pct,
            fat_tail_factor=snapshot.fat_tail_factor,
            earnings_block_days=snapshot.earnings_block_days,
            news_buy_bias_max_boost_pct=snapshot.news_buy_bias_max_boost_pct,
        ),
        True,
    )


def load_operator_trading_settings() -> OperatorSettingsResolution:
    """Lees de operator-strategie + winstdoel-overlay en bouw de
    snapshot die de orchestrator-scoring-leg consumeert.

    Bij elke fout (geen storage, geen rij, kapotte JSON) valt het
    netjes terug op de doctrine-defaults — de live beslissing draait
    dan op de gepubliceerde CLAUDE.md-waarden. ``source`` documenteert
    welke tak gepakt is voor de audit-trail.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        snapshot, overridden = _apply_profit_target_override(DOCTRINE_DEFAULTS)
        return OperatorSettingsResolution(
            snapshot=snapshot,
            source="storage-unavailable",
            profit_target_overridden=overridden,
        )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyTradingSettingsRepository(
                checked.connection, checked.readiness
            )
            result = repo.get_settings("default")
    except StorageConnectionError as exc:
        logger.warning("operator-settings lookup error: %s", exc)
        snapshot, overridden = _apply_profit_target_override(DOCTRINE_DEFAULTS)
        return OperatorSettingsResolution(
            snapshot=snapshot,
            source="storage-error",
            profit_target_overridden=overridden,
        )

    if not result.found or result.record is None:
        snapshot, overridden = _apply_profit_target_override(DOCTRINE_DEFAULTS)
        return OperatorSettingsResolution(
            snapshot=snapshot,
            source="doctrine-default",
            profit_target_overridden=overridden,
        )
    blob = result.record.user_strategy or {}
    snapshot = _snapshot_from_strategy_blob(blob)
    snapshot, overridden = _apply_profit_target_override(snapshot)
    return OperatorSettingsResolution(
        snapshot=snapshot,
        source="operator",
        profit_target_overridden=overridden,
    )


__all__ = [
    "DOCTRINE_DEFAULTS",
    "OperatorSettingsResolution",
    "load_operator_trading_settings",
]
