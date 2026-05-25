import type { Metadata } from "next";
import Link from "next/link";

import { AccountModeBadge } from "@/components/AccountModeBadge";
import { ColdStartBanner } from "@/components/ColdStartBanner";
import { SystemEventsIndicator } from "@/components/SystemEventsIndicator";

import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Outlook Manager",
  description: "Modern dashboard foundation in eenvoudige Nederlandse taal",
};

const navItems = [
  ["/", "Dashboard"],
  ["/portefeuille", "Portefeuille"],
  ["/volglijst", "Volglijst"],
  ["/suggesties", "Suggesties"],
  ["/ibkr-acties", "IBKR Acties"],
  ["/onderzoek", "Onderzoek"],
  ["/historiek", "Historiek"],
  ["/audit", "Audit"],
  ["/instellingen", "Instellingen"],
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nl">
      <body>
        <div className="app-shell">
          <aside className="side-nav">
            <h1>Portfolio Outlook Manager</h1>
            <nav aria-label="Hoofdnavigatie">
              {navItems.map(([href, label]) => (
                <Link href={href} key={href}>{label}</Link>
              ))}
            </nav>
          </aside>
          <div className="main-area">
            <header className="top-status">
              <div>
                <p className="top-title">Release 1 dashboard</p>
                <p className="top-sub">Veilige basis zonder runtime-data.</p>
              </div>
              <div className="top-actions">
                <AccountModeBadge />
                <SystemEventsIndicator />
              </div>
            </header>
            <ColdStartBanner />
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
