---
summary: After every push, reload HA core config and check logs — errors stay hidden until reload.
before_action:
  - About to push a config change that must take effect on HA
  - About to verify a config change live
on_symptom:
  - "config change pushed but behaviour unchanged"
  - "no error in HA but new YAML seems ignored"
  - "dashboard YAML edit pushed but the card/view still shows the old layout"
  - "template sensor is fresh but the dashboard table disagrees"
---

# Reload after push

HA auto-pulls the current git branch. Local edits are NOT live until pushed.

## Gotchas

- **Reload after every push.** Call `homeassistant.reload_core_config` (MCP/API) then check logs. Config errors stay invisible until a reload happens.
- **Push first when debugging with Playwright.** Edits aren't live pre-push; push, reload, then refresh the page.
- **YAML-mode Lovelace dashboards do NOT reload via any service.** `reload_core_config`, `reload_all`, browser hard-refresh, and nav-away-back all leave `dashboards/**/*.yaml` changes invisible — the running frontend keeps the dashboard parsed in memory from startup. Only `homeassistant.restart` picks up dashboard YAML edits. (Template sensors + automations DO reload via the normal services — so a profile sensor can read fresh while the dashboard table built from the same data stays stale. Confusing split; restart resolves it.)
