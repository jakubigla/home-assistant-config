# Appliances View Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the narrow two-column appliances view at `/wall-tablet/appliances` with a full-width single-section dashboard that exposes at-a-glance status, a conditional live vacuum map, one-tap settings chips, silent-until-relevant consumable/dock warnings, a laundry countdown hero, and a `browser_mod` lifetime-stats popup per vacuum.

**Architecture:** Single `type: sections` view, `max_columns: 3`, one section with `column_span: 3`. Every top-level child in the section gets `grid_options: { columns: full }`. Layered vertically: status strip → vacuums row (`horizontal-stack`) → reminder toggle row → laundry row (`horizontal-stack`) → laundry door chip. All templating is inline Jinja; no new helpers, template sensors, or automations are created.

**Tech Stack:** Home Assistant Lovelace YAML, Mushroom cards (`mushroom-template-card`, `mushroom-chips-card`, `mushroom-vacuum-card`, `mushroom-entity-card`), `picture-entity` for maps, `browser_mod.popup` for stats dialog. Verification via pre-commit, HA `homeassistant.reload_core_config` reload, `/api/error_log` inspection, and Playwright screenshots at tablet viewport (1280×800).

**Spec:** `docs/superpowers/specs/2026-04-19-appliances-view-redesign-design.md`

**Branch:** `chore/dashboard-redesign` (already checked out — do NOT push to `main`).

---

## File Structure

Files to modify:
- `dashboards/tablet/appliances.yaml` — full rewrite. Incremental commits grow the file task-by-task.

Files to reference but not modify:
- `packages/bootstrap/templates/binary_sensors/*.yaml` — idiom reference only.
- `dashboards/tablet/home.yaml` — Mushroom chip idiom reference (lines 89-108, 440-486).
- Existing scripts: `script.vacuum_clean_mudroom`, `script.vacuum_clean_kitchen`.

Files created: none.

---

## Conventions used throughout

These rules apply to every task below. Violations fail verification.

- **Full-width containers.** Every direct child of the section gets
  `grid_options: { columns: full }`. `horizontal-stack` goes on a full-width
  slot; its children do NOT need `grid_options` themselves.
- **Jinja guards.**
  - `state_attr(e, 'x') | default('v', true)` — the `true` is mandatory.
    Bare `| default('v')` does not catch `None`.
  - Numerics: always pipe through `| float(0)` (or `| int(0)`) before
    `round` / comparison.
  - Completion-time / ISO strings: check `states(x) not in ('unknown',
    'unavailable')` before calling `as_timestamp`.
- **88-char lines.** Prefer `{% if %}/{% else %}/{% endif %}` over long
  inline ternaries; yamllint in pre-commit warns on >88.
- **Services.** Use `tap_action: { action: perform-action, perform_action:
  <domain.service>, ... }` — NOT the legacy `service:` key.
- **Commits per task.** Each task ends with a commit, then push to origin
  so HA pulls. Never squash within this plan.

---

## Per-task verification recipe

Each task ends with this verification block. Commands are the same every
time; only the Playwright URL changes if the tab route changes (it does
not here). Keep the command block inline in each task so the executor
doesn't need to scroll.

Preconditions in `.env` (already present):
- `API_ACCESS_TOKEN=<ha_long_lived_token>`

Standard verification after every commit:

```bash
# 1. Push branch
git push

# 2. Wait ~10s for HA to pull (HA polls the branch)
sleep 12

# 3. Reload Lovelace on HA
source .env && curl -sS -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://homeassistant.local:8123/api/services/homeassistant/reload_core_config \
  --data '{}' -o /dev/null -w "HTTP %{http_code}\n"

# 4. Tail error log for the last minute
source .env && curl -sS -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/error_log | tail -80
```

If `/api/error_log` shows a template error mentioning `appliances.yaml` or
any entity ID used in this plan — stop, fix the template, recommit.

The Playwright verification step is run only in Task 1 (smoke) and Task 8
(full visual pass).

---

## Task 1: Scaffold single full-width section

**Purpose:** Replace the existing two-section layout with a single
full-width section containing one stub card. Proves the `max_columns: 3` +
`column_span: 3` + `grid_options: { columns: full }` idiom works for this
view before any real cards are added.

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Overwrite `dashboards/tablet/appliances.yaml` with scaffold**

Replace the entire file with:

```yaml
---
title: Appliances
path: appliances
icon: mdi:washing-machine
type: sections
max_columns: 3
sections:
  - column_span: 3
    cards:
      - type: markdown
        grid_options:
          columns: full
        content: "Appliances view — redesign in progress"
```

- [ ] **Step 2: Lint**

Run:

```bash
uv run pre-commit run --all-files
```

