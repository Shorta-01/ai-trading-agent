import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DecisionPackageResponse } from "@/lib/apiClient";

// Task 133: the DecisionPackageDetail now reads useRouter() for the
// "Maak actie" button. Mock next/navigation so the existing render
// tests don't trip the "app router not mounted" invariant.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

import { DecisionPackageDetail } from "./DecisionPackageDetail";

const HAPPY: DecisionPackageResponse = {
  decision_package_id: "dp-test",
  forecast_run_id: "fcst-test",
  composed_at: "2026-05-25T07:00:00+00:00",
  valid_until: "2026-06-22T07:00:00+00:00",
  ibkr_account_id: "DU1234567",
  conid: "ASML.AS",
  symbol: "ASML",
  exchange: "AEB",
  currency_local: "EUR",
  asset_class: "STK",
  user_holds_position: true,
  held_quantity: "10",
  held_avg_cost_local: "620.00",
  current_price_local: "640.12345600",
  current_price_eur: "640.12345600",
  as_of_market_data_ts: "2026-05-24T20:00:00+00:00",
  freshness_state: "fresh",
  data_age_trading_days: 0,
  forecast_method: "historical_bootstrap_v1",
  p10_log_return: "-0.05",
  p50_log_return: "0.02",
  p90_log_return: "0.08",
  p10_price_eur: "608.769000",
  p50_price_eur: "652.929000",
  p90_price_eur: "693.282000",
  prob_positive: "0.62",
  prob_loss_gt_5pct: "0.12",
  expected_volatility_annualized: "0.25",
  forecast_confidence_level: "Hoog",
  suggested_action_label: "Bekijken",
  block_reason: null,
  gate_outcomes: [
    { gate_name: "forecast_valid", passed: true, reason_nl: "" },
    { gate_name: "data_fresh", passed: true, reason_nl: "" },
    {
      gate_name: "freshness_within_sla",
      passed: false,
      reason_nl: "Marktdata is 10 dagen oud; SLA is 3 dagen.",
    },
  ],
  evidence_references: [
    {
      source_id: "snap-1",
      source_type: "market_data_snapshot",
      claim_summary: "EOD-snapshot voor ASML op 24 mei 2026",
    },
  ],
  deterministic_dutch_explanation:
    "Voor ASML duidt de voorspelling op een signaal om te bekijken (label: Bekijken) over de komende 20 handelsdagen.",
  audit_trail_hash:
    "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  previous_package_hash: null,
  sector: null,
  market_cap_eur: null,
  pe_ratio: null,
  momentum_6m_pct: null,
  momentum_12m_pct: null,
  dividend_yield_pct: null,
  next_earnings_date: null,
  next_earnings_status: null,
  expected_dividend_gross_local: null,
  expected_dividend_currency: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

afterEach(() => {
  cleanup();
});

describe("DecisionPackageDetail", () => {
  it("renders all seven Dutch sections", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    expect(screen.getByTestId("dp-section-header")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-forecast")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-current")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-gates")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-evidence")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-explanation")).toBeInTheDocument();
    expect(screen.getByTestId("dp-section-audit")).toBeInTheDocument();
  });

  it("color-codes the label badge per locked Dutch label", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const badge = screen.getByTestId("dp-label-badge");
    expect(badge).toHaveTextContent("Bekijken");
    // Bekijken → amber (#fef3c7 background).
    expect(badge.getAttribute("style")).toMatch(
      /background:\s*rgb\(254,\s*243,\s*199\)/,
    );
  });

  it("renders the forecast quantile band in EUR", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const band = screen.getByTestId("dp-field-band");
    expect(band).toHaveTextContent("€608,77");
    expect(band).toHaveTextContent("€652,93");
    expect(band).toHaveTextContent("€693,28");
  });

  it("renders probabilities as Dutch percentages", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    expect(screen.getByTestId("dp-field-prob-positive")).toHaveTextContent(
      "62%",
    );
    expect(screen.getByTestId("dp-field-prob-loss")).toHaveTextContent(
      "12%",
    );
  });

  it("renders held position info when user_holds_position is true", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const position = screen.getByTestId("dp-field-position");
    expect(position).toHaveTextContent("10 stuks");
    expect(position).toHaveTextContent("620.00");
  });

  it("renders 'Niet in portefeuille' when not held", () => {
    const notHeld = {
      ...HAPPY,
      user_holds_position: false,
      held_quantity: null,
      held_avg_cost_local: null,
    };
    render(<DecisionPackageDetail package={notHeld} />);
    expect(screen.getByTestId("dp-field-position")).toHaveTextContent(
      "Niet in portefeuille.",
    );
  });

  it("renders each gate row with pass/fail status", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const failingGate = screen.getByTestId(
      "dp-gate-row-freshness_within_sla",
    );
    expect(failingGate).toHaveTextContent("Gefaald");
    expect(failingGate).toHaveTextContent("Marktdata is 10 dagen oud");
    const passingGate = screen.getByTestId("dp-gate-row-forecast_valid");
    expect(passingGate).toHaveTextContent("Geslaagd");
  });

  it("renders evidence references", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const evidence = screen.getByTestId(
      "dp-evidence-market_data_snapshot",
    );
    expect(evidence).toHaveTextContent(
      "EOD-snapshot voor ASML op 24 mei 2026",
    );
  });

  it("renders the deterministic Dutch explanation verbatim", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    expect(screen.getByTestId("dp-explanation-text")).toHaveTextContent(
      HAPPY.deterministic_dutch_explanation,
    );
  });

  it("truncates audit hash and expands on click", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    const hash = screen.getByTestId("dp-audit-hash");
    expect(hash).toHaveTextContent("abcdef012345…");
    fireEvent.click(screen.getByTestId("dp-audit-hash-toggle"));
    expect(hash).toHaveTextContent(HAPPY.audit_trail_hash);
  });

  it("shows 'first package' note when previous_package_hash is null", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    expect(
      screen.getByTestId("dp-previous-hash-none"),
    ).toHaveTextContent("Eerste Decision Package");
  });

  it("shows truncated previous hash when chain exists", () => {
    const withPrev = {
      ...HAPPY,
      previous_package_hash:
        "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
    };
    render(<DecisionPackageDetail package={withPrev} />);
    expect(screen.getByTestId("dp-previous-hash")).toHaveTextContent(
      "fedcba987654…",
    );
  });

  // V1.2 §BL — Bedrijfsinfo sectie (CLAUDE.md §9 enrichment).

  it("hides Bedrijfsinfo section when all enrichment fields are null", () => {
    render(<DecisionPackageDetail package={HAPPY} />);
    expect(screen.queryByTestId("dp-section-company-info")).toBeNull();
  });

  it("renders Bedrijfsinfo section when any enrichment field is set", () => {
    const withCompany = {
      ...HAPPY,
      sector: "Technology",
      market_cap_eur: "275000000000",
      pe_ratio: "32.5",
      momentum_6m_pct: "5.2",
      momentum_12m_pct: "12.8",
      dividend_yield_pct: "0.7",
      next_earnings_date: "2026-07-15",
      next_earnings_status: "upcoming",
      expected_dividend_gross_local: "1.45",
      expected_dividend_currency: "EUR",
    };
    render(<DecisionPackageDetail package={withCompany} />);
    expect(screen.getByTestId("dp-section-company-info")).toBeTruthy();
    expect(screen.getByTestId("dp-field-sector")).toHaveTextContent(
      "Technology",
    );
    expect(screen.getByTestId("dp-field-market-cap")).toHaveTextContent(
      /mrd|mln/i,
    );
    expect(screen.getByTestId("dp-field-pe-ratio")).toHaveTextContent(
      "32,5",
    );
    expect(screen.getByTestId("dp-field-momentum")).toHaveTextContent(
      /6m/i,
    );
    expect(screen.getByTestId("dp-field-momentum")).toHaveTextContent(
      /12m/i,
    );
    expect(screen.getByTestId("dp-field-div-yield")).toHaveTextContent(
      "0,70%",
    );
    expect(
      screen.getByTestId("dp-field-next-earnings"),
    ).toHaveTextContent("15/07/2026");
    expect(
      screen.getByTestId("dp-field-expected-dividend"),
    ).toHaveTextContent("1.45");
  });

  it("renders only the present enrichment subset", () => {
    const partial = {
      ...HAPPY,
      sector: "Healthcare",
      pe_ratio: "18.0",
      // rest null
    };
    render(<DecisionPackageDetail package={partial} />);
    expect(screen.getByTestId("dp-section-company-info")).toBeTruthy();
    expect(screen.getByTestId("dp-field-sector")).toBeTruthy();
    expect(screen.getByTestId("dp-field-pe-ratio")).toBeTruthy();
    expect(screen.queryByTestId("dp-field-market-cap")).toBeNull();
    expect(screen.queryByTestId("dp-field-next-earnings")).toBeNull();
  });
});
