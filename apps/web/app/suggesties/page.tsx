/**
 * Task 132: Suggesties page — explainer-only empty state.
 *
 * The Suggesties grid is explicitly out of scope for V1.1.0 (Task 132
 * brief §Out of scope). Decision Packages are composed in the
 * background on every morning_briefing run; the user reaches them via
 * the "Bekijk Decision Package" button on each row in Volglijst.
 */

export default function Page() {
  return (
    <main className="page-wrap" data-testid="suggesties-page">
      <h2>Suggesties</h2>
      <p data-testid="suggesties-empty-state-explainer">
        Suggesties komen binnenkort. Decision Packages worden nu opgebouwd
        op de achtergrond. Bekijk individuele Decision Packages via de
        &quot;Bekijk Decision Package&quot; knop op elke voorspelling in
        Volglijst.
      </p>
    </main>
  );
}
