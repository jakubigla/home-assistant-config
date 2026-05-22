# tooling/

<!-- LEAVES:START -->
- [dashboard-url-hyphen](dashboard-url-hyphen.md) — Lovelace dashboard URL keys must contain a hyphen or HA rejects config load.
  - **before**: About to add a lovelace dashboard under lovelace.dashboards
  - **symptom**: Url path needs to contain a hyphen; HA config load fails after adding a dashboard
- [mushroom-visibility-gotcha](mushroom-visibility-gotcha.md) — Avoid mutually-exclusive visibility pairs on mushroom-template-cards; a crashing card kills its section.
  - **before**: About to add conditional visibility to a mushroom card; About to add a mass-player-card or other crash-prone card
  - **symptom**: section renders blank or disappears; TypeError: Cannot set properties of undefined (setting 'hass')
- [playwright-validate-dashboards](playwright-validate-dashboards.md) — Dashboard edits must end with a Playwright visual check; screenshots go in .playwright-mcp/.
  - **before**: About to finish a dashboard edit; About to claim a dashboard change works
  - **symptom**: dashboard layout looks wrong or narrow; section renders blank
<!-- LEAVES:END -->
