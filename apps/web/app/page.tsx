"use client";

/**
 * V1.2 §AF — Morning dashboard.
 *
 * Single-screen layout designed for the 07:00 Brussel check-in:
 * status strip → vandaag te doen + te keuren → portfolio KPI's →
 * profit-harvest cyclus + watchlist → doctrine output → open
 * orders + recent gebeurd. Detail-widgets blijven beschikbaar in
 * een collapsible blok eronder voor diepgaander spitten.
 */

import { BelgianTobYtdWidget } from "@/components/BelgianTobYtdWidget";
import { CalibrationCoverageBadge } from "@/components/CalibrationCoverageBadge";
import { EarningsThisWeekStrip } from "@/components/EarningsThisWeekStrip";
import { ForecastDaySummaryWidget } from "@/components/ForecastDaySummaryWidget";
import { LastVisitDiffStrip } from "@/components/LastVisitDiffStrip";
import { MarketHoursWidget } from "@/components/MarketHoursWidget";
import { MorningStatusStrip } from "@/components/MorningStatusStrip";
import { NavSparkline } from "@/components/NavSparkline";
import { OpenOrdersPanel } from "@/components/OpenOrdersPanel";
import { OrchestratorVerdictsSummary } from "@/components/OrchestratorVerdictsSummary";
import { PendingApprovalsPanel } from "@/components/PendingApprovalsPanel";
import { PortfolioKpiTiles } from "@/components/PortfolioKpiTiles";
import { PredictorPerformanceWidget } from "@/components/PredictorPerformanceWidget";
import { ProfitHarvestCycleWidget } from "@/components/ProfitHarvestCycleWidget";
import { RecentActivityPanel } from "@/components/RecentActivityPanel";
import { RecentDecisionsStrip } from "@/components/RecentDecisionsStrip";
import { ReconciliationStatusWidget } from "@/components/ReconciliationStatusWidget";
import { SchedulerStatusBadge } from "@/components/SchedulerStatusBadge";
import { TodayActionsPanel } from "@/components/TodayActionsPanel";
import { TodaysActionsCounter } from "@/components/TodaysActionsCounter";
import { TriageStrip } from "@/components/TriageStrip";
import { WatchlistSnapshot } from "@/components/WatchlistSnapshot";

export default function HomePage() {
  return (
    <main className="page-wrap">
      <MorningStatusStrip />
      <LastVisitDiffStrip />
      <EarningsThisWeekStrip />
      <TriageStrip />

      <section style={{ marginBottom: 12 }}>
        <ForecastDaySummaryWidget />
      </section>

      <div
        data-testid="morning-grid-top"
        style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 1fr",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <TodayActionsPanel />
        <PendingApprovalsPanel />
      </div>

      <PortfolioKpiTiles />

      <div
        data-testid="morning-grid-portfolio"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <ProfitHarvestCycleWidget />
        <WatchlistSnapshot />
      </div>

      <OrchestratorVerdictsSummary />

      <div
        data-testid="morning-grid-activity"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <OpenOrdersPanel />
        <RecentActivityPanel />
      </div>

      <BelgianTobYtdWidget />

      <details
        data-testid="morning-detail-archive"
        style={{
          marginTop: 8,
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: "8px 12px",
        }}
      >
        <summary
          style={{
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 13,
            color: "#374151",
          }}
        >
          Detail &amp; archief — losse widgets
        </summary>
        <div style={{ paddingTop: 12 }}>
          <TodaysActionsCounter />
          <section
            style={{
              marginBottom: "0.75rem",
              display: "flex",
              gap: 8,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <SchedulerStatusBadge />
            <CalibrationCoverageBadge />
          </section>
          <section style={{ marginBottom: "0.75rem" }}>
            <NavSparkline />
          </section>
          <section style={{ marginBottom: "0.75rem" }}>
            <MarketHoursWidget />
          </section>
          <section style={{ marginBottom: "0.75rem" }}>
            <RecentDecisionsStrip />
          </section>
          <section style={{ marginBottom: "0.75rem" }}>
            <ReconciliationStatusWidget />
          </section>
          <section style={{ marginBottom: "0.75rem" }}>
            <PredictorPerformanceWidget />
          </section>
        </div>
      </details>
    </main>
  );
}
