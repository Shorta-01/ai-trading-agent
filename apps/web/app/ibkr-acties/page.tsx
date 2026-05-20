import { EmptyState } from "@/components/EmptyState";

export default function Page() {
  return (
    <main className="page-wrap">
      <h2>Ibkr-acties</h2>
      <EmptyState title="Module in opbouw" message="Deze pagina toont later echte workflow-data zodra de benodigde runtime actief is." />
    </main>
  );
}
