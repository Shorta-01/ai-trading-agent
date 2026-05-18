import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Portfolio Outlook Manager",
  description: "Technische skeleton in papergeldmodus",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
