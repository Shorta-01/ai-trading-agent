import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { PriceFreshnessBadge } from "./PriceFreshnessBadge";

afterEach(() => {
  cleanup();
});

describe("PriceFreshnessBadge", () => {
  it("renders the green Vers state when fresh", () => {
    render(<PriceFreshnessBadge freshness="fresh" />);
    const badge = screen.getByTestId("price-freshness-badge");
    expect(badge).toHaveAttribute("data-state", "fresh");
    expect(badge).toHaveTextContent("Vers");
  });

  it("renders the amber Verouderd state when stale", () => {
    render(<PriceFreshnessBadge freshness="stale" />);
    const badge = screen.getByTestId("price-freshness-badge");
    expect(badge).toHaveAttribute("data-state", "stale");
    expect(badge).toHaveTextContent("Verouderd");
  });

  it("renders the grey Niet beschikbaar state when unavailable", () => {
    render(<PriceFreshnessBadge freshness="unavailable" />);
    const badge = screen.getByTestId("price-freshness-badge");
    expect(badge).toHaveAttribute("data-state", "unavailable");
    expect(badge).toHaveTextContent("Niet beschikbaar");
  });
});
