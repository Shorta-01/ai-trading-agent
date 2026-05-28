"use client";

import { decisionPackagesExportUrl } from "@/lib/apiClient";

/**
 * Downloads the latest system suggestions (buy/sell actions + full "why")
 * as a structured Markdown file. The backend serves the document with a
 * Content-Disposition: attachment header, so a plain anchor navigation
 * triggers a download the user can save or forward.
 */
export function ExportSuggestionsButton() {
  return (
    <a
      data-testid="export-suggestions-button"
      href={decisionPackagesExportUrl()}
      download
      style={{
        display: "inline-block",
        padding: "8px 16px",
        background: "#1d4ed8",
        color: "#ffffff",
        borderRadius: 6,
        fontWeight: 600,
        textDecoration: "none",
        fontSize: 14,
      }}
      title="Download alle actuele suggesties (koop/verkoop + volledige uitleg) als .md-bestand"
    >
      Exporteer suggesties (.md)
    </a>
  );
}