Expected: all hooks `Passed` (some skipped for empty scope). If
`yamllint` fails on `dashboards/**`, that's unexpected — read the message
and fix indentation/trailing-space before committing.

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): scaffold full-width appliances section"
```

- [ ] **Step 4: Push and reload**

Run the standard verification recipe (push → sleep 12 → reload → tail
error log). Error log must contain no entries referencing
`appliances.yaml`.

- [ ] **Step 5: Playwright smoke test**

Open `/wall-tablet/appliances` via Playwright at viewport 1280×800.
Take a screenshot and confirm:
- The markdown card fills the full viewport width (no narrow single
  column).
- No red error banner at the top of the card area.

If the stub card is narrow: the three-lever idiom failed. Recheck
`max_columns: 3`, `column_span: 3`, and the card's `grid_options:
columns: full`.

---

## Task 2: Status strip (4 chips, top row)

**Purpose:** Full-width `horizontal-stack` with four `mushroom-template-card`
chips — one per appliance. Shows the single number that matters and
changes primary/secondary/icon/color by active state.

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Replace the stub markdown with the status-strip block**

Inside `sections: - column_span: 3: cards:`, replace the single `markdown`
card with:

```yaml
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-template-card
            entity: vacuum.dreamebot_l10_ultra
            primary: >-
              {% set s = states('vacuum.dreamebot_l10_ultra') %}
              {% if s in ('docked', 'returning') %}
              {{ states('sensor.dreamebot_l10_ultra_battery_level') }}% · Docked
              {% else %}
              {{ states('sensor.dreamebot_l10_ultra_current_room') }} ·
              {{ states('sensor.dreamebot_l10_ultra_cleaning_time') | int(0) }}m
              {% endif %}
            secondary: Ground Floor · L10 Ultra
            icon: >-
              {% if states('vacuum.dreamebot_l10_ultra') in ('docked',
              'returning') %}mdi:robot-vacuum-variant{% else %}mdi:robot-vacuum
              {% endif %}
            icon_color: >-
              {% set e = states('sensor.dreamebot_l10_ultra_error') %}
              {% if e not in ('no_error', 'unknown', 'unavailable') %}red
              {% elif states('vacuum.dreamebot_l10_ultra') == 'docked' %}green
              {% else %}blue{% endif %}
            layout: horizontal
            tap_action:
              action: more-info

          - type: custom:mushroom-template-card
            entity: vacuum.x40_master
            primary: >-
              {% set s = states('vacuum.x40_master') %}
              {% if s in ('docked', 'returning') %}
              {{ states('sensor.x40_master_battery_level') }}% · Docked
              {% else %}
              {{ states('sensor.x40_master_current_room') }} ·
              {{ states('sensor.x40_master_cleaning_time') | int(0) }}m
              {% endif %}
            secondary: First Floor · X40 Master
            icon: >-
              {% if states('vacuum.x40_master') in ('docked', 'returning') %}
              mdi:robot-vacuum-variant{% else %}mdi:robot-vacuum{% endif %}
            icon_color: >-
              {% set e = states('sensor.x40_master_error') %}
              {% if e not in ('no_error', 'unknown', 'unavailable') %}red
              {% elif states('vacuum.x40_master') == 'docked' %}green
              {% else %}blue{% endif %}
            layout: horizontal
            tap_action:
              action: more-info

          - type: custom:mushroom-template-card
            entity: binary_sensor.washer_power
            primary: >-
              {% set ms = states('sensor.washer_machine_state') %}
              {% set ct = states('sensor.washer_completion_time') %}
              {% if ms != 'stop' and ct not in ('unknown', 'unavailable') %}
              {{ ((as_timestamp(ct) - as_timestamp(now())) / 60) | round(0) }}m left
              {% else %}Idle{% endif %}
            secondary: >-
              {% set ms = states('sensor.washer_machine_state') %}
              {% if ms != 'stop' %}
              {{ states('sensor.washer_job_state') | replace('_', ' ') | title }}
              {% else %}
              {% set ct = states('sensor.washer_completion_time') %}
              {% if ct not in ('unknown', 'unavailable') %}
              Last: {{ as_timestamp(ct) | timestamp_custom('%d %b %H:%M') }}
              {% else %}No recent runs{% endif %}
              {% endif %}
            icon: mdi:washing-machine
            icon_color: >-
              {% if states('sensor.washer_machine_state') != 'stop' %}blue
              {% else %}disabled{% endif %}
            layout: horizontal
            tap_action:
              action: more-info

          - type: custom:mushroom-template-card
            entity: binary_sensor.tumble_dryer_power
            primary: >-
              {% set ms = states('sensor.tumble_dryer_machine_state') %}
              {% set ct = states('sensor.tumble_dryer_completion_time') %}
              {% if ms != 'stop' and ct not in ('unknown', 'unavailable') %}
              {{ ((as_timestamp(ct) - as_timestamp(now())) / 60) | round(0) }}m left
              {% else %}Idle{% endif %}
            secondary: >-
              {% set ms = states('sensor.tumble_dryer_machine_state') %}
              {% if ms != 'stop' %}
              {{ states('sensor.tumble_dryer_job_state') | replace('_', ' ') | title }}
              {% else %}
              {% set ct = states('sensor.tumble_dryer_completion_time') %}
              {% if ct not in ('unknown', 'unavailable') %}
              Last: {{ as_timestamp(ct) | timestamp_custom('%d %b %H:%M') }}
              {% else %}No recent runs{% endif %}
              {% endif %}
            icon: mdi:tumble-dryer
            icon_color: >-
              {% if states('sensor.tumble_dryer_machine_state') != 'stop' %}amber
              {% else %}disabled{% endif %}
            layout: horizontal
            tap_action:
              action: more-info
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

