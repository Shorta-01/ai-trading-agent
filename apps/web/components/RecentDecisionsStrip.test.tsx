import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SuggestionsGridResponse } from "@/lib/apiClient";

const getSuggestionsGrid = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSuggestionsGrid: (...a: unknown[]) => getSuggestionsGrid(...a),
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

import { RecentDecisionsStrip } from "./RecentDecisionsStrip";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: SuggestionsGridResponse) {
  return Promise.resolve({ ok: true as const, data });
}

function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function _item(
  overrides: Partial<
    SuggestionsGridResponse["sections"][0]["items"][0]
  > = {},
): SuggestionsGridResponse["sections"][0]["items"][0] {
  return {
    suggestion_id: "sug-aapl-1",
    ibkr_conid: "265598",
    symbol: "AAPL",
    currency: "USD",
    forecast_id: null,
    generated_at: "2026-06-03T06:30:00+00:00",
    valid_until: "2026-06-03T20:00:00+00:00",
    valid_until_age_minutes: 0,
    risk_profile: "Gebalanceerd",
    has_position: true,
    action_label: "HOLD",
    action_label_nl: "Houden",
    confidence_label: "high",
    confidence_label_nl: "Hoog",
    confidence_score: "0.85",
    rationale_nl: "x",
    drivers: [],
    blockers: [],
    status: "ready",
    blocking_reason: null,
    branch_reason_nl: null,
    downgrade_reason_nl: null,
    top_driver_nl: null,
    blocking_reason_nl: null,
    expected_return_pct: null,
    prob_gain_pct: null,
    diff_status: "ongewijzigd",
    previous_action_label_nl: null,
    ...overrides,
  };
}

function _grid(
  items: Array<ReturnType<typeof _item>>,
): SuggestionsGridResponse {
  return {
    status: "ok",
    status_nl: "x",
    help_nl: "x",
    risk_profile: "Gebalanceerd",
    actions_allowed: true,
    safe_for_orders: false,
    generated_at: null,
    section_count: 1,
    total_item_count: items.length,
    new_count: 0,
    changed_count: 0,
    sections: [
      {
        action_label_nl: "Houden",
        section_title_nl: "Houden",
        item_count: items.length,
        items,
      },
    ],
  };
}

beforeEach(() => getSuggestionsGrid.mockReset());
afterEach(() => cleanup());

describe("RecentDecisionsStrip", () => {
  it("renders the empty-state when no suggestions are available", async () => {
    getSuggestionsGrid.mockReturnValue(ok(_grid([])));
    render(<RecentDecisionsStrip />);
    expect(
      await screen.findByTestId("recent-decisions-empty"),
    ).toBeInTheDocument();
  });

  it("flattens sections and renders newest first", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok(
        _grid([
          _item({
            suggestion_id: "sug-1",
            symbol: "AAPL",
            generated_at: "2026-06-03T06:30:00+00:00",
            action_label_nl: "Verkopen",
          }),
          _item({
            suggestion_id: "sug-2",
            symbol: "MSFT",
            generated_at: "2026-06-03T06:35:00+00:00", // newer
            action_label_nl: "Kopen",
          }),
        ]),
      ),
    );
    render(<RecentDecisionsStrip />);
    const list = await screen.findByTestId("recent-decisions-list");
    const rows = list.querySelectorAll("[data-testid^='recent-decisions-row-']");
    await waitFor(() => expect(rows.length).toBe(2));
    // Newest first.
    expect(rows[0].getAttribute("data-testid")).toBe(
      "recent-decisions-row-sug-2",
    );
    expect(rows[1].getAttribute("data-testid")).toBe(
      "recent-decisions-row-sug-1",
    );
  });

  it("caps the strip at five rows", async () => {
    const items = Array.from({ length: 12 }, (_, i) =>
      _item({
        suggestion_id: `sug-${i}`,
        symbol: `AS${i}`,
        generated_at: `2026-06-03T06:${String(50 - i).padStart(2, "0")}:00+00:00`,
      }),
    );
    getSuggestionsGrid.mockReturnValue(ok(_grid(items)));
    render(<RecentDecisionsStrip />);
    const list = await screen.findByTestId("recent-decisions-list");
    await waitFor(() =>
      expect(
        list.querySelectorAll("[data-testid^='recent-decisions-row-']").length,
      ).toBe(5),
    );
  });

  it("badges 'nieuw' rows visibly via the diff-status attribute", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok(
        _grid([
          _item({
            suggestion_id: "sug-new",
            symbol: "NEW",
            diff_status: "nieuw",
          }),
        ]),
      ),
    );
    render(<RecentDecisionsStrip />);
    const row = await screen.findByTestId("recent-decisions-row-sug-new");
    expect(row.getAttribute("data-diff-status")).toBe("nieuw");
    expect(row.textContent).toContain("nieuw");
  });

  it("falls back to an error line when the API is unreachable", async () => {
    getSuggestionsGrid.mockReturnValue(fail());
    render(<RecentDecisionsStrip />);
    expect(
      await screen.findByTestId("recent-decisions-error"),
    ).toBeInTheDocument();
  });
});
