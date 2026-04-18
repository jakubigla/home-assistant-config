# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the single-file tablet dashboard to a multi-dashboard, multi-tab system (tablet + phone) with 8 tablet tabs and 4 phone tabs, each in its own file under `dashboards/tablet/` and `dashboards/phone/`.

**Architecture:** Thin top-level dashboard files (`tablet.yaml`, `phone.yaml`) stitch together per-tab includes. Each tab ≤ ~300 lines. New dashboard registered via `lovelace.dashboards` in `configuration.yaml`. Visual language preserved (Mushroom cards, card-mod styling, existing semantic colours).

**Tech Stack:** Home Assistant YAML, Mushroom card family, card-mod, mass-player-card, Jinja2 templates, pre-commit (yamllint), `uv` for Python tooling.

**Spec:** [`docs/superpowers/specs/2026-04-18-dashboard-redesign-design.md`](../specs/2026-04-18-dashboard-redesign-design.md)

---

## Conventions for every task

- **Verification cadence per task:** (1) `uv run pre-commit run --all-files`, (2) HA config check if YAML affects core (non-dashboard), (3) push to remote so HA auto-pulls, (4) load dashboard in a browser at `http://homeassistant.local:8123/<path>` and confirm no card errors.
- **Playwright MCP** is available for UI verification when a task says "verify in browser" — take a screenshot and check for red error toasts or card-level "Custom element not found" messages.
- **Deploy:** HA auto-pulls from the current branch. Push after each task so changes go live.
- **Commit message style:** match recent repo style — `feat(dashboard): ...`, `chore(dashboard): ...`, `refactor(dashboard): ...`.
- **Never push to `main`.** Work on the current branch (`chore/dashboard-redesign`) or a task-specific branch and open a PR when ready.
- **DRY:** if a card block is duplicated across files, extract to a template sensor or YAML anchor.

---

## Task 1: Scaffold file structure and register phone dashboard

**Files:**
- Create: `dashboards/tablet/home.yaml`
- Create: `dashboards/tablet/settings.yaml`
- Create: `dashboards/tablet/doorbell.yaml`
- Modify (rewrite): `dashboards/tablet.yaml`
- Create: `dashboards/phone.yaml`
- Create: `dashboards/phone/home.yaml` (placeholder)
- Modify: `configuration.yaml:46-60` (dashboards block)

- [ ] **Step 1: Extract current Home view into `dashboards/tablet/home.yaml`**

Copy the entire first view block from the existing `dashboards/tablet.yaml` (lines ~4–801 — the view with `path: home`) into a new file `dashboards/tablet/home.yaml`. The new file's structure:

```yaml
---
title: Home
path: home
icon: mdi:home
type: sections
max_columns: 4
sections:
  # ...paste the three existing sections here verbatim...
```

Strip the outer `views:` / list-dash; the file's top level is the view object.

- [ ] **Step 2: Extract Settings view into `dashboards/tablet/settings.yaml`**

Copy the Settings view block (existing lines ~882–904) into the new file with the same pattern: top level = the view object, no `views:` wrapper.

- [ ] **Step 3: Extract Doorbell view into `dashboards/tablet/doorbell.yaml`**

Copy the Doorbell view block (existing lines ~905–916) into the new file:

```yaml
---
title: Doorbell
path: doorbell
type: panel
visible: false
cards:
  - type: picture-entity
    entity: camera.doorbell_rtsp
    camera_view: live
    show_state: false
    show_name: false
```

- [ ] **Step 4: Rewrite `dashboards/tablet.yaml` as a thin stitching file**

Replace `dashboards/tablet.yaml` entirely with:

```yaml
---
title: Tablet Dashboard
views:
  - !include tablet/home.yaml
  - !include tablet/settings.yaml
  - !include tablet/doorbell.yaml
```

The current Bedroom view is intentionally dropped (not included). Future specialty tabs (Climate, Media, Appliances, Outdoor, Security, Energy) will be added in later tasks.

- [ ] **Step 5: Create placeholder phone dashboard files**

Create `dashboards/phone/home.yaml`:

```yaml
---
title: Home
path: home
icon: mdi:home
type: sections
max_columns: 1
sections:
  - cards:
      - type: markdown
        content: "Phone dashboard — under construction"
```

Create `dashboards/phone.yaml`:

```yaml
---
title: Phone
views:
  - !include phone/home.yaml
```

- [ ] **Step 6: Register phone dashboard in `configuration.yaml`**

Edit `configuration.yaml` lovelace.dashboards block (lines 46–60). Add a `phone` entry after `energy-monitor`:

```yaml
  dashboards:
    wall-tablet:
      mode: yaml
      filename: dashboards/tablet.yaml
      title: Tablet
      icon: mdi:tablet
      show_in_sidebar: true
      require_admin: false
    energy-monitor:
      mode: yaml
      filename: dashboards/energy.yaml
      title: Energy
      icon: mdi:lightning-bolt
      show_in_sidebar: true
      require_admin: false
    phone:
      mode: yaml
      filename: dashboards/phone.yaml
      title: Phone
      icon: mdi:cellphone
      show_in_sidebar: true
      require_admin: false
```

- [ ] **Step 7: Run pre-commit**

Run: `uv run pre-commit run --all-files`
Expected: PASS (yamllint, end-of-files, etc.)

- [ ] **Step 8: Commit**

```bash
git add configuration.yaml dashboards/tablet.yaml dashboards/tablet/ dashboards/phone.yaml dashboards/phone/
git commit -m "$(cat <<'EOF'
chore(dashboard): scaffold per-tab file structure

Split monolithic tablet.yaml into per-view includes under dashboards/tablet/.
Drop the Bedroom view (now covered by Home + planned specialty tabs).
Register a new `phone` dashboard with a placeholder Home view.
EOF
)"
```

- [ ] **Step 9: Push and verify in browser**

Run: `git push`

Open `http://homeassistant.local:8123/wall-tablet/home` — confirm it renders identically to before (status column, lights, media, vacuums, curtains). Open `http://homeassistant.local:8123/phone/home` — confirm the "under construction" placeholder renders. Open `http://homeassistant.local:8123/wall-tablet/settings` and `/wall-tablet/doorbell` — confirm both still work.

If any page shows a 404 or blank view, HA needs a dashboard-config reload: via UI Developer Tools → YAML → Reload Lovelace, or restart the HA core.

---

## Task 2: Extract alarm-readiness Jinja into template sensors

**Files:**
- Create: `packages/bootstrap/templates/binary_sensors/home_ready_to_arm.yaml`
- Create: `packages/bootstrap/templates/sensors/home_status_counts.yaml`
- Create (dir): `packages/bootstrap/templates/sensors/` if not already existing
- Modify: `dashboards/tablet/home.yaml` — replace the 5 Jinja duplications with state reads
- Modify: `packages/bootstrap/config.yaml` — ensure `!include_dir_list templates` picks up nested sensors (verify current pattern)

- [ ] **Step 1: Verify template include pattern**

Check how templates are currently wired. Read `packages/bootstrap/config.yaml`:

```
template: !include_dir_list templates
```

Then check that `!include_dir_list templates` recursively finds nested dirs. Current structure is `templates/binary_sensors/*.yaml`. Adding `templates/sensors/*.yaml` should work. If not, we'll use explicit includes.

Run:

```bash
ls packages/bootstrap/templates/
```

Expected output: `binary_sensors` (and possibly other already-present dirs). Our new `sensors/` dir will sit alongside.

- [ ] **Step 2: Create `home_ready_to_arm` binary sensor**

Create `packages/bootstrap/templates/binary_sensors/home_ready_to_arm.yaml`:

