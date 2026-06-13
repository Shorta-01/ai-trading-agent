import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type { MacroSnapshotResponse } from "@/lib/apiClient";

const getMacroSnapshot = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getMacroSnapshot: (...a: unknown[]) => getMacroSnapshot(...a),
  },
}));

import { MacroRegimeStrip } from "./MacroRegimeStrip";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeResponse(
  overrides: Partial<MacroSnapshotResponse> = {},
): MacroSnapshotResponse {
  return {
    title_nl: "Markt-regime",
    help_nl: "help",
    state: "rustig",
    severity: "info",
    headline_nl: "Markt-regime rustig.",
    vix_level: 14.5,
    ma_short_day: 5100,
    ma_long_day: 5050,
    last_evaluated_at: "2026-06-13T09:00:00Z",
    sample_size: 12,
    ...overrides,
  };
}

beforeEach(() => {
  getMacroSnapshot.mockReset();
});

afterEach(() => cleanup());

describe("MacroRegimeStrip", () => {
  it("renders a green strip with the headline when the regime is rustig", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: true as const,
      data: makeResponse(),
    });
    render(<MacroRegimeStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("macro-regime-strip").getAttribute("data-state"),
      ).toBe("rustig");
    });
    expect(screen.getByTestId("macro-regime-badge").textContent).toBe("Rustig");
    expect(
      screen.getByTestId("macro-regime-headline").textContent,
    ).toContain("Markt-regime rustig");
  });

  it("renders a yellow strip when the regime is verhoogd", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: true as const,
      data: makeResponse({
        state: "verhoogd",
        severity: "warning",
        headline_nl: "Verhoogde volatiliteit: VIX 28,0 boven drempel.",
        vix_level: 28.0,
      }),
    });
    render(<MacroRegimeStrip />);
    await waitFor(() => {
      expect(
        screen
          .getByTestId("macro-regime-strip")
          .getAttribute("data-severity"),
      ).toBe("warning");
    });
    expect(screen.getByTestId("macro-regime-badge").textContent).toBe("Verhoogd");
    expect(
      screen.getByTestId("macro-regime-headline").textContent,
    ).toContain("VIX 28");
  });

  it("renders a red strip when the regime is stress", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: true as const,
      data: makeResponse({
        state: "stress",
        severity: "critical",
        headline_nl: "Macro-stress: VIX 32,0 en S&P bear-trend.",
        vix_level: 32.0,
      }),
    });
    render(<MacroRegimeStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("macro-regime-strip").getAttribute("data-state"),
      ).toBe("stress");
    });
    expect(screen.getByTestId("macro-regime-badge").textContent).toBe("Stress");
  });

  it("shows the VIX badge when a level is present", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: true as const,
      data: makeResponse({ vix_level: 17.2 }),
    });
    render(<MacroRegimeStrip />);
    await waitFor(() => {
      expect(screen.queryByTestId("macro-regime-vix")).not.toBeNull();
    });
    expect(screen.getByTestId("macro-regime-vix").textContent).toContain(
      "VIX 17,2",
    );
  });

  it("hides the VIX badge when no level is present", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: true as const,
      data: makeResponse({ vix_level: null }),
    });
    render(<MacroRegimeStrip />);
    await screen.findByTestId("macro-regime-strip");
    expect(screen.queryByTestId("macro-regime-vix")).toBeNull();
  });

  it("falls back to an onbekend strip when the API returns no data", async () => {
    getMacroSnapshot.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<MacroRegimeStrip />);
    const strip = await screen.findByTestId("macro-regime-strip");
    expect(strip.getAttribute("data-state")).toBe("onbekend");
  });
});
