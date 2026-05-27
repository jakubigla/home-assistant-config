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

- **End every dashboard edit with a Playwright visual check.** Non-visual checks alone aren't
  enough. Push first (edits aren't live until pushed), reload, then snapshot.
- **Save screenshots into `.playwright-mcp/` only**, never the repo root.
- **Dashboards live in `dashboards/{tablet,phone}.yaml`;** each view is a separate file included
  from the entrypoint. Tablet `home.yaml` uses `sections` layout.
- **HA caches the *parsed* lovelace config in server memory** — WS `lovelace/config` and the
  frontend render return that cache, not disk, for 30+ min after a pull. Force a re-read:
  `sendMessagePromise({type:'lovelace/config', url_path:'wall-tablet', force:true})`. A no-`force`
  read silently shows stale config (cache, not a pull problem — pull is on-or-off; see
  **reload-after-push**).
- **Template *sensors* aren't cached this way** — a chip updates on `template.reload` while a
  markdown card in the same view stays stale until the parse is re-read. Chip-vs-card disagreement
  is the tell.
