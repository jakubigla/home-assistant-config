# Appliances View Redesign — Design Spec

**Date:** 2026-04-19
**Branch:** `chore/dashboard-redesign`
**File touched:** `dashboards/tablet/appliances.yaml` (full rewrite)
**Status:** Design approved by user; awaiting written-spec review.

## Goal

The current Appliances view on the tablet dashboard (`/wall-tablet/appliances`)
uses only ~30% of the screen. Two narrow sections stack a mushroom-vacuum-card
for each robot plus a single power-state chip for each washer/dryer. The wide
tablet viewport leaves huge whitespace and the integrations expose far more
useful data and actions than are surfaced.

The redesign takes advantage of the available space to present:
- At-a-glance status for all four appliances at the top.
- A live vacuum map when a bot is actively cleaning.
- Frequently-used settings (suction, cleaning mode, mop humidity, DnD) as
  one-tap cycle-select chips.
- Countdown and cycle state for washer and dryer when running.
- Silent-until-relevant warnings for low consumables and dock issues.
- Useful auxiliary context: reminder-automation toggles, laundry door sensor,
  last-run summaries, and a lifetime-stats popup per vacuum.

Primary use case: **balanced** — monitoring hero + curated quick-actions +
conditional detail strip. Not action-dense, not purely read-only.

## Non-goals

- Creating new "clean X room" scripts. Only the two existing scripts
  (`script.vacuum_clean_mudroom`, `script.vacuum_clean_kitchen`) are wired.
  Additional room scripts are out of scope and deferred.
- Adding the attic vacuum. A commented-out placeholder already exists in the
  current file and stays as-is.
- Exposing write-access to washer/dryer selects (water temperature, spin
  level, rinse cycles). These are practically only set on the appliance
  itself; the dashboard shows them read-only.
- Building lifetime statistics into the primary layout. They live behind a
  `browser_mod.popup` triggered by a chip.
- New Home Assistant template sensors, input_booleans, or automation changes.
  Every derived value is computed inline in Jinja inside the Lovelace YAML.

## High-level layout

Single `type: sections` view with `max_columns: 3` and one section with
`column_span: 3`. Every direct child card inside the section carries
`grid_options: { columns: full }`. This is the idiomatic full-width pattern
from the ha-dashboards skill — the three levers (max_columns, column_span,
grid_options) lined up to prevent the single-section layout from collapsing
into a narrow column.

Vertical ordering:

1. **Status strip** — 4 chips across (one per appliance).
2. **Vacuums row** — L10 Ultra and X40 Master, half-width each, via
   `horizontal-stack`.
3. **Vacuum-reminder toggle row** — slim row, two entity-cards across.
4. **Laundry row** — washer and dryer, half-width each, via
   `horizontal-stack`.
5. **Laundry-door chip** — single full-width chip under the laundry row.

## Section 1 — Status strip

Full-width `horizontal-stack` of four `custom:mushroom-template-card` chips.
Each chip summarises a single appliance and responds to its active/idle
state via templated `primary`, `secondary`, `icon`, and `icon_color`.

Chip layout (`layout: horizontal`):

- **L10 Ultra**
  - primary — cleaning: `{{ current_room }} · {{ cleaning_time }}m`;
    idle: `{{ battery }}% · Docked`
  - secondary — "Ground Floor"
  - icon — `mdi:robot-vacuum` (cleaning) / `mdi:robot-vacuum-variant` (docked)
  - icon_color — `blue` cleaning, `green` docked, `red` on error
  - tap_action — `more-info` on `vacuum.dreamebot_l10_ultra`
- **X40 Master** — same structure with x40 entities; secondary "First Floor"
- **Washer**
  - primary — running: `{{ minutes_left }}m left`;
    idle: `Idle · {{ last_run_ago }}`
  - secondary — running: `{{ job_state | title }}`; idle: "Last: {{ when }}"
  - icon — `mdi:washing-machine`
  - icon_color — `blue` running, `disabled` idle
  - tap_action — `more-info` on `binary_sensor.washer_power`
