# Tablet Climate View — Redesign

**Date:** 2026-04-18
**Scope:** Tablet dashboard only — `dashboards/tablet/climate.yaml`
**Status:** Design approved, pending plan

## Problem

The current climate tab does not fit the way climate is actually used in the house:

- The two "thermostat" cards on the page are `climate.living_room` and `climate.bedroom`, which are the **air conditioners**, not the heating. The real heating (Homecome `climate.floor_heating` and `climate.main_heating`) has never been on the page.
- Humidifier cards take up primary space even though humidifiers are informational — the daily signal is room humidity, not humidifier control.
- Curtains live in the climate tab even though they are not climate.
- Layout is locked to three equal columns and always shows everything with the same emphasis, regardless of season.

## Goals

- Put Homecome heating front-and-centre outside summer.
- Put the ACs front-and-centre in summer.
- Keep humidifiers visible but demoted to status indicators, with full control one tap away.
- Remove curtains from the climate tab.
- Allow horizontal rows and non-uniform sizing — not forced 3 × N grid.

## Non-goals

- Phone climate view. No phone climate tab exists today; adding one is out of scope.
- Any change to the humidifier, AC, or Homecome integrations themselves.
- Any change to `climate.living_room` / `climate.bedroom` entity IDs (the names are misleading but renaming is a separate cleanup).
- Exposing a Homecome schedule/programme — the integration does not expose one, so the dashboard shows mode, preset, `hvac_action`, setpoint, current temp only.

## Entities in scope

| Role | Entity | Notes |
|---|---|---|
| Heating — floor | `climate.floor_heating` | Homecome. `hvac_modes: off, auto`. |
| Heating — radiators | `climate.main_heating` | Homecome. Friendly name "Radiators". |
| AC — living room | `climate.living_room` | Midea. Full HVAC mode/fan/swing/preset surface. |
| AC — bedroom | `climate.bedroom` | Midea. Friendly name "Air conditioner". |
| Humidifier — living room | `humidifier.living_room` | Often unavailable. |
| Humidifier — bedroom | `humidifier.bedroom` | Often unavailable. |
| Living Room hygro | `sensor.living_room_hygro_temperature`, `sensor.living_room_hygro_humidity` | |
| Bedroom hygro | `sensor.bedroom_hygro_temperature`, `sensor.bedroom_hygro_humidity` | |
| Outdoor weather | `weather.forecast_home` | Used instead of `sensor.bosh_junkers_outdoor_temp_sensor`. |

Deliberately excluded: curtains, water heater, Bosh Junkers outdoor temp sensor, toilet hygro.

## Layout

Single-section `type: sections` view. The view uses `max_columns: 3` and the single section uses `column_span: 3` so it fills the full tablet landscape width; every card inside the section uses `grid_options: { columns: full }` so each horizontal-stack consumes an entire section row instead of a narrow 1/3-of-a-row cell.

Row order, top to bottom:

1. **Weather strip** — one-line summary from `weather.forecast_home`.
2. **Primary hero** — two full-size `thermostat` cards in a `horizontal-stack`. Heating in winter, AC in summer.
3. **Secondary strip** — compact two-chip `horizontal-stack` of `mushroom-template-card`s for the *other* mode. Tap → more-info.
4. **Per-room environment** — two chips (Living Room, Bedroom). Each shows temp + humidity + humidifier status. Tap → more-info on humidifier.
5. **24 h trend graphs** — two `history-graph` cards side-by-side, one per room, temp + humidity.

Rows 2 and 3 swap contents by season. Rows 1, 4, 5 are static.

## Seasonal swap

### New template binary sensor

**File:** `packages/bootstrap/templates/binary_sensors/cooling_season.yaml`

Matches the structure of existing files in this directory (e.g. `office_hours.yaml`, `bed_time.yaml`) — top-level `binary_sensor:` list, snake_case `name`. `packages/bootstrap/config.yaml` already includes the folder recursively via `template: !include_dir_list templates`.

```yaml
---
binary_sensor:
  - name: cooling_season
    state: >
      {{ now().month in [5, 6, 7, 8, 9] }}
    icon: >
      {{ 'mdi:snowflake' if now().month in [5, 6, 7, 8, 9] else 'mdi:radiator' }}
```

`binary_sensor.cooling_season` — `on` from May 1 through Sep 30, `off` otherwise. Reusable outside the dashboard (e.g. for future heating/AC automations).

### Visibility pattern

Four swap-aware cards total. Each uses a `visibility` block tied to `binary_sensor.cooling_season`:

```yaml
visibility:
  - condition: state
    entity: binary_sensor.cooling_season
    state: "on"    # cooling-season variant; use "off" for heating-season variant
```

Only two of the four render at any time.

| Position | Cooling season (May–Sep) | Heating season (Oct–Apr) |
|---|---|---|
| Row 2 — hero | AC thermostats (LR + BR) | Heating thermostats (floor + radiators) |
| Row 3 — strip | Heating chips (floor + radiators) | AC chips (LR + BR) |

## Card details

