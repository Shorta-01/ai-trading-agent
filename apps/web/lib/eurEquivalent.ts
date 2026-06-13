/**
 * V1.2 §AV / CLAUDE.md §6.1 — EUR-equivalent transparency.
 *
 * Deterministic calculators for the +4% profit-harvest doctrine.
 * The orchestrator already sizes BUYs to hit roughly €N notional;
 * these helpers translate that into:
 *
 *   - +4% gross EUR vs +4% net EUR (na 0,70% TOB round-trip)
 *   - FX sensitivity for non-EUR positions (what happens if the
 *     EUR-pair drifts ±5% before exit)
 *
 * Pure functions, no I/O. The web components import them; tests
 * hit them directly for precise number-checks.
 */

// Belgian TOB on standard stocks: 0.35% per leg, 2 legs per round-
// trip. Accumulating ETFs would be higher (1.32%) but the doctrine
// universe is stocks-only by default (CLAUDE.md §4).
export const TOB_ROUND_TRIP_PCT = 0.7;
export const TARGET_GROSS_PCT = 4.0;

export type EurEquivalent = {
  gross_eur: number;
  tob_eur: number;
  net_eur: number;
};

export type FxSensitivityRow = {
  scenario_nl: string;
  fx_rate: number;
  net_eur: number;
};

/**
 * Compute the EUR-equivalent of a +4% gross gain on a notional_eur
 * position, with the Belgian TOB round-trip subtracted.
 *
 * Inputs are strings because that's how the API ships money (full
 * precision via Decimal). We parse defensively — invalid strings
 * return zeroes so the UI just shows €0,00 instead of crashing.
 */
export function computeEurEquivalent(
  notional_eur: string,
  targetGrossPct: number = TARGET_GROSS_PCT,
  tobPct: number = TOB_ROUND_TRIP_PCT,
): EurEquivalent {
  const notional = Number(notional_eur);
  if (!Number.isFinite(notional) || notional <= 0) {
    return { gross_eur: 0, tob_eur: 0, net_eur: 0 };
  }
  const gross = notional * (targetGrossPct / 100);
  const tob = notional * (tobPct / 100);
  const net = gross - tob;
  return { gross_eur: gross, tob_eur: tob, net_eur: net };
}

/**
 * Compute FX sensitivity scenarios for a non-EUR position.
 *
 * Returns three scenarios (current, -5% EUR pair, +5% EUR pair) so
 * the operator sees what happens if the FX rate drifts before exit.
 * Always uses the spot rate at draft creation as the baseline.
 *
 * For EUR positions (or when fx_rate is missing / 1) returns an
 * empty array — the caller can then skip the FX block entirely.
 */
export function computeFxSensitivity(
  notional_eur: string,
  fx_rate_at_creation: string,
  currency_local: string,
  targetGrossPct: number = TARGET_GROSS_PCT,
  tobPct: number = TOB_ROUND_TRIP_PCT,
): FxSensitivityRow[] {
  if (currency_local === "EUR") return [];
  const baseRate = Number(fx_rate_at_creation);
  const notional = Number(notional_eur);
  if (
    !Number.isFinite(baseRate) ||
    !Number.isFinite(notional) ||
    baseRate <= 0 ||
    notional <= 0 ||
    baseRate === 1
  ) {
    return [];
  }
  // Local-currency gain stays constant; the EUR-conversion shifts.
  // gross_local = notional_local * 4%   =  (notional_eur * baseRate) * 4%
  // net_eur(scenario) = gross_local / scenarioRate - TOB
  const grossLocal = notional * baseRate * (targetGrossPct / 100);
  const tobEur = notional * (tobPct / 100);
  const scenarios: Array<{ delta: number; label_nl: string }> = [
    { delta: 0, label_nl: "Huidige koers" },
    { delta: -0.05, label_nl: "EUR-pair −5% (sterkere EUR)" },
    { delta: 0.05, label_nl: "EUR-pair +5% (zwakkere EUR)" },
  ];
  return scenarios.map(({ delta, label_nl }) => {
    const scenarioRate = baseRate * (1 + delta);
    const grossEur = grossLocal / scenarioRate;
    return {
      scenario_nl: `${label_nl} (EUR/${currency_local} = ${formatRate(scenarioRate)})`,
      fx_rate: scenarioRate,
      net_eur: grossEur - tobEur,
    };
  });
}

export function formatEur(value: number): string {
  return value.toLocaleString("nl-BE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  });
}

export function formatEurDetail(value: number): string {
  return value.toLocaleString("nl-BE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  });
}

function formatRate(value: number): string {
  return value.toLocaleString("nl-BE", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  });
}