```yaml
---
binary_sensor:
  - name: home_ready_to_arm
    state: >
      {% set doors = [
        states('binary_sensor.terrace_left_door'),
        states('binary_sensor.terrace_main_door'),
        states('binary_sensor.balcony_door'),
        states('binary_sensor.garage_door')
      ] %}
      {% set presence = [
        states('binary_sensor.bedroom_entrance_presence'),
        states('binary_sensor.bathroom_presence'),
        states('binary_sensor.first_floor_corridor_presence'),
        states('binary_sensor.laundry_room_sensor_occupancy'),
        states('binary_sensor.bedroom_wardrobe_occupancy')
      ] %}
      {% set open_doors = doors | select('eq', 'on') | list | count %}
      {% set occupied = presence | select('eq', 'on') | list | count %}
      {% set any_bad = (doors + presence) | reject('in', ['on', 'off']) | list | count > 0 %}
      {{ open_doors == 0 and occupied == 0 and not any_bad }}
    attributes:
      open_doors_count: >
        {% set doors = [
          states('binary_sensor.terrace_left_door'),
          states('binary_sensor.terrace_main_door'),
          states('binary_sensor.balcony_door'),
          states('binary_sensor.garage_door')
        ] %}
        {{ doors | select('eq', 'on') | list | count }}
      occupied_zones_count: >
        {% set presence = [
          states('binary_sensor.bedroom_entrance_presence'),
          states('binary_sensor.bathroom_presence'),
          states('binary_sensor.first_floor_corridor_presence'),
          states('binary_sensor.laundry_room_sensor_occupancy'),
          states('binary_sensor.bedroom_wardrobe_occupancy')
        ] %}
        {{ presence | select('eq', 'on') | list | count }}
```

