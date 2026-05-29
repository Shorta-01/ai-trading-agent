import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchSourceRecord } from "@/lib/apiClient";

const listResearchSources = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listResearchSources: (...a: unknown[]) => listResearchSources(...a),
    createResearchSource: vi.fn(),
    uploadResearchSourceFile: vi.fn(),
    getResearchSource: vi.fn(),
    getUrlMetadata: vi.fn(),
    getUserNote: vi.fn(),
    getLatestProcessingStatus: vi.fn(),
    getUploadedFileMetadata: vi.fn(),
    extractResearchSourceText: vi.fn(),
    createUrlMetadata: vi.fn(),
    createUserNote: vi.fn(),
  },
}));

import ResearchSourcesPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const SOURCE = {
  library_source_id: "src-1",
  title: "Jaarverslag ASML",
  asset_symbol: "ASML",
  source_kind: "document_metadata",
  document_type: "annual_report",
  status: "active",
  analysis_status: "pending",
} as unknown as ResearchSourceRecord;

beforeEach(() => listResearchSources.mockReset());
afterEach(() => cleanup());

describe("ResearchSourcesPage", () => {
  it("lists sources and reports storage available", async () => {
    listResearchSources.mockReturnValue(
      Promise.resolve({ ok: true as const, data: { records: [SOURCE] } }),
    );
    render(<ResearchSourcesPage />);
    expect(await screen.findByText("Jaarverslag ASML")).toBeInTheDocument();
    expect(
      screen.getByText("Onderzoeksbibliotheek: beschikbaar"),
    ).toBeInTheDocument();
    expect(screen.getByText("Opslagstatus: Beschikbaar")).toBeInTheDocument();
  });

  it("shows the 503 storage message", async () => {
    listResearchSources.mockReturnValue(
      Promise.resolve({ ok: false as const, status: 503, message: "x" }),
    );
    render(<ResearchSourcesPage />);
    expect(
      await screen.findByText(/De opslag is nog niet verbonden/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Onderzoeksbibliotheek: niet beschikbaar"),
    ).toBeInTheDocument();
  });

  it("shows the generic load-error message", async () => {
    listResearchSources.mockReturnValue(
      Promise.resolve({ ok: false as const, status: 500, message: "x" }),
    );
    render(<ResearchSourcesPage />);
    expect(
      await screen.findByText(/Onderzoeksbronnen konden niet geladen worden/),
    ).toBeInTheDocument();
  });
});