Expected: Passed. If yamllint flags a long line, split the offending
`>-` block into `{% if %}` / `{% endif %}` pairs.

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): appliances status strip"
```

- [ ] **Step 4: Push and reload**

Run the standard verification recipe. Confirm no template errors.

---

## Task 3: L10 Ultra vacuum card

**Purpose:** Left half of the vacuums row. Hero vacuum card + status line +
conditional live map + 4 setting chips + 2 room-clean script buttons +
conditional consumables warning + conditional dock warning + footer
(last-run chip + stats popup chip).

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the vacuums-row horizontal-stack after the status strip**

After the status-strip `horizontal-stack` (still inside the same
`cards:` list), append a new `horizontal-stack` containing a
`vertical-stack` for L10. The X40 side is filled in Task 4 as the second
child of the same `horizontal-stack`. For now, add only the L10 vertical
stack as the **first** child; X40 slot will be added in Task 4.

Append:

```yaml
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: vertical-stack
            cards:
              - type: custom:mushroom-vacuum-card
                entity: vacuum.dreamebot_l10_ultra
                name: Ground Floor — L10 Ultra
                icon_animation: true
                commands:
                  - start_pause
                  - stop
                  - locate
                  - return_home
                layout: horizontal

              - type: custom:mushroom-template-card
                entity: vacuum.dreamebot_l10_ultra
                primary: >-
                  {% set s = states('vacuum.dreamebot_l10_ultra') %}
                  {% if s in ('docked', 'returning') %}
                  {{ states('sensor.dreamebot_l10_ultra_battery_level') }}% ·
                  {{ states('sensor.dreamebot_l10_ultra_status') | replace('_',
                  ' ') | title }}
                  {% else %}
                  {{ states('sensor.dreamebot_l10_ultra_current_room') }}
                  {% endif %}
                secondary: >-
                  {% set s = states('vacuum.dreamebot_l10_ultra') %}
                  {% if s in ('docked', 'returning') %}Docked
                  {% else %}
                  {{ states('sensor.dreamebot_l10_ultra_cleaned_area') |
                  int(0) }} m² · {{
                  states('sensor.dreamebot_l10_ultra_cleaning_time') | int(0)
                  }} min
                  {% endif %}
                icon: >-
                  {% if states('vacuum.dreamebot_l10_ultra') in ('docked',
                  'returning') %}mdi:battery{% else %}mdi:broom{% endif %}
                icon_color: >-
                  {% if states('vacuum.dreamebot_l10_ultra') in ('docked',
                  'returning') %}green{% else %}blue{% endif %}
                layout: horizontal

              - type: custom:mushroom-template-card
                entity: sensor.dreamebot_l10_ultra_error
                primary: >-
                  {{ states('sensor.dreamebot_l10_ultra_error') |
                  replace('_', ' ') | title }}
                secondary: Error
                icon: mdi:alert
                icon_color: red
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.dreamebot_l10_ultra_error') not in
                      ('no_error', 'unknown', 'unavailable') }}

              - type: picture-entity
                entity: camera.dreamebot_l10_ultra_map
                camera_image: camera.dreamebot_l10_ultra_map
                aspect_ratio: "16:10"
                show_state: false
                show_name: false
                visibility:
                  - condition: state
                    entity: vacuum.dreamebot_l10_ultra
                    state_not: docked
                  - condition: state
                    entity: sensor.dreamebot_l10_ultra_state
                    state_not: charging_completed

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: select.dreamebot_l10_ultra_suction_level
                    icon: mdi:fan
                    icon_color: >-
                      {% if states('select.dreamebot_l10_ultra_suction_level')
                      == 'quiet' %}disabled{% else %}blue{% endif %}
                    content: >-
                      {{ states('select.dreamebot_l10_ultra_suction_level') |
                      title }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.dreamebot_l10_ultra_suction_level
                  - type: template
                    entity: select.dreamebot_l10_ultra_cleaning_mode
                    icon: >-
                      {% set m =
                      states('select.dreamebot_l10_ultra_cleaning_mode') %}
                      {% if 'mop' in m and 'sweep' in m %}mdi:broom
                      {% elif 'mop' in m %}mdi:water
                      {% else %}mdi:broom{% endif %}
                    icon_color: teal
                    content: >-
                      {{ states('select.dreamebot_l10_ultra_cleaning_mode') |
                      replace('_', ' ') | title }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.dreamebot_l10_ultra_cleaning_mode
                  - type: template
                    entity: select.dreamebot_l10_ultra_mop_pad_humidity
                    icon: mdi:water-percent
                    icon_color: cyan
                    content: >-
                      {{ states('select.dreamebot_l10_ultra_mop_pad_humidity')
                      | title }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.dreamebot_l10_ultra_mop_pad_humidity
                  - type: template
                    entity: switch.dreamebot_l10_ultra_dnd
                    icon: mdi:sleep
                    icon_color: >-
                      {% if is_state('switch.dreamebot_l10_ultra_dnd', 'on') %}
                      green{% else %}disabled{% endif %}
                    content: DnD
                    tap_action:
                      action: perform-action
                      perform_action: switch.toggle
                      target:
                        entity_id: switch.dreamebot_l10_ultra_dnd

              - type: grid
                columns: 2
                square: false
                cards:
                  - type: custom:mushroom-template-card
                    entity: script.vacuum_clean_mudroom
                    primary: Clean Mudroom
                    icon: mdi:door
                    icon_color: teal
                    layout: horizontal
                    tap_action:
                      action: perform-action
                      perform_action: script.turn_on
                      target:
                        entity_id: script.vacuum_clean_mudroom
                  - type: custom:mushroom-template-card
                    entity: script.vacuum_clean_kitchen
                    primary: Clean Kitchen
                    icon: mdi:silverware-fork-knife
                    icon_color: orange
                    layout: horizontal
                    tap_action:
                      action: perform-action
                      perform_action: script.turn_on
                      target:
                        entity_id: script.vacuum_clean_kitchen

              - type: custom:mushroom-template-card
                entity: sensor.dreamebot_l10_ultra_filter_left
                primary: Consumables low
                secondary: >-
                  {% set items = namespace(v=[]) %}
                  {% set vals = {
                    'Main brush':
                    states('sensor.dreamebot_l10_ultra_main_brush_left'),
                    'Side brush':
                    states('sensor.dreamebot_l10_ultra_side_brush_left'),
                    'Filter':
                    states('sensor.dreamebot_l10_ultra_filter_left'),
                    'Sensor':
                    states('sensor.dreamebot_l10_ultra_sensor_dirty_left'),
                    'Mop pad':
                    states('sensor.dreamebot_l10_ultra_mop_pad_left'),
                    'Detergent':
                    states('sensor.dreamebot_l10_ultra_detergent_left')
                  } %}
                  {% for name, v in vals.items() %}
                  {% if v not in ('unknown', 'unavailable') and
                  (v | float(100)) < 20 %}
                  {% set items.v = items.v + [name ~ ' ' ~ v ~ '%'] %}
                  {% endif %}
                  {% endfor %}
                  {{ items.v | join(' · ') }}
                icon: mdi:alert
                icon_color: orange
                layout: horizontal
                tap_action:
                  action: more-info
                visibility:
                  - condition: template
                    value_template: >-
                      {% set vals = [
                        states('sensor.dreamebot_l10_ultra_main_brush_left'),
                        states('sensor.dreamebot_l10_ultra_side_brush_left'),
                        states('sensor.dreamebot_l10_ultra_filter_left'),
                        states('sensor.dreamebot_l10_ultra_sensor_dirty_left'),
                        states('sensor.dreamebot_l10_ultra_mop_pad_left'),
                        states('sensor.dreamebot_l10_ultra_detergent_left')
                      ] %}
                      {{ vals | map('float', 100) | select('lt', 20) |
                      list | length > 0 }}

              - type: custom:mushroom-template-card
                entity: sensor.dreamebot_l10_ultra_low_water_warning
                primary: Dock attention
                secondary: >-
                  {% set items = namespace(v=[]) %}
                  {% if states('sensor.dreamebot_l10_ultra_low_water_warning')
                  != 'no_warning' %}
                  {% set items.v = items.v + ['Water low'] %}
                  {% endif %}
                  {% if states('sensor.dreamebot_l10_ultra_mop_pad') !=
                  'installed' %}
                  {% set items.v = items.v + ['Mop pad missing'] %}
                  {% endif %}
                  {% if states('sensor.dreamebot_l10_ultra_dust_collection') !=
                  'available' %}
                  {% set items.v = items.v + ['Dust bag'] %}
                  {% endif %}
                  {{ items.v | join(' · ') }}
                icon: mdi:alert-circle
                icon_color: red
                layout: horizontal
                tap_action:
                  action: more-info
                visibility:
                  - condition: template
                    value_template: >-
                      {{
                      states('sensor.dreamebot_l10_ultra_low_water_warning')
                      != 'no_warning'
                      or
                      states('sensor.dreamebot_l10_ultra_mop_pad') !=
                      'installed'
                      or
                      states('sensor.dreamebot_l10_ultra_dust_collection') !=
                      'available' }}

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: sensor.dreamebot_l10_ultra_cleaning_history
                    icon: mdi:history
                    icon_color: purple
                    content: >-
                      {%- set ns = namespace(d='', t='', a='') -%}
                      {%- for k, v in
                      states.sensor.dreamebot_l10_ultra_cleaning_history.attributes.items()
                      -%}
                      {%- if not ns.t and v is mapping and v.completed is
                      defined and v.completed -%}
                      {%- set ns.d = v.timestamp | timestamp_custom('%d %b
                      %H:%M') -%}
                      {%- set ns.t = v.cleaning_time -%}
                      {%- set ns.a = v.cleaned_area -%}
                      {%- endif -%}
                      {%- endfor -%}
                      {{ ns.d }} · {{ ns.t }}m · {{ ns.a }}m²
                    tap_action:
                      action: more-info
                  - type: template
                    entity: sensor.dreamebot_l10_ultra_cleaning_count
                    icon: mdi:chart-box
                    icon_color: indigo
                    content: Stats
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

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

Expected: Passed.

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): L10 Ultra vacuum card with map and stats popup"
```

- [ ] **Step 4: Push and reload**

Run standard recipe. Inspect error log for `l10_ultra` template errors.

- [ ] **Step 5: Service-risk check — `select.select_next`**

Verify the service exists on this HA version:

```bash
source .env && curl -sS -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/services | python3 -c "
import json, sys
services = json.load(sys.stdin)
for block in services:
    if block['domain'] == 'select':
        print('select services:', list(block['services'].keys()))
"
```

Expected output contains `select_next`. If it does not (older HA pre-2024),
replace every `perform_action: select.select_next` in the file with a
`perform_action: select.select_option` block and a Jinja-driven
rotating `data: { option: ... }` — note the substitution in the plan and
recommit.

---

## Task 4: X40 Master vacuum card

**Purpose:** Right half of the vacuums row. Mirrors Task 3 with two
structural differences:
1. X40 has NO `mop_pad_left` or `detergent_left` `%`-sensors, so the
   consumables warning iterates over only four keys.
2. X40 uses string `*_status` sensors (`dust_bag_status`,
   `clean_water_tank_status`, `dirty_water_tank_status`,
   `detergent_status`) for dock-attention instead of the `low_water_warning`
   + `mop_pad` pair used on L10.
3. No room-clean script buttons (grid omitted) — scripts don't exist yet.

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the X40 vertical-stack as the second child of the
  vacuums-row horizontal-stack**

Inside the `horizontal-stack` created in Task 3, after the L10
`vertical-stack` entry (sibling, same indent), add:

```yaml
          - type: vertical-stack
            cards:
              - type: custom:mushroom-vacuum-card
                entity: vacuum.x40_master
                name: First Floor — X40 Master
                icon_animation: true
                commands:
                  - start_pause
                  - stop
                  - locate
                  - return_home
                layout: horizontal

              - type: custom:mushroom-template-card
                entity: vacuum.x40_master
                primary: >-
                  {% set s = states('vacuum.x40_master') %}
                  {% if s in ('docked', 'returning') %}
                  {{ states('sensor.x40_master_battery_level') }}% ·
                  {{ states('sensor.x40_master_status') | replace('_', ' ') |
                  title }}
                  {% else %}
                  {{ states('sensor.x40_master_current_room') }}
                  {% endif %}
                secondary: >-
                  {% set s = states('vacuum.x40_master') %}
                  {% if s in ('docked', 'returning') %}Docked
                  {% else %}
                  {{ states('sensor.x40_master_cleaned_area') | int(0) }} m² ·
                  {{ states('sensor.x40_master_cleaning_time') | int(0) }} min
                  {% endif %}
                icon: >-
                  {% if states('vacuum.x40_master') in ('docked', 'returning')
                  %}mdi:battery{% else %}mdi:broom{% endif %}
                icon_color: >-
                  {% if states('vacuum.x40_master') in ('docked', 'returning')
                  %}green{% else %}blue{% endif %}
                layout: horizontal

              - type: custom:mushroom-template-card
                entity: sensor.x40_master_error
                primary: >-
                  {{ states('sensor.x40_master_error') | replace('_', ' ') |
                  title }}
                secondary: Error
                icon: mdi:alert
                icon_color: red
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.x40_master_error') not in
                      ('no_error', 'unknown', 'unavailable') }}

              - type: picture-entity
                entity: camera.x40_master_map
                camera_image: camera.x40_master_map
                aspect_ratio: "16:10"
                show_state: false
                show_name: false
                visibility:
                  - condition: state
                    entity: vacuum.x40_master
                    state_not: docked
                  - condition: state
                    entity: sensor.x40_master_state
                    state_not: charging_completed

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: select.x40_master_suction_level
                    icon: mdi:fan
                    icon_color: >-
                      {% if states('select.x40_master_suction_level') ==
                      'quiet' %}disabled{% else %}blue{% endif %}
                    content: >-
                      {{ states('select.x40_master_suction_level') | title }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.x40_master_suction_level
                  - type: template
                    entity: select.x40_master_cleaning_mode
                    icon: >-
                      {% set m = states('select.x40_master_cleaning_mode') %}
                      {% if 'mop' in m and 'sweep' in m %}mdi:broom
                      {% elif 'mop' in m %}mdi:water
                      {% else %}mdi:broom{% endif %}
                    icon_color: teal
                    content: >-
                      {{ states('select.x40_master_cleaning_mode') |
                      replace('_', ' ') | title }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.x40_master_cleaning_mode
                  - type: template
                    entity: select.x40_master_mop_pad_humidity
                    icon: mdi:water-percent
                    icon_color: cyan
                    content: >-
                      {{ states('select.x40_master_mop_pad_humidity') | title
                      }}
                    tap_action:
                      action: perform-action
                      perform_action: select.select_next
                      target:
                        entity_id: select.x40_master_mop_pad_humidity
                  - type: template
                    entity: switch.x40_master_dnd
                    icon: mdi:sleep
                    icon_color: >-
                      {% if is_state('switch.x40_master_dnd', 'on') %}green
                      {% else %}disabled{% endif %}
                    content: DnD
                    tap_action:
                      action: perform-action
                      perform_action: switch.toggle
                      target:
                        entity_id: switch.x40_master_dnd

              - type: custom:mushroom-template-card
                entity: sensor.x40_master_filter_left
                primary: Consumables low
                secondary: >-
                  {% set items = namespace(v=[]) %}
                  {% set vals = {
                    'Main brush':
                    states('sensor.x40_master_main_brush_left'),
                    'Side brush':
                    states('sensor.x40_master_side_brush_left'),
                    'Filter':
                    states('sensor.x40_master_filter_left'),
                    'Sensor':
                    states('sensor.x40_master_sensor_dirty_left')
                  } %}
                  {% for name, v in vals.items() %}
                  {% if v not in ('unknown', 'unavailable') and
                  (v | float(100)) < 20 %}
                  {% set items.v = items.v + [name ~ ' ' ~ v ~ '%'] %}
                  {% endif %}
                  {% endfor %}
                  {{ items.v | join(' · ') }}
                icon: mdi:alert
                icon_color: orange
                layout: horizontal
                tap_action:
                  action: more-info
                visibility:
                  - condition: template
                    value_template: >-
                      {% set vals = [
                        states('sensor.x40_master_main_brush_left'),
                        states('sensor.x40_master_side_brush_left'),
                        states('sensor.x40_master_filter_left'),
                        states('sensor.x40_master_sensor_dirty_left')
                      ] %}
                      {{ vals | map('float', 100) | select('lt', 20) |
                      list | length > 0 }}

              - type: custom:mushroom-template-card
                entity: sensor.x40_master_dust_bag_status
                primary: Dock attention
                secondary: >-
                  {% set items = namespace(v=[]) %}
                  {% if states('sensor.x40_master_dust_bag_status') !=
                  'installed' %}
                  {% set items.v = items.v + ['Dust bag'] %}
                  {% endif %}
                  {% if states('sensor.x40_master_clean_water_tank_status') !=
                  'installed' %}
                  {% set items.v = items.v + ['Clean water tank'] %}
                  {% endif %}
                  {% if states('sensor.x40_master_dirty_water_tank_status') !=
                  'installed' %}
                  {% set items.v = items.v + ['Dirty water tank'] %}
                  {% endif %}
                  {% if states('sensor.x40_master_detergent_status') !=
                  'installed' %}
                  {% set items.v = items.v + ['Detergent'] %}
                  {% endif %}
                  {% if states('sensor.x40_master_mop_pad') != 'installed' %}
                  {% set items.v = items.v + ['Mop pad'] %}
                  {% endif %}
                  {{ items.v | join(' · ') }}
                icon: mdi:alert-circle
                icon_color: red
                layout: horizontal
                tap_action:
                  action: more-info
                visibility:
                  - condition: template
                    value_template: >-
                      {{
                      states('sensor.x40_master_dust_bag_status') !=
                      'installed'
                      or
                      states('sensor.x40_master_clean_water_tank_status') !=
                      'installed'
                      or
                      states('sensor.x40_master_dirty_water_tank_status') !=
                      'installed'
                      or
                      states('sensor.x40_master_detergent_status') !=
                      'installed'
                      or
                      states('sensor.x40_master_mop_pad') != 'installed' }}

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: sensor.x40_master_cleaning_history
                    icon: mdi:history
                    icon_color: purple
                    content: >-
                      {%- set ns = namespace(d='', t='', a='') -%}
                      {%- for k, v in
                      states.sensor.x40_master_cleaning_history.attributes.items()
                      -%}
                      {%- if not ns.t and v is mapping and v.completed is
                      defined and v.completed -%}
                      {%- set ns.d = v.timestamp | timestamp_custom('%d %b
                      %H:%M') -%}
                      {%- set ns.t = v.cleaning_time -%}
                      {%- set ns.a = v.cleaned_area -%}
                      {%- endif -%}
                      {%- endfor -%}
                      {{ ns.d }} · {{ ns.t }}m · {{ ns.a }}m²
                    tap_action:
                      action: more-info
                  - type: template
                    entity: sensor.x40_master_cleaning_count
                    icon: mdi:chart-box
                    icon_color: indigo
                    content: Stats
                    tap_action:
                      action: fire-dom-event
                      browser_mod:
                        service: browser_mod.popup
                        data:
                          title: X40 Master — Lifetime stats
                          content:
                            type: entities
                            entities:
                              - sensor.x40_master_cleaning_count
                              - sensor.x40_master_total_cleaned_area
                              - sensor.x40_master_total_cleaning_time
                              - sensor.x40_master_first_cleaning_date
                              - sensor.x40_master_firmware_version
                              - sensor.x40_master_main_brush_time_left
                              - sensor.x40_master_side_brush_time_left
                              - sensor.x40_master_filter_time_left
                              - sensor.x40_master_sensor_dirty_time_left
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): X40 Master vacuum card"
```

- [ ] **Step 4: Push and reload**

Run standard recipe. Error log must have no X40 template errors.

---

## Task 5: Vacuum reminder toggle row

**Purpose:** Slim row between the vacuums and laundry rows. Two
`mushroom-entity-card`s for toggling the `vacuum_reminder_*` automations.

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the reminder row as a sibling of the vacuums
  horizontal-stack**

Still inside the same `cards:` list (one level under `column_span: 3`),
after the vacuums `horizontal-stack`, add:

```yaml
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-entity-card
            entity: automation.vacuum_reminder_ground_floor
            name: Ground Floor reminders
            icon: mdi:bell-ring
            icon_color: >-
              {% if is_state('automation.vacuum_reminder_ground_floor', 'on')
              %}green{% else %}disabled{% endif %}
            tap_action:
              action: perform-action
              perform_action: automation.toggle
              target:
                entity_id: automation.vacuum_reminder_ground_floor
            layout: horizontal

          - type: custom:mushroom-entity-card
            entity: automation.vacuum_reminder_first_floor
            name: First Floor reminders
            icon: mdi:bell-ring
            icon_color: >-
              {% if is_state('automation.vacuum_reminder_first_floor', 'on')
              %}green{% else %}disabled{% endif %}
            tap_action:
              action: perform-action
              perform_action: automation.toggle
              target:
                entity_id: automation.vacuum_reminder_first_floor
            layout: horizontal
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): vacuum reminder toggle row"
```

- [ ] **Step 4: Push and reload**

Standard recipe.

---

## Task 6: Washer card

**Purpose:** Left half of the laundry row. Two mutually-exclusive hero
blocks (running vs idle) selected by `visibility:` on `machine_state` +
a sub-chips row (water temp read-only, spin level read-only, rinse cycles
read-only, bubble soak toggle) + conditional indicator strip (child lock
/ remote control — both hidden when off).

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the laundry-row horizontal-stack with the washer
  vertical-stack as the first child**

After the reminder row, still inside the top-level `cards:` list, add:

```yaml
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: vertical-stack
            cards:
              - type: custom:mushroom-template-card
                entity: sensor.washer_machine_state
                primary: >-
                  {% set ct = states('sensor.washer_completion_time') %}
                  {% if ct not in ('unknown', 'unavailable') %}
                  {{ ((as_timestamp(ct) - as_timestamp(now())) / 60) |
                  round(0) }}m left · finishes {{ as_timestamp(ct) |
                  timestamp_custom('%H:%M') }}
                  {% else %}Running{% endif %}
                secondary: >-
                  {{ states('sensor.washer_job_state') | replace('_', ' ') |
                  title }}
                icon: mdi:washing-machine
                icon_color: blue
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.washer_machine_state') != 'stop' }}

              - type: custom:mushroom-template-card
                entity: sensor.washer_machine_state
                primary: Washer · Idle
                secondary: >-
                  {% set ct = states('sensor.washer_completion_time') %}
                  {% set ed = states('sensor.washer_energy_difference') %}
                  {% if ct not in ('unknown', 'unavailable') %}
                  Last: {{ as_timestamp(ct) | timestamp_custom('%d %b %H:%M')
                  }}
                  {% if ed not in ('unknown', 'unavailable') %}
                  · {{ ed | float(0) | round(2) }} kWh
                  {% endif %}
                  {% else %}No recent runs{% endif %}
                icon: mdi:washing-machine
                icon_color: disabled
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.washer_machine_state') == 'stop' }}

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: select.washer_water_temperature
                    icon: mdi:thermometer
                    icon_color: red
                    content: >-
                      {{ states('select.washer_water_temperature') }}°C
                    tap_action:
                      action: more-info
                  - type: template
                    entity: select.washer_spin_level
                    icon: mdi:rotate-3d-variant
                    icon_color: blue
                    content: >-
                      {{ states('select.washer_spin_level') }} rpm
                    tap_action:
                      action: more-info
                  - type: template
                    entity: number.washer_rinse_cycles
                    icon: mdi:water-sync
                    icon_color: cyan
                    content: >-
                      {{ states('number.washer_rinse_cycles') | int(0) }}×
                    tap_action:
                      action: more-info
                  - type: template
                    entity: switch.washer_bubble_soak
                    icon: mdi:chart-bubble
                    icon_color: >-
                      {% if is_state('switch.washer_bubble_soak', 'on') %}
                      green{% else %}disabled{% endif %}
                    content: Bubble
                    tap_action:
                      action: perform-action
                      perform_action: switch.toggle
                      target:
                        entity_id: switch.washer_bubble_soak

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: binary_sensor.washer_child_lock
                    icon: mdi:lock
                    icon_color: amber
                    content: Child lock
                    tap_action:
                      action: more-info
                    visibility:
                      - condition: state
                        entity: binary_sensor.washer_child_lock
                        state: "on"
                  - type: template
                    entity: binary_sensor.washer_remote_control
                    icon: mdi:remote
                    icon_color: green
                    content: Remote
                    tap_action:
                      action: more-info
                    visibility:
                      - condition: state
                        entity: binary_sensor.washer_remote_control
                        state: "on"
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): washer card with countdown and settings chips"
```

- [ ] **Step 4: Push and reload**

Standard recipe. Error log must be clean.

---

## Task 7: Dryer card

**Purpose:** Right half of the laundry row. Same structure as the washer
card (Task 6), but with dryer entities, amber icon color when running,
and a dryer-specific sub-chips row (wrinkle prevent toggle, wrinkle
prevent active indicator, last-cycle energy).

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the dryer vertical-stack as the second child of the
  laundry-row horizontal-stack**

Inside the laundry-row `horizontal-stack` (from Task 6), after the washer
vertical-stack, add as a sibling:

```yaml
          - type: vertical-stack
            cards:
              - type: custom:mushroom-template-card
                entity: sensor.tumble_dryer_machine_state
                primary: >-
                  {% set ct = states('sensor.tumble_dryer_completion_time') %}
                  {% if ct not in ('unknown', 'unavailable') %}
                  {{ ((as_timestamp(ct) - as_timestamp(now())) / 60) |
                  round(0) }}m left · finishes {{ as_timestamp(ct) |
                  timestamp_custom('%H:%M') }}
                  {% else %}Running{% endif %}
                secondary: >-
                  {{ states('sensor.tumble_dryer_job_state') | replace('_', ' ')
                  | title }}
                icon: mdi:tumble-dryer
                icon_color: amber
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.tumble_dryer_machine_state') !=
                      'stop' }}

              - type: custom:mushroom-template-card
                entity: sensor.tumble_dryer_machine_state
                primary: Dryer · Idle
                secondary: >-
                  {% set ct = states('sensor.tumble_dryer_completion_time') %}
                  {% set ed =
                  states('sensor.tumble_dryer_energy_difference') %}
                  {% if ct not in ('unknown', 'unavailable') %}
                  Last: {{ as_timestamp(ct) | timestamp_custom('%d %b %H:%M')
                  }}
                  {% if ed not in ('unknown', 'unavailable') %}
                  · {{ ed | float(0) | round(2) }} kWh
                  {% endif %}
                  {% else %}No recent runs{% endif %}
                icon: mdi:tumble-dryer
                icon_color: disabled
                layout: horizontal
                visibility:
                  - condition: template
                    value_template: >-
                      {{ states('sensor.tumble_dryer_machine_state') ==
                      'stop' }}

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: switch.tumble_dryer_wrinkle_prevent
                    icon: mdi:iron-outline
                    icon_color: >-
                      {% if is_state('switch.tumble_dryer_wrinkle_prevent',
                      'on') %}green{% else %}disabled{% endif %}
                    content: Wrinkle
                    tap_action:
                      action: perform-action
                      perform_action: switch.toggle
                      target:
                        entity_id: switch.tumble_dryer_wrinkle_prevent
                  - type: template
                    entity: binary_sensor.tumble_dryer_wrinkle_prevent_active
                    icon: mdi:auto-fix
                    icon_color: amber
                    content: Active
                    tap_action:
                      action: more-info
                    visibility:
                      - condition: state
                        entity:
                          binary_sensor.tumble_dryer_wrinkle_prevent_active
                        state: "on"
                  - type: template
                    entity: sensor.tumble_dryer_energy_difference
                    icon: mdi:flash
                    icon_color: yellow
                    content: >-
                      {{
                      states('sensor.tumble_dryer_energy_difference') |
                      float(0) | round(2) }} kWh
                    tap_action:
                      action: more-info

              - type: custom:mushroom-chips-card
                chips:
                  - type: template
                    entity: binary_sensor.tumble_dryer_child_lock
                    icon: mdi:lock
                    icon_color: amber
                    content: Child lock
                    tap_action:
                      action: more-info
                    visibility:
                      - condition: state
                        entity: binary_sensor.tumble_dryer_child_lock
                        state: "on"
                  - type: template
                    entity: binary_sensor.tumble_dryer_remote_control
                    icon: mdi:remote
                    icon_color: green
                    content: Remote
                    tap_action:
                      action: more-info
                    visibility:
                      - condition: state
                        entity: binary_sensor.tumble_dryer_remote_control
                        state: "on"
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): dryer card with wrinkle prevent and energy chip"
```

- [ ] **Step 4: Push and reload**

Standard recipe. Clean error log.

---

## Task 8: Laundry door chip + full visual verification

**Purpose:** Append the full-width laundry-door chip under the laundry
row, then run a comprehensive Playwright pass across idle + simulated
active states to catch any layout regression.

**Files:**
- Modify: `dashboards/tablet/appliances.yaml`

- [ ] **Step 1: Append the laundry-door chip as the last card**

After the laundry-row `horizontal-stack`, still inside the top-level
`cards:` list, add:

```yaml
      - type: custom:mushroom-template-card
        entity: binary_sensor.laundry_doors
        grid_options:
          columns: full
        primary: Laundry door
        secondary: >-
          {% if is_state('binary_sensor.laundry_doors', 'on') %}Open
          {% else %}Closed{% endif %}
        icon: >-
          {% if is_state('binary_sensor.laundry_doors', 'on') %}mdi:door-open
          {% else %}mdi:door-closed{% endif %}
        icon_color: >-
          {% if is_state('binary_sensor.laundry_doors', 'on') %}amber
          {% else %}disabled{% endif %}
        layout: horizontal
        tap_action:
          action: more-info
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "feat(dashboard): laundry door chip"
```

- [ ] **Step 4: Push and reload**

Standard recipe. Final clean error log expected.

- [ ] **Step 5: Playwright — idle state full screenshot**

Open a Chromium browser at viewport 1280×800 (tablet landscape). Log in
using the HA token from `.env`. Force-refetch the Lovelace config via the
WebSocket bridge before navigating (per `references/verify.md` in the
ha-dashboards skill). Then navigate to
`http://homeassistant.local:8123/wall-tablet/appliances` and screenshot.

