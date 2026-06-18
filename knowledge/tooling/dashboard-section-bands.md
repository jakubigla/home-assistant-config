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

Bands = two columns side-by-side, then a full-width row beneath. HA packs sections by width, not
intent, so sibling sections reflow unpredictably across `max_columns`/viewport.

## Gotchas

- **Pattern A: one full-width section, rows are `horizontal-stack`s.** `max_columns: 3`, single
  section with `column_span: 3`, every row card (weather, each band) carries `grid_options: {
  columns: full }`. A band = `horizontal-stack` of `vertical-stack`s → exact, even columns that
  never reflow.
- **`column_span` on sibling sections is the trap** — sections you intend to stack render
  side-by-side (and vice versa) depending on `max_columns`; bumping to 4 collapses the whole grid
  to one column.
- **A `horizontal-stack` without `grid_options: columns: full` gets ~3/12 cells** and fragments.
  Set it on every full-width row card.
- **Mushroom run-script buttons: `layout: vertical` in a narrow column** — `horizontal` clips the
  label and floats the icon when tight.
- **Existing-dashboard edits auto-reload after push, no restart.** Push, force-refetch refresh,
  reverify with Playwright. See **reload-after-push**, **playwright-validate-dashboards**.