### Row 1 — Weather strip

Built-in `type: weather-forecast` card, full width. Shows current condition + 5-day daily forecast. The earlier mushroom-template-card design rendered as a thin text line with dead space on a wide tablet viewport; the built-in card gives a proper hero strip.

```yaml
type: weather-forecast
grid_options:
  columns: full
entity: weather.forecast_home
show_current: true
show_forecast: true
forecast_type: daily
```

### Row 2 — Primary hero

`horizontal-stack` of two `type: thermostat` cards.

- Heating variant (visible when cooling_season = off):
  - `climate.floor_heating` named "Floor Heating"
  - `climate.main_heating` named "Radiators"
- AC variant (visible when cooling_season = on):
  - `climate.living_room` named "Living Room AC"
  - `climate.bedroom` named "Bedroom AC"

### Row 3 — Secondary strip

`horizontal-stack` of two `mushroom-template-card`s. Each chip:

- Primary: friendly name + current temperature (e.g. `Floor Heating · 23.1°C`).
- Secondary: `hvac_action` for heating (`heating`, `idle`), state for AC (`off`, `cool`, `auto`).
- Icon: `mdi:radiator` for heating chips, `mdi:air-conditioner` for AC chips. Muted colour when mode is off/idle.
- Tap: `more-info` on the climate entity — gives full control without cluttering the page.

### Row 4 — Per-room environment

`horizontal-stack` of two `mushroom-template-card`s.

- Living Room chip:
  - Primary: `{{ states('sensor.living_room_hygro_temperature') | float(0) | round(1) }}°C · {{ states('sensor.living_room_hygro_humidity') | int }}%`
  - Secondary: `Living Room`
  - Icon: `mdi:sofa` — matches the established room-identity convention in `dashboards/tablet/home.yaml`. Colour signals humidifier state: `blue` when `humidifier.living_room` is `on`, `disabled` otherwise (including when unavailable).
  - Tap: `more-info` on `humidifier.living_room`.
- Bedroom chip: same pattern with bedroom sensors, `humidifier.bedroom`, and `mdi:bed` icon.

### Row 5 — 24 h trend sparklines

`horizontal-stack` of four `type: sensor` cards, one per metric, `graph: line`, `hours_to_show: 24`. Using `type: sensor` keeps each card compact (big number + small sparkline) and avoids `history-graph`'s behaviour of stacking multi-entity cards into separate panels (which clipped titles and wasted vertical space).

- Living Room Temp — `sensor.living_room_hygro_temperature`
- Living Room Humidity — `sensor.living_room_hygro_humidity`
- Bedroom Temp — `sensor.bedroom_hygro_temperature`
- Bedroom Humidity — `sensor.bedroom_hygro_humidity`

## Removed from the climate tab

- Curtains section (`cover.ground_floor`, `cover.living_room_main`, `cover.living_room_left`, `cover.bedroom`). Not deleted from HA — just not on this tab.
- "Per-Area Environment" entity lists (`sensor.*_hygro_temperature`, `sensor.*_hygro_humidity`) — replaced by row 4.
- Standalone humidifier control cards — demoted to the row 4 chips.

## Files touched

- **Modified:** `dashboards/tablet/climate.yaml` — full rewrite.
- **New:** `packages/bootstrap/templates/binary_sensors/cooling_season.yaml`.
- **No change:** `configuration.yaml` — packages are auto-included.

## Risks and mitigations

- **Homecome heating shows `off` all summer.** Not a bug — the secondary-strip variant handles that cleanly (chip says "idle" or state `off`). No extra guarding.
- **Humidifiers are `unavailable` long term.** Chips still render the temp + humidity reading from the hygro sensor, which is the signal that matters. Humidifier icon just goes muted.
- **`visibility` + `horizontal-stack`.** HA sections view supports per-card `visibility`; wrapping a `horizontal-stack` with visibility works the same as wrapping a single card. Verified by the existing `home.yaml` pattern of conditional content within stacks.
- **New template sensor requires a reload.** Standard HA template reload or restart. Per `feedback_reload_ha_after_push.md`, any push must be followed by reload + log check.

## Testing plan

- Before push: `uv run yamllint .` passes.
- After push: reload template entities, confirm `binary_sensor.cooling_season` resolves to `false` (today is 2026-04-18, April → heating season).
- Reload Lovelace resources, open tablet dashboard.
- Verify:
  - Row 2 shows the two heating thermostats (floor + radiators) with setpoints.
  - Row 3 shows the two AC chips with current temp + state.
  - Row 4 shows Living Room and Bedroom chips with correct temp / humidity.
  - Row 5 renders both 24 h graphs.
  - Curtains are gone.
- Simulate summer by editing the template to hardcode `true` (or by checking the result shape in the May–Sep case) and verify the swap renders AC in row 2, heating chips in row 3. Revert the stub.

## Commit plan

Two commits on a branch:

1. `feat(templates): add cooling_season binary sensor` — the new template file only.
2. `feat(dashboard): redesign tablet climate view` — the dashboard rewrite.

PR into `main`.
