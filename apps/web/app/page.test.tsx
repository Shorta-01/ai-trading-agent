import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

// The morning dashboard composes many self-fetching child widgets;
// stub them so this test only exercises page composition.
vi.mock("@/components/MorningStatusStrip", () => ({
  MorningStatusStrip: () => <div data-testid="stub-morning-status-strip" />,
}));
vi.mock("@/components/LastVisitDiffStrip", () => ({
  LastVisitDiffStrip: () => <div data-testid="stub-last-visit-diff-strip" />,
}));
vi.mock("@/components/EarningsThisWeekStrip", () => ({
  EarningsThisWeekStrip: () => <div data-testid="stub-earnings-this-week-strip" />,
}));
vi.mock("@/components/EarningsRefreshButton", () => ({
  EarningsRefreshButton: () => <div data-testid="stub-earnings-refresh-button" />,
}));
vi.mock("@/components/BelgianTobYtdWidget", () => ({
  BelgianTobYtdWidget: () => <div data-testid="stub-belgian-tob-ytd-widget" />,
}));
vi.mock("@/components/TriageStrip", () => ({
  TriageStrip: () => <div data-testid="stub-triage-strip" />,
}));
vi.mock("@/components/TodayActionsPanel", () => ({
  TodayActionsPanel: () => <div data-testid="stub-today-actions-panel" />,
}));
vi.mock("@/components/PendingApprovalsPanel", () => ({
  PendingApprovalsPanel: () => <div data-testid="stub-pending-approvals-panel" />,
}));
vi.mock("@/components/PortfolioKpiTiles", () => ({
  PortfolioKpiTiles: () => <div data-testid="stub-portfolio-kpi-tiles" />,
}));
vi.mock("@/components/ProfitHarvestCycleWidget", () => ({
  ProfitHarvestCycleWidget: () => (
    <div data-testid="stub-profit-harvest-cycle-widget" />
  ),
}));
vi.mock("@/components/WatchlistSnapshot", () => ({
  WatchlistSnapshot: () => <div data-testid="stub-watchlist-snapshot" />,
}));
vi.mock("@/components/OrchestratorVerdictsSummary", () => ({
  OrchestratorVerdictsSummary: () => (
    <div data-testid="stub-orchestrator-verdicts-summary" />
  ),
}));
vi.mock("@/components/OpenOrdersPanel", () => ({
  OpenOrdersPanel: () => <div data-testid="stub-open-orders-panel" />,
}));
vi.mock("@/components/RecentActivityPanel", () => ({
  RecentActivityPanel: () => <div data-testid="stub-recent-activity-panel" />,
}));
vi.mock("@/components/TodaysActionsCounter", () => ({
  TodaysActionsCounter: () => null,
}));
vi.mock("@/components/SchedulerStatusBadge", () => ({
  SchedulerStatusBadge: () => null,
}));
vi.mock("@/components/CalibrationCoverageBadge", () => ({
  CalibrationCoverageBadge: () => null,
}));
vi.mock("@/components/ForecastDaySummaryWidget", () => ({
  ForecastDaySummaryWidget: () => null,
}));
vi.mock("@/components/NavSparkline", () => ({
  NavSparkline: () => null,
}));
vi.mock("@/components/MarketHoursWidget", () => ({
  MarketHoursWidget: () => null,
}));
vi.mock("@/components/RecentDecisionsStrip", () => ({
  RecentDecisionsStrip: () => null,
}));
vi.mock("@/components/ReconciliationStatusWidget", () => ({
  ReconciliationStatusWidget: () => null,
}));
vi.mock("@/components/PredictorPerformanceWidget", () => ({
  PredictorPerformanceWidget: () => null,
}));

import HomePage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

afterEach(() => cleanup());

describe("HomePage (morning dashboard)", () => {
  it("renders the status strip and the top te-doen / te-keuren row", () => {
    render(<HomePage />);
    expect(
      screen.getByTestId("stub-morning-status-strip"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("morning-grid-top")).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-today-actions-panel"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-pending-approvals-panel"),
    ).toBeInTheDocument();
  });

  it("renders the portfolio KPI tiles and the profit-harvest + watchlist row", () => {
    render(<HomePage />);
    expect(
      screen.getByTestId("stub-portfolio-kpi-tiles"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("morning-grid-portfolio")).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-profit-harvest-cycle-widget"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("stub-watchlist-snapshot")).toBeInTheDocument();
  });

  it("renders the doctrine output summary and the activity row", () => {
    render(<HomePage />);
    expect(
      screen.getByTestId("stub-orchestrator-verdicts-summary"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("morning-grid-activity")).toBeInTheDocument();
    expect(screen.getByTestId("stub-open-orders-panel")).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-recent-activity-panel"),
    ).toBeInTheDocument();
  });

  it("exposes a collapsible Detail & archief section for the legacy widgets", () => {
    render(<HomePage />);
    const details = screen.getByTestId("morning-detail-archive");
    expect(details).toBeInTheDocument();
    expect(details.tagName.toLowerCase()).toBe("details");
    expect(details).toHaveTextContent("Detail");
  });

  it("renders the §AG follow-up surfaces (last-visit, earnings, TOB ytd)", () => {
    render(<HomePage />);
    expect(
      screen.getByTestId("stub-last-visit-diff-strip"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-earnings-this-week-strip"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("stub-belgian-tob-ytd-widget"),
    ).toBeInTheDocument();
  });
});
