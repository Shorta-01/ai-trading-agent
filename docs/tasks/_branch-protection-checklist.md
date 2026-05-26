# Branch Protection Checklist

These settings cannot be configured from code. Apply them by hand in
GitHub once Phase 0 is merged.

**Repository:** `Shorta-01/ai-trading-agent`
**Target branch:** `main`
**Path in GitHub UI:** Settings → Branches → Branch protection rules → Add rule
(or edit the existing rule for `main`).

## Required settings

- [ ] **Branch name pattern:** `main`
- [ ] **Require a pull request before merging**
  - [ ] Required number of approvals before merging: at least 1
  - [ ] Dismiss stale pull request approvals when new commits are pushed: on
- [ ] **Require status checks to pass before merging**
  - [ ] Require branches to be up to date before merging: on
  - [ ] Required status checks (existing `ci.yml` jobs):
    - [ ] `domain`
    - [ ] `portfolio`
    - [ ] `storage`
    - [ ] `api`
    - [ ] `worker`
    - [ ] `web`
  - [ ] Do **not** yet require `python-health` or `web-health` from
        `code-health.yml`. These run in report-only mode during Phase 0
        and Phase 1; promote them to required only after Phase 1d
        baselining (see `docs/code-health/_tooling.md`).
- [ ] **Do not allow bypassing the above settings:** on
- [ ] **Restrict who can push to matching branches:** maintain default
      (no direct pushes to `main` outside of PR merges).
- [ ] **Allow force pushes:** off (no force pushes)
- [ ] **Allow deletions:** off (no deletions)

## Merge method

- [ ] **Allowed merge methods:** Squash merge only.
- [ ] **Default merge method:** Squash and merge.
- [ ] Set in: Settings → General → Pull Requests → uncheck "Allow merge
      commits" and "Allow rebase merging", leave "Allow squash merging"
      ticked, and set it as the default.

## After applying

- [ ] Confirm by opening a throwaway PR with a failing CI run and
      verifying that the merge button is blocked.
- [ ] Add a line to `docs/decisions/decision-log.md` noting the date
      the protection rules were applied and by whom.
