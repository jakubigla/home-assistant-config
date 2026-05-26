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
  - "fix iterated several times but the change never appears on the dashboard"
---

# Reload after push

HA auto-pulls the current git branch. Local edits are NOT live until pushed.

## Gotchas

- **Reload after every push.** Call `homeassistant.reload_core_config` (MCP/API) then check logs. Config errors stay invisible until a reload happens.
- **`reload_core_config` and `template.reload` do NOT reload scripts or automations.** Each domain reloads independently: edited a script → call `script.reload`; edited an automation → call `automation.reload`; edited `template:` sensors → `template.reload`. Reloading only core+template leaves the OLD script/automation body running — it executes pre-edit logic (missing guards, stale durations) with no error, while template sensors correctly show the new values, so it looks like only part of the change landed (hit during garden cycle-and-soak: script ran its pre-guard version and opened a valve that should have been skipped). When unsure, reload all four or `homeassistant.restart`.
- **Push first when debugging with Playwright.** Edits aren't live pre-push; push, reload, then refresh the page.
- **Edits to an existing dashboard auto-reload — do NOT restart HA for them.** Changes to an already-registered `dashboards/**/*.yaml` are picked up after the push; a browser refresh shows them (force-refetch / nav away+back to beat frontend cache). Reserve `homeassistant.restart` for adding a **new** dashboard (a new `lovelace.dashboards.<key>` registration), which only loads on restart.
- **The git-pull addon is binary: it pulls continuously or not at all — there is NO interval lag.** A pushed change is on HA disk within seconds, OR the addon is off/broken/on the wrong branch and the change will NEVER arrive on its own. Don't wait out a phantom "pull window" — if a push isn't live after reload, check that the addon is actually running and tracking the branch you pushed. (A render once misdiagnosed as a nunjucks scoping bug was really the pull addon being off — the file never arrived, not "hadn't arrived yet".)
- **Verify what HA actually has on disk before re-editing.** Embed a unique marker in the edit, push, then confirm it landed on HA disk — don't trust the browser. Dashboards: read the live lovelace config over WebSocket (`lovelace/config` with `url_path`) and grep for the marker. Template sensors: render the sensor body via `POST /api/template` and compare. Marker present → verify render. Marker absent → pull is not running (or wrong branch); fix the addon, don't wait.