Verify visually:
- Status strip spans the full viewport width — four chips visible with
  no side whitespace.
- L10 Ultra card and X40 Master card sit side-by-side at ~50%/50%.
- Both vacuum cards show "Docked" state in their status line.
- No live map is rendered (both docked).
- No "Consumables low" or "Dock attention" card is rendered (healthy
  state).
- Settings chip row (Suction / Mode / Humidity / DnD) renders with
  current values.
- Reminder row shows both automations with a green bell if on.
- Washer card shows "Washer · Idle" with "Last: <timestamp>".
- Dryer card shows "Dryer · Idle" with "Last: <timestamp>".
- Laundry door chip at the bottom shows "Closed".

- [ ] **Step 6: Playwright — sanity check chip tap actions**

For each of the four settings chips on the L10 card, simulate a click
and observe via `curl /api/states/select.dreamebot_l10_ultra_suction_level`
that the state changes to the next option within 3 seconds. Reset after:

```bash
source .env && curl -sS -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  http://homeassistant.local:8123/api/services/select/select_option \
  --data '{"entity_id":"select.dreamebot_l10_ultra_suction_level","option":"strong"}' \
  -o /dev/null -w "HTTP %{http_code}\n"
```

If any chip tap fails (state does not advance), the `select.select_next`
service is not supported on this HA version. Stop and apply the
fallback from Task 3, Step 5.

