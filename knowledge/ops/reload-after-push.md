---
summary: After every push, reload HA core config and check logs — errors stay hidden until reload.
before_action:
  - About to push a config change that must take effect on HA
  - About to verify a config change live
on_symptom:
  - "config change pushed but behaviour unchanged"
  - "no error in HA but new YAML seems ignored"
---

# Reload after push

HA auto-pulls the current git branch. Local edits are NOT live until pushed.

## Gotchas

- **Reload after every push.** Call `homeassistant.reload_core_config` (MCP/API) then check logs. Config errors stay invisible until a reload happens.
- **Push first when debugging with Playwright.** Edits aren't live pre-push; push, reload, then refresh the page.
