# tooling/

<!-- LEAVES:START -->
- [dashboard-section-bands](dashboard-section-bands.md) — For exact band layouts use one full-width section with horizontal-stacks, not column_span on sibling sections.
  - **before**: About to build a multi-column band layout (two columns side by side, then a full-width row) in a sections view; About to set column_span on sibling sections to control side-by-side placement
  - **symptom**: sections meant to sit side by side stack vertically, or vice versa, after a restart; a sections-view column is squeezed narrow while the other has dead space; mushroom run-script buttons stretch tall or clip their label inside a narrow column
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