- [ ] **Step 7: Playwright — stats popup**

Click the "Stats" chip on the L10 card. Confirm a modal opens titled
"L10 Ultra — Lifetime stats" containing 11 entity rows (cleaning count,
total area, total time, first cleaning date, firmware version, and six
consumable time-left sensors). Close it; repeat for the X40 card (9
rows).

- [ ] **Step 8: Playwright — simulated running state for the washer**

Temporarily set the washer machine state to `run` to verify the
running hero renders. This goes through `set_state` via REST (idempotent
snapshot — reset after):

```bash
# snapshot current state
source .env && BEFORE=$(curl -sS -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states/sensor.washer_machine_state \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['state'])")
echo "Washer was: $BEFORE"

# fake-set to run
curl -sS -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  http://homeassistant.local:8123/api/states/sensor.washer_machine_state \
  --data '{"state":"run"}' -o /dev/null -w "HTTP %{http_code}\n"
```

Screenshot the washer card — confirm it now shows "Nm left · finishes
HH:MM" with a blue spinning icon. Then restore:

```bash
curl -sS -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  http://homeassistant.local:8123/api/states/sensor.washer_machine_state \
  --data "{\"state\":\"$BEFORE\"}" -o /dev/null -w "HTTP %{http_code}\n"
```

Note: the Samsung integration will overwrite this state on its next
poll (seconds to a minute). The snapshot is only a visual sanity check,
not a behaviour change. Skip this step if the washer is already running.

