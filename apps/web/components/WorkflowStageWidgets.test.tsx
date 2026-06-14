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
} from "@/lib/apiClient";

const getLatestActionDrafts = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getLatestActionDrafts: (...a: unknown[]) => getLatestActionDrafts(...a),
  },
}));

import {
  Stage2ReadyToSendWidget,
  Stage3SubmittedWidget,
} from "./WorkflowStageWidgets";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeDraft(
  status: string,
  overrides: Partial<AssetActionDraftResponse> = {},
): AssetActionDraftResponse {
  return {
    draft_id: `draft-${status}-${Math.random().toString(36).slice(2)}`,
    decision_package_id: "dp1",
    decision_package_content_hash: "hash",
    ibkr_conid: "c1",
    symbol: "AAPL",
    currency: "USD",
    exchange: null,
    primary_exchange: null,
    account_mode: "paper",
    expected_account_mode: "paper",
    action_side: "BUY",
    order_type: "LMT",
    tif: "DAY",
    quantity: "100",
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
    source_action_label: "BUY",
    source_action_label_nl: "Kopen",
    status,
    dry_run_status: "passed",
    dry_run_failures: [],
    blocking_reason: null,
    rationale_nl: "",
    explanation_nl: "",
    created_at: "2026-06-14T10:00:00Z",
    updated_at: "2026-06-14T10:00:00Z",
    safe_for_submission: false,
    safe_for_orders: false,
    safe_for_broker_submission: false,
    ...overrides,
  };
}

function makeResp(
  drafts: AssetActionDraftResponse[],
): LatestActionDraftsResponse {
  return {
    status: "ok",
    help_nl: "",
    items: drafts,
  };
}

beforeEach(() => {
  getLatestActionDrafts.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("Stage2ReadyToSendWidget", () => {
  it("toont loading state initieel", () => {
    getLatestActionDrafts.mockImplementation(
      () => new Promise<never>(() => {}),
    );
    render(<Stage2ReadyToSendWidget />);
    expect(screen.getByTestId("stage-2-ready-to-send-loading")).toBeTruthy();
  });

  it("toont empty wanneer geen user_approved drafts", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([makeDraft("proposed")]),
    });
    render(<Stage2ReadyToSendWidget />);
    await waitFor(() => {
      expect(screen.getByTestId("stage-2-ready-to-send-empty")).toBeTruthy();
    });
  });

  it("telt user_approved + approved samen", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([
        makeDraft("user_approved"),
        makeDraft("user_approved"),
        makeDraft("approved"),
        makeDraft("proposed"),
        makeDraft("filled"),
      ]),
    });
    render(<Stage2ReadyToSendWidget />);
    await waitFor(() => {
      expect(screen.getByTestId("stage-2-ready-to-send-total")).toBeTruthy();
    });
    expect(
      screen.getByTestId("stage-2-ready-to-send-total").textContent,
    ).toMatch(/3/);
  });

  it("toont link naar /ibkr-acties", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([makeDraft("user_approved")]),
    });
    render(<Stage2ReadyToSendWidget />);
    await waitFor(() => {
      const link = screen.getByTestId("stage-2-ready-to-send-link");
      expect(link.getAttribute("href")).toBe("/ibkr-acties");
    });
  });

  it("toont error wanneer fetch faalt", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: false,
      reason: "not_reachable",
    });
    render(<Stage2ReadyToSendWidget />);
    await waitFor(() => {
      expect(screen.getByTestId("stage-2-ready-to-send-error")).toBeTruthy();
    });
  });
});

describe("Stage3SubmittedWidget", () => {
  it("toont empty wanneer geen submitted/working/filled", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([makeDraft("proposed"), makeDraft("user_approved")]),
    });
    render(<Stage3SubmittedWidget />);
    await waitFor(() => {
      expect(screen.getByTestId("stage-3-submitted-empty")).toBeTruthy();
    });
  });

  it("telt alle Stage-3 statuses + toont breakdown", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([
        makeDraft("submitted"),
        makeDraft("submitted"),
        makeDraft("working"),
        makeDraft("filled"),
        makeDraft("partially_filled"),
        makeDraft("proposed"), // not counted
      ]),
    });
    render(<Stage3SubmittedWidget />);
    await waitFor(() => {
      expect(screen.getByTestId("stage-3-submitted-total")).toBeTruthy();
    });
    expect(screen.getByTestId("stage-3-submitted-total").textContent).toMatch(
      /5/,
    );
    expect(screen.getByTestId("stage-3-status-submitted").textContent).toMatch(
      /Verzonden.*2/,
    );
    expect(screen.getByTestId("stage-3-status-working").textContent).toMatch(
      /Werkend.*1/,
    );
    expect(screen.getByTestId("stage-3-status-filled").textContent).toMatch(
      /Gevuld.*1/,
    );
    expect(
      screen.getByTestId("stage-3-status-partially_filled").textContent,
    ).toMatch(/Deels gevuld.*1/);
  });

  it("toont link naar /ibkr-acties", async () => {
    getLatestActionDrafts.mockResolvedValue({
      ok: true,
      data: makeResp([makeDraft("filled")]),
    });
    render(<Stage3SubmittedWidget />);
    await waitFor(() => {
      const link = screen.getByTestId("stage-3-submitted-link");
      expect(link.getAttribute("href")).toBe("/ibkr-acties");
    });
  });
});
