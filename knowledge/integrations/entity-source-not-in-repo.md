---
summary: Many entities come from integrations, not YAML — query live HA, don't grep the repo.
before_action:
  - About to check whether an entity exists
  - About to confirm an entity id before using it
on_symptom:
  - "entity not found by grepping the repo"
  - "automation references an entity absent from any YAML"
---

# Entities aren't all in the repo

## Gotchas

- **Query live HA for entity existence.** Use MCP / `hass-cli` / API — Zigbee, MQTT, Satel, HACS entities aren't referenced in any YAML here. Grepping the repo gives false negatives.
- **Escalation order:** MCP tools, then `/cli` (`hass-cli`), then `/api` (curl/websocat), then Playwright (last resort).
