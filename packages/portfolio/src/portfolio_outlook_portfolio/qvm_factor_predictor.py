"""QVM (Quality + Value + Momentum) factor predictor (Slice 16).

Classic three-factor scoring (Fama-French + AQR lineage):

* **Quality** — companies with high return on invested capital (ROIC)
  and high gross margins compound capital efficiently. Z-scored
  cross-sectionally over the universe snapshot.
* **Value** — cheap on P/E + P/B + EV/EBITDA. We invert each ratio
  (low ratio → high score) before averaging.
* **Momentum** — 6-month + 12-month total returns. Same z-score
  approach.

The composite QVM = average of the three normalised scores. A positive
composite means the asset is *cheap, high-quality, and rising* relative
to its universe — the textbook "good buy" combination. A negative
composite means the opposite.

The composite is mapped onto an annualised drift (capped at ±25 %,
same convention as Momentum) and then horizon-scaled. Trailing
6-month volatility from the bars defines the distribution width.

This module is pure Python. The universe snapshot is injected as a
``UniverseFundamentals`` fixture in this slice; Slice 17 wires the
daily scan that populates the universe from EODHD fundamentals.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from .baseline_forecast import DEFAULT_TRADING_DAYS_PER_YEAR
from .predictor_protocol import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    PredictionDistribution,
    PredictorInputs,
)

MODEL_CODE: Final[str] = "qvm_factor_v1"
MODEL_VERSION: Final[str] = "v1.0.0"

# Minimum bar count we still want to ground the distribution width.
QVM_MIN_BARS: Final[int] = 130

# Minimum universe size for a meaningful z-score. Below this we report
# the symbol as ``insufficient_universe`` rather than guess.
QVM_MIN_UNIVERSE_SIZE: Final[int] = 5

# Conservative cap on the projected annualised drift implied by the
# composite score, mirroring the Momentum predictor.
MAX_ANNUAL_DRIFT_PCT: Final[float] = 25.0

# Per-ratio sanity clips before averaging. Wild outliers (negative P/E
# for distressed companies; absurd EV/EBITDA on micro-cap names) would
# blow up the z-score; clipping keeps the signal stable.
PE_CLIP: Final[tuple[float, float]] = (1.0, 80.0)
PB_CLIP: Final[tuple[float, float]] = (0.1, 25.0)
EV_EBITDA_CLIP: Final[tuple[float, float]] = (1.0, 60.0)

BLOCKING_REASON_INSUFFICIENT_UNIVERSE: Final[str] = "insufficient_universe"
BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE: Final[str] = "symbol_not_in_universe"
BLOCKING_REASON_INSUFFICIENT_FACTORS: Final[str] = "insufficient_factors"


@dataclass(frozen=True)
class FundamentalsEntry:
    """One asset's row in the universe snapshot.

    Mirrors the persisted ``AssetFundamentalsSnapshotRecord`` but
    stays a pure-Python value object so the predictor doesn't depend
    on the storage package.
    """

    symbol: str
    sector: str | None
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    ev_ebitda: Decimal | None
    roic_pct: Decimal | None
    gross_margin_pct: Decimal | None
    return_6m_pct: Decimal | None
    return_12m_pct: Decimal | None


@dataclass(frozen=True)
class UniverseFundamentals:
    """A snapshot of fundamentals across the scored universe."""

    entries: tuple[FundamentalsEntry, ...]

    def by_symbol(self) -> dict[str, FundamentalsEntry]:
        return {e.symbol: e for e in self.entries}


_ComponentGetter = Callable[[FundamentalsEntry], list[float] | None]


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _zscore(value: float, values: Sequence[float]) -> float | None:
    """Compute the z-score of ``value`` against the population
    ``values``. Returns ``None`` when the population has fewer than 2
    members (cannot compute SD at all). A zero-spread universe yields a
    z-score of ``0.0`` — the factor genuinely carries no signal across
    the universe, so the target's relative score is neutral."""

    if len(values) < 2:
        return None
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values)
    if sd == 0:
        return 0.0
    return (value - mean) / sd


def _quality_components(entry: FundamentalsEntry) -> list[float] | None:
    """Return the raw quality components for one entry, or ``None`` if
    fewer than one component is available."""

    components: list[float] = []
    roic = _to_float(entry.roic_pct)
    if roic is not None:
        components.append(roic)
    gm = _to_float(entry.gross_margin_pct)
    if gm is not None:
        components.append(gm)
    return components or None


def _value_components(entry: FundamentalsEntry) -> list[float] | None:
    """Return inverted, clipped value components (low ratio → high
    score). ``None`` if no components available."""

    components: list[float] = []
    pe = _to_float(entry.pe_ratio)
    if pe is not None and pe > 0:
        components.append(-_clip(pe, *PE_CLIP))
    pb = _to_float(entry.pb_ratio)
    if pb is not None and pb > 0:
        components.append(-_clip(pb, *PB_CLIP))
    ev = _to_float(entry.ev_ebitda)
    if ev is not None and ev > 0:
        components.append(-_clip(ev, *EV_EBITDA_CLIP))
    return components or None


