import { describe, expect, it } from "vitest";

import {
  computeEurEquivalent,
  computeFxSensitivity,
  formatEur,
  formatEurDetail,
  TARGET_GROSS_PCT,
  TOB_ROUND_TRIP_PCT,
} from "./eurEquivalent";

describe("computeEurEquivalent", () => {
  it("computes +4% gross and net-after-TOB on a €15.000 notional", () => {
    const result = computeEurEquivalent("15000");
    expect(result.gross_eur).toBeCloseTo(600, 4);
    expect(result.tob_eur).toBeCloseTo(105, 4);
    expect(result.net_eur).toBeCloseTo(495, 4);
  });

  it("scales linearly with notional", () => {
    const small = computeEurEquivalent("5000");
    const big = computeEurEquivalent("50000");
    expect(big.net_eur / small.net_eur).toBeCloseTo(10, 4);
  });

  it("returns zero when the notional is non-numeric", () => {
    const result = computeEurEquivalent("oeps");
    expect(result).toEqual({ gross_eur: 0, tob_eur: 0, net_eur: 0 });
  });

  it("returns zero when the notional is non-positive", () => {
    const result = computeEurEquivalent("0");
    expect(result).toEqual({ gross_eur: 0, tob_eur: 0, net_eur: 0 });
  });

  it("respects custom target + TOB percentages", () => {
    const result = computeEurEquivalent("10000", 5, 1.32);
    // gross = 500, tob = 132, net = 368
    expect(result.gross_eur).toBeCloseTo(500, 4);
    expect(result.tob_eur).toBeCloseTo(132, 4);
    expect(result.net_eur).toBeCloseTo(368, 4);
  });

  it("uses the doctrine constants by default", () => {
    expect(TARGET_GROSS_PCT).toBe(4);
    expect(TOB_ROUND_TRIP_PCT).toBe(0.7);
  });
});

describe("computeFxSensitivity", () => {
  it("returns an empty list for EUR positions", () => {
    expect(computeFxSensitivity("10000", "1", "EUR")).toEqual([]);
  });

  it("returns an empty list when fx_rate is 1 (no conversion)", () => {
    expect(computeFxSensitivity("10000", "1", "USD")).toEqual([]);
  });

  it("returns three scenarios for a non-EUR position", () => {
    const rows = computeFxSensitivity("10000", "0.92", "USD");
    expect(rows).toHaveLength(3);
    expect(rows[0].scenario_nl).toContain("Huidige koers");
    expect(rows[1].scenario_nl).toContain("sterkere EUR");
    expect(rows[2].scenario_nl).toContain("zwakkere EUR");
  });

  it("matches the doctrine math at the current fx rate", () => {
    // notional_eur = €10.000 at EUR/USD = 0.92.
    // gross_local = 10000 * 0.92 * 4% = $368.
    // net_eur at current rate = $368 / 0.92 - €70 (TOB) = €400 - €70 = €330.
    const rows = computeFxSensitivity("10000", "0.92", "USD");
    expect(rows[0].fx_rate).toBeCloseTo(0.92, 4);
    expect(rows[0].net_eur).toBeCloseTo(330, 2);
  });

  it("shows EUR weakening reduces the EUR-converted gain", () => {
    const rows = computeFxSensitivity("10000", "0.92", "USD");
    // EUR -5% strengthening → rate down to 0.874 → MORE EUR for the same USD
    // gain → net_eur should be higher than the baseline.
    expect(rows[1].net_eur).toBeGreaterThan(rows[0].net_eur);
    // EUR +5% weakening → rate up to 0.966 → fewer EUR → net_eur lower.
    expect(rows[2].net_eur).toBeLessThan(rows[0].net_eur);
  });

  it("returns an empty list when notional or fx_rate is invalid", () => {
    expect(computeFxSensitivity("nope", "0.92", "USD")).toEqual([]);
    expect(computeFxSensitivity("10000", "nope", "USD")).toEqual([]);
    expect(computeFxSensitivity("10000", "0", "USD")).toEqual([]);
  });
});

describe("formatEur", () => {
  it("formats a whole euro amount in Belgian-Dutch locale", () => {
    expect(formatEur(1234)).toMatch(/€/);
    expect(formatEur(1234)).toMatch(/1\.234/);
  });

  it("rounds to whole euros", () => {
    expect(formatEur(1234.56)).not.toMatch(/56/);
  });
});

describe("formatEurDetail", () => {
  it("keeps two decimals", () => {
    expect(formatEurDetail(1234.5)).toMatch(/1\.234,50/);
  });
});
