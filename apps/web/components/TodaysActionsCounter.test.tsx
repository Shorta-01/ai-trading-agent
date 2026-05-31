import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getSuggestionsGrid = vi.fn();
const getActionDraftsTeKeuren = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSuggestionsGrid: (...a: unknown[]) => getSuggestionsGrid(...a),
    getActionDraftsTeKeuren: (...a: unknown[]) =>
      getActionDraftsTeKeuren(...a),
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

import { TodaysActionsCounter } from "./TodaysActionsCounter";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => {
  getSuggestionsGrid.mockReset();
  getActionDraftsTeKeuren.mockReset();
});

afterEach(() => cleanup());

describe("TodaysActionsCounter", () => {
  it("renders both cards with counts and the new/changed subline", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok({
        status: "ok",
        status_nl: "x",
        help_nl: "x",
        risk_profile: "Gebalanceerd",
        actions_allowed: true,
        safe_for_orders: false,
        generated_at: null,
        section_count: 2,
        total_item_count: 5,
        new_count: 3,
        changed_count: 1,
        sections: [],
      }),
    );
    getActionDraftsTeKeuren.mockReturnValue(
      ok({
        ibkr_account_id: "DU1",
        drafts: [{} as object, {} as object],
        safe_for_submission: false,
      }),
    );
    render(<TodaysActionsCounter />);
    const suggestions = await screen.findByTestId(
      "todays-actions-suggestions-card",
    );
    await waitFor(() =>
      expect(suggestions.textContent).toContain("5"),
    );
    expect(suggestions.textContent).toContain("3 nieuw");
    expect(suggestions.textContent).toContain("1 gewijzigd");
    expect(suggestions.getAttribute("href")).toBe("/suggesties");

    const drafts = await screen.findByTestId("todays-actions-drafts-card");
    await waitFor(() => expect(drafts.textContent).toContain("2"));
    expect(drafts.getAttribute("href")).toBe("/ibkr-acties");
  });

  it("marks the drafts card as ok (green) when there are zero to review", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok({
        status: "ok",
        status_nl: "x",
        help_nl: "x",
        risk_profile: "Gebalanceerd",
        actions_allowed: true,
        safe_for_orders: false,
        generated_at: null,
        section_count: 0,
        total_item_count: 0,
        new_count: 0,
        changed_count: 0,
        sections: [],
      }),
    );
    getActionDraftsTeKeuren.mockReturnValue(
      ok({
        ibkr_account_id: "DU1",
        drafts: [],
        safe_for_submission: false,
      }),
    );
    render(<TodaysActionsCounter />);
    const drafts = await screen.findByTestId("todays-actions-drafts-card");
    await waitFor(() =>
      expect(drafts.getAttribute("data-tone")).toBe("ok"),
    );
    expect(drafts.textContent).toContain("Geen actie nodig");
  });

  it("marks the suggestions card as attention when there are open suggestions", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok({
        status: "ok",
        status_nl: "x",
        help_nl: "x",
        risk_profile: "Gebalanceerd",
        actions_allowed: true,
        safe_for_orders: false,
        generated_at: null,
        section_count: 1,
        total_item_count: 3,
        new_count: 2,
        changed_count: 0,
        sections: [],
      }),
    );
    getActionDraftsTeKeuren.mockReturnValue(
      ok({ ibkr_account_id: "DU1", drafts: [], safe_for_submission: false }),
    );
    render(<TodaysActionsCounter />);
    const card = await screen.findByTestId(
      "todays-actions-suggestions-card",
    );
    await waitFor(() =>
      expect(card.getAttribute("data-tone")).toBe("attention"),
    );
  });

  it("falls back to em-dash counts when one API fails", async () => {
    getSuggestionsGrid.mockReturnValue(fail());
    getActionDraftsTeKeuren.mockReturnValue(fail());
    render(<TodaysActionsCounter />);
    const suggestions = await screen.findByTestId(
      "todays-actions-suggestions-card",
    );
    expect(suggestions.textContent).toContain("—");
    const drafts = await screen.findByTestId("todays-actions-drafts-card");
    expect(drafts.textContent).toContain("—");
  });
});
