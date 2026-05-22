---
summary: Never push to main — feature branch + PR only.
before_action:
  - About to commit or push a config change
  - About to create a branch for new work
on_symptom:
  - "on main branch with local changes"
---

# Never push to main

## Gotchas

- **Never push to `main`.** Use a feature branch + PR. `no-commit-to-branch` pre-commit hook blocks direct commits to main/master.
