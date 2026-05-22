---
summary: Dashboard edits must end with a Playwright visual check; screenshots go in .playwright-mcp/.
before_action:
  - About to finish a dashboard edit
  - About to claim a dashboard change works
on_symptom:
  - "dashboard layout looks wrong or narrow"
  - "section renders blank"
---

# Playwright-validate dashboards

## Gotchas

- **End every dashboard edit with a Playwright visual check.** Non-visual checks alone aren't enough. Push first (edits aren't live until pushed), reload, then snapshot.
- **Save screenshots into `.playwright-mcp/` only**, never the repo root.
- **Dashboards live in `dashboards/{tablet,phone}.yaml`;** each view is a separate file included from the entrypoint. Tablet `home.yaml` uses `sections` layout.
