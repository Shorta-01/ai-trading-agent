import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProviderSourceResponse } from "@/lib/apiClient";

const getRequestAuditProviderSource = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRequestAuditProviderSource: (...a: unknown[]) =>
      getRequestAuditProviderSource(...a),
  },
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ providerSourceId: "ps-1" }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import Page from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const RECORD = {
  provider_source_id: "ps-1",
  provider_code: "alpha",
  data_domain: "prices",
  disabled_at: null,
  disabled_reason: null,
} as unknown as ProviderSourceResponse;

beforeEach(() => getRequestAuditProviderSource.mockReset());
afterEach(() => cleanup());

describe("Provider-source detail page", () => {
  it("renders the record on success", async () => {
    getRequestAuditProviderSource.mockReturnValue(
      Promise.resolve({ ok: true as const, data: RECORD }),
    );
    render(<Page />);
    expect(await screen.findByText("ps-1")).toBeInTheDocument();
    expect(getRequestAuditProviderSource).toHaveBeenCalledWith("ps-1");
  });

  it("renders the unreachable fallback on failure", async () => {
    getRequestAuditProviderSource.mockReturnValue(
      Promise.resolve({ ok: false as const, reason: "not_reachable" }),
    );
    render(<Page />);
    expect(await screen.findByText("API niet bereikbaar.")).toBeInTheDocument();
  });
});
