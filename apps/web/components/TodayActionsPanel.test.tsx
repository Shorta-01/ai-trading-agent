import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render as rtlRender, screen } from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  AssetSuggestionResponse,
  LatestSuggestionsResponse,
} from "@/lib/apiClient";

const getLatestSuggestions = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getLatestSuggestions: (...a: unknown[]) => getLatestSuggestions(...a),
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

import { TodayActionsPanel } from "./TodayActionsPanel";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeSuggestion(
  overrides: Partial<AssetSuggestionResponse> & { symbol: string },
): AssetSuggestionResponse {
  return {
    suggestion_id: `s-${overrides.symbol}`,
    ibkr_conid: "1",
    currency: "EUR",
    forecast_id: "fc",
    model_code: "m",
    model_version: "1",
    generated_at: "2026-06-12T07:00:00Z",
    valid_until: "2026-06-13T07:00:00Z",
    risk_profile: "moderate",
    has_position: false,
    action_label: "buy",
    action_label_nl: "Kopen",
    confidence_label: "high",
    confidence_label_nl: "Hoog",
    confidence_score: "0.9",
    rationale_nl: "Doctrine signaal positief",
    drivers: [],
    blockers: [],
    status: "ready",
    blocking_reason: null,
    safe_for_action_drafts: true,
    safe_for_orders: false,
    safe_for_broker_submission: false,
    ...overrides,
  };
}

const SAMPLE: LatestSuggestionsResponse = {
  status: "ready",
  status_nl: "Klaar",
  help_nl: "",
  risk_profile: "moderate",
  items: [
    makeSuggestion({ symbol: "AAPL", action_label_nl: "Kopen" }),
    makeSuggestion({ symbol: "MSFT", action_label_nl: "Kopen" }),
    makeSuggestion({ symbol: "OLD", action_label_nl: "Verkopen" }),
    makeSuggestion({ symbol: "HOLD", action_label_nl: "Houden" }),
  ],
};

beforeEach(() => {
  getLatestSuggestions.mockReset();
});

afterEach(() => cleanup());

const ok = <T,>(data: T) => ({ ok: true as const, data });

describe("TodayActionsPanel", () => {
  it("groups suggestions into Dutch action buckets", async () => {
    getLatestSuggestions.mockResolvedValue(ok(SAMPLE));
    render(<TodayActionsPanel />);
    expect(await screen.findByTestId("today-actions-bucket-Kopen")).toBeInTheDocument();
    expect(screen.getByTestId("today-actions-bucket-Verkopen")).toBeInTheDocument();
    expect(screen.getByTestId("today-actions-bucket-Houden")).toBeInTheDocument();
    expect(screen.getByTestId("today-actions-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("today-actions-row-MSFT")).toBeInTheDocument();
    expect(screen.getByTestId("today-actions-row-OLD")).toBeInTheDocument();
  });

  it("omits empty buckets", async () => {
    getLatestSuggestions.mockResolvedValue(
      ok({ ...SAMPLE, items: [makeSuggestion({ symbol: "AAPL", action_label_nl: "Kopen" })] }),
    );
    render(<TodayActionsPanel />);
    await screen.findByTestId("today-actions-bucket-Kopen");
    expect(screen.queryByTestId("today-actions-bucket-Verkopen")).toBeNull();
    expect(screen.queryByTestId("today-actions-bucket-Houden")).toBeNull();
  });

  it("renders Dutch empty state when no suggestions exist", async () => {
    getLatestSuggestions.mockResolvedValue(ok({ ...SAMPLE, items: [] }));
    render(<TodayActionsPanel />);
    expect(
      await screen.findByText("Nog geen suggesties vandaag"),
    ).toBeInTheDocument();
  });
});
