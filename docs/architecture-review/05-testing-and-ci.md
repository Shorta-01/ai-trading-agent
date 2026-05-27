# Architecture Review 05 — Testing and CI

**Scope.** Verdict-driven assessment of the test suite + CI pipeline. 8 architectural questions covering test volume, real-vs-mock discipline, shared fixtures, coverage measurement, parallelism, test categorisation, CI structure, and frontend test mix. Recommendations belong in Track 1c.

**Reality docs referenced**: T-009 (CI inventory + Docker layout), T-050-T-058 (per-tool code-health baselines), T-059 (master findings), T-036 §5 (per-app CI verdicted acceptable), T-037 §1+§3 (Python 3.12 + mypy --strict verdicted state-of-the-art).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | 240-file / 56k-LOC Python test suite (1.8× test:source ratio) | **State-of-the-art** |
| 2 | Real-implementation discipline (3 of 240 tests use mocks, ~1%) | **State-of-the-art** |
| 3 | Zero `conftest.py` files (no shared fixtures) | **Outdated** |
| 4 | No code coverage measurement (no `coverage.py` / `pytest-cov` / no CI gate) | **Risky** |
| 5 | No test parallelism (no pytest-xdist; Playwright `workers=1`) | **Outdated** |
| 6 | Only `pytest.mark.parametrize`; no custom markers | **Acceptable** |
| 7 | CI 10-job matrix (8 ci.yml + 2 code-health.yml) + 3-attempt checkout retry | **Acceptable** |
| 8 | Frontend test split: Vitest unit + Playwright e2e + no contract / visual / a11y | **Acceptable** |

**Distribution**: 2 state-of-the-art + 3 acceptable + 2 outdated + 1 risky. Heavy "acceptable" + standout state-of-the-art in test volume + discipline.

## 1. 240-file / 56k-LOC Python test suite (1.8× test:source ratio)

### Current implementation

Grep proof:
- `find apps/api/tests apps/worker/tests packages/*/tests -name "test_*.py" | wc -l` → **240** Python test files.
- Total LOC: **56,462** across those 240 files.
- Source LOC across the same packages (apps/api/src + apps/worker/src + packages/{domain,portfolio,storage}/src per T-001-T-007): ~31,000 LOC estimated.
- Ratio: **~1.82× test code per source line.**

For comparison: industry-typical test:source ratios are 0.5-1.5×. Codebases with safety-critical or financial logic frequently push 2-3×.

Plus frontend:
- 11 Vitest unit test files (`apps/web/components/*.test.tsx`).
- 8 Playwright e2e specs (`apps/web/tests/e2e/*.spec.ts`).

Test discovery via the per-package `[tool.pytest]` config in each `pyproject.toml`.

### State-of-the-art alternative

The 1.8× ratio IS state-of-the-art for financial-system Python. Higher ratios (2-3×) exist but trade off against maintenance cost. Some teams use:
- **Property-based testing** (`hypothesis`) — single test file generates thousands of cases. Reduces test file count but increases per-test execution cost.
- **Fuzzing** (`atheris`) — random input generation. Niche.

The current approach is example-based (`@pytest.mark.parametrize`) + a few property-test patterns via parametrize sweeps.

### Verdict — State-of-the-art

The volume signals serious investment in test coverage. The ratio (~1.82×) is at the high end of typical for the codebase's domain (financial / trading).

T-051's `mypy --strict` baseline passing 0 errors across 198 source files demonstrates that the test discipline is matched by type discipline.

### Performance implication

56k LOC of tests run sequentially: ~5-15 minutes for the full suite (estimate). Per-package CI parallelism (§7) brings this to ~3 minutes wall-clock at the slowest job.

### Improvement direction (for Track 1c)

None on volume. Optional: add `hypothesis` for the Decimal math + ladder of edge cases in `packages/portfolio/src/.../belgian_tax.py`. Track 1c.

## 2. Real-implementation discipline (3 of 240 tests use mocks)

### Current implementation

Grep proof:
- `grep -rln "unittest.mock\|@patch\|MagicMock\|Mock(" apps/api/tests apps/worker/tests packages/*/tests | wc -l` → **3** files.
- **3 of 240 test files** use mocks. **~1.25% mock ratio**.

The 237 other test files exercise:
- Real Pydantic models (per T-001 / T-002).
- Real SQLAlchemy queries against real SQLite (in-memory) or Postgres (Testcontainers — not currently configured but the patterns support it).
- Real `Decimal` math.
- Real Alembic migrations applied to the test DB on setup.
- Real worker orchestrator paths.