- **Dryer** — same, amber icon when running, template uses the dryer sensors.

Active detection:
- Vacuum: `states('vacuum.<bot>') != 'docked'` AND not `charging_completed`.
- Washer/dryer: `states('sensor.<app>_machine_state') != 'stop'`.

`minutes_left` template (guarded against stale completion_time):

```jinja
{% set ct = states('sensor.washer_completion_time') %}
{% set running = states('sensor.washer_machine_state') != 'stop' %}
{% if running and ct not in ('unknown', 'unavailable') %}
  {{ ((as_timestamp(ct) - as_timestamp(now())) / 60) | round(0) }}
{% else %}
  0
{% endif %}
```

## Section 2 — Vacuum cards (L10 and X40)

Each vacuum renders as a vertical stack inside one half of a
`horizontal-stack`. Both cards share the same structure; only entity IDs
differ. The sub-blocks (referred to by number) mirror the brainstorm design:

### 2a. Hero

`custom:mushroom-vacuum-card` with the existing command cluster
(`start_pause`, `stop`, `locate`, `return_home`), `icon_animation: true`,
`layout: horizontal`. Name shows the floor label ("Ground Floor" /
"First Floor").

### 2b. Status line

Single `custom:mushroom-template-card` (`layout: horizontal`) that changes
by vacuum state:
- Idle: primary = `{{ battery }}% · {{ status | title }}`,
  secondary = "Docked", icon `mdi:battery`, green.
- Cleaning: primary = `{{ current_room }}`,
  secondary = `{{ cleaned_area }} m² · {{ cleaning_time }} min`,
  icon `mdi:broom`, blue.
- Error: primary = `{{ error | replace('_', ' ') | title }}`,
  icon `mdi:alert`, red. Only renders when
  `sensor.<bot>_error not in ('no_error', 'unknown', 'unavailable')`.

### 2c. Live map (conditional)

`type: picture-entity` card pointing at `camera.<bot>_map`.
- `aspect_ratio: 16/10`
- `show_state: false`, `show_name: false`
- `visibility` condition: vacuum state is neither `docked` nor
  `charging_completed`. When docked the map is hidden and the card stack
  collapses above the settings row.

### 2d. Settings chips row

`custom:mushroom-chips-card` with four chips, wired to existing `select` and
`switch` entities. Tap cycles the select via `tap_action: perform-action`
targeting `select.select_next` (services in HA 2024.11+); DnD toggles via
`switch.toggle`.

Chips:
1. **Suction** — `select.<bot>_suction_level`. Icon `mdi:fan`. Content
   shows current value (e.g. "Strong"). Color `blue` when not "quiet".
2. **Mode** — `select.<bot>_cleaning_mode`. Icon `mdi:broom` for sweeping,
   `mdi:water` for mopping, `mdi:broom`+water for combo.
3. **Humidity** — `select.<bot>_mop_pad_humidity`. Icon `mdi:water-percent`.
4. **DnD** — `switch.<bot>_dnd`. Icon `mdi:sleep`. Green when on.

### 2e. Room-clean buttons

`type: grid` with `columns: 2`, `square: false`. L10 shows the two existing
scripts (`script.vacuum_clean_mudroom`, `script.vacuum_clean_kitchen`). X40
leaves the grid empty (card omitted) until scripts are authored.

### 2f. Consumables warning (conditional)

Single `custom:mushroom-template-card`, red/orange icon (`mdi:alert`),
rendered only when any consumable is below 20%. Visibility uses a compound
`or` across six states. Content lists the specific consumables below
threshold:

