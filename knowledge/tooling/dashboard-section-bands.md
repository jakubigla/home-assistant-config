---
summary: For exact band layouts use one full-width section with horizontal-stacks, not column_span on sibling sections.
before_action:
  - About to build a multi-column band layout (two columns side by side, then a full-width row) in a sections view
  - About to set column_span on sibling sections to control side-by-side placement
on_symptom:
  - "sections meant to sit side by side stack vertically, or vice versa, after a restart"
  - "a sections-view column is squeezed narrow while the other has dead space"
  - "mushroom run-script buttons stretch tall or clip their label inside a narrow column"
---

# Dashboard section bands

Want bands: two columns side-by-side, then a full-width row beneath. The intuitive approach — multiple sibling sections with `column_span` — reflows unpredictably across `max_columns`/viewport math (HA packs sections by width, not by intent). Burned 4 restart cycles learning this.

## Gotchas

- **Use Pattern A: one full-width section, rows are `horizontal-stack`s.** `max_columns: 3`, a single section with `column_span: 3`, and each row card (weather, each band) carries `grid_options: { columns: full }`. Inside a band, a `horizontal-stack` of `vertical-stack`s gives exact, even side-by-side columns that never reflow.
- **`column_span` on sibling sections is the trap.** Two sections you intend to stack render side-by-side (and vice versa) depending on `max_columns` — the ha-dashboards skill's layout reference common-failure table calls this out. Bumping `max_columns` to 4 made the whole grid collapse to one stacked column instead.
- **A `horizontal-stack` without `grid_options: columns: full` gets ~3/12 cells** and the band fragments. Set it on every full-width row card.
- **Mushroom run-script buttons: use `layout: vertical` in a narrow column.** `layout: horizontal` clips the label (`Lawn…`) and floats the icon when the column is tight.
- **YAML dashboards only reload on `homeassistant.restart`** — every band iteration needs a restart + reload-and-reverify, not a config-reload service. See the **reload-after-push** leaf. Verify each pass with Playwright (per **playwright-validate-dashboards**).