The few mocks: where the boundary is genuinely external — e.g., IBKR adapter (mocked because `ibapi` requires a TWS connection), Anthropic SDK (mocked because real calls would burn budget), EODHD HTTP (mocked because rate-limited).

This is documented across T-019 (real `place_order` test pattern), T-020 (real reconciliation Pass A/B/C against test fixtures), T-022 (real `compute_tob` arithmetic).

### State-of-the-art alternative

Two opposing schools in Python testing:
- **London school** (mock-heavy): unit tests mock everything outside the unit under test. Fast, fragile to refactors.
- **Detroit / Chicago school** (real-impl): test the system end-to-end with real collaborators. Slower per test, robust to refactors.

In 2025 Python, both are accepted. For financial systems, real-impl is preferred because **mock drift** is a silent risk — a mock for `Decimal` math that returns the wrong rounding hides the bug.

### Verdict — State-of-the-art

The 1% mock ratio is **extraordinary** for a codebase of this size. The codebase tests with real Pydantic, real SQLAlchemy, real Decimal math, real Alembic migrations. This is the **strongest single testing-discipline signal in the audit**.

The trade-offs:
- Tests are slower (every test sets up a fresh SQLite DB + applies 53 migrations).
- Tests catch real bugs (no mock-drift hiding bad behavior).
- Refactors don't break test count linearly (real-impl tests survive method renames).

T-019 + T-020 documented end-to-end submission-sweep tests + reconciliation-pass tests that exercise the actual state machines + actual DB writes. These are the kinds of tests that would be near-impossible with London-school mocking.

### Performance implication

Slower per-test (DB setup is heavy). Per-suite, the difference is bounded — 240 files × ~1 second setup each = ~4 minutes. CI parallelism (§7) absorbs this at the job level.

### Improvement direction (for Track 1c)

None. This is the gold standard for financial Python testing. Phase 1c should explicitly NOT recommend adding more mocks.

## 3. Zero `conftest.py` files (no shared fixtures)

### Current implementation

Grep proof:
- `find apps packages -name "conftest.py" | wc -l` → **0**.

**No `conftest.py` files exist anywhere in the test directories.** Pytest's standard shared-fixture mechanism is not used.

Consequences observed across test files:
- Each test file constructs its own SQLite engine + applies migrations + seeds test data inline.
- The same setup boilerplate appears across many test files (e.g., creating a test action draft, seeding the database).
- Pytest auto-discovers fixtures only within the test file or imported helpers; no shared fixture imports between files.

T-009 inventory didn't surface a "test helpers" module that imports across packages. Each package's `tests/` is self-contained.

### State-of-the-art alternative

The pytest-canonical pattern:
- `conftest.py` at the repo root or per-test-directory.
- Fixtures defined once: `@pytest.fixture def test_db()`, `@pytest.fixture def sample_action_draft()`.
- Test files just declare `def test_foo(test_db, sample_action_draft)` — pytest auto-injects.

Mid-size codebases typically have 3-10 fixtures in `conftest.py`. Larger codebases have nested conftest.py per subdirectory.

### Verdict — Outdated

Zero shared fixtures is unusual at this codebase size. The cost is **duplication**:
- N test files each setting up a SQLite engine = N copies of engine-setup code.
- Maintenance: a change to test-setup convention requires touching all 240 files instead of one `conftest.py`.

The codebase's real-impl discipline (§2) magnifies the duplication: every test does heavy setup, and that setup is repeated everywhere.

The pattern isn't broken — tests run, tests pass — but the code organisation is 2010-pytest-tutorial style, not modern pytest. T-051's 0-error baseline is achieved despite this, not because of it.

### Performance implication

Inline setup means more per-test cost. With shared fixtures + `scope="session"` or `scope="module"`, expensive setup (DB schema apply) happens once per session, not once per test.

A `conftest.py` with `@pytest.fixture(scope="session") def engine_with_schema()` could plausibly halve the wall-clock test runtime.

### Improvement direction (for Track 1c)

Add per-package `conftest.py` with the shared SQLite engine + migration apply + common record factories. Migration is incremental — old tests work, new tests use fixtures.

## 4. No code coverage measurement

### Current implementation