```jinja
{% set items = [] %}
{% set vals = {
  'Main brush': states('sensor.<bot>_main_brush_left'),
  'Side brush': states('sensor.<bot>_side_brush_left'),
  'Filter':     states('sensor.<bot>_filter_left'),
  'Sensor':     states('sensor.<bot>_sensor_dirty_left'),
  'Mop pad':    states('sensor.<bot>_mop_pad_left'),
  'Detergent':  states('sensor.<bot>_detergent_left')
} %}
{% for name, v in vals.items() %}
  {% if v not in ('unknown', 'unavailable') and (v | float(100)) < 20 %}
    {% set items = items + [name ~ ' ' ~ v ~ '%'] %}
  {% endif %}
{% endfor %}
{{ items | join(' · ') }}
```

Per-bot consumables differ:
- **L10 Ultra** iterates all six keys above (main brush, side brush,
  filter, sensor, mop pad, detergent).
- **X40 Master** only has four `%`-sensors exposed: main brush, side
  brush, filter, sensor. Its mop-pad and detergent are exposed as string
  `*_status` states instead (`installed` / `enabled`), handled in 2g.

The template for X40 iterates only those four keys; the mop pad and
detergent go into the dock warning.

### 2g. Dock warning (conditional)

Similar to 2f but for dock state. Renders only when something is off:
- L10: `sensor.dreamebot_l10_ultra_low_water_warning != 'no_warning'`, or
  `mop_pad != 'installed'`, or `dust_collection != 'available'`.
- X40: any of `dust_bag_status`, `clean_water_tank_status`,
  `dirty_water_tank_status`, `detergent_status`, `mop_pad` not in
  `('installed', 'enabled')`.

Content: short list of the offending items.

### 2h. Footer row

`custom:mushroom-chips-card` with two chips:
- **Last run** — re-uses the existing `cleaning_history` template from the
  current file, shortened to `{{ date }} · {{ time }} · {{ area }}`.
- **Stats** — icon `mdi:chart-box`, content "Stats". Tap fires
  `browser_mod.popup` with a custom card payload.

Stats popup payload (L10 example):

```yaml
tap_action:
  action: fire-dom-event
  browser_mod:
    service: browser_mod.popup
    data:
      title: L10 Ultra — Lifetime stats
      content:
        type: entities
        entities:
          - sensor.dreamebot_l10_ultra_cleaning_count
          - sensor.dreamebot_l10_ultra_total_cleaned_area
          - sensor.dreamebot_l10_ultra_total_cleaning_time
          - sensor.dreamebot_l10_ultra_first_cleaning_date
          - sensor.dreamebot_l10_ultra_firmware_version
          - sensor.dreamebot_l10_ultra_main_brush_time_left
          - sensor.dreamebot_l10_ultra_side_brush_time_left
          - sensor.dreamebot_l10_ultra_filter_time_left
          - sensor.dreamebot_l10_ultra_sensor_dirty_time_left
          - sensor.dreamebot_l10_ultra_mop_pad_time_left
          - sensor.dreamebot_l10_ultra_detergent_time_left
```

## Section 3 — Vacuum-reminder toggle row

Thin `horizontal-stack` between vacuums and laundry:

- `custom:mushroom-entity-card` on `automation.vacuum_reminder_ground_floor`
  - name "Ground Floor reminders", icon `mdi:bell-ring`
  - `tap_action`: `toggle` (uses `automation.toggle` service)
- Same for `automation.vacuum_reminder_first_floor`, name "First Floor
  reminders"

Icon color: `green` when on, `disabled` when off.

## Section 4 — Laundry cards

Each of washer and dryer is a vertical stack inside a half-width
`horizontal-stack` slot. Structure:

### 4a. Hero — conditional split

Two `custom:mushroom-template-card` blocks wrapped in mutually exclusive
`visibility:` on `sensor.<app>_machine_state`.

Running card (visibility: `machine_state != 'stop'`):
- primary: `{{ minutes_left }}m left · finishes {{ finish_time_hhmm }}`
- secondary: `{{ job_state | replace('_', ' ') | title }}`
- icon: `mdi:washing-machine` / `mdi:tumble-dryer`
- icon_color: `blue` washer, `amber` dryer
- card_mod on icon for slow spin animation (optional polish)

