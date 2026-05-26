# Dead Code — populated in Phase 1d

## FIND-VULTURE-001 — unsatisfiable `if False else` ternary in research-source reference validator

- **File:** `packages/domain/src/portfolio_outlook_domain/research_suggestions.py:281`
- **Tool:** `vulture 2.16`, raw output `/tmp/vulture-baseline.log` (T-052)
- **Evidence:**

  ```python
  # packages/domain/src/portfolio_outlook_domain/research_suggestions.py:278-285
  def _validate_reference(self) -> "ResearchSourceReference":
      if self.source_type in {
          ResearchSourceType.USER_URL,
          ResearchSourceType.WEBPAGE if False else ResearchSourceType.UNKNOWN,
      }:
          pass
      if (
          self.source_type
  ```

- **Why it matters (plain English):** the literal `if False else X` ternary always evaluates to `X` (here `ResearchSourceType.UNKNOWN`), so the `ResearchSourceType.WEBPAGE` branch is unreachable. The set always contains `{USER_URL, UNKNOWN}`. Already surfaced as an Open Question in `docs/reality/components/domain-research-and-suggestions.md` ("looks like leftover refactor"); independently confirmed by vulture at 100% confidence.
- **Fix approach:** drop the unreachable branch — replace with `ResearchSourceType.UNKNOWN` directly. If `WEBPAGE` was meant to be in the set, restore it; the comment context in the surrounding file suggests `WEBPAGE` belongs to a *different* enum (`ResearchDocumentType`), so the leftover form is genuinely dead.
- **Complexity:** trivial.
- **Severity:** low. The validator's `pass` body means the dead branch has no observable effect today — but it's a typed-enum red flag that will mislead future readers.
- **Related findings:** none yet; this is the only `unsatisfiable` finding emitted by vulture in this baseline.
