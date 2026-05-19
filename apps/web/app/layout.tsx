import type { Metadata } from "next";
import Link from "next/link";

import { SystemEventsIndicator } from "@/components/SystemEventsIndicator";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Trading-Agent",
  description: "Moderne Nederlandstalige paper-only dashboard basis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nl">
      <body>
        <div className="top-nav">
          <nav className="main-nav" aria-label="Hoofdnavigatie">
            <Link href="/">Dashboard</Link>
            <Link href="/research-sources" title="Bewaar bronnen zoals notities, URL’s en documentmetadata die later kunnen helpen bij onderzoek. Deze bronnen zijn bewijs, geen handelsinstructies.">Onderzoeksbibliotheek</Link>
          </nav>
          <SystemEventsIndicator />
        </div>
        {children}
      </body>
    </html>
  );
}
