# Layout Mechanics — `type: sections`

Reference for the grid-math behind Lovelace section views. Load when layout behaves unexpectedly (narrow columns, fragmented rows, dead space, stacks breaking across columns).

## Table of contents

- [The mental model](#the-mental-model)
- [Decision tree: which layout pattern?](#decision-tree-which-layout-pattern)
- [Pattern A: one-section, full-width](#pattern-a-one-section-full-width)
- [Pattern B: multi-section natural flow](#pattern-b-multi-section-natural-flow)
- [Pattern C: panel view (one hero card)](#pattern-c-panel-view-one-hero-card)
- [`grid_options` reference](#grid_options-reference)
- [`visibility` reference](#visibility-reference)
- [Common failure symptoms](#common-failure-symptoms)

## The mental model

A `type: sections` view is a **grid of sections**. Each section is itself a **grid of cards**.

- **View grid:** width = `max_columns` (default 4). Each section occupies 1 column by default; `column_span: N` makes it wider.
- **Section grid:** 12 cells per row. Each card occupies `grid_options.columns` cells (default ~3 for most card types). `columns: full` spans the whole row.

If a layout breaks, the fix is almost always at one of these two levels.

## Decision tree: which layout pattern?

```
Is the dashboard a single vertical flow (weather, then hero, then chips, then graphs)?
├── YES → Pattern A (one-section, full-width)
└── NO
    ├── Is there one dominant hero card that should fill the entire viewport?
    │   └── YES → Pattern C (panel view)
    └── NO → Pattern B (multi-section natural flow)
```

## Pattern A: one-section, full-width

Use when you want a single column of full-width rows — e.g. weather hero, thermostats side by side, chip strip, graph strip.

```yaml
type: sections
max_columns: 3
sections:
  - column_span: 3
    cards:
      - type: weather-forecast
        grid_options:
          columns: full
        entity: weather.forecast_home
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: thermostat
            entity: climate.floor_heating
          - type: thermostat
            entity: climate.main_heating
      # ...
```

Every card (including every `horizontal-stack`) needs `grid_options: columns: full`. Without it, HA allocates roughly 3 of the 12 section-grid cells per card and rows fragment — your two-thermostat stack becomes a narrow 1/4-width cell sitting next to other narrow cells from the row above.

**Why not just `max_columns: 1`?** Because HA caps the single-section width at `section_min_column_width * 1` + padding — about 500 px on a 1280 px tablet. This is the most common trap; it looks right in code but renders as a narrow slab.

## Pattern B: multi-section natural flow

Use when the page has genuinely independent column-shaped regions — e.g. the tablet home page with Status / Devices / Scenes as three stacked themes.

```yaml
type: sections
max_columns: 3
sections:
  - title: Status
    cards: [...]
  - title: Devices
    cards: [...]
  - title: Scenes
    cards: [...]
```

HA arranges sections side-by-side up to `max_columns`, wrapping on narrow viewports. No `column_span`, no `grid_options` needed — sections manage their own widths.

Use this when you genuinely have N parallel content tracks. Don't fake it with one-section-per-row — that's Pattern A without the span.

## Pattern C: panel view (one hero card)

Use when one card is the whole page (media control wall panel, camera stream, single floor plan).

```yaml
type: panel
cards:
  - type: picture-elements
    # ...
```

Panel view ignores the sections/grid system entirely; the single card gets 100% viewport. Don't fight this with wrapping cards — if you find yourself using `vertical-stack` to add more content, switch to Pattern A instead.

## `grid_options` reference

Applied to any card inside a section. All fields optional.

```yaml
grid_options:
  columns: full        # 1-12 or "full" — how many of the 12 cells
  rows: auto           # 1-N or "auto" — how many row-cells tall
```

- **`columns: full`** — span the whole row. Use this on `horizontal-stack`, `weather-forecast`, `history-graph`, any card that needs the full section width.
- **`columns: 6`** — half width. Use when pairing two cards side-by-side *without* wrapping in `horizontal-stack`.
- **`rows: auto`** — let the card size itself. Default. Override only to enforce specific tile sizing on a grid-of-tiles layout.

If the field is omitted, HA picks a default based on card type. The defaults are inconsistent across card types — safer to set explicitly when full-width matters.

## `visibility` reference

Render a card (or section) conditionally. All conditions must pass.

```yaml
- type: horizontal-stack
  visibility:
    - condition: state
      entity: binary_sensor.cooling_season
      state: "off"
  # ...
```

Supported conditions:

- `state` — exact state match. `state:` takes a string or list of strings.
- `numeric_state` — `above:` / `below:` for numeric comparison.
- `screen` — viewport width media query (`media_query: "(min-width: 1024px)"`).
- `user` — match specific HA user IDs.
- `and` / `or` — combine nested conditions.

For seasonal swaps, the template-binary-sensor + `state` pattern is idiomatic. Two mutually-exclusive cards (one with `state: "on"`, one with `state: "off"`) share a binary_sensor and exactly one renders. Prefer this over wrapping both in `type: conditional`, which adds a layout-confusing extra card.

## Common failure symptoms

| Symptom | Cause | Fix |
|---|---|---|
| Narrow content, big empty margins | `max_columns: 1` capping section width | Pattern A: `max_columns: 3` + `column_span: 3` |
| Weather hero renders as tiny chip | `mushroom-template-card` at full width looks like a status line | Switch to `type: weather-forecast` built-in |
| `horizontal-stack` becomes a narrow box next to other cards | Missing `grid_options: columns: full` on the stack | Add it |
| Two sections intended to stack vertically render side-by-side | `max_columns: 2+` at view level treats each section as a column | Either use Pattern A (one section) or set `column_span` on each |
| Graph titles get clipped / axis labels overlap | `type: history-graph` with 2 entities at narrow width | Switch to one `type: sensor` per entity in a `horizontal-stack` |
| Conditional row leaves whitespace when the other variant is active | Default — visibility hides but the section still reserves layout flow slot; usually OK | If visually wrong, inspect section order; often fine |
