import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type { SectorSpreadResponse, SectorRow } from "@/lib/apiClient";

const getSectorSpread = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSectorSpread: (...a: unknown[]) => getSectorSpread(...a),
  },
}));

import { SectorSpreadWidget } from "./SectorSpreadWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeRow(
  overrides: Partial<SectorRow> & { sector: string },
): SectorRow {
  return {
    weight_pct: 50,
    notional_local_approx: "10000.00",
    position_count: 1,
    ...overrides,
  };
}

function makeResponse(items: SectorRow[]): SectorSpreadResponse {
  return {
    title_nl: "Sector-verdeling",
    help_nl: "help",
    items,
    total_positions: items.reduce((s, r) => s + r.position_count, 0),
    has_unclassified: items.some((r) => r.sector.toLowerCase() === "onbekend"),
  };
}

beforeEach(() => {
  getSectorSpread.mockReset();
});

afterEach(() => cleanup());

describe("SectorSpreadWidget", () => {
  it("renders one bar per sector with the percentage", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ sector: "Technology", weight_pct: 66.7, position_count: 2 }),
        makeRow({ sector: "Healthcare", weight_pct: 33.3, position_count: 1 }),
      ]),
    });
    render(<SectorSpreadWidget />);
    expect(await screen.findByTestId("sector-bar-technology")).toBeInTheDocument();
    expect(screen.getByTestId("sector-bar-healthcare")).toBeInTheDocument();
    expect(
      screen.getByTestId("sector-bar-technology-pct").textContent,
    ).toContain("66,7");
  });

  it("renders the position count next to each sector label", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ sector: "Technology", position_count: 3, weight_pct: 100 }),
      ]),
    });
    render(<SectorSpreadWidget />);
    const bar = await screen.findByTestId("sector-bar-technology");
    expect(bar.textContent).toContain("3 posities");
  });

  it("singularises 'positie' when count is 1", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ sector: "Technology", position_count: 1 }),
      ]),
    });
    render(<SectorSpreadWidget />);
    const bar = await screen.findByTestId("sector-bar-technology");
    expect(bar.textContent).toContain("1 positie");
    expect(bar.textContent).not.toContain("1 posities");
  });

  it("shows the unclassified note when has_unclassified is true", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ sector: "Technology", weight_pct: 60 }),
        makeRow({ sector: "onbekend", weight_pct: 40 }),
      ]),
    });
    render(<SectorSpreadWidget />);
    await screen.findByTestId("sector-spread-list");
    expect(
      screen.getByTestId("sector-spread-unclassified-note"),
    ).toBeInTheDocument();
  });

  it("hides the unclassified note when has_unclassified is false", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([makeRow({ sector: "Technology", weight_pct: 100 })]),
    });
    render(<SectorSpreadWidget />);
    await screen.findByTestId("sector-spread-list");
    expect(
      screen.queryByTestId("sector-spread-unclassified-note"),
    ).toBeNull();
  });

  it("shows a Dutch empty state when no positions are present", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([]),
    });
    render(<SectorSpreadWidget />);
    expect(
      await screen.findByText("Nog geen posities"),
    ).toBeInTheDocument();
  });

  it("shows position-count chip in the panel head", async () => {
    getSectorSpread.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ sector: "Tech", position_count: 5, weight_pct: 100 }),
      ]),
    });
    render(<SectorSpreadWidget />);
    await screen.findByTestId("sector-bar-tech");
    expect(
      screen.getByTestId("sector-spread-widget").textContent,
    ).toContain("5 posities");
  });
});
