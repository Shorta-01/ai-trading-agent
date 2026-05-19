import type { Metadata } from "next";

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
          <SystemEventsIndicator />
        </div>
        {children}
      </body>
    </html>
  );
}