Grep proof:
- `grep -rln "coverage\|pytest-cov" pyproject.toml apps/*/pyproject.toml packages/*/pyproject.toml .github/workflows/` → **0** matches.
- No `coverage.py` in any dependency declaration.
- No `pytest-cov` in any dev-dependencies.
- No `--cov` flags in CI commands.

The codebase has 240 test files and 56k LOC of tests but **no measurement of which source lines those tests actually exercise**.

T-052 (vulture) baseline detected dead code via static analysis, but vulture only catches structural dead code (functions never referenced), not "tested-only-via-happy-path-not-the-error-branch" dead coverage.

### State-of-the-art alternative

- **`coverage.py` + `pytest-cov`**: industry standard. Reports per-line, per-branch coverage.
- **CI gate**: `coverage report --fail-under=80` aborts CI if coverage drops below threshold.
- **Codecov / Coveralls**: external services for coverage history + PR-diff coverage.
- **Mutation testing** (`mutmut`, `cosmic-ray`): tests whether the tests actually catch bugs (kill mutations). Stronger signal than line coverage.

For a financial system in 2025, some form of coverage measurement is mainstream.

### Verdict — Risky

Two risks:
1. **Unknown coverage of the order-execution path**: T-019 documented the submitter + 12 Tier-1 gates. Are all 12 gates tested in all combinations? Without coverage, unknown. T-019 tests show happy-path + a few failure paths; full combinatoric coverage is impossible to verify.
2. **Regression-detection blindspot**: a refactor that accidentally removes a code path won't fail tests (the tests don't exercise that path); coverage drop would catch it.

The high mock ratio (§2) means most code paths ARE exercised end-to-end, partially mitigating this risk. But "most paths" without measurement isn't "all paths".

### Performance implication

Adding coverage measurement adds ~10-30% to test runtime. Negligible compared to the test suite's own duration.

### Improvement direction (for Track 1c)

Add `coverage.py` + `pytest-cov`. Set a baseline (whatever the suite measures today) + a CI gate that prevents regression. Track 1c.

## 5. No test parallelism

### Current implementation

Grep proof:
- `grep -l "pytest-xdist" apps/api/pyproject.toml apps/worker/pyproject.toml packages/*/pyproject.toml` → 0 matches.
- CI commands: `pytest -q` or `cd ... && pytest` — no `-n auto` flag.
- `apps/web/playwright.config.ts:11` — `workers: 1` (single Playwright worker).
- `apps/web/vitest.config.ts` — no `poolOptions.threads` or `--max-workers` config; Vitest's default (uses worker threads, but limited by I/O of jsdom).

CI achieves parallelism at the **job level** (per-package; §7), not at the test level within each job.

### State-of-the-art alternative

- **pytest-xdist**: `pytest -n auto` distributes tests across CPU cores. Most Python codebases use this for suites >100 files.
- **Playwright workers**: default is number of CPU cores. Setting `workers: 1` deliberately serialises e2e tests.
- **Vitest parallel**: enabled by default; the codebase uses defaults.

The deliberate `workers: 1` in Playwright suggests intent — e2e tests likely share state (test database, login session) and can't safely parallelise. Documented in `playwright.config.ts:13` comment: "One browser (chromium) keeps CI fast" — but workers=1 is about parallelism, not browser count.

### Verdict — Outdated

The lack of pytest-xdist is the biggest miss. With 240 test files, parallel execution would cut the per-job CI time significantly (4-8 CPU cores ÷ sequential = ~1/4 to 1/8 the wall-clock).

The Playwright `workers: 1` is defensible if e2e tests share state, but the choice should be documented + revisited. T-009 didn't surface a shared-state reason.

### Performance implication

**Significant CI cost**. Each per-package job (§7) runs its tests sequentially. The slowest job (likely `api` with the most tests) bounds the CI wall-clock. With xdist, the slowest job could be ~50% faster.

Across the 8 jobs running in parallel at the CI matrix level, the absolute saving is small — the suite is already parallel at job level. But local dev (`make test`) is fully sequential and would benefit significantly.

### Improvement direction (for Track 1c)

Add `pytest-xdist` to dev-dependencies. Set `addopts = "-n auto"` per pyproject. Verify e2e tests can parallelise (add `workers: auto` in playwright.config.ts if they can). Track 1c.

## 6. Only `pytest.mark.parametrize`; no custom markers

### Current implementation

