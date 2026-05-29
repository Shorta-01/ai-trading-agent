import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { FreshnessAuditResponse } from "@/lib/apiClient";

const getRequestAuditFreshnessAudit = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRequestAuditFreshnessAudit: (...a: unknown[]) =>
      getRequestAuditFreshnessAudit(...a),
  },
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ freshnessAuditId: "fa-1" }),
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
  freshness_audit_id: "fa-1",
  freshness_status: "fresh",
  reason_code: null,
  data_domain: "prices",
  evaluated_at: "2026-05-28T10:00:00+00:00",
  source_timestamp: null,
  safe_for_analysis: true,
} as unknown as FreshnessAuditResponse;

beforeEach(() => getRequestAuditFreshnessAudit.mockReset());
afterEach(() => cleanup());

describe("Freshness-audit detail page", () => {
  it("renders the record on success", async () => {
    getRequestAuditFreshnessAudit.mockReturnValue(
      Promise.resolve({ ok: true as const, data: RECORD }),
    );
    render(<Page />);
    expect(await screen.findByText("fa-1")).toBeInTheDocument();
    expect(getRequestAuditFreshnessAudit).toHaveBeenCalledWith("fa-1");
  });

  it("renders the unreachable fallback on failure", async () => {
    getRequestAuditFreshnessAudit.mockReturnValue(
      Promise.resolve({ ok: false as const, reason: "not_reachable" }),
    );
    render(<Page />);
    expect(await screen.findByText("API niet bereikbaar.")).toBeInTheDocument();
  });
});