def _momentum_components(entry: FundamentalsEntry) -> list[float] | None:
    components: list[float] = []
    r6 = _to_float(entry.return_6m_pct)
    if r6 is not None:
        components.append(r6)
    r12 = _to_float(entry.return_12m_pct)
    if r12 is not None:
        components.append(r12)
    return components or None


def _entry_factor_value(
    entry: FundamentalsEntry,
    component_getter: _ComponentGetter,
) -> float | None:
    components = component_getter(entry)
    if components is None:
        return None
    return statistics.fmean(components)


def _factor_score_for_symbol(
    *,
    entries: Sequence[FundamentalsEntry],
    target_symbol: str,
    component_getter: _ComponentGetter,
) -> float | None:
    """Compute one factor's z-score for ``target_symbol`` against the
    universe."""

    universe_values: list[float] = []
    target_value: float | None = None
    for entry in entries:
        value = _entry_factor_value(entry, component_getter)
        if value is None:
            continue
        universe_values.append(value)
        if entry.symbol == target_symbol:
            target_value = value
    if target_value is None:
        return None
    return _zscore(target_value, universe_values)


def _direction_label(expected_return_pct: float) -> str:
    if expected_return_pct >= 10.0:
        return DIRECTION_STRONG_UP
    if expected_return_pct >= 2.0:
        return DIRECTION_SLIGHT_UP
    if expected_return_pct > -2.0:
        return DIRECTION_FLAT
    if expected_return_pct > -10.0:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_STRONG_DOWN


def _decimal(value: float, places: int = 6) -> Decimal:
    quant = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quant)


def _money(value: float) -> Decimal:
    return _decimal(value, 6)