Idle card (visibility: `machine_state == 'stop'`):
- primary: "Idle"
- secondary: `Last: {{ completion_dt | timestamp_custom('%d %b %H:%M') }}
  · {{ energy_diff }} kWh`
- icon: greyscale, `icon_color: disabled`

Guard the completion_time template against `unknown`/`unavailable`:

```jinja
{% set ct = states('sensor.washer_completion_time') %}
{% if ct in ('unknown', 'unavailable') %}never{% else %}
{{ as_timestamp(ct) | timestamp_custom('%d %b %H:%M') }}
{% endif %}
```

### 4b. Sub-chips row (always visible)

`custom:mushroom-chips-card`.

Washer chips:
- Water temp — read-only, `select.washer_water_temperature`, icon
  `mdi:thermometer`, content `{{ state }}°C`.
- Spin — read-only, `select.washer_spin_level`, icon `mdi:rotate-3d-variant`,
  content `{{ state }} rpm`.
- Rinse cycles — read-only, `number.washer_rinse_cycles`, icon
  `mdi:water-sync`, content `{{ state }}×`.
- Bubble soak — tappable, `switch.washer_bubble_soak`, icon
  `mdi:chart-bubble`, green when on, `tap_action: toggle`.

Dryer chips:
- Wrinkle prevent — tappable, `switch.tumble_dryer_wrinkle_prevent`, icon
  `mdi:iron-outline`, green when on.
- Wrinkle active — read-only,
  `binary_sensor.tumble_dryer_wrinkle_prevent_active`, icon
  `mdi:auto-fix`, amber when on, `visibility` hides when off.
- Last-cycle energy — `sensor.tumble_dryer_energy_difference`, icon
  `mdi:flash`, content `{{ state | float(0) | round(2) }} kWh`.

### 4c. Indicator strip (conditional)

Tiny chips that only render when the underlying binary sensor is on:
- `binary_sensor.<app>_child_lock` → icon `mdi:lock`, label "Child lock"
- `binary_sensor.<app>_remote_control` → icon `mdi:remote`, label "Remote"

Implemented as two `mushroom-template-card` chips inside a
`mushroom-chips-card`, each with a `visibility` rule so the strip is empty
most of the time.

## Section 5 — Laundry door chip

Full-width `mushroom-template-card` at the bottom of the section:

- entity: `binary_sensor.laundry_doors`
- icon: `mdi:door-open` when on, `mdi:door-closed` when off
- icon_color: amber when on, disabled when off
- primary: "Laundry door"
- secondary: `{{ 'Open' if is_state('binary_sensor.laundry_doors', 'on')
  else 'Closed' }}`
- tap_action: `more-info`

## Jinja traps to respect

From the `ha-dashboards` skill:
1. `state_attr(e, 'attr') | default('x', true)` — `default` without
   `true` does NOT catch `None`.
2. Numeric attrs: `| float(0) | round(N)`. Every `cleaned_area`,
   `cleaning_time`, `battery_level`, `power` derivation must go through
   `float(0)` first.
3. Completion-time arithmetic: always guard the ISO timestamp against
   `unknown`/`unavailable` before calling `as_timestamp`.
4. Prefer `{% if %}/{% else %}/{% endif %}` blocks over inline ternaries
   when lines approach 88 chars.
5. `tap_action: perform-action` — the current services are
   `select.select_next` and `switch.toggle`. Use `perform_action` (the
   modern key), not `service:`.

## Card inventory

