---
summary: A new !secret must be added to HA's own /config/secrets.yaml too — gitignored secrets.yaml never ships via git.
before_action:
  - About to add a new !secret reference to any YAML that gets pushed
  - About to add a rest/command_line/integration that pulls credentials or a URL from a secret
on_symptom:
  - "config reload returns HTTP 500 after a push that added a !secret"
  - "Secret <name> not defined"
  - "Failed to reload the Home Assistant Core configuration"
  - "new entities never appear after adding a !secret-backed sensor"
---

# Secret must exist on the HA box

## Gotchas

- **A new `!secret foo` only resolves against HA's OWN `/config/secrets.yaml`.** `secrets.yaml` is
  gitignored, so adding the key locally and pushing does NOT deliver it — add it on the HA box too
  (File Editor / SSH addon), or the reference is undefined there.
- **A missing secret fails the ENTIRE config reload, not just that entity.** `reload_core_config`
  (and every domain reload) returns HTTP 500 "Server got itself in trouble"; HA keeps the OLD config
  loaded, so NONE of the pushed changes go live — looks like a broad pull/reload failure, not a
  one-line typo. (Hit adding `garden_rain_url` for the Open-Meteo rest sensor.)
- **The real error is only in the supervisor core log**, not `/api/error_log` (404 on this setup)
  nor `system_log/list`. Fetch `GET /api/hassio/core/logs` and grep for
  `Secret <name> not defined`.
- **Always add the placeholder to `secrets.fake.yaml`** (committed) when adding the real key to
  `secrets.yaml` — that's the only git-visible record the key exists. Match the existing flat-key
  pattern (e.g. a full URL as one secret, like `twilio_calls_url`, since `!secret` interpolates a
  whole value and can't be spliced mid-string).
- Distinct from a stale pull / domain-reload miss — see **reload-after-push**. There the config is
  valid and loads; here it 500s and refuses to load at all.
