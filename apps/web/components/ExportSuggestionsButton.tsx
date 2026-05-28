"use client";

import { decisionPackagesExportUrl } from "@/lib/apiClient";
import { cn } from "@/lib/cn";

/**
 * Downloads the latest system suggestions (buy/sell actions + full "why")
 * as a structured Markdown file. The backend serves the document with a
 * Content-Disposition: attachment header, so a plain anchor navigation
 * triggers a download the user can save or forward.
 *
 * Styled with Tailwind utilities — the first component on the new design
 * system (the rest still use inline styles until migrated).
 */
export function ExportSuggestionsButton({ className }: { className?: string }) {
  return (
    <a
      data-testid="export-suggestions-button"
      href={decisionPackagesExportUrl()}
      download
      className={cn(
        "inline-block rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white no-underline hover:bg-blue-800",
        className,
      )}
      title="Download alle actuele suggesties (koop/verkoop + volledige uitleg) als .md-bestand"
    >
      Exporteer suggesties (.md)
    </a>
  );
}