| Section | Card type | Notes |
|---|---|---|
| 1 | `horizontal-stack` → 4× `custom:mushroom-template-card` | status strip |
| 2a | `custom:mushroom-vacuum-card` | one per bot |
| 2b | `custom:mushroom-template-card` | state-driven status line |
| 2c | `type: picture-entity` | conditional map |
| 2d | `custom:mushroom-chips-card` | 4 setting chips |
| 2e | `type: grid` (columns 2) | room-clean scripts (L10 only) |
| 2f | `custom:mushroom-template-card` | conditional consumable warn |
| 2g | `custom:mushroom-template-card` | conditional dock warn |
| 2h | `custom:mushroom-chips-card` | last run + stats popup |
| 3 | `horizontal-stack` → 2× `custom:mushroom-entity-card` | reminder toggles |
| 4a | 2× `custom:mushroom-template-card` with `visibility` | running/idle hero |
| 4b | `custom:mushroom-chips-card` | appliance-specific sub-chips |
| 4c | `custom:mushroom-chips-card` | visibility-gated indicators |
| 5 | `custom:mushroom-template-card` | laundry door |

All rows and top-level containers get `grid_options: { columns: full }`.

## Verification plan

Follow the skill's push-HA-pull-Playwright loop:

1. `uv run pre-commit run --all-files` — YAML syntax + other hooks.
2. Commit to `chore/dashboard-redesign`; do not push to `main`.
3. `git push`. Wait 5–10s for HA to pull.
4. Trigger `homeassistant.reload_core_config` or `reload_all`; tail
   `home-assistant.log` for template errors.
5. Playwright: force-refetch lovelace config through the WebSocket bridge,
   navigate to `/wall-tablet/appliances`, take a full-viewport screenshot
   at tablet resolution (1280×800 landscape).
6. Confirm:
   - Status strip fills full width, four chips visible.
   - Both vacuum cards visible side by side, status line renders with
     correct battery and "Docked" label.
   - Live map hidden (both bots should be `charging_completed` at the
     time of verification unless a run is active).
   - Settings chips show current values; tap cycles do not throw.
   - Consumables + dock warnings silent when all consumables >=20% and
     dock OK.
   - Reminder toggle row shows both automations.
   - Laundry cards render in "Idle" variant when machines are stopped;
     `completion_time` template renders without `None` errors.
   - Laundry-door chip shows correct state.
   - `browser_mod.popup` opens when Stats chip is tapped.

## Open questions (resolved during brainstorm)

- **Live map always-on vs conditional?** Conditional (hidden when docked).
- **Consumables grid vs silent-warning?** Silent-warning (threshold 20%).
- **Laundry progress bar vs countdown?** Countdown hero, no helper needed.
- **Vacuum quick-actions?** Settings cycle chips only; new per-room
  scripts deferred.
- **Dryer controls?** Wrinkle prevent + bubble soak (washer) as toggles;
  washer setting selects shown read-only.
- **Lifetime stats?** Popup via `browser_mod.popup`.

## Risks

1. **`perform_action: select.select_next` semantics.** On some integrations
   the service wraps modulo across options; on others it throws at the end
   of the list. Verify during Playwright step; if it throws, swap to
   `select.select_option` with an explicit option value per chip state.
2. **Mushroom card `visibility:` on chips** — the chips-card element
   historically lagged the section-view `visibility` spec. If a chip
   refuses to hide, extract it into its own `mushroom-template-card` as a
   peer row with card-level visibility.
3. **Stale completion_time** — when the machine has never run or lost the
   sensor, the timestamp is `unavailable` / in the past. The Jinja guards
   must treat both cases. Any uncaught `None` crashes the entire card.
4. **browser_mod browser ID matching** — the popup targets the calling
   browser automatically; no per-tablet config needed. If the popup does
   not render, check that the tablet's browser is registered (it is, per
   the `sensor.browser_mod_*` list) and that the `browser_mod` frontend
   module is loaded in resources (it is — browser_mod is already used
   elsewhere in this repo).

## Success criteria

- Appliances view fills the full tablet viewport (no dead side columns).
- Idle tablet (both vacuums docked, both laundry machines idle) shows a
  clean, glanceable layout with zero visible warnings.
- Active tablet (vacuum running or laundry running) surfaces the
  countdown/current-room context at-a-glance without needing to tap in.
- All tap-actions route to sensible targets (cycle selects, toggle
  switches, open stats popup, open more-info).
- Pre-commit passes.
- No template errors in `home-assistant.log` after reload.
