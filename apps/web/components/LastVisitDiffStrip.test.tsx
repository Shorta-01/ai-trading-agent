import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  LatestActionDraftsResponse,
  OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const listOrchestratorVerdicts = vi.fn();
const getLatestActionDrafts = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listOrchestratorVerdicts: (...a: unknown[]) =>
      listOrchestratorVerdicts(...a),
    getLatestActionDrafts: (...a: unknown[]) => getLatestActionDrafts(...a),
  },
}));

import { LastVisitDiffStrip } from "./LastVisitDiffStrip";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

const STORAGE_KEY = "ai-trading-agent:last-visit-v1";

function verdicts(
  ids: string[],
): OrchestratorVerdictsListResponse {
  return {
    title_nl: "",
    help_nl: "",
    items: ids.map((id) => ({
      verdict_id: id,
      symbol: id.toUpperCase(),
      ibkr_conid: 1,
      forecast_id: id,
      generated_at: "2026-06-12T07:00:00Z",
      decision: "suggest",
      blocking_reason: null,
      summary_nl: "",
      details_json: {},
    })),
  };
}

function drafts(ids: string[]): LatestActionDraftsResponse {
  return {
    status: "ready",
    help_nl: "",
    items: ids.map((id) => ({
      draft_id: id,
      decision_package_id: "dp",
      decision_package_content_hash: "h",
      ibkr_conid: "1",
      symbol: id.toUpperCase(),
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
      estimated_order_value: null,
      estimated_cash_before: null,
      estimated_cash_after: null,
      estimated_position_quantity_before: null,
      estimated_position_quantity_after: null,
      estimated_position_value_after: null,
      estimated_portfolio_weight_after_pct: null,
      estimated_concentration_impact_pct: null,
      orderimpact_base_currency: null,
      estimated_belgian_tob: null,
      belgian_tob_security_class: null,
      source_action_label: "buy",
      source_action_label_nl: "Kopen",
      status: "draft",
      dry_run_status: "passed",
      dry_run_failures: [],
      blocking_reason: null,
      rationale_nl: "",
      explanation_nl: "",
      created_at: "2026-06-12T08:00:00Z",
      updated_at: "2026-06-12T08:00:00Z",
      safe_for_submission: true,
      safe_for_orders: false,
      safe_for_broker_submission: false,
    })),
  };
}

beforeEach(() => {
  listOrchestratorVerdicts.mockReset();
  getLatestActionDrafts.mockReset();
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
});

describe("LastVisitDiffStrip", () => {
  it("renders the first-visit baseline prompt when no snapshot exists", async () => {
    listOrchestratorVerdicts.mockResolvedValue(ok(verdicts(["v1"])));
    getLatestActionDrafts.mockResolvedValue(ok(drafts(["d1"])));
    render(<LastVisitDiffStrip />);
    const strip = await screen.findByTestId("last-visit-strip");
    expect(strip).toHaveTextContent("Eerste bezoek");
    expect(
      screen.getByTestId("last-visit-strip-baseline"),
    ).toBeInTheDocument();
  });

  it("shows the diff when new verdicts and drafts appear since the snapshot", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        recorded_at: "2026-06-11T08:00:00Z",
        verdict_ids: ["v1"],
        draft_ids: ["d1"],
      }),
    );
    listOrchestratorVerdicts.mockResolvedValue(ok(verdicts(["v1", "v2"])));
    getLatestActionDrafts.mockResolvedValue(ok(drafts(["d1", "d2", "d3"])));
    render(<LastVisitDiffStrip />);
    await screen.findByTestId("last-visit-strip");
    expect(
      screen.getByTestId("last-visit-strip-new-verdicts"),
    ).toHaveTextContent("1 nieuwe verdict");
    expect(
      screen.getByTestId("last-visit-strip-new-drafts"),
    ).toHaveTextContent("2 nieuwe action drafts");
  });

  it("hides the strip after the operator acknowledges", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        recorded_at: "2026-06-11T08:00:00Z",
        verdict_ids: ["v1"],
        draft_ids: [],
      }),
    );
    listOrchestratorVerdicts.mockResolvedValue(ok(verdicts(["v1", "v2"])));
    getLatestActionDrafts.mockResolvedValue(ok(drafts([])));
    render(<LastVisitDiffStrip />);
    const ack = await screen.findByTestId("last-visit-strip-ack");
    fireEvent.click(ack);
    await waitFor(() => {
      expect(screen.queryByTestId("last-visit-strip")).toBeNull();
    });
    const stored = window.localStorage.getItem(STORAGE_KEY);
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!) as {
      verdict_ids: string[];
      draft_ids: string[];
    };
    expect(parsed.verdict_ids).toEqual(["v1", "v2"]);
  });

  it("renders nothing when there is no delta since the last snapshot", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        recorded_at: "2026-06-11T08:00:00Z",
        verdict_ids: ["v1"],
        draft_ids: ["d1"],
      }),
    );
    listOrchestratorVerdicts.mockResolvedValue(ok(verdicts(["v1"])));
    getLatestActionDrafts.mockResolvedValue(ok(drafts(["d1"])));
    const { container } = render(<LastVisitDiffStrip />);
    await waitFor(() => {
      expect(listOrchestratorVerdicts).toHaveBeenCalledTimes(1);
      expect(getLatestActionDrafts).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="last-visit-strip"]'),
    ).toBeNull();
  });
});
