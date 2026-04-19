# Card Type Cheatsheet

Card-by-card decision matrix with copy-paste snippets. Load when choosing what card to use for a given job.

## Table of contents

- [Decision matrix](#decision-matrix)
- [Weather — hero strip](#weather--hero-strip)
- [Climate — full control](#climate--full-control)
- [Climate — status chip](#climate--status-chip)
- [Sensor trend — sparkline](#sensor-trend--sparkline)
- [Sensor value — big number](#sensor-value--big-number)
- [Room environment chip](#room-environment-chip)
- [Door / binary status chip](#door--binary-status-chip)
- [Scripts / actions](#scripts--actions)
- [Covers / curtains / gates](#covers--curtains--gates)
- [Heading / divider](#heading--divider)
- [Layout wrappers](#layout-wrappers)

## Decision matrix

| Want... | Card type | Notes |
|---|---|---|
| Weather hero | `type: weather-forecast` | Built-in. NOT mushroom-template-card. |
| Thermostat with dial + setpoint | `type: thermostat` | Works for any climate entity (AC too). |
| Compact climate/AC status | `custom:mushroom-template-card` | With icon_color tied to hvac_action / state. |
| 24 h trend, one metric | `type: sensor` with `graph: line` | Big number + sparkline. |
| 24 h trend, many metrics combined | `custom:mini-graph-card` if installed; else stack multiple `type: sensor` | history-graph with 2+ entities fragments. |
| On/off, open/closed chip | `custom:mushroom-template-card` or `custom:mushroom-chips-card` | |
| Run a script | `custom:mushroom-template-card` + `tap_action: perform-action` | |
| Curtain / cover | `custom:mushroom-cover-card` | Has button + position controls. |
| Media playback | `custom:mass-player-card` | For Music Assistant. Uses `entities:` array, not `entity:`. |
| Section heading inside section | `type: heading` | `heading_style: subtitle` for a lighter header. |

## Weather — hero strip

**Use `type: weather-forecast`** (HA built-in). Full-width, big icon, current conditions, forecast strip.

```yaml
- type: weather-forecast
  grid_options:
    columns: full
  entity: weather.forecast_home
  show_current: true
  show_forecast: true
  forecast_type: daily      # or "hourly"
```

Canonical weather entity in this repo: `weather.forecast_home` (Met.no).

**Do NOT use** `custom:mushroom-template-card` to build a weather hero. It renders as a thin text-only strip with a tiny icon — fine for a phone chip row, wrong for a tablet hero.

## Climate — full control

```yaml
- type: thermostat
  entity: climate.floor_heating
  name: Floor Heating
```

Works for any climate entity — Homecome heating *or* Midea AC. Shows current temp, setpoint dial, hvac_action. +/- buttons appear automatically when the entity supports target-temperature adjustment.

Pair two in a `horizontal-stack` for side-by-side heroes.

## Climate — status chip

Compact row card that shows state without opening full controls. Tap opens `more-info`.

```yaml
- type: custom:mushroom-template-card
  entity: climate.living_room
  icon: mdi:air-conditioner
  icon_color: >-
    {{ 'blue' if states('climate.living_room') not in ['off', 'unavailable'] else 'disabled' }}
  primary: Living Room AC
  secondary: >-
    {{ state_attr('climate.living_room', 'current_temperature') | float(0) | round(1) }}°C · {{ states('climate.living_room') | capitalize }}
  layout: horizontal
  tap_action:
    action: more-info
```

For heating chips, swap `mdi:air-conditioner` → `mdi:radiator`, blue → orange, and show `hvac_action`:

```yaml
secondary: >-
  {{ state_attr('climate.main_heating', 'current_temperature') | float(0) | round(1) }}°C · {{ state_attr('climate.main_heating', 'hvac_action') | default('idle', true) | capitalize }}
```

Note `| default('idle', true)` — the `, true` is critical (catches `None` as well as undefined).

## Sensor trend — sparkline

```yaml
- type: sensor
  entity: sensor.living_room_hygro_temperature
  graph: line
  hours_to_show: 24
  name: Living Room Temp
```

Renders as: card title + big current value + small inline sparkline below. Good for compact trend strips; four across in a `horizontal-stack` works well on a climate page.

**Avoid `type: history-graph` with multiple entities** — HA renders each entity as a separate stacked panel with its own y-axis. Two rooms × temp+humidity gives four stacked panels and frequent title clipping when the left y-axis takes many characters (e.g. `21.9`, `22.2`, `22.5` vs integer-only `27`, `28`).

## Sensor value — big number

Static, no trend:

```yaml
- type: entity
  entity: sensor.bosh_junkers_outdoor_temp_sensor
  name: Outdoor
```

Or as a chip with an icon:

```yaml
- type: custom:mushroom-entity-card
  entity: sensor.bosh_junkers_outdoor_temp_sensor
  name: Outdoor
  icon: mdi:thermometer
  layout: horizontal
```

## Room environment chip

Shows temp/humidity with icon color signalling humidifier state. Tap opens humidifier more-info.

```yaml
- type: custom:mushroom-template-card
  entity: sensor.living_room_hygro_temperature
  icon: mdi:sofa                         # room-identity icon — mdi:bed for bedroom
  icon_color: >-
    {{ 'blue' if is_state('humidifier.living_room', 'on') else 'disabled' }}
  primary: >-
    {{ states('sensor.living_room_hygro_temperature') | float(0) | round(1) }}°C · {{ states('sensor.living_room_hygro_humidity') | float(0) | round(0) | int }}%
  secondary: Living Room
  layout: horizontal
  tap_action:
    action: more-info
    entity: humidifier.living_room       # override — default would open the hygro sensor
```

**Primary/secondary choice:**

- On a climate-focused page (data is the point): primary = reading, secondary = room name.
- On a home/overview page (room identity is the point): primary = room name, secondary = reading. See `dashboards/tablet/home.yaml:440-486` for the inverse pattern.

## Door / binary status chip

```yaml
- type: template
  entity: binary_sensor.terrace_main_door
  icon: >-
    {{ 'mdi:door-open' if is_state('binary_sensor.terrace_main_door', 'on') else 'mdi:door-closed' }}
  icon_color: >-
    {{ 'red' if is_state('binary_sensor.terrace_main_door', 'on') else 'green' }}
  content: >-
    Main: {{ 'Open' if is_state('binary_sensor.terrace_main_door', 'on') else 'Closed' }}
  tap_action:
    action: more-info
```

Used inside `custom:mushroom-chips-card: chips: [...]`. See `dashboards/tablet/outdoor.yaml` for multi-chip examples.

## Scripts / actions

Run a script on tap:

```yaml
- type: custom:mushroom-template-card
  entity: script.gate_open
  primary: Open Gate
  icon: mdi:gate-open
  icon_color: teal
  layout: horizontal
  tap_action:
    action: perform-action
    perform_action: script.turn_on
    target:
      entity_id: script.gate_open
```

## Covers / curtains / gates

```yaml
- type: custom:mushroom-cover-card
  entity: cover.pergola_roof
  name: Pergola Roof
  icon: mdi:pergola
  show_buttons_control: true
  show_position_control: false     # true for curtains with partial positions
  layout: horizontal
```

## Heading / divider

```yaml
- type: heading
  heading: Run Scripts
  heading_style: subtitle         # or "title" for a bigger header
```

Use sparingly — in this repo, most dashboards signal grouping by whitespace + ordering, not explicit headings.

## Layout wrappers

- **`horizontal-stack`** — children side-by-side, equal widths. Needs `grid_options: columns: full` inside a section. Each child further gets its own width by HA defaults.
- **`vertical-stack`** — children stacked. Rarely needed inside `sections` (sections already stack vertically); useful inside other wrappers.
- **`grid`** (not `type: sections`) — fixed columns. Use for 2×N tile grids of equal-sized cards:

  ```yaml
  - type: grid
    columns: 2
    square: false
    cards:
      - [...tile 1]
      - [...tile 2]
  ```

  `square: false` lets card heights match content instead of forcing square aspect.
