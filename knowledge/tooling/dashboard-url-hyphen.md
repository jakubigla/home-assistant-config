---
summary: Lovelace dashboard URL keys must contain a hyphen or HA rejects config load.
before_action:
  - About to add a lovelace dashboard under lovelace.dashboards
on_symptom:
  - "Url path needs to contain a hyphen"
  - "HA config load fails after adding a dashboard"
---

# Dashboard URL keys need a hyphen

## Gotchas

- **`lovelace.dashboards.<key>` must contain a hyphen** (e.g. `wall-tablet`, `mobile-phone`). `phone:` alone fails config load with "Url path needs to contain a hyphen".
