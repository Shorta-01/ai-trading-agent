import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Trading-Agent",
  description: "Moderne Nederlandstalige paper-only dashboard basis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
