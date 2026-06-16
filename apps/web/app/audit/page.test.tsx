import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  FreshnessAuditListResponse,
  ProviderSourceListResponse,
  RequestLogListResponse,
} from "@/lib/apiClient";

const getRequestAuditRequestLogs = vi.fn();
const getRequestAuditProviderSources = vi.fn();
const getRequestAuditFreshnessAudits = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRequestAuditRequestLogs: (...a: unknown[]) =>
      getRequestAuditRequestLogs(...a),
    getRequestAuditProviderSources: (...a: unknown[]) =>
      getRequestAuditProviderSources(...a),
    getRequestAuditFreshnessAudits: (...a: unknown[]) =>
      getRequestAuditFreshnessAudits(...a),
  },
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import AuditPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const EMPTY_LOGS = {
  items: [],
  total_count: 0,
  blocked_for_analysis_count: 0,
  blocked_for_suggestions_count: 0,
  blocked_for_action_drafts_count: 0,
} as unknown as RequestLogListResponse;
const EMPTY_SOURCES = {
  items: [],
  total_count: 0,
} as unknown as ProviderSourceListResponse;
const EMPTY_FRESH = {
  items: [],
  total_count: 0,
  blocked_for_analysis_count: 0,
  blocked_for_suggestions_count: 0,
  blocked_for_action_drafts_count: 0,
} as unknown as FreshnessAuditListResponse;

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => {
  getRequestAuditRequestLogs.mockReset();
  getRequestAuditProviderSources.mockReset();
  getRequestAuditFreshnessAudits.mockReset();
});
afterEach(() => cleanup());

describe("AuditPage", () => {
  it("renders the overview once all three lists load", async () => {
    getRequestAuditRequestLogs.mockReturnValue(ok(EMPTY_LOGS));
    getRequestAuditProviderSources.mockReturnValue(ok(EMPTY_SOURCES));
    getRequestAuditFreshnessAudits.mockReturnValue(ok(EMPTY_FRESH));
    render(<AuditPage />);
    expect(await screen.findByText("Read-only records: 0")).toBeInTheDocument();
  });

  it("stays on the loading state when a list fails", async () => {
    getRequestAuditRequestLogs.mockReturnValue(ok(EMPTY_LOGS));
    getRequestAuditProviderSources.mockReturnValue(fail());
    getRequestAuditFreshnessAudits.mockReturnValue(ok(EMPTY_FRESH));
    render(<AuditPage />);
    expect(await screen.findByText("Laden...")).toBeInTheDocument();
  });

  it("renders the IBKR-config audit-trail discovery card with link", async () => {
    // V1.2 §BZ vervolg: vanaf het audit-overzicht navigeert
    // operator/accountant naar de IBKR-config audit-trail.
    getRequestAuditRequestLogs.mockReturnValue(ok(EMPTY_LOGS));
    getRequestAuditProviderSources.mockReturnValue(ok(EMPTY_SOURCES));
    getRequestAuditFreshnessAudits.mockReturnValue(ok(EMPTY_FRESH));
    render(<AuditPage />);
    const card = await screen.findByTestId("audit-ibkr-config-card");
    expect(card).toBeInTheDocument();
    // Next.js Link forwarded data-testid is unreliable in jsdom; query
    // via the rendered anchor text.
    const link = screen.getByText(/Open IBKR-config audit-trail/);
    expect(link.getAttribute("href")).toBe("/admin/audit/ibkr-config");
  });
});
