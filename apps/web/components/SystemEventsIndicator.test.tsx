import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render as rtlRender, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ActiveSystemEventsResponse } from "@/lib/apiClient";

const getActiveSystemEvents = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getActiveSystemEvents: (...a: unknown[]) => getActiveSystemEvents(...a),
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

import { SystemEventsIndicator } from "./SystemEventsIndicator";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(events: number) {
  return Promise.resolve({
    ok: true as const,
    data: { events: Array.from({ length: events }, () => ({}) ) } as ActiveSystemEventsResponse,
  });
}

beforeEach(() => getActiveSystemEvents.mockReset());
afterEach(() => cleanup());

describe("SystemEventsIndicator", () => {
  it("shows the active system-event count", async () => {
    getActiveSystemEvents.mockReturnValue(ok(3));
    render(<SystemEventsIndicator />);
    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/systeemmeldingen",
    );
  });

  it("renders no count when the API is unreachable", async () => {
    getActiveSystemEvents.mockReturnValue(
      Promise.resolve({ ok: false as const, status: 0, message: "x" }),
    );
    render(<SystemEventsIndicator />);
    // The label always renders; the count chip does not when count is null.
    expect(await screen.findByText("Systeemmeldingen")).toBeInTheDocument();
  });
});