Grep proof:
- `grep -rn "@pytest.mark" apps/api/tests apps/worker/tests packages/*/tests` → all matches are `@pytest.mark.parametrize`.
- No `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.ibkr`, `@pytest.mark.e2e`, or any custom markers.
- No `[tool.pytest.ini_options] markers = [...]` declarations in pyproject files.

All 240 tests are treated equivalently. Running `pytest` runs all of them. There is no fast-feedback subset.

### State-of-the-art alternative

The pytest-canonical markers pattern:
- `@pytest.mark.slow` — tests that take >1 second. Excluded from fast CI runs.
- `@pytest.mark.integration` — tests requiring external services (IBKR, DB, etc.).
- `@pytest.mark.unit` — pure-Python tests.
- CI runs `pytest -m unit` for fast feedback, then `pytest -m "not slow"` for the full suite, then `pytest` (everything including slow) on merge.

For a codebase with real-impl tests (§2) that include DB setup, the slow / fast distinction matters.

### Verdict — Acceptable

The current model — all tests are equal — works for the codebase's scale. With 240 tests running in ~3-5 minutes per job, there's no urgent need for a fast subset.

The trade-off becomes meaningful if/when:
- A specific subset of tests becomes very slow (e.g., a 30-second test that runs on every PR).
- Developers want sub-minute feedback on the local dev cycle.

Currently, neither is documented.

### Performance implication

None at current scale.

### Improvement direction (for Track 1c)

Optional: add `@pytest.mark.slow` for tests >1 second + a `pytest -m "not slow"` fast-CI path. Useful only if test duration becomes a pain point.

## 7. CI 10-job matrix + 3-attempt checkout retry

### Current implementation

`.github/workflows/ci.yml`:
- 8 jobs: `domain`, `portfolio`, `storage`, `api`, `worker`, `web` + 2 setup jobs.
- Each job: 3-attempt `actions/checkout@v4` retry (T-009 inventory documented this pattern explicitly).
- Each job: setup-python or setup-node + install + run.
- Per-job `working-directory: packages/<x>` or `apps/<y>`.

`.github/workflows/code-health.yml`:
- 2 jobs running the code-health tool baselines.

The 3-attempt checkout retry is unusual — defends against GitHub's transient checkout failures. T-009 §3 documented this as a pattern.

### State-of-the-art alternative

- **GitHub Actions Matrix strategy**: `strategy.matrix.package: [domain, portfolio, ...]` collapses 8 jobs into 1 matrix-driven definition. Less YAML duplication.
- **Reusable workflows**: `workflows/python-package-test.yml` called from each per-package job. Centralises setup logic.
- **Concurrency groups**: cancel-in-progress for PR updates. Standard for high-PR-volume repos.

The current per-job copy-paste is verbose but readable. T-036 §5 already verdicted this as "acceptable" at the CI level.

### Verdict — Acceptable

The 10-job CI structure works. The 3-attempt checkout retry is **smart defensive engineering** — most codebases don't bother and occasionally suffer flaky CI from GitHub Actions transient failures. T-009 inventory confirmed this pattern.

Limitations:
- YAML duplication across 8 jobs (~30 LOC each = ~240 LOC of near-identical YAML).
- No `paths-filter` on the per-job triggers — every PR runs all 10 jobs even if only the frontend changed. Wasteful for trivial PRs.

### Performance implication

CI wall-clock bounded by the slowest job. With 8 jobs running in parallel, total cost is ~slowest-job × 8 (parallel utilisation). GitHub bills minutes per job.

### Improvement direction (for Track 1c)

Optional: matrix strategy for DRY-ness; `paths-filter` for skipping unaffected jobs. Track 1c.

## 8. Frontend test split: Vitest unit + Playwright e2e + no contract / visual / a11y

### Current implementation

- **Vitest unit tests**: 11 files (`apps/web/components/*.test.tsx`) — React component rendering + interaction.
- **Playwright e2e**: 8 spec files (`apps/web/tests/e2e/*.spec.ts`) — full-stack against `npm run build` + `next start`.
- `apps/web/vitest.config.ts` — jsdom environment + setupFiles.
- `apps/web/playwright.config.ts` — chromium only + workers=1 + 60s timeout.

**Missing frontend test types**:
- **Contract tests** (between TS + Python types): per T-038 §6, `apiClient.ts` re-declares Python Pydantic response types manually. No automated check that the TS types match the API responses.
- **Visual regression** (Chromatic, Percy): no snapshot-based UI testing.
- **Accessibility tests** (`@axe-core/playwright`, `pa11y`): no automated a11y assertions.

