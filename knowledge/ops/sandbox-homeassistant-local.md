---
summary: Sandbox blocks homeassistant.local — curl against HA needs dangerouslyDisableSandbox.
before_action:
  - About to curl or websocat the HA instance
on_symptom:
  - "connection refused or blocked hitting homeassistant.local"
  - "curl to HA times out in sandbox"
---

# Sandbox + homeassistant.local

## Gotchas

- **Sandbox blocks `homeassistant.local`.** curl/websocat against HA needs `dangerouslyDisableSandbox: true` on the Bash call.
- **Env vars are preloaded via direnv.** Use `$HA_URL`, `$HA_TOKEN`, `$API_ACCESS_TOKEN` directly. `.env` reads are hook-blocked — never source the dotenv file.
