"""Task 132: Decision Package composition.

Public surface:

* :func:`compose_decision_package` — the pure composition function.
* :func:`compute_audit_trail_hash` — canonical SHA-256 of the package
  content (exposed for tests + downstream verification).
* :data:`GeblokkeerdForecastError` — raised by the composer when asked
  to compose for a ``Geblokkeerd`` forecast (caller bug).
"""

from portfolio_outlook_worker.decision_package.composer import (
    GeblokkeerdForecastError,
    compose_decision_package,
    compute_audit_trail_hash,
    evaluate_gates,
)
from portfolio_outlook_worker.decision_package.dutch_explanation_template import (
    render_explanation,
)

__all__ = [
    "GeblokkeerdForecastError",
    "compose_decision_package",
    "compute_audit_trail_hash",
    "evaluate_gates",
    "render_explanation",
]
