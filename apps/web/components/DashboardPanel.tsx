import { ReactNode } from "react";
import { HelpTooltip } from "@/components/HelpTooltip";

export function DashboardPanel({ title, help, children }: { title: string; help: string; children: ReactNode }) {
  return (
    <section className="dashboard-panel">
      <header className="panel-head">
        <h2>{title}</h2>
        <HelpTooltip text={help} />
      </header>
      {children}
    </section>
  );
}
