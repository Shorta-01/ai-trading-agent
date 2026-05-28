"use client";

/**
 * Reports uncaught dashboard errors to the central error log so the badge +
 * panel cover browser-side failures too. Mounted once in the root layout.
 *
 * Best-effort + self-protecting: a failed report is swallowed (never reports
 * its own failure, which would loop).
 */

import { useEffect } from "react";

import { apiClient } from "@/lib/apiClient";

export function FrontendErrorReporter() {
  useEffect(() => {
    function report(
      message: string,
      stack: string | null,
      source: string,
    ): void {
      void apiClient
        .reportError({
          message: message.slice(0, 500) || "Onbekende frontend-fout",
          component: "dashboard",
          stack: stack,
          context: { source },
        })
        .catch(() => {});
    }

    function onError(event: ErrorEvent): void {
      report(
        event.message || "Onbekende frontend-fout",
        event.error?.stack ?? null,
        event.filename ? `${event.filename}:${event.lineno}` : "window.error",
      );
    }

    function onRejection(event: PromiseRejectionEvent): void {
      const reason = event.reason as { message?: string; stack?: string } | undefined;
      report(
        `Unhandled rejection: ${reason?.message ?? String(event.reason)}`,
        reason?.stack ?? null,
        "unhandledrejection",
      );
    }

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  return null;
}
