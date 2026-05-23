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

## Merge gate
- [ ] Do not merge unless this PR is green on all six required CI jobs.
- [ ] If CI is red, fix this same PR branch first; do not merge red.
- [ ] Separate repair PRs are only for accidentally already-merged broken `main`.

## Product tracking and safety
- [ ] Product tracking docs checked/updated (`current-state`, `task-history`, `version-1-backlog`, `version-1-scope-register`, `next-task`).
- [ ] Task queue / next-task alignment checked.
- [ ] No product safety boundary violated (no live trading, no auto-trading, no broker execution without explicit approval, no fake data).
