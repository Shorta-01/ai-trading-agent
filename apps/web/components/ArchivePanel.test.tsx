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

const listArchive = vi.fn();
const generateArchive = vi.fn();
const archivePdfUrl = vi.fn().mockReturnValue("/archief.pdf");

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listArchive: (...a: unknown[]) => listArchive(...a),
    generateArchive: (...a: unknown[]) => generateArchive(...a),
    archivePdfUrl: (...a: unknown[]) => archivePdfUrl(...a),
  },
}));

import { ArchivePanel } from "./ArchivePanel";

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

beforeEach(() => {
  listArchive.mockReset();
  generateArchive.mockReset();
});

afterEach(() => cleanup());

describe("ArchivePanel", () => {
  it("shows empty state when no archives", async () => {
    listArchive.mockResolvedValue({
      ok: true as const,
      data: { title_nl: "", help_nl: "", items: [] },
    });
    render(<ArchivePanel defaultYear={2026} defaultMonth={5} />);
    expect(await screen.findByTestId("archive-empty")).toBeInTheDocument();
  });

  it("renders a row per archive entry", async () => {
    listArchive.mockResolvedValue({
      ok: true as const,
      data: {
        title_nl: "",
        help_nl: "",
        items: [
          {
            archive_id: "a1",
            year: 2026,
            month: 6,
            pdf_size_bytes: 50000,
            generated_at: "2026-07-01T08:00:00Z",
            source: "operator-manual",
          },
        ],
      },
    });
    render(<ArchivePanel defaultYear={2026} defaultMonth={5} />);
    expect(
      await screen.findByTestId("archive-row-2026-6"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("archive-download-2026-6"),
    ).toHaveAttribute("href", "/archief.pdf");
  });

  it("calls generateArchive when the button is clicked", async () => {
    listArchive.mockResolvedValue({
      ok: true as const,
      data: { title_nl: "", help_nl: "", items: [] },
    });
    generateArchive.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, archive_id: "x", pdf_size_bytes: 1024 },
    });
    render(<ArchivePanel defaultYear={2026} defaultMonth={5} />);
    await screen.findByTestId("archive-empty");
    fireEvent.click(screen.getByTestId("archive-generate-button"));
    await waitFor(() => {
      expect(generateArchive).toHaveBeenCalledWith({ year: 2026, month: 5 });
    });
  });

  it("shows an error when generation fails", async () => {
    listArchive.mockResolvedValue({
      ok: true as const,
      data: { title_nl: "", help_nl: "", items: [] },
    });
    generateArchive.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<ArchivePanel defaultYear={2026} defaultMonth={5} />);
    await screen.findByTestId("archive-empty");
    fireEvent.click(screen.getByTestId("archive-generate-button"));
    expect(await screen.findByTestId("archive-error")).toHaveTextContent(
      "mislukt",
    );
  });
});