def _prob(value: float) -> Decimal:
    bounded = max(0.0, min(1.0, value))
    return _decimal(bounded, 6)


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _log_returns(prices: Sequence[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        curr = prices[i]
        if prev <= 0 or curr <= 0:
            continue
        out.append(math.log(curr / prev))
    return out


def _blocked(
    *,
    horizon_trading_days: int,
    current_price: Decimal,
    reason: str,
    explanation_nl: str,
) -> PredictionDistribution:
    safe_horizon = horizon_trading_days if horizon_trading_days > 0 else 21
    safe_price = current_price if current_price > 0 else Decimal("0.000001")
    return PredictionDistribution(
        model_code=MODEL_CODE,
        model_version=MODEL_VERSION,
        horizon_trading_days=safe_horizon,
        current_price=safe_price,
        p10_price=safe_price,
        p50_price=safe_price,
        p90_price=safe_price,
        prob_gain=Decimal("0.500000"),
        prob_loss=Decimal("0.500000"),
        expected_return_pct=Decimal("0.000000"),
        direction=DIRECTION_FLAT,
        confidence_score=Decimal("0.000000"),
        status=STATUS_BLOCKED,
        blocking_reason=reason,
        explanation_nl=explanation_nl,
    )


def _confidence_from_factor_count(factor_count: int, universe_size: int) -> float:
    """0.4 at one factor with a tiny universe; up to 0.8 at three
    factors with a large universe."""

    factor_factor = factor_count / 3.0  # 1.0 with all three factors
    universe_factor = min(1.0, universe_size / 50.0)
    return 0.4 + 0.4 * factor_factor * universe_factor


class QvmFactorPredictor:
    """Cross-sectional Quality + Value + Momentum factor predictor."""

    def __init__(
        self,
        *,
        universe: UniverseFundamentals,
        target_symbol: str,
        minimum_bars_required: int = QVM_MIN_BARS,
        max_annual_drift_pct: float = MAX_ANNUAL_DRIFT_PCT,
        trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR,
    ) -> None:
        self._universe = universe
        self._target_symbol = target_symbol
        self._minimum_bars_required = minimum_bars_required
        self._max_annual_drift_pct = max_annual_drift_pct
        self._trading_days_per_year = trading_days_per_year

    @property
    def model_code(self) -> str:
        return MODEL_CODE

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution:
        horizon = inputs.horizon_trading_days
        if horizon <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_HORIZON,
                explanation_nl="Horizon moet positief zijn.",
            )
        if inputs.current_price <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_CURRENT_PRICE,
                explanation_nl="Huidige prijs is niet beschikbaar of <= 0.",
            )
        if len(inputs.historical_bars) < self._minimum_bars_required:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INSUFFICIENT_HISTORY,
                explanation_nl=(
                    f"QVM vereist minstens {self._minimum_bars_required} bars; "
                    f"{len(inputs.historical_bars)} ontvangen."
                ),
            )
        entries = self._universe.entries
        if len(entries) < QVM_MIN_UNIVERSE_SIZE:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INSUFFICIENT_UNIVERSE,
                explanation_nl=(
                    f"QVM-universe heeft minder dan {QVM_MIN_UNIVERSE_SIZE} "
                    f"entries; {len(entries)} ontvangen."
                ),
            )
        if self._target_symbol not in self._universe.by_symbol():
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE,
                explanation_nl=(
                    f"Symbool {self._target_symbol} ontbreekt in de "
                    "geleverde universe-snapshot."
                ),
            )

        quality_z = _factor_score_for_symbol(
            entries=entries,
            target_symbol=self._target_symbol,
            component_getter=_quality_components,
        )
        value_z = _factor_score_for_symbol(
            entries=entries,
            target_symbol=self._target_symbol,
            component_getter=_value_components,
        )
        momentum_z = _factor_score_for_symbol(
            entries=entries,
            target_symbol=self._target_symbol,
            component_getter=_momentum_components,
        )
        factor_scores = [z for z in (quality_z, value_z, momentum_z) if z is not None]
        if not factor_scores:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INSUFFICIENT_FACTORS,
                explanation_nl=(
                    "Geen van de QVM-factoren kon worden berekend voor "
                    f"{self._target_symbol}; check fundamentals-snapshot."
                ),
            )

        composite_z = statistics.fmean(factor_scores)
        # Map z-score onto [-1, +1] using a soft tanh-like clip at ±2.
        composite_clipped = max(-1.0, min(1.0, composite_z / 2.0))

        annual_drift_pct = self._max_annual_drift_pct * composite_clipped
        annual_drift_log = (
            math.log(1.0 + annual_drift_pct / 100.0)
            if annual_drift_pct > -100.0
            else -1.0
        )
        horizon_drift_log = annual_drift_log * (horizon / self._trading_days_per_year)

        prices = [float(bar.close_price) for bar in inputs.historical_bars]
        recent_returns = _log_returns(prices[-min(126, len(prices)) :])
        sd_recent = (
            statistics.pstdev(recent_returns) if len(recent_returns) >= 2 else 0.0
        )
        if sd_recent <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_FLAT_HISTORY,
                explanation_nl=(
                    "Recente prijsreeks heeft geen volatiliteit; QVM kan "
                    "geen distributie afleiden."
                ),
            )
        horizon_sd_log = sd_recent * math.sqrt(horizon)
        current = float(inputs.current_price)
        p10_log = horizon_drift_log + horizon_sd_log * (-1.2815515655446004)
        p50_log = horizon_drift_log
        p90_log = horizon_drift_log + horizon_sd_log * 1.2815515655446004
        p10 = current * math.exp(p10_log)
        p50 = current * math.exp(p50_log)
        p90 = current * math.exp(p90_log)

        z_for_zero = -horizon_drift_log / horizon_sd_log if horizon_sd_log > 0 else 0.0
        prob_gain = 1.0 - _normal_cdf(z_for_zero)
        prob_loss = 1.0 - prob_gain
        expected_return_pct = (math.exp(p50_log) - 1.0) * 100.0

        confidence = _confidence_from_factor_count(len(factor_scores), len(entries))

        q_text = f"Q={quality_z:.2f}" if quality_z is not None else "Q=n/b"
        v_text = f"V={value_z:.2f}" if value_z is not None else "V=n/b"
        m_text = f"M={momentum_z:.2f}" if momentum_z is not None else "M=n/b"
        explanation = (
            f"QVM-factor: {q_text}, {v_text}, {m_text}; composite={composite_z:.2f} "
            f"(clipped {composite_clipped:.2f}) → verwachte rendement over "
            f"{horizon} dagen = {expected_return_pct:.2f}%. "
            f"Universe-size: {len(entries)}."
        )

        return PredictionDistribution(
            model_code=MODEL_CODE,
            model_version=MODEL_VERSION,
            horizon_trading_days=horizon,
            current_price=inputs.current_price,
            p10_price=_money(p10),
            p50_price=_money(p50),
            p90_price=_money(p90),
            prob_gain=_prob(prob_gain),
            prob_loss=_prob(prob_loss),
            expected_return_pct=_decimal(expected_return_pct, 6),
            direction=_direction_label(expected_return_pct),
            confidence_score=_decimal(confidence, 6),
            status=STATUS_READY,
            blocking_reason=None,
            explanation_nl=explanation,
        )


__all__ = [
    "MODEL_CODE",
    "MODEL_VERSION",
    "QVM_MIN_BARS",
    "QVM_MIN_UNIVERSE_SIZE",
    "MAX_ANNUAL_DRIFT_PCT",
    "BLOCKING_REASON_INSUFFICIENT_UNIVERSE",
    "BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE",
    "BLOCKING_REASON_INSUFFICIENT_FACTORS",
    "FundamentalsEntry",
    "UniverseFundamentals",
    "QvmFactorPredictor",
]