### State-of-the-art alternative

A mature 2025 frontend test pyramid:
- Unit (Vitest): individual components in isolation.
- Integration: component composition + state management.
- Contract: API request/response schemas match.
- Visual regression: snapshot per-page or per-component.
- E2E: critical user flows end-to-end.
- A11y: every page passes WCAG AA.

The current split covers unit + e2e but skips the middle three. Contract testing is the most-relevant miss given T-038 §6's hand-typed apiClient.

### Verdict — Acceptable

8 Playwright e2e tests is a respectable smoke suite. 11 Vitest unit tests is light for 48 components but adequate for the highest-risk components.

The missing test types are tier-2 concerns. The codebase isn't broken; it's just at the "we have tests" level, not the "we have all the kinds of tests" level.

### Performance implication

Vitest: ~10-30 seconds for unit tests. Playwright: ~2-5 minutes for 8 e2e specs (workers=1 makes this sequential). Acceptable.

### Improvement direction (for Track 1c)

Highest-value addition: contract tests via OpenAPI schema validation (couples with T-038 §6 OpenAPI codegen). Track 1c.

## 9. Observations across the 8 questions

### 9.1 Pattern: discipline at the test layer; infrastructure-debt at the support layer

Mirroring T-039's data-layer pattern: the tests themselves are rigorous and disciplined (real-impl, 1.8× ratio); the supporting infrastructure (conftest, coverage, parallelism) is missing or 2010-era.

### 9.2 Pattern: real-impl testing is unusually strong

The 1% mock ratio is the audit's strongest single "we know what we're doing" signal in any layer. T-019, T-020, T-022, T-023 all rely on real-impl tests that exercise actual state machines + actual DB writes. This is the testing equivalent of T-039's Decimal-as-string discipline.

### 9.3 Pattern: no measurement layer

No coverage tooling (§4) means the test surface is unmeasured. Combined with no markers (§6), there's no way to slice or filter the test suite. The discipline + volume are there; the observability isn't.

### 9.4 What's clearly good

- 240-file Python test suite + 1.8× test:source ratio.
- 1% mock ratio (real-implementation discipline).
- `mypy --strict` everywhere passing 0 errors (T-051).
- CI 3-attempt checkout retry (smart defensive engineering).

### 9.5 What's clearly outdated

- Zero `conftest.py` (no shared fixtures despite 240 test files).
- No test parallelism (no pytest-xdist; Playwright workers=1).

### 9.6 What's risky

- No code coverage measurement → unknown which code paths are tested.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | 240-file test suite | State-of-the-art | None |
| 2 | Real-impl discipline | State-of-the-art | None (DO NOT add mocks) |
| 3 | Zero `conftest.py` | Outdated | **Medium** (shared fixtures) |
| 4 | No coverage | **Risky** | **High** (CI gate) |
| 5 | No parallelism | Outdated | Medium (pytest-xdist) |
| 6 | No custom markers | Acceptable | Low |
| 7 | 10-job CI matrix + retry | Acceptable | Low (matrix DRY) |
| 8 | Vitest + Playwright + no contract | Acceptable | Medium (OpenAPI contract tests, couples with T-038 §6) |

**Recommendations deferred to Track 1c.**

## 11. References

- `apps/api/tests/`, `apps/worker/tests/`, `packages/{domain,portfolio,storage}/tests/` — 240 test files, 56k LOC
- `apps/web/components/*.test.tsx` — 11 Vitest unit tests
- `apps/web/tests/e2e/*.spec.ts` — 8 Playwright e2e specs
- `apps/web/vitest.config.ts` — jsdom + setupFiles
- `apps/web/playwright.config.ts` — chromium + workers=1 + 60s timeout
- `.github/workflows/ci.yml` — 8 per-package jobs + 3-attempt checkout retry
- `.github/workflows/code-health.yml` — 2 baseline jobs
- T-009 `build-ci-and-scripts.md` (CI inventory + retry pattern)
- T-036 §5 (per-app CI jobs already verdicted acceptable)
- T-037 §3 (mypy --strict already verdicted state-of-the-art)
- T-038 §6 (apiClient.ts hand-typed — drives §8 contract-test gap)
- T-050-T-058 (per-tool code-health baselines)
- T-051 `mypy --strict` baseline (0 errors across 198 source files)
- T-059 master findings consolidation
- T-019 / T-020 / T-022 / T-023 — examples of real-impl tests exercising state machines