- [ ] **Step 9: Open PR (if one does not already exist)**

```bash
gh pr list --head chore/dashboard-redesign
```

If no open PR exists, create one:

```bash
gh pr create --title "Redesign tablet appliances view" --body "$(cat <<'EOF'
## Summary
- Full-width single-section appliances view with four-chip status strip
- Conditional live vacuum map (visible only when cleaning)
- One-tap settings chips (suction / mode / mop humidity / DnD)
- Silent-until-relevant consumables & dock warnings
- Laundry countdown hero + Samsung-settings chips
- Lifetime stats popup via browser_mod

## Test plan
- [x] Pre-commit passes
- [x] No template errors in `/api/error_log` after reload
- [x] Playwright: status strip full-width, vacuums side-by-side, laundry
      shows idle and running hero variants
- [x] Chip tap cycles select options
- [x] Stats popup renders for both vacuums
EOF
)"
```

---

## Self-review checklist

After implementing all 8 tasks, confirm:

- [ ] Spec §1 layout: status strip → vacuums row → reminder row → laundry
      row → door chip — all 5 blocks present.
- [ ] Spec §2 status strip: 4 chips, active-state templates, more-info
      tap — done in Task 2.
- [ ] Spec §3 vacuum card: all 8 sub-blocks (hero, status line, error,
      map, settings chips, room scripts L10 only, consumables warn, dock
      warn, footer) — done in Tasks 3 and 4.
- [ ] Spec §4 reminder row: both automations togglable — Task 5.
- [ ] Spec §5 laundry: running/idle hero, per-appliance sub-chips,
      conditional indicator strip — Tasks 6 and 7.
- [ ] Spec §6 laundry door: full-width chip — Task 8.
- [ ] Every Jinja numeric pipe goes through `float(0)` / `int(0)`.
- [ ] Every `completion_time` access is guarded against `unknown` /
      `unavailable`.
- [ ] Every `state_attr` default uses `| default('v', true)`.
- [ ] Every top-level child card has `grid_options: { columns: full }`.
- [ ] `tap_action` uses `perform_action:` (not `service:`).
- [ ] No new helpers, template sensors, or automations added.

If any line is unchecked, go back to the corresponding task.
