---
summary: Dashboard edits must end with a Playwright visual check; screenshots go in .playwright-mcp/.
before_action:
  - About to finish a dashboard edit
  - About to claim a dashboard change works
on_symptom:
  - "dashboard layout looks wrong or narrow"
  - "section renders blank"
  - "dashboard card shows old values after the pull landed"
  - "WS lovelace/config returns stale config"
---

# Playwright-validate dashboards

## Gotchas

- **End every dashboard edit with a Playwright visual check.** Non-visual checks alone aren't enough. Push first (edits aren't live until pushed), reload, then snapshot.
- **Save screenshots into `.playwright-mcp/` only**, never the repo root.
- **Dashboards live in `dashboards/{tablet,phone}.yaml`;** each view is a separate file included from the entrypoint. Tablet `home.yaml` uses `sections` layout.
- **HA caches the *parsed* YAML lovelace config in server memory.** The WS `lovelace/config` request — and the normal frontend render — return that cache, NOT the file on disk. After a pull lands new dashboard YAML, the config can keep returning OLD content for 30+ min. To read the current on-disk state you MUST force a re-read: `hass.connection.sendMessagePromise({type:'lovelace/config', url_path:'wall-tablet', force:true})`. A no-`force` read silently shows stale config — don't mistake it for git-pull lag (see [reload-after-push]).
- **Template *sensors* are not cached this way** — a chip reading a sensor updates as soon as the template reloads, while a markdown card in the same view stays stale until the lovelace parse is re-read. Disagreement between a chip and a card is the tell.
