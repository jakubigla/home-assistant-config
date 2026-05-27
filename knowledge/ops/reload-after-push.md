---
summary: After every push, reload HA core config and check logs — errors stay hidden until reload.
before_action:
  - About to push a config change that must take effect on HA
  - About to verify a config change live
on_symptom:
  - "config change pushed but behaviour unchanged"
  - "no error in HA but new YAML seems ignored"
  - "script or automation still runs old behaviour after reload"
  - "template sensor updated but script/automation logic is stale"
  - "dashboard YAML edit pushed but the view still shows the old layout (try a force-refresh first)"
  - "edit pushed but still not live after reload + browser hard-refresh"
  - "new automation or script file shows MISSING on first reload right after push"
  - "fix iterated several times but the change never appears on the dashboard"
---

# Reload after push

HA auto-pulls the current git branch. Local edits are NOT live until pushed.

## Gotchas

- **Reload after every push.** Call `homeassistant.reload_core_config` (MCP/API) then check logs. Config errors stay invisible until a reload happens.
- **`reload_core_config` and `template.reload` do NOT reload scripts/automations.** Each domain reloads independently: script → `script.reload`, automation → `automation.reload`, `template:` sensors → `template.reload`. Reloading only core+template leaves the OLD script/automation body running — pre-edit logic, no error, while template sensors show new values, so only part of the change appears to land (a script once ran its pre-guard version and opened a valve that should have skipped). When unsure, reload all four or `homeassistant.restart`.
- **Push first when debugging with Playwright** — edits aren't live pre-push; push, reload, refresh.
- **Existing-dashboard edits auto-reload — do NOT restart for them.** An already-registered `dashboards/**/*.yaml` is picked up after push (browser force-refetch to beat frontend cache). `homeassistant.restart` is only for registering a NEW `lovelace.dashboards.<key>`.
- **The git-pull addon is binary — continuous or not at all, NO interval lag.** A push is on disk within seconds, OR the addon is off/broken/wrong-branch and the change NEVER arrives. Don't wait out a phantom pull window; not live after reload → check the addon is running and tracking your branch (a "nunjucks scoping bug" was once just the addon being off).
- **One exception to "no lag": the few-second post-push race.** A reload fired immediately after `git push` can beat the pull — a just-pushed NEW file shows MISSING on the first reload, present on a retry ~seconds later. **Retry the reload once before concluding the addon is broken.** Transient (retry fixes it) vs persistent broken-addon (retry never does).
- **Verify what HA has on disk before re-editing** — embed a unique marker, push, confirm it landed; don't trust the browser. Dashboards: WS `lovelace/config` (`url_path`, `force:true`) + grep. Template sensors: `POST /api/template` + compare. Marker absent → pull broken/wrong-branch, fix the addon.
