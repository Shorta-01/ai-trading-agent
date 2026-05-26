# Bugs — populated in Phase 1d

## FIND-PIPAUDIT-001 — `fastapi==0.136.3` is a malicious release injecting an undocumented `fastar` dependency (MAL-2026-4750)

- **Tool:** `pip-audit 2.10.0`, raw output `/tmp/pip-audit-baseline.json` (T-054).
- **Package:** `fastapi`
- **Installed version:** `0.136.3`
- **Fixed version:** none listed by the advisory (the malicious release does not have a "fixed-in" pointer — the remediation is to pin away from `0.136.3`).
- **Advisory ID:** `MAL-2026-4750` (no CVE alias yet).
- **Project pin:** `apps/api/pyproject.toml:7` declares `"fastapi>=0.115.0"` with no upper bound. The unbounded `>=` resolved to the malicious `0.136.3` at install time.
- **Evidence (advisory body, abridged):**

  > "This release of fastapi 0.136.3 modifies pyproject.toml and PKG-INFO to add an undocumented dependency 'fastar>=0.9.0' to the [project.optional-dependencies] standard group … The README documents every other dependency in the [standard] group (httpx, jinja2, python-multipart, uvicorn, fastapi-cli, email-validator, pydantic-settings, pydantic-extra-types) but does not mention 'fastar'. Because the documented recommended install command is `pip install \"fastapi[standard]\"`, every user following the official documentation silently pulls the unrelated 'fastar' package onto their developer or CI machine. The name 'fastar' is a typosquat-shaped substitution against 'fastapi'/'fastapi-*' namespaces … Whoever controls 'fastar' on PyPI gains code execution at install time on a very large user base."

- **Why it matters (plain English):** the project pins `fastapi>=0.115.0` and resolved to the tainted `0.136.3`. The malicious payload only triggers when someone runs `pip install fastapi[standard]` (which pulls the typosquat `fastar` package as a "standard" extra). The project does **not** currently install with `[standard]` — `grep -rn "fastapi\[standard\]\|fastar"` across infra/docker, apps, packages, and `.github/workflows/` returned zero matches, and `pip show fastar` confirms it is not installed in the current venv. So the blast radius today is **theoretical**: any developer or CI run that hand-types `pip install fastapi[standard]` would silently pull the typosquat. The bare `fastapi` install path used by this project does not trigger the payload.

  However: the project is still running a release that the PyPA advisory database flags as malicious. The maintainer's PyPI account is implicitly compromised or hostile; future minor releases under the same line are not safe to trust by default.

- **Fix approach:**

  1. **Pin away from `0.136.3`** in `apps/api/pyproject.toml`: change `"fastapi>=0.115.0"` to a bounded range (e.g. `"fastapi>=0.115.0,<0.136"` or pin a specific known-clean version like `"fastapi==0.115.6"`).
  2. **Re-resolve** the venv (`pip install --upgrade fastapi`) to drop `0.136.3`.
  3. **Add a CI guard**: ensure `pip-audit` runs against the lockfile / resolved env at merge time so future malicious releases are caught before they land. (Out of scope for the fix itself — this is a separate Phase 4 task.)

- **Complexity:** small (one-line pyproject change + venv refresh).
- **Severity:** **high**. (Per the task spec, CVSS-missing defaults to medium; this finding is bumped to high because (a) the advisory is a confirmed malicious release rather than a regular CVE, (b) the project is actively running it, and (c) AGENTS.md's "No external API calls without documented adapter and test strategy" doesn't directly cover supply-chain but the spirit of the project's safety posture argues for prompt remediation.)
- **Related findings:** none — this is the only supply-chain advisory in the baseline. The four pip CVEs in the dismissed list are build-time-tool-only.
