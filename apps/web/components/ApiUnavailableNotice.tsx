import { HelpText } from "@/components/HelpText";

export function ApiUnavailableNotice() {
  return (
    <article className="dashboard-card dashboard-card-error" role="status" aria-live="polite">
      <h3>API niet bereikbaar</h3>
      <p>De dashboardgegevens kunnen nu niet worden opgehaald.</p>
      <HelpText text="Start eerst de backend-API. Daarna vernieuw je deze pagina om de status te laden." />
    </article>
  );
}
