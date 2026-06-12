import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render as rtlRender, screen } from "@testing-library/react";
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

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { PendingApprovalsPanel } from "./PendingApprovalsPanel";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

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
    limit_price: "100,00",
    estimated_order_value: "1000,00",
    estimated_cash_before: "5000",
    estimated_cash_after: "4000",
    estimated_position_quantity_before: "0",
    estimated_position_quantity_after: "10",
    estimated_position_value_after: "1000",
    estimated_portfolio_weight_after_pct: "5,00",
    estimated_concentration_impact_pct: "0",
    orderimpact_base_currency: "EUR",
    estimated_belgian_tob: "3,50",
    belgian_tob_security_class: "stock",
    source_action_label: "buy",
    source_action_label_nl: "Kopen",
    status: "draft",
    dry_run_status: "passed",
    dry_run_failures: [],
    blocking_reason: null,
    rationale_nl: "Doctrine geslaagd",
    explanation_nl: "",
    created_at: "2026-06-12T08:00:00Z",
    updated_at: "2026-06-12T08:00:00Z",
    safe_for_submission: true,
    safe_for_orders: false,
    safe_for_broker_submission: false,
    ...overrides,
  };
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

const SAMPLE: LatestActionDraftsResponse = {
  status: "ready",
  help_nl: "",
  items: [
    makeDraft({ draft_id: "d1", symbol: "AAPL" }),
    makeDraft({
      draft_id: "d2",
      symbol: "MSFT",
      dry_run_status: "failed",
      dry_run_failures: ["concentration"],
    }),
    makeDraft({ draft_id: "d3", symbol: "OLD", status: "approved" }),
  ],
};

beforeEach(() => {
  getLatestActionDrafts.mockReset();
});

afterEach(() => cleanup());

describe("PendingApprovalsPanel", () => {
  it("renders one row per pending draft with dry-run badge", async () => {
    getLatestActionDrafts.mockResolvedValue(ok(SAMPLE));
    render(<PendingApprovalsPanel />);
    expect(
      await screen.findByTestId("pending-approval-row-d1"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("pending-approval-row-d1-dryrun")).toHaveTextContent(
      "Dry-run geslaagd",
    );
    expect(screen.getByTestId("pending-approval-row-d2-dryrun")).toHaveTextContent(
      "Dry-run mislukt",
    );
  });

  it("hides drafts that are already approved or submitted", async () => {
    getLatestActionDrafts.mockResolvedValue(ok(SAMPLE));
    render(<PendingApprovalsPanel />);
    await screen.findByTestId("pending-approval-row-d1");
    expect(screen.queryByTestId("pending-approval-row-d3")).toBeNull();
  });

  it("renders Dutch empty state when nothing is pending", async () => {
    getLatestActionDrafts.mockResolvedValue(ok({ ...SAMPLE, items: [] }));
    render(<PendingApprovalsPanel />);
    expect(
      await screen.findByText("Geen acties te keuren"),
    ).toBeInTheDocument();
  });
});
