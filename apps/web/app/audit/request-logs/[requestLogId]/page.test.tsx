import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RequestLogResponse } from "@/lib/apiClient";

const getRequestAuditRequestLog = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRequestAuditRequestLog: (...a: unknown[]) =>
      getRequestAuditRequestLog(...a),
  },
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ requestLogId: "rl-1" }),
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
  request_log_id: "rl-1",
  request_status: "completed",
  provider_code: "alpha",
  data_domain: "prices",
  created_at: "2026-05-28T10:00:00+00:00",
  safe_for_analysis: true,
} as unknown as RequestLogResponse;

beforeEach(() => getRequestAuditRequestLog.mockReset());
afterEach(() => cleanup());

describe("Request-log detail page", () => {
  it("renders the record on success", async () => {
    getRequestAuditRequestLog.mockReturnValue(
      Promise.resolve({ ok: true as const, data: RECORD }),
    );
    render(<Page />);
    expect(await screen.findByText("rl-1")).toBeInTheDocument();
    expect(getRequestAuditRequestLog).toHaveBeenCalledWith("rl-1");
  });

  it("renders the unreachable fallback on failure", async () => {
    getRequestAuditRequestLog.mockReturnValue(
      Promise.resolve({ ok: false as const, reason: "not_reachable" }),
    );
    render(<Page />);
    expect(await screen.findByText("API niet bereikbaar.")).toBeInTheDocument();
  });
});