> **Note:** original spec used `binary_sensor.bedroom_presence` and `device_class: safety`; both were corrected during Task 2 review (entity didn't exist in HA; safety class is inverted for `on=safe` semantics).

- [ ] **Step 3: Update `dashboards/tablet/home.yaml` to read from the new sensor**

Replace the 3 Jinja duplications inside the `mushroom-template-card` (icon, icon_color, primary) with reads from `binary_sensor.home_ready_to_arm`:

```yaml
- type: custom:mushroom-template-card
  entity: alarm_control_panel.main
  icon: "{{ 'mdi:shield-check' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'mdi:shield-alert' }}"
  icon_color: "{{ 'green' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'red' }}"
  primary: "{{ 'Ready to Arm' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'Not Ready' }}"
  layout: vertical
  tap_action:
    action: more-info
  card_mod:
    style: |
      ha-card { font-size: 18px; }
```

Also replace the 1F occupancy chip to read from `state_attr('binary_sensor.home_ready_to_arm', 'occupied_zones_count')`:

```yaml
- type: template
  icon: mdi:home-floor-1
  icon_color: "{{ 'red' if (state_attr('binary_sensor.home_ready_to_arm', 'occupied_zones_count') | int(0)) > 0 else 'green' }}"
  content: >
    {% set c = state_attr('binary_sensor.home_ready_to_arm', 'occupied_zones_count') | int(0) %}
    {{ '1F: ' ~ c ~ ' zone' ~ ('s' if c != 1) if c > 0 else '1F: Clear' }}
```

- [ ] **Step 4: Run HA config check and reload templates**

First, run pre-commit:

```bash
uv run pre-commit run --all-files
```

Expected: PASS.

Then push and trigger HA template reload. Via HA MCP (`mcp__HomeAssistant__HassTurnOn` with the relevant reload service) or via the dev panel UI. Simpler: push and wait for HA to pull, then in the HA UI go to Developer Tools → YAML → Reload Template Entities. Confirm `binary_sensor.home_ready_to_arm` appears in Developer Tools → States.

- [ ] **Step 5: Verify dashboard still renders**

Open `http://homeassistant.local:8123/wall-tablet/home`. The alarm card should look identical. Toggle a door open (e.g., `binary_sensor.terrace_left_door` via HA MCP) and watch the alarm card flip to "Not Ready" — confirms the sensor works.

- [ ] **Step 6: Commit and push**

```bash
git add packages/bootstrap/templates/binary_sensors/home_ready_to_arm.yaml dashboards/tablet/home.yaml
git commit -m "$(cat <<'EOF'
refactor(dashboard): extract alarm-readiness template sensor

Collapse 5 duplicated Jinja blocks on the Home view into a single
binary_sensor.home_ready_to_arm with count attributes. Cards now just
read state, simplifying future dashboard edits.
EOF
)"
git push
```

---

## Task 3: Tablet Appliances tab

**Files:**
- Create: `dashboards/tablet/appliances.yaml`
- Modify: `dashboards/tablet.yaml` — add `- !include tablet/appliances.yaml`

- [ ] **Step 1: Create `dashboards/tablet/appliances.yaml`**

Three-column `sections` layout: Vacuums, Laundry, Humidifiers.

```yaml
---
title: Appliances
path: appliances
icon: mdi:washing-machine
type: sections
max_columns: 3
sections:
  - title: Vacuums
    cards:
      - type: heading
        heading: Ground Floor — Dreame L10 Ultra
        heading_style: subtitle
      - type: custom:mushroom-vacuum-card
        entity: vacuum.dreamebot_l10_ultra
        name: Ground Floor
        icon_animation: true
        commands:
          - start_pause
          - stop
          - locate
          - return_home
        layout: horizontal
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            entity: sensor.dreamebot_l10_ultra_battery_level
            icon: mdi:battery
            icon_color: green
            content: "{{ states('sensor.dreamebot_l10_ultra_battery_level') }}%"
            tap_action: { action: more-info }
          - type: template
            entity: sensor.dreamebot_l10_ultra_filter_left
            icon: mdi:air-filter
            icon_color: blue
            content: "{{ states('sensor.dreamebot_l10_ultra_filter_left') }}%"
            tap_action: { action: more-info }
          - type: template
            entity: sensor.dreamebot_l10_ultra_cleaning_history
            icon: mdi:history
            icon_color: purple
            content: >-
              {%- set ns = namespace(d='', t='', a='') -%}
              {%- for k, v in states.sensor.dreamebot_l10_ultra_cleaning_history.attributes.items() -%}
                {%- if not ns.t and v is mapping and v.completed is defined and v.completed -%}
                  {%- set ns.d = v.timestamp | timestamp_custom('%d %b %H:%M') -%}
                  {%- set ns.t = v.cleaning_time -%}
                  {%- set ns.a = v.cleaned_area -%}
                {%- endif -%}
              {%- endfor -%}
              {{ ns.d }} · {{ ns.t }} · {{ ns.a }}
            tap_action: { action: more-info }
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
              target: { entity_id: script.vacuum_clean_mudroom }
          - type: custom:mushroom-template-card
            entity: script.vacuum_clean_kitchen
            primary: Clean Kitchen
            icon: mdi:silverware-fork-knife
            icon_color: orange
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target: { entity_id: script.vacuum_clean_kitchen }
      - type: heading
        heading: First Floor — X40 Master
        heading_style: subtitle
      - type: custom:mushroom-vacuum-card
        entity: vacuum.x40_master
        name: First Floor
        icon_animation: true
        commands: [start_pause, stop, locate, return_home]
        layout: horizontal
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            entity: sensor.x40_master_battery_level
            icon: mdi:battery
            icon_color: green
            content: "{{ states('sensor.x40_master_battery_level') }}%"
            tap_action: { action: more-info }
          - type: template
            entity: sensor.x40_master_filter_left
            icon: mdi:air-filter
            icon_color: blue
            content: "{{ states('sensor.x40_master_filter_left') }}%"
            tap_action: { action: more-info }
          - type: template
            entity: sensor.x40_master_cleaning_history
            icon: mdi:history
            icon_color: purple
            content: >-
              {%- set ns = namespace(d='', t='', a='') -%}
              {%- for k, v in states.sensor.x40_master_cleaning_history.attributes.items() -%}
                {%- if not ns.t and v is mapping and v.completed is defined and v.completed -%}
                  {%- set ns.d = v.timestamp | timestamp_custom('%d %b %H:%M') -%}
                  {%- set ns.t = v.cleaning_time -%}
                  {%- set ns.a = v.cleaned_area -%}
                {%- endif -%}
              {%- endfor -%}
              {{ ns.d }} · {{ ns.t }} · {{ ns.a }}
            tap_action: { action: more-info }
      # Attic vacuum placeholder — uncomment & update entity IDs when added.
      # - type: heading
      #   heading: Attic
      #   heading_style: subtitle
      # - type: custom:mushroom-vacuum-card
      #   entity: vacuum.attic_placeholder
      #   ...

  - title: Laundry
    cards:
      - type: heading
        heading: Washer
        heading_style: subtitle
      - type: custom:mushroom-template-card
        entity: binary_sensor.washer_power
        icon: mdi:washing-machine
        icon_color: "{{ 'blue' if is_state('binary_sensor.washer_power', 'on') else 'disabled' }}"
        primary: Washer
        secondary: "{{ 'Running' if is_state('binary_sensor.washer_power', 'on') else 'Idle' }}"
        layout: horizontal
        tap_action: { action: more-info }
      - type: heading
        heading: Dryer
        heading_style: subtitle
      - type: custom:mushroom-template-card
        entity: binary_sensor.tumble_dryer_power
        icon: mdi:tumble-dryer
        icon_color: "{{ 'blue' if is_state('binary_sensor.tumble_dryer_power', 'on') else 'disabled' }}"
        primary: Dryer
        secondary: "{{ 'Running' if is_state('binary_sensor.tumble_dryer_power', 'on') else 'Idle' }}"
        layout: horizontal
        tap_action: { action: more-info }

  - title: Humidifiers
    cards:
      - type: custom:mushroom-entity-card
        entity: humidifier.living_room
        name: Living Room
        layout: horizontal
        tap_action: { action: more-info }
      - type: custom:mushroom-entity-card
        entity: humidifier.bedroom
        name: Bedroom
        layout: horizontal
        tap_action: { action: more-info }
```

- [ ] **Step 2: Register Appliances view in `dashboards/tablet.yaml`**

Add the include after Home:

```yaml
---
title: Tablet Dashboard
views:
  - !include tablet/home.yaml
  - !include tablet/appliances.yaml
  - !include tablet/settings.yaml
  - !include tablet/doorbell.yaml
```

- [ ] **Step 3: Pre-commit**

Run: `uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 4: Push, verify**

```bash
git add dashboards/tablet/appliances.yaml dashboards/tablet.yaml
git commit -m "feat(dashboard): add Appliances tab (tablet)"
git push
```

Open `http://homeassistant.local:8123/wall-tablet/appliances`. Verify: both vacuum cards render, clean-room buttons present, washer/dryer cards show correct state, humidifier entities present.

---

## Task 4: Tablet Climate tab

**Files:**
- Create: `dashboards/tablet/climate.yaml`
- Modify: `dashboards/tablet.yaml`
- Modify: `dashboards/tablet/home.yaml` — remove the bottom curtains list (moved here)

- [ ] **Step 1: Create `dashboards/tablet/climate.yaml`**

Three columns: Thermostats & Humidifiers, Per-Area Environment, Curtains.

```yaml
---
title: Climate
path: climate
icon: mdi:thermostat
type: sections
max_columns: 3
sections:
  - title: Thermostats
    cards:
      - type: thermostat
        entity: climate.living_room
        name: Living Room
      - type: thermostat
        entity: climate.bedroom
        name: Bedroom
      - type: humidifier
        entity: humidifier.living_room
        name: Living Room Humidifier
      - type: humidifier
        entity: humidifier.bedroom
        name: Bedroom Humidifier

  - title: Per-Area Environment
    cards:
      - type: entities
        title: Temperature
        entities:
          - sensor.living_room_hygro_temperature
          - sensor.bedroom_hygro_temperature
          # Add other area hygro sensors as they become available.
      - type: entities
        title: Humidity
        entities:
          - sensor.living_room_hygro_humidity
          - sensor.bedroom_hygro_humidity
      - type: history-graph
        title: Living Room (24h)
        hours_to_show: 24
        entities:
          - sensor.living_room_hygro_temperature
          - sensor.living_room_hygro_humidity
      - type: history-graph
        title: Bedroom (24h)
        hours_to_show: 24
        entities:
          - sensor.bedroom_hygro_temperature
          - sensor.bedroom_hygro_humidity

  - title: Curtains
    cards:
      - type: custom:mushroom-cover-card
        entity: cover.ground_floor
        name: All Ground Floor
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
      - type: custom:mushroom-cover-card
        entity: cover.living_room_main
        name: Living Room Main
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
      - type: custom:mushroom-cover-card
        entity: cover.living_room_left
        name: Living Room Left
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
      - type: custom:mushroom-cover-card
        entity: cover.bedroom
        name: Bedroom
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
```

- [ ] **Step 2: Remove the curtains block from `dashboards/tablet/home.yaml`**

In `home.yaml`, delete the block that starts with `- type: heading\n    heading: Curtains` and continues through all four `mushroom-cover-card` entries plus the trailing markdown separator. This block lives in the third section (Appliances/Curtains column in the current layout).

- [ ] **Step 3: Register Climate view**

Update `dashboards/tablet.yaml`:

```yaml
---
title: Tablet Dashboard
views:
  - !include tablet/home.yaml
  - !include tablet/climate.yaml
  - !include tablet/appliances.yaml
  - !include tablet/settings.yaml
  - !include tablet/doorbell.yaml
```

- [ ] **Step 4: Pre-commit, commit, push**

```bash
uv run pre-commit run --all-files
git add dashboards/tablet/climate.yaml dashboards/tablet/home.yaml dashboards/tablet.yaml
git commit -m "feat(dashboard): add Climate tab, move curtains off Home"
git push
```

- [ ] **Step 5: Verify**

Open `http://homeassistant.local:8123/wall-tablet/climate`. Verify thermostats, humidifiers, graphs, and all four covers render. Reopen `/wall-tablet/home` — confirm curtains block is gone without layout breakage.

---

## Task 5: Tablet Media tab

**Files:**
- Create: `dashboards/tablet/media.yaml`
- Modify: `dashboards/tablet.yaml`
- Modify: `dashboards/tablet/home.yaml` — remove voice-music-search-card (moves to Media)

- [ ] **Step 1: Create `dashboards/tablet/media.yaml`**

Three sections; `mass-player-card` isolated in its own section (crash containment).

```yaml
---
title: Media
path: media
icon: mdi:music
type: sections
max_columns: 3
sections:
  - title: Playback
    cards:
      - type: custom:mass-player-card
        entity: media_player.living_room_tv
      # Constrain visual dominance via card-mod if the card renders too large:
      # - add card_mod style capping max-height or width here after step 5 visual check.

  - title: Now Playing & Quick-Play
    cards:
      - type: custom:mushroom-media-player-card
        entity: media_player.living_room_tv
        layout: horizontal
        show_volume_level: true
        use_media_info: true
        volume_controls: [volume_set]
        media_controls: [previous, play_pause_stop, next]
      - type: grid
        columns: 3
        square: false
        cards:
          - type: custom:mushroom-template-card
            primary: Discover Weekly
            icon: mdi:playlist-star
            icon_color: green
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target: { entity_id: script.music_play_discover_weekly }
          - type: custom:mushroom-template-card
            primary: Random Playlist
            icon: mdi:shuffle-variant
            icon_color: purple
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target: { entity_id: script.music_play_random_playlist }
          - type: custom:mushroom-template-card
            primary: Last Played
            icon: mdi:history
            icon_color: blue
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target: { entity_id: script.music_play_last_played }
      - type: custom:voice-music-search-card

  - title: Scene System
    cards:
      - type: markdown
        content: |
          **Living Room Scenes**

          Use the Aqara Cube to cycle scenes:
          - **Shake** — next scene
          - **Flip 90°** — previous scene
          - **Tap** — confirm / apply

          Current scene shown below.
      - type: custom:mushroom-entity-card
        entity: input_select.living_room_scene
        name: Active Scene
        layout: horizontal
        tap_action: { action: more-info }
```

> **Note on `input_select.living_room_scene`:** if the scene-system entity ID is different in this repo, update it here. Grep for `living_room_scene` under `packages/areas/ground-floor/living-room/` to confirm.

- [ ] **Step 2: Remove voice-music-search-card from Home**

In `dashboards/tablet/home.yaml`, delete the line `- type: custom:voice-music-search-card` (it's at the bottom of the Media section on the current Home).

- [ ] **Step 3: Register Media view**

Update `dashboards/tablet.yaml` — add `- !include tablet/media.yaml` after Climate.

- [ ] **Step 4: Pre-commit, commit, push**

```bash
uv run pre-commit run --all-files
git add dashboards/tablet/media.yaml dashboards/tablet/home.yaml dashboards/tablet.yaml
git commit -m "feat(dashboard): add Media tab with mass-player-card"
git push
```

- [ ] **Step 5: Verify — watch for mass-player-card crash**

Open `http://homeassistant.local:8123/wall-tablet/media`. If the `mass-player-card` shows a red error box ("Custom element not found" or `TypeError: Cannot set properties of undefined`), check:

1. Is `mass-player-card.js` loaded? Confirm `configuration.yaml` lovelace.resources includes `mass-player-card`.
2. Is the "Music Assistant Queue Actions" HACS integration installed? If not, install it (required dep).
3. Is `media_player.living_room_tv` the correct entity for Music Assistant? If Music Assistant exposes a separate `media_player.*_mass` entity, point at that instead.

If the card dominates vertical space, add a card-mod wrapper:

```yaml
- type: custom:mass-player-card
  entity: media_player.living_room_tv
  card_mod:
    style: |
      ha-card { max-height: 420px; overflow: auto; }
```

---

## Task 6: Tablet Outdoor tab

**Files:**
- Create: `dashboards/tablet/outdoor.yaml`
- Modify: `dashboards/tablet.yaml`

- [ ] **Step 1: Survey outdoor entities**

Run:

```bash
ls packages/areas/outdoor/garden/scripts/
```

```bash
grep -r "cover.pergola\|cover.gate\|light.porch\|light.terrace\|switch.gate\|binary_sensor.gate" packages/ | head -40
```

Use the output to populate the outdoor dashboard with real entity IDs. Common ones from spec: garden irrigation mode select, pergola `cover.pergola_roof` or similar, gate state + trigger, porch + terrace lights, forecast.

- [ ] **Step 2: Create `dashboards/tablet/outdoor.yaml`**

Three sections; entity IDs to verify in Step 1.

```yaml
---
title: Outdoor
path: outdoor
icon: mdi:tree
type: sections
max_columns: 3
sections:
  - title: Garden
    cards:
      - type: custom:mushroom-select-card
        entity: input_select.garden_irrigation_mode
        name: Irrigation Mode
        icon: mdi:sprinkler-variant
        layout: horizontal
      # Add zone switches / schedule cards once verified
      # (entity IDs from packages/areas/outdoor/garden/)

  - title: Pergola, Gate & Lights
    cards:
      - type: custom:mushroom-cover-card
        entity: cover.pergola_roof
        name: Pergola Roof
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
      - type: custom:mushroom-select-card
        entity: input_select.pergola_weather_mode
        name: Pergola Weather Mode
        icon: mdi:weather-pouring
        layout: horizontal
      - type: custom:mushroom-entity-card
        entity: cover.gate
        name: Gate
        layout: horizontal
        tap_action: { action: toggle }
      - type: custom:mushroom-light-card
        entity: light.porch
        name: Porch
        use_light_color: true
        show_brightness_control: true
        layout: horizontal
      - type: custom:mushroom-light-card
        entity: light.terrace
        name: Terrace
        use_light_color: true
        show_brightness_control: true
        layout: horizontal

  - title: Weather
    cards:
      - type: weather-forecast
        entity: weather.forecast_home
        forecast_type: daily
      - type: weather-forecast
        entity: weather.forecast_home
        forecast_type: hourly
```

> **Replace entity IDs found not to exist with their actual names**, or comment out and annotate with `# TODO: confirm entity ID` after verifying against HA states.

- [ ] **Step 3: Register, lint, commit, push**

```bash
# Update dashboards/tablet.yaml to include outdoor.yaml after media
uv run pre-commit run --all-files
git add dashboards/tablet/outdoor.yaml dashboards/tablet.yaml
git commit -m "feat(dashboard): add Outdoor tab"
git push
```

- [ ] **Step 4: Verify and patch missing entities**

Open `http://homeassistant.local:8123/wall-tablet/outdoor`. Any card showing "Entity not available" — find the correct entity ID via HA MCP (`GetLiveContext` or entity registry), update the YAML, and amend the commit or commit a fix.

---

## Task 7: Tablet Security tab

**Files:**
- Create: `dashboards/tablet/security.yaml`
- Modify: `dashboards/tablet.yaml`

- [ ] **Step 1: Create `dashboards/tablet/security.yaml`**

```yaml
---
title: Security
path: security
icon: mdi:shield
type: sections
max_columns: 3
sections:
  - title: Alarm
    cards:
      - type: alarm-panel
        entity: alarm_control_panel.main
        name: Satel Alarm
        states: [arm_away, arm_home, arm_night]
      - type: custom:mushroom-template-card
        entity: binary_sensor.home_ready_to_arm
        icon: "{{ 'mdi:shield-check' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'mdi:shield-alert' }}"
        icon_color: "{{ 'green' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'red' }}"
        primary: "{{ 'Ready to Arm' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'Not Ready' }}"
        secondary: >-
          {{ state_attr('binary_sensor.home_ready_to_arm', 'open_doors_count') | int(0) }} open doors ·
          {{ state_attr('binary_sensor.home_ready_to_arm', 'occupied_zones_count') | int(0) }} occupied
        layout: horizontal
        tap_action: { action: more-info }
      - type: custom:mushroom-entity-card
        entity: switch.garage_door
        name: Garage Door Output
        layout: horizontal
        tap_action: { action: toggle }

  - title: Zones
    cards:
      - type: entities
        title: Doors
        entities:
          - entity: binary_sensor.terrace_left_door
            name: Terrace Left
          - entity: binary_sensor.terrace_main_door
            name: Terrace Main
          - entity: binary_sensor.balcony_door
            name: Balcony
          - entity: binary_sensor.garage_door
            name: Garage
      - type: entities
        title: Motion
        entities:
          - entity: binary_sensor.living_room_motion
            name: Living Room
          - entity: binary_sensor.vestibule_motion
            name: Vestibule
          - entity: binary_sensor.garage_motion
            name: Garage

  - title: Doorbell
    cards:
      - type: picture-entity
        entity: camera.doorbell_rtsp
        camera_view: live
        show_state: false
        show_name: false
      - type: logbook
        title: Recent Activity
        hours_to_show: 24
        entities:
          - alarm_control_panel.main
          - binary_sensor.terrace_left_door
          - binary_sensor.terrace_main_door
          - binary_sensor.balcony_door
          - binary_sensor.garage_door
          - binary_sensor.living_room_motion
          - binary_sensor.vestibule_motion
          - binary_sensor.garage_motion
```

- [ ] **Step 2: Register, lint, commit, push**

```bash
# Add - !include tablet/security.yaml to dashboards/tablet.yaml
uv run pre-commit run --all-files
git add dashboards/tablet/security.yaml dashboards/tablet.yaml
git commit -m "feat(dashboard): add Security tab"
git push
```

- [ ] **Step 3: Verify**

Open `/wall-tablet/security`. Confirm alarm panel arm/disarm buttons work, zones list shows statuses, doorbell camera renders, logbook shows recent events.

---

## Task 8: Tablet Energy tab — migrate and retire standalone dashboard

**Files:**
- Create: `dashboards/tablet/energy.yaml` (content from existing `dashboards/energy.yaml` + additions)
- Modify: `dashboards/tablet.yaml`
- Delete: `dashboards/energy.yaml`
- Modify: `configuration.yaml` — remove the `energy-monitor` dashboard registration

- [ ] **Step 1: Copy existing energy dashboard content**

Copy the two sections from `dashboards/energy.yaml` into a new file `dashboards/tablet/energy.yaml`. Restructure top-level as a view (not a views list):

```yaml
---
title: Energy
path: energy
icon: mdi:lightning-bolt
type: sections
max_columns: 3
sections:
  - title: Consumption Trends
    cards:
      - type: statistics-graph
        title: Monthly Energy by Device
        period: month
        stat_types: [change]
        chart_type: bar
        entities:
          - entity: sensor.sypialnia_lazienka_energy
            name: Ensuite Bathroom
          - entity: sensor.kuchnia_ledy_energy
            name: Kitchen LEDs
          - entity: sensor.living_room_light_standing_lamp_energy
            name: Standing Lamp
          - entity: sensor.swiatlo_przed_domem_energy
            name: Porch
          - entity: sensor.main_bathroom_energy
            name: Bathroom
          - entity: sensor.wyspa_swiatla_energy
            name: Kitchen Island
          - entity: sensor.boiler_room_energy
            name: Boiler Room
          - entity: sensor.laundry_energy
            name: Laundry
          - entity: sensor.bedroom_reflectors_energy
            name: Bedroom Reflectors
          - entity: sensor.sypialnia_sonia_swiatlo_energy
            name: Bedroom Sona
      - type: statistics-graph
        title: Weekly Energy by Device
        period: week
        stat_types: [change]
        chart_type: bar
        entities:
          - entity: sensor.sypialnia_lazienka_energy
            name: Ensuite Bathroom
          - entity: sensor.kuchnia_ledy_energy
            name: Kitchen LEDs
          - entity: sensor.living_room_light_standing_lamp_energy
            name: Standing Lamp
          - entity: sensor.swiatlo_przed_domem_energy
            name: Porch
          - entity: sensor.main_bathroom_energy
            name: Bathroom
          - entity: sensor.wyspa_swiatla_energy
            name: Kitchen Island
          - entity: sensor.boiler_room_energy
            name: Boiler Room
          - entity: sensor.laundry_energy
            name: Laundry
          - entity: sensor.bedroom_reflectors_energy
            name: Bedroom Reflectors
          - entity: sensor.sypialnia_sonia_swiatlo_energy
            name: Bedroom Sona

  - title: All-Time Totals
    cards:
      - type: entities
        title: Cumulative Energy (kWh)
        entities:
          - entity: sensor.sypialnia_lazienka_energy
            name: Ensuite Bathroom
          - entity: sensor.kuchnia_ledy_energy
            name: Kitchen LEDs
          - entity: sensor.living_room_light_standing_lamp_energy
            name: Standing Lamp
          - entity: sensor.swiatlo_przed_domem_energy
            name: Porch
          - entity: sensor.main_bathroom_energy
            name: Bathroom
          - entity: sensor.wyspa_swiatla_energy
            name: Kitchen Island
          - entity: sensor.boiler_room_energy
            name: Boiler Room
          - entity: sensor.laundry_energy
            name: Laundry
          - entity: sensor.bedroom_reflectors_energy
            name: Bedroom Reflectors
          - entity: sensor.sypialnia_sonia_swiatlo_energy
            name: Bedroom Sona

  - title: Live & Today
    cards:
      - type: custom:mushroom-template-card
        icon: mdi:flash
        icon_color: amber
        primary: Live power strip card — add once power-meter sensors are confirmed
        secondary: Requires live power entities (e.g. sensor.*_power). Grep for `_power` under packages/ to find candidates.
        layout: vertical
      # Today sparkline — uses existing energy sensors with sensor-card graph
      - type: sensor
        entity: sensor.sypialnia_lazienka_energy
        graph: line
        hours_to_show: 24
        name: Ensuite Bathroom (24h)
```

> **Step 1b (if any Polish-named sensor IDs don't exist):** cross-check each entity with `grep -r "sensor.sypialnia_lazienka_energy" packages/`. Remove/rename entities not in the registry.

- [ ] **Step 2: Register in `dashboards/tablet.yaml`**

Add `- !include tablet/energy.yaml` after Security.

- [ ] **Step 3: Delete standalone energy dashboard**

```bash
git rm dashboards/energy.yaml
```

- [ ] **Step 4: Remove `energy-monitor` from `configuration.yaml`**

Delete this block from `configuration.yaml`:

```yaml
    energy-monitor:
      mode: yaml
      filename: dashboards/energy.yaml
      title: Energy
      icon: mdi:lightning-bolt
      show_in_sidebar: true
      require_admin: false
```

- [ ] **Step 5: Lint, commit, push**

```bash
uv run pre-commit run --all-files
git add dashboards/tablet/energy.yaml dashboards/tablet.yaml dashboards/energy.yaml configuration.yaml
git commit -m "feat(dashboard): move Energy into tablet tab, retire standalone dashboard"
git push
```

- [ ] **Step 6: Verify**

Open `/wall-tablet/energy`. Confirm both statistics-graphs render, entities card populated, live sparkline renders. Confirm `/energy-monitor/energy` returns 404 (dashboard removed).

---

## Task 9: Tablet Home tab rebalance + add drill-down navigation

**Files:**
- Modify: `dashboards/tablet/home.yaml`

- [ ] **Step 1: Regroup into 3 logical columns**

The current Home tab has three sections. Rebalance per the spec:
- **Column 1 — Status & Security:** persons + alarm, door chips, weather, doorbell camera (moved here from column 2), NEW active-scene chip
- **Column 2 — Lights & Actions:** lights grid (9 + All Off), now-playing media, 3 music quick-play, 2 vacuum quick-scripts
- **Column 3 — Comfort:** LR climate card, BR climate card, compact curtains (GF + BR), NEW active-appliances strip, NEW "Today" card

Move the `picture-entity` doorbell camera from section 2 into section 1. Move the `mushroom-media-player-card` + quick-play buttons into section 2 next to the lights grid. Section 3 gets climate + compact-curtains (two covers only: `cover.ground_floor`, `cover.bedroom`).

- [ ] **Step 2: Add active-scene chip**

Add to the chips row in Column 1 (merge into existing `mushroom-chips-card` or add a new chip card):

```yaml
- type: template
  entity: input_select.living_room_scene
  icon: mdi:movie-open
  icon_color: purple
  content: "{{ states('input_select.living_room_scene') }}"
  tap_action:
    action: navigate
    navigation_path: /wall-tablet/media
```

- [ ] **Step 3: Add active-appliances strip**

Add to Column 3:

```yaml
- type: custom:mushroom-chips-card
  alignment: start
  chips:
    - type: template
      entity: binary_sensor.washer_power
      icon: mdi:washing-machine
      icon_color: "{{ 'blue' if is_state('binary_sensor.washer_power', 'on') else 'disabled' }}"
      content: "Washer {{ 'on' if is_state('binary_sensor.washer_power', 'on') else 'idle' }}"
      tap_action:
        action: navigate
        navigation_path: /wall-tablet/appliances
    - type: template
      entity: binary_sensor.tumble_dryer_power
      icon: mdi:tumble-dryer
      icon_color: "{{ 'blue' if is_state('binary_sensor.tumble_dryer_power', 'on') else 'disabled' }}"
      content: "Dryer {{ 'on' if is_state('binary_sensor.tumble_dryer_power', 'on') else 'idle' }}"
      tap_action:
        action: navigate
        navigation_path: /wall-tablet/appliances
    - type: template
      entity: vacuum.dreamebot_l10_ultra
      icon: mdi:robot-vacuum
      icon_color: "{{ 'green' if is_state('vacuum.dreamebot_l10_ultra', 'cleaning') else 'disabled' }}"
      content: "GF Vacuum {{ states('vacuum.dreamebot_l10_ultra') }}"
      tap_action:
        action: navigate
        navigation_path: /wall-tablet/appliances
    - type: template
      entity: vacuum.x40_master
      icon: mdi:robot-vacuum
      icon_color: "{{ 'green' if is_state('vacuum.x40_master', 'cleaning') else 'disabled' }}"
      content: "1F Vacuum {{ states('vacuum.x40_master') }}"
      tap_action:
        action: navigate
        navigation_path: /wall-tablet/appliances
```

- [ ] **Step 4: Add "Today" card**

Add to Column 3 at the bottom:

```yaml
- type: custom:mushroom-template-card
  icon: mdi:home-analytics
  icon_color: teal
  primary: Today
  secondary: >-
    {% set lights_on = states.light
      | selectattr('state', 'eq', 'on')
      | list | count %}
    {{ lights_on }} light{{ 's' if lights_on != 1 }} on
  layout: horizontal
  tap_action:
    action: navigate
    navigation_path: /wall-tablet/energy
```

(Energy-today sensor is optional — add once a suitable total is confirmed.)

- [ ] **Step 5: Wire up section-heading navigation**

For each `type: heading` in `home.yaml`, add a `tap_action`:

```yaml
- type: heading
  heading: Lights
  heading_style: subtitle
  tap_action:
    action: navigate
    navigation_path: /wall-tablet/climate   # or whichever tab makes sense
```

Targets:
- "Media" heading → `/wall-tablet/media`
- "Vacuums" heading → `/wall-tablet/appliances`
- "Curtains" heading (if still present on Home) → `/wall-tablet/climate`

- [ ] **Step 6: Lint, commit, push, verify on real tablet**

```bash
uv run pre-commit run --all-files
git add dashboards/tablet/home.yaml
git commit -m "feat(dashboard): rebalance Home tab with drill-down navigation"
git push
```

Open `http://homeassistant.local:8123/wall-tablet/home` on the actual wall tablet (or via Playwright MCP if remote). Check:

1. All three columns render.
2. Heights are reasonably balanced (± 150 px is acceptable — document actual gap).
3. Tapping a section heading navigates to the matching tab.
4. Active-scene chip reflects current scene.
5. Active-appliances strip updates when washer/dryer/vacuum state changes.

If heights are still off, tune by moving the "Today" card or adding spacing. This is the pixel-balancing pass — it's expected to take a few iterations.

---

## Task 10: Phone dashboard — Home and Away tabs

**Files:**
- Modify: `dashboards/phone/home.yaml`
- Create: `dashboards/phone/away.yaml`
- Modify: `dashboards/phone.yaml`

- [ ] **Step 1: Rewrite `dashboards/phone/home.yaml`**

Single-column, compact, finger-friendly.

```yaml
---
title: Home
path: home
icon: mdi:home
type: sections
max_columns: 1
sections:
  - cards:
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-person-card
            entity: person.jakub
            icon_type: entity-picture
            layout: vertical
          - type: custom:mushroom-person-card
            entity: person.sona
            icon_type: entity-picture
            layout: vertical
      - type: custom:mushroom-template-card
        entity: binary_sensor.home_ready_to_arm
        icon: "{{ 'mdi:shield-check' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'mdi:shield-alert' }}"
        icon_color: "{{ 'green' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'red' }}"
        primary: "{{ 'Ready to Arm' if is_state('binary_sensor.home_ready_to_arm', 'on') else 'Not Ready' }}"
        secondary: Tap for alarm
        layout: horizontal
        tap_action:
          action: navigate
          navigation_path: /phone/away

  - cards:
      - type: custom:mushroom-chips-card
        alignment: justify
        chips:
          - type: action
            icon: mdi:lightbulb-group-off
            icon_color: red
            content: All off
            tap_action:
              action: perform-action
              perform_action: light.turn_off
              target: { entity_id: all }
          - type: template
            entity: media_player.living_room_tv
            icon: mdi:pause
            icon_color: blue
            content: Pause
            tap_action:
              action: perform-action
              perform_action: media_player.media_pause
              target: { entity_id: media_player.living_room_tv }
          - type: template
            entity: input_select.living_room_scene
            icon: mdi:movie-open
            icon_color: purple
            content: "{{ states('input_select.living_room_scene') }}"
            tap_action: { action: more-info }

      - type: custom:mushroom-template-card
        entity: weather.forecast_home
        icon: >-
          mdi:weather-{{ states('weather.forecast_home')
            | replace('partlycloudy','partly-cloudy')
            | replace('clear-night','night') }}
        primary: >-
          {{ state_attr('weather.forecast_home','temperature') | float(0) }}°C
          {{ states('weather.forecast_home') | capitalize }}
        secondary: >-
          Humidity {{ state_attr('weather.forecast_home','humidity') | float(0) | round(0) | int }}%
        layout: horizontal
        tap_action: { action: more-info }

      - type: custom:mushroom-media-player-card
        entity: media_player.living_room_tv
        use_media_info: true
        volume_controls: [volume_set]
        media_controls: [previous, play_pause_stop, next]
        layout: horizontal

      - type: custom:mushroom-template-card
        icon: mdi:lightbulb-on
        icon_color: amber
        primary: >-
          {% set c = states.light | selectattr('state','eq','on') | list | count %}
          {{ c }} light{{ 's' if c != 1 }} on
        secondary: Tap for rooms
        layout: horizontal
        tap_action:
          action: navigate
          navigation_path: /phone/rooms

      - type: custom:mushroom-chips-card
        alignment: start
        chips:
          - type: template
            entity: binary_sensor.washer_power
            icon: mdi:washing-machine
            icon_color: "{{ 'blue' if is_state('binary_sensor.washer_power','on') else 'disabled' }}"
            content: "Washer {{ 'on' if is_state('binary_sensor.washer_power','on') else 'idle' }}"
          - type: template
            entity: binary_sensor.tumble_dryer_power
            icon: mdi:tumble-dryer
            icon_color: "{{ 'blue' if is_state('binary_sensor.tumble_dryer_power','on') else 'disabled' }}"
            content: "Dryer {{ 'on' if is_state('binary_sensor.tumble_dryer_power','on') else 'idle' }}"
```

- [ ] **Step 2: Create `dashboards/phone/away.yaml`**

Single-column, security-focused.

```yaml
---
title: Away
path: away
icon: mdi:shield
type: sections
max_columns: 1
sections:
  - cards:
      - type: alarm-panel
        entity: alarm_control_panel.main
        name: Alarm
        states: [arm_away, arm_home, arm_night]

  - cards:
      - type: picture-entity
        entity: camera.doorbell_rtsp
        camera_view: live
        show_state: false
        show_name: false

  - cards:
      - type: entities
        title: Doors
        entities:
          - entity: binary_sensor.terrace_left_door
            name: Terrace Left
          - entity: binary_sensor.terrace_main_door
            name: Terrace Main
          - entity: binary_sensor.balcony_door
            name: Balcony
          - entity: binary_sensor.garage_door
            name: Garage
      - type: entities
        title: Motion
        entities:
          - entity: binary_sensor.living_room_motion
          - entity: binary_sensor.vestibule_motion
          - entity: binary_sensor.garage_motion

  - cards:
      - type: custom:mushroom-entity-card
        entity: cover.gate
        name: Gate
        layout: horizontal
        tap_action: { action: toggle }

  - cards:
      - type: logbook
        title: Recent Alarm Events
        hours_to_show: 48
        entities:
          - alarm_control_panel.main
          - binary_sensor.terrace_left_door
          - binary_sensor.terrace_main_door
          - binary_sensor.balcony_door
          - binary_sensor.garage_door
```

- [ ] **Step 3: Register Away in `dashboards/phone.yaml`**

```yaml
---
title: Phone
views:
  - !include phone/home.yaml
  - !include phone/away.yaml
```

- [ ] **Step 4: Lint, commit, push, verify**

```bash
uv run pre-commit run --all-files
git add dashboards/phone/ dashboards/phone.yaml
git commit -m "feat(dashboard): add Phone Home and Away tabs"
git push
```

Open `http://homeassistant.local:8123/phone/home` and `/phone/away` on an actual phone (or via Playwright with mobile viewport). Confirm single-column, tap targets are comfortable, chip row action works.

---

## Task 11: Phone Rooms tab + per-room sub-views

**Files:**
- Create: `dashboards/phone/rooms.yaml`
- Modify: `dashboards/phone.yaml`

- [ ] **Step 1: Room picker view with sub-views**

HA supports sub-views inside a single dashboard via `subview: true` on a view. Because `rooms.yaml` is a single `!include` file, the sub-views must be declared as additional views in `dashboards/phone.yaml`. We'll add one root rooms tile view + N sub-view files.

Create `dashboards/phone/rooms.yaml` (tile picker):

```yaml
---
title: Rooms
path: rooms
icon: mdi:floor-plan
type: sections
max_columns: 1
sections:
  - title: Ground Floor
    cards:
      - type: grid
        columns: 2
        square: false
        cards:
          - type: custom:mushroom-template-card
            icon: mdi:sofa
            primary: Living Room
            secondary: "{{ states('sensor.living_room_hygro_temperature') | float(0) | round(1) }}°C"
            tap_action: { action: navigate, navigation_path: /phone/room-living-room }
          - type: custom:mushroom-template-card
            icon: mdi:countertop
            primary: Kitchen
            tap_action: { action: navigate, navigation_path: /phone/room-kitchen }
          - type: custom:mushroom-template-card
            icon: mdi:toilet
            primary: Toilet
            tap_action: { action: navigate, navigation_path: /phone/room-toilet }

  - title: First Floor
    cards:
      - type: grid
        columns: 2
        square: false
        cards:
          - type: custom:mushroom-template-card
            icon: mdi:bed
            primary: Bedroom
            secondary: "{{ states('sensor.bedroom_hygro_temperature') | float(0) | round(1) }}°C"
            tap_action: { action: navigate, navigation_path: /phone/room-bedroom }
          - type: custom:mushroom-template-card
            icon: mdi:bathtub
            primary: Bathroom
            tap_action: { action: navigate, navigation_path: /phone/room-bathroom }
          - type: custom:mushroom-template-card
            icon: mdi:coat-rack
            primary: Hall
            tap_action: { action: navigate, navigation_path: /phone/room-hall }

  - title: Outdoor
    cards:
      - type: grid
        columns: 2
        square: false
        cards:
          - type: custom:mushroom-template-card
            icon: mdi:tree
            primary: Garden
            tap_action: { action: navigate, navigation_path: /phone/room-garden }
          - type: custom:mushroom-template-card
            icon: mdi:umbrella-beach
            primary: Terrace
            tap_action: { action: navigate, navigation_path: /phone/room-terrace }
          - type: custom:mushroom-template-card
            icon: mdi:home
            primary: Porch
            tap_action: { action: navigate, navigation_path: /phone/room-porch }
          - type: custom:mushroom-template-card
            icon: mdi:gate
            primary: Gate
            tap_action: { action: navigate, navigation_path: /phone/room-gate }
```

- [ ] **Step 2: Create sub-view files (one per room)**

For each room, create `dashboards/phone/rooms/<room>.yaml`. Example Living Room sub-view:

```yaml
---
title: Living Room
path: room-living-room
icon: mdi:sofa
subview: true
type: sections
max_columns: 1
sections:
  - cards:
      - type: custom:mushroom-template-card
        entity: sensor.living_room_hygro_temperature
        icon: mdi:thermometer
        icon_color: orange
        primary: Living Room
        secondary: >-
          {{ states('sensor.living_room_hygro_temperature') | float(0) | round(1) }}°C ·
          {{ states('sensor.living_room_hygro_humidity') | float(0) | round(0) | int }}%
        layout: horizontal
        tap_action: { action: more-info, entity: climate.living_room }

  - cards:
      - type: custom:mushroom-light-card
        entity: light.living_room_corner_lamp
        name: Corner Lamp
        use_light_color: true
        show_brightness_control: true
        layout: horizontal
      - type: custom:mushroom-light-card
        entity: light.living_room_standing_lamp
        name: Standing Lamp
        use_light_color: true
        show_brightness_control: true
        layout: horizontal
      # Add remaining living-room light entities here.

  - cards:
      - type: custom:mushroom-cover-card
        entity: cover.living_room_main
        name: Main Curtain
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
      - type: custom:mushroom-cover-card
        entity: cover.living_room_left
        name: Left Curtain
        show_buttons_control: true
        show_position_control: true
        layout: horizontal
```

Create a minimal sub-view for each remaining room in the picker list (Kitchen, Toilet, Bedroom, Bathroom, Hall, Garden, Terrace, Porch, Gate). Keep them short — temp sensor, lights, main actions, and anything else relevant. For rooms with no sensors (e.g. Gate), include only the main action (`cover.gate` toggle).

Before writing each sub-view, discover that room's entities:

```bash
# Replace <room-dir> with the kebab path (e.g. first-floor/bedroom, outdoor/garden)
grep -rhoE "^\s*- (light|cover|switch|binary_sensor|sensor|climate|humidifier|vacuum)\.[a-z0-9_]+" \
  packages/areas/<room-dir>/ | sort -u
```

Populate the sub-view's sections with the output. Skip entities that are aggregations already surfaced elsewhere (e.g. `cover.ground_floor` group belongs on the floor level, not inside the Living Room sub-view).

> **Pattern for each sub-view file:** `path: room-<kebab-case>`, `subview: true`, single column, sections per logical grouping (env / lights / curtains / actions).

- [ ] **Step 3: Register all sub-views in `dashboards/phone.yaml`**

```yaml
---
title: Phone
views:
  - !include phone/home.yaml
  - !include phone/rooms.yaml
  - !include phone/away.yaml
  - !include phone/rooms/living-room.yaml
  - !include phone/rooms/kitchen.yaml
  - !include phone/rooms/toilet.yaml
  - !include phone/rooms/bedroom.yaml
  - !include phone/rooms/bathroom.yaml
  - !include phone/rooms/hall.yaml
  - !include phone/rooms/garden.yaml
  - !include phone/rooms/terrace.yaml
  - !include phone/rooms/porch.yaml
  - !include phone/rooms/gate.yaml
```

Sub-views with `subview: true` don't appear in the tab bar; they're only reachable via `navigate` action. This matches the spec's intent.

- [ ] **Step 4: Lint, commit, push, verify**

```bash
uv run pre-commit run --all-files
git add dashboards/phone/ dashboards/phone.yaml
git commit -m "feat(dashboard): add Phone Rooms tab with per-room sub-views"
git push
```

Verify on phone (or Playwright mobile viewport): tap a room tile on `/phone/rooms`, confirm sub-view loads with no tab-bar clutter, back button returns to Rooms.

---

## Task 12: Phone Energy tab

**Files:**
- Create: `dashboards/phone/energy.yaml`
- Modify: `dashboards/phone.yaml`

- [ ] **Step 1: Create `dashboards/phone/energy.yaml`**

Compact view — summary numbers first, graphs below.

```yaml
---
title: Energy
path: energy
icon: mdi:lightning-bolt
type: sections
max_columns: 1
sections:
  - cards:
      - type: custom:mushroom-template-card
        icon: mdi:flash
        icon_color: amber
        primary: >-
          {% set total = (states('sensor.sypialnia_lazienka_energy')  | float(0) +
                         states('sensor.kuchnia_ledy_energy')         | float(0) +
                         states('sensor.living_room_light_standing_lamp_energy') | float(0) +
                         states('sensor.swiatlo_przed_domem_energy')  | float(0) +
                         states('sensor.main_bathroom_energy')        | float(0) +
                         states('sensor.wyspa_swiatla_energy')        | float(0) +
                         states('sensor.boiler_room_energy')          | float(0) +
                         states('sensor.laundry_energy')              | float(0) +
                         states('sensor.bedroom_reflectors_energy')   | float(0) +
                         states('sensor.sypialnia_sonia_swiatlo_energy') | float(0)) %}
          {{ total | round(1) }} kWh total
        secondary: All tracked devices · cumulative
        layout: vertical

  - cards:
      - type: statistics-graph
        title: This Week
        period: day
        days_to_show: 7
        stat_types: [change]
        chart_type: bar
        entities:
          - sensor.sypialnia_lazienka_energy
          - sensor.kuchnia_ledy_energy
          - sensor.living_room_light_standing_lamp_energy
          - sensor.swiatlo_przed_domem_energy
          - sensor.main_bathroom_energy
          - sensor.wyspa_swiatla_energy
          - sensor.boiler_room_energy
          - sensor.laundry_energy
          - sensor.bedroom_reflectors_energy
          - sensor.sypialnia_sonia_swiatlo_energy

  - cards:
      - type: statistics-graph
        title: Monthly
        period: month
        stat_types: [change]
        chart_type: bar
        entities:
          - sensor.sypialnia_lazienka_energy
          - sensor.kuchnia_ledy_energy
          - sensor.living_room_light_standing_lamp_energy
          - sensor.swiatlo_przed_domem_energy
          - sensor.main_bathroom_energy
          - sensor.wyspa_swiatla_energy
          - sensor.boiler_room_energy
          - sensor.laundry_energy
          - sensor.bedroom_reflectors_energy
          - sensor.sypialnia_sonia_swiatlo_energy
```

- [ ] **Step 2: Register**

Add `- !include phone/energy.yaml` to `dashboards/phone.yaml` after `away.yaml` (before the sub-views so it appears in the tab bar).

- [ ] **Step 3: Lint, commit, push, verify**

```bash
uv run pre-commit run --all-files
git add dashboards/phone/energy.yaml dashboards/phone.yaml
git commit -m "feat(dashboard): add Phone Energy tab"
git push
```

Verify `/phone/energy` on a phone — confirm total number, weekly bars, monthly bars render without horizontal overflow.

---

## Task 13: Polish pass

**Files:** any across `dashboards/` needing tweaks after real-device review.

- [ ] **Step 1: Full visual audit on tablet**

Open each tablet tab at `http://homeassistant.local:8123/wall-tablet/<path>` on the wall tablet:

- `/home` — logical grouping balanced?
- `/climate`, `/media`, `/appliances`, `/outdoor`, `/security`, `/energy`, `/settings`, `/doorbell`

For any tab with card errors, misaligned spacing, or crash-looking red boxes, open a browser console and look for red "Custom element not found" messages. Fix the entity ID or card type.

- [ ] **Step 2: Full visual audit on phone**

Open each phone tab at `http://homeassistant.local:8123/phone/<path>` on an actual phone (not the tablet). Walk through Rooms sub-views. Confirm drill-down → back navigation works.

- [ ] **Step 3: Apply card-mod polish**

For any cards whose spacing looks off, add a `card_mod.style` wrapper — match the existing stacked-card pattern (rounded-top + flat-bottom) for cards grouped in vertical-stack.

- [ ] **Step 4: Update area README files if entity lists changed**

For each area package whose dashboard representation changed significantly, run the `/ha-area-docs` skill on that area — but **only if** the area package files themselves changed, not just the dashboard. Dashboard-only changes don't update area READMEs.

- [ ] **Step 5: Final lint, commit, push**

```bash
uv run pre-commit run --all-files
git add dashboards/
git commit -m "chore(dashboard): polish pass — spacing, entity fixes, card-mod tweaks"
git push
```

- [ ] **Step 6: Open PR**

If not already in a PR, open one:

```bash
gh pr create --title "Dashboard redesign: multi-dashboard, multi-tab layout" --body "$(cat <<'EOF'
## Summary
- Split monolithic tablet.yaml into per-tab includes under dashboards/tablet/
- New `phone` dashboard with Home, Rooms (with sub-views), Away, Energy
- Retired standalone energy.yaml (content merged into tablet/energy.yaml)
- Extracted alarm-readiness Jinja into binary_sensor.home_ready_to_arm
- 8 visible tablet tabs + 1 hidden (Doorbell); 4 phone tabs + room sub-views

## Test plan
- [ ] Tablet loads all 8 tabs without card errors
- [ ] Phone loads all 4 tabs without card errors
- [ ] Doorbell hidden view still triggered by existing automations
- [ ] Alarm card reflects real door/occupancy state via new template sensor
- [ ] mass-player-card on Media tab renders without crashing
- [ ] Adding a hypothetical device → only tab file + (optional) phone file changes
EOF
)"
```

---

## Risks & rollback

- **Dashboard fails to load:** revert the latest commit with `git revert HEAD` and push. HA auto-pulls the revert.
- **`mass-player-card` crash:** if the card's section also drags other sections down, remove the card (comment out in `tablet/media.yaml`) and commit a hotfix. Prior reason for removal was size, not stability — confirm which during Task 5 verification.
- **Template sensor evaluation slow:** the `home_ready_to_arm` sensor reads ~9 entities on every state change. If HA logs show high template-evaluation times, split into two sensors (doors + presence) or precompute via automation.

## Scope boundary reminder

- No new HACS cards beyond those already installed.
- No theme / colour change.
- No new appliance integrations — surface existing entities only.
- Sub-views in Phone Rooms are additional views within the same dashboard, not a separate dashboard.
