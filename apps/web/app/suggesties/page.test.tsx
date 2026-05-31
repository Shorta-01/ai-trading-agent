import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SuggestionsGridResponse } from "@/lib/apiClient";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const getSuggestionsGrid = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSuggestionsGrid: (...a: unknown[]) => getSuggestionsGrid(...a),
  },
}));

import Page from "./page";

const ok = <T,>(data: T) => ({ ok: true as const, data });

const SAMPLE: SuggestionsGridResponse = {
  status: "ok",
  status_nl: "2 suggesties in 2 secties (1 nieuw)",
  help_nl: "Help text.",
  risk_profile: "Gebalanceerd",
  actions_allowed: false,
  safe_for_orders: false,
  generated_at: "2026-05-31T07:00:00+00:00",
  section_count: 2,
  total_item_count: 2,
  new_count: 1,
  changed_count: 1,
  sections: [
    {
      action_label_nl: "Verkopen",
      section_title_nl: "Verkopen — directe actie",
      item_count: 1,
      items: [
        {
          suggestion_id: "sug-msft",
          ibkr_conid: "msft-conid",
          symbol: "MSFT",
          currency: "USD",
          forecast_id: "fc-msft",
          generated_at: "2026-05-31T07:00:00+00:00",
          valid_until: "2026-06-01T07:00:00+00:00",
          valid_until_age_minutes: 1440,
          risk_profile: "Gebalanceerd",
          has_position: true,
          action_label: "Verkopen",
          action_label_nl: "Verkopen",
          confidence_label: "high",
          confidence_label_nl: "Hoog",
          confidence_score: "0.85",
          rationale_nl: "Verkopen: sterke daling verwacht.",
          drivers: ["direction_label=strong_down"],
          blockers: [],
          status: "ready",
          blocking_reason: null,
          branch_reason_nl: "Reeds in bezit + sterke daling → Verkopen.",
          downgrade_reason_nl: null,
          top_driver_nl: "Sterke daling verwacht; 18% kans op winst.",
          blocking_reason_nl: null,
          expected_return_pct: "-6.50",
          prob_gain_pct: "18.0",
          diff_status: "gewijzigd",
          previous_action_label_nl: "Houden",
        },
      ],
    },
    {
      action_label_nl: "Kopen",
      section_title_nl: "Kopen — nieuwe positie",
      item_count: 1,
      items: [
        {
          suggestion_id: "sug-aapl",
          ibkr_conid: "aapl-conid",
          symbol: "AAPL",
          currency: "USD",
          forecast_id: "fc-aapl",
          generated_at: "2026-05-31T07:00:00+00:00",
          valid_until: "2026-06-01T07:00:00+00:00",
          valid_until_age_minutes: 1440,
          risk_profile: "Gebalanceerd",
          has_position: false,
          action_label: "Kopen",
          action_label_nl: "Kopen",
          confidence_label: "high",
          confidence_label_nl: "Hoog",
          confidence_score: "0.80",
          rationale_nl: "Kopen: sterke stijging verwacht.",
          drivers: ["direction_label=strong_up"],
          blockers: [],
          status: "ready",
          blocking_reason: null,
          branch_reason_nl: "Niet in bezit + sterke stijging → Kopen.",
          downgrade_reason_nl: null,
          top_driver_nl: "Sterke stijging verwacht; 72% kans op winst.",
          blocking_reason_nl: null,
          expected_return_pct: "4.50",
          prob_gain_pct: "72.0",
          diff_status: "nieuw",
          previous_action_label_nl: null,
        },
      ],
    },
  ],
};

beforeEach(() => {
  getSuggestionsGrid.mockReset();
  getSuggestionsGrid.mockReturnValue(ok(SAMPLE));
});

afterEach(() => cleanup());

describe("SuggestionsGridPage", () => {
  it("renders sections in locked order with diff badges", async () => {
    render(<Page />);
    expect(await screen.findByTestId("suggesties-page")).toBeInTheDocument();
    // Verkopen section must render before Kopen.
    const sections = await screen.findAllByTestId(/^suggesties-section-/);
    const verkopenIndex = sections.findIndex(
      (el) => el.getAttribute("data-testid") === "suggesties-section-Verkopen",
    );
    const kopenIndex = sections.findIndex(
      (el) => el.getAttribute("data-testid") === "suggesties-section-Kopen",
    );
    expect(verkopenIndex).toBeGreaterThanOrEqual(0);
    expect(kopenIndex).toBeGreaterThan(verkopenIndex);
    // Diff badges visible.
    expect(screen.getByTestId("suggesties-row-badge-nieuw")).toHaveTextContent(
      "NIEUW",
    );
    expect(
      screen.getByTestId("suggesties-row-badge-gewijzigd"),
    ).toHaveTextContent("GEWIJZIGD");
    // Top driver renders inline.
    expect(
      screen.getAllByTestId("suggesties-row-top-driver")[0],
    ).toHaveTextContent("Sterke daling verwacht");
  });

  it("expands a row to show full rationale + previous label", async () => {
    render(<Page />);
    const toggle = await screen.findByTestId("suggesties-row-toggle-MSFT");
    await userEvent.click(toggle);
    const details = screen.getByTestId("suggesties-row-details-MSFT");
    expect(details).toHaveTextContent("Volledige redenering");
    expect(details).toHaveTextContent("Verkopen: sterke daling verwacht");
    expect(details).toHaveTextContent("Gisteren: Houden");
  });

  it("filters by diff status", async () => {
    render(<Page />);
    const filter = await screen.findByTestId("suggesties-filter-diff");
    await userEvent.selectOptions(filter, "nieuw");
    await waitFor(() => {
      expect(screen.queryByTestId("suggesties-row-MSFT")).not.toBeInTheDocument();
      expect(screen.getByTestId("suggesties-row-AAPL")).toBeInTheDocument();
    });
  });

  it("shows the empty state when there are zero sections", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok({
        ...SAMPLE,
        status: "no_suggestions",
        status_nl: "Nog geen suggesties beschikbaar",
        sections: [],
        section_count: 0,
        total_item_count: 0,
        new_count: 0,
        changed_count: 0,
      }),
    );
    render(<Page />);
    expect(await screen.findByTestId("suggesties-empty")).toBeInTheDocument();
  });

  it("disables export CSV when no rows", async () => {
    getSuggestionsGrid.mockReturnValue(
      ok({
        ...SAMPLE,
        sections: [],
        section_count: 0,
        total_item_count: 0,
        new_count: 0,
        changed_count: 0,
      }),
    );
    render(<Page />);
    const button = await screen.findByTestId("suggesties-export-csv");
    expect(button).toBeDisabled();
  });

  it("shows the 'nieuw sinds vorige bezoek' badge when localStorage has an earlier visit", async () => {
    // Seed a visit timestamp from well before the sample's generated_at.
    const earlier = new Date("2026-05-30T10:00:00Z").getTime();
    window.localStorage.setItem("suggesties:lastVisitAt", String(earlier));
    render(<Page />);
    const badge = await screen.findByTestId("suggesties-since-last-visit");
    expect(badge).toHaveTextContent("2 nieuw sinds je vorige bezoek");
    window.localStorage.clear();
  });

  it("hides the badge when there is no prior visit recorded", async () => {
    window.localStorage.clear();
    render(<Page />);
    expect(
      await screen.findByTestId("suggesties-page"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("suggesties-since-last-visit"),
    ).not.toBeInTheDocument();
  });
});
