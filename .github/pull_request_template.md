## Summary
- 

## Testing
- [ ] domain
- [ ] storage
- [ ] portfolio
- [ ] api
- [ ] worker
- [ ] web

## CI pre-verification
- [ ] I verified there are no open PRs.
- [ ] I verified the latest `main` CI run is green.
- [ ] I verified all six required jobs passed on `main`: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- [ ] If direct verification was blocked, I included this exact note in the PR body:

> Pre-implementation CI was user-confirmed green, but Codex could not independently verify the latest main CI from this environment.

## Merge gate
- [ ] Do not merge until GitHub CI is green for this PR across all six jobs: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- [ ] If CI fails after PR creation, fix the failures in this same PR before merge.
