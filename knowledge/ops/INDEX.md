# ops/

<!-- LEAVES:START -->
- [never-push-main](never-push-main.md) — Never push to main — feature branch + PR only.
  - **before**: About to commit or push a config change; About to create a branch for new work
  - **symptom**: on main branch with local changes
- [reload-after-push](reload-after-push.md) — After every push, reload HA core config and check logs — errors stay hidden until reload.
  - **before**: About to push a config change that must take effect on HA; About to verify a config change live
  - **symptom**: config change pushed but behaviour unchanged; no error in HA but new YAML seems ignored; script or automation still runs old behaviour after reload; template sensor updated but script/automation logic is stale; dashboard YAML edit pushed but the view still shows the old layout (try a force-refresh first); edit pushed but still not live after reload + browser hard-refresh; new automation or script file shows MISSING on first reload right after push; fix iterated several times but the change never appears on the dashboard
- [sandbox-homeassistant-local](sandbox-homeassistant-local.md) — Sandbox blocks homeassistant.local — curl against HA needs dangerouslyDisableSandbox.
  - **before**: About to curl or websocat the HA instance
  - **symptom**: connection refused or blocked hitting homeassistant.local; curl to HA times out in sandbox
<!-- LEAVES:END -->
