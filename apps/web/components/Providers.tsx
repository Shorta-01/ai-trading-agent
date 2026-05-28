"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * App-wide TanStack Query provider. Server-state (data fetched from the
 * API) is owned by the query cache so multiple components that read the
 * same endpoint share one request + one poll cycle instead of each
 * running its own `setInterval` — meaningful on a single, modest Pi.
 *
 * Defaults are tuned for a single-user home dashboard: no retry storms,
 * no refetch-on-focus churn, a short stale window so repeat reads are
 * served from cache.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            refetchOnWindowFocus: false,
            staleTime: 15_000,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
