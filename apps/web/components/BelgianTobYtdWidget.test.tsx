import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  AssetActionDraftResponse,
  LatestActionDraftsResponse,
  TobYearToDateResponse,
} from "@/lib/apiClient";

const getLatestActionDrafts = vi.fn();
const getTobYearToDate = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getLatestActionDrafts: (...a: unknown[]) => getLatestActionDrafts(...a),
    getTobYearToDate: (...a: unknown[]) => getTobYearToDate(...a),
  },
}));

import { BelgianTobYtdWidget } from "./BelgianTobYtdWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const currentYear = new Date().getUTCFullYear();
const previousYear = currentYear - 1;

function makeDraft(
  overrides: Partial<AssetActionDraftResponse> & {
    draft_id: string;
    symbol: string;
  },
): AssetActionDraftResponse {
  return {
    decision_package_id: "dp",
    decision_package_content_hash: "h",
    ibkr_conid: "1",
    currency: "EUR",
    exchange: null,
    primary_exchange: null,
    account_mode: "paper",
    expected_account_mode: "paper",
    action_side: "BUY",
    order_type: "LMT",
    tif: "DAY",
    quantity: "10",
    limit_price: "100",
    estimated_order_value: "1000",
    estimated_cash_before: "5000",
    estimated_cash_after: "4000",
    estimated_position_quantity_before: "0",
    estimated_position_quantity_after: "10",
    estimated_position_value_after: "1000",
    estimated_portfolio_weight_after_pct: "5",
    estimated_concentration_impact_pct: "0",
    orderimpact_base_currency: "EUR",
    estimated_belgian_tob: "3,50",
    belgian_tob_security_class: "stock",
    source_action_label: "buy",
    source_action_label_nl: "Kopen",
    status: "approved",
    dry_run_status: "passed",
    dry_run_failures: [],
    blocking_reason: null,
    rationale_nl: "",
    explanation_nl: "",
    created_at: `${currentYear}-06-12T08:00:00Z`,
    updated_at: `${currentYear}-06-12T08:00:00Z`,
    safe_for_submission: true,
    safe_for_orders: false,
    safe_for_broker_submission: false,
    ...overrides,
  };
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

const DRAFT_SAMPLE: LatestActionDraftsResponse = {
  status: "ready",
  help_nl: "",
  items: [
    makeDraft({ draft_id: "d1", symbol: "AAPL", estimated_belgian_tob: "3,50" }),
    makeDraft({
      draft_id: "d2",
      symbol: "MSFT",
      estimated_belgian_tob: "1,20",
      belgian_tob_security_class: "bond",
    }),
    makeDraft({
      draft_id: "d3",
      symbol: "OLD",
      updated_at: `${previousYear}-06-12T08:00:00Z`,
    }),
    makeDraft({
      draft_id: "d4",
      symbol: "DRAFT_ONLY",
      status: "draft",
    }),
  ],
};

const REALISED_EMPTY: TobYearToDateResponse = {
  title_nl: "",
  help_nl: "",
  year: currentYear,
  executions_count: 0,
  by_currency: {},
  by_security_class: {},
  note_nl: "Nog geen IBKR-fills geregistreerd",
  safe_for_orders: false,
};

const REALISED_SAMPLE: TobYearToDateResponse = {
  title_nl: "",
  help_nl: "",
  year: currentYear,
  executions_count: 2,
  by_currency: { EUR: "3.50", USD: "3.50" },
  by_security_class: { standard_stock: { EUR: "3.50", USD: "3.50" } },
  note_nl: "V1-universe: alles standard_stock",
  safe_for_orders: false,
};

beforeEach(() => {
  getLatestActionDrafts.mockReset();
  getTobYearToDate.mockReset();
});

afterEach(() => cleanup());

describe("BelgianTobYtdWidget", () => {
  it("uses realised TOB from /tob/year-to-date when executions exist", async () => {
    getTobYearToDate.mockResolvedValue(ok(REALISED_SAMPLE));
    getLatestActionDrafts.mockResolvedValue(ok(DRAFT_SAMPLE));
    render(<BelgianTobYtdWidget />);
    await waitFor(() => {
      expect(
        screen.getByTestId("belgian-tob-ytd-widget"),
      ).toHaveAttribute("data-mode", "realised");
    });
    expect(
      screen.getByTestId("belgian-tob-ytd-currency-EUR"),
    ).toHaveTextContent("EUR 3.50");
    expect(
      screen.getByTestId("belgian-tob-ytd-currency-USD"),
    ).toHaveTextContent("USD 3.50");
    expect(
      screen.getByTestId("belgian-tob-ytd-class-standard_stock-EUR"),
    ).toHaveTextContent("standard_stock (EUR): 3.50");
  });

  it("falls back to indicative draft-based view when no realised fills", async () => {
    getTobYearToDate.mockResolvedValue(ok(REALISED_EMPTY));
    getLatestActionDrafts.mockResolvedValue(ok(DRAFT_SAMPLE));
    render(<BelgianTobYtdWidget />);
    await waitFor(() => {
      expect(
        screen.getByTestId("belgian-tob-ytd-widget"),
      ).toHaveAttribute("data-mode", "indicatief");
    });
    await waitFor(() => {
      expect(screen.getByTestId("belgian-tob-ytd-total")).toHaveTextContent(
        "EUR 4.70",
      );
    });
    expect(
      screen.getByTestId("belgian-tob-ytd-class-stock"),
    ).toHaveTextContent("stock: EUR 3.50");
    expect(
      screen.getByTestId("belgian-tob-ytd-class-bond"),
    ).toHaveTextContent("bond: EUR 1.20");
  });

  it("renders a Dutch zero-state when both endpoints report empty", async () => {
    getTobYearToDate.mockResolvedValue(ok(REALISED_EMPTY));
    getLatestActionDrafts.mockResolvedValue(
      ok({ ...DRAFT_SAMPLE, items: [] }),
    );
    render(<BelgianTobYtdWidget />);
    expect(
      await screen.findByText("Nog geen geboekte TOB dit jaar."),
    ).toBeInTheDocument();
  });
});
