# Garage View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated **Garage** view to the tablet and phone dashboards showing the BMW CarData vehicle card (i4 M50), garage-door control + status, EV charging detail, and trip/range stats.

**Architecture:** Two new Lovelace view files (`dashboards/tablet/garage.yaml`, `dashboards/phone/garage.yaml`), each `type: sections`. Tablet is 3-column full-width; phone is single-column. Both included from their dashboard entrypoints. Dashboard-only change — no new template/helper entities.

**Tech Stack:** Home Assistant Lovelace YAML, Mushroom cards (`mushroom-cover-card`, `mushroom-template-card`, `mushroom-chips-card`), `custom:bmw-cardata-vehicle-card` (auto-registered by integration).

**Testing model:** No unit tests exist for dashboards. The verification loop is: lint → commit → push → HA auto-pull → Playwright live check (force-refetch WS config, navigate, screenshot to `.playwright-mcp/`). Each task ends by confirming the live render.

---

## Reference constants (verified live 2026-05-25)

- BMW device_id: `95997f834d22c4835e55ba4bc7524717` (i4 M50, EV)
- Card: `custom:bmw-cardata-vehicle-card` — auto-registered, no HACS frontend install
- Garage cover: `cover.garage_door` (device_class garage, open/close/stop)
- Garage status zone: `binary_sensor.garage_door` (`on`=open)
- Garage transit: `input_select.garage_door_state` (`idle`/`opening`/`closing`)
- Garage motion: `binary_sensor.garage_motion`
- EV sensors (all `sensor.i4_m50_*`): `battery_hv_state_of_charge`, `battery_ev_target_state_of_charge`, `charging_ev_predicted_state_of_charge`, `battery_ev_charging_current_limit`, `charging_ev_charging_state`, `charging_port_plug_lock_state`, `range_ev_estimate_during_charging`, `vehicle_mileage`, `trip_battery_charge_level_at_end_of_trip`
- Tablet dashboard URL: `/wall-tablet/garage` · Phone: `/mobile-phone/garage`

Branch: `chore/may-fixes`. Never push to `main`.

---

## Task 1: Tablet view — scaffold + vehicle hero

**Files:**
- Create: `dashboards/tablet/garage.yaml`
- Modify: `dashboards/tablet.yaml` (insert include after `outdoor`)

- [ ] **Step 1: Create tablet view with header + BMW hero card**

Create `dashboards/tablet/garage.yaml`:

```yaml
---
title: Garage
path: garage
icon: mdi:garage
type: sections
max_columns: 3
sections:
  - column_span: 3
    cards:
      - type: custom:bmw-cardata-vehicle-card
        grid_options:
          columns: full
        device_id: 95997f834d22c4835e55ba4bc7524717
```

- [ ] **Step 2: Wire the include into the tablet entrypoint**

In `dashboards/tablet.yaml`, insert the garage include between `outdoor` and `security`:

```yaml
  - !include tablet/outdoor.yaml
  - !include tablet/garage.yaml
  - !include tablet/security.yaml
```

- [ ] **Step 3: Lint**

Run: `uv run pre-commit run --all-files`
Expected: PASS (dashboards excluded from yamllint; other hooks pass).

- [ ] **Step 4: Commit + push**

```bash
git add dashboards/tablet/garage.yaml dashboards/tablet.yaml
git commit -m "feat(garage): add tablet garage view with BMW vehicle card"
git push
```

- [ ] **Step 5: Playwright verify hero renders**

Wait ~10s for HA pull. Force-refetch lovelace config over WebSocket, navigate to
`http://homeassistant.local:8123/wall-tablet/garage`, screenshot to `.playwright-mcp/`.
Expected: Garage tab present in nav; BMW vehicle card renders with image/range/indicators/map
(NOT a red error card). If error card → check device_id and that `custom:bmw-cardata-vehicle-card`
is registered.

---

## Task 2: Tablet view — garage door control row

**Files:**
- Modify: `dashboards/tablet/garage.yaml`

- [ ] **Step 1: Append garage-door horizontal-stack under the hero card**

Add to the `cards:` list in `dashboards/tablet/garage.yaml`, after the BMW card:

```yaml
      - type: heading
        heading: Garage Door
        heading_style: title
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-cover-card
            entity: cover.garage_door
            name: Garage Door
            show_buttons_control: true
            layout: horizontal
          - type: custom:mushroom-template-card
            entity: binary_sensor.garage_door
            icon: >-
              {% set t = states('input_select.garage_door_state') %}
              {% if t in ['opening', 'closing'] %}mdi:garage-alert
              {% elif is_state('binary_sensor.garage_door', 'on') %}mdi:garage-open
              {% else %}mdi:garage{% endif %}
            icon_color: >-
              {% set t = states('input_select.garage_door_state') %}
              {% if t in ['opening', 'closing'] %}amber
              {% elif is_state('binary_sensor.garage_door', 'on') %}red
              {% else %}green{% endif %}
            primary: >-
              {% set t = states('input_select.garage_door_state') %}
              {% if t == 'opening' %}Opening…
              {% elif t == 'closing' %}Closing…
              {% elif is_state('binary_sensor.garage_door', 'on') %}Open
              {% else %}Closed{% endif %}
            secondary: >-
              {{ as_timestamp(states.binary_sensor.garage_door.last_changed)
                 | timestamp_custom('%a %H:%M') }}
            layout: horizontal
            tap_action:
              action: more-info
          - type: custom:mushroom-template-card
            entity: binary_sensor.garage_motion
            icon: >-
              {{ 'mdi:motion-sensor' if is_state('binary_sensor.garage_motion', 'on')
              else 'mdi:motion-sensor-off' }}
            icon_color: >-
              {{ 'blue' if is_state('binary_sensor.garage_motion', 'on') else 'disabled' }}
            primary: >-
              {{ 'Motion' if is_state('binary_sensor.garage_motion', 'on') else 'Clear' }}
            secondary: Garage
            layout: horizontal
            tap_action:
              action: more-info
```

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 3: Commit + push**

```bash
git add dashboards/tablet/garage.yaml
git commit -m "feat(garage): add garage door control + status row"
git push
```

- [ ] **Step 4: Playwright verify**

Force-refetch WS config, navigate to `/wall-tablet/garage`, screenshot to `.playwright-mcp/`.
Expected: cover card with open/close/stop buttons; status card shows "Closed" green `mdi:garage`
(current live state); motion card shows "Clear" disabled.

---

## Task 3: Tablet view — EV charging row

**Files:**
- Modify: `dashboards/tablet/garage.yaml`

- [ ] **Step 1: Append EV charging horizontal-stack**

Add after the garage-door stack in `dashboards/tablet/garage.yaml`:

```yaml
      - type: heading
        heading: Charging
        heading_style: title
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_charging_ev_charging_state
            icon: mdi:ev-station
            icon_color: >-
              {% set s = states('sensor.i4_m50_charging_ev_charging_state') %}
              {% if s in ['unknown', 'unavailable', 'INVALID', 'NOCHARGING', 'None', ''] %}disabled
              {% else %}green{% endif %}
            primary: >-
              {% set s = states('sensor.i4_m50_charging_ev_charging_state') %}
              {% if s in ['unknown', 'unavailable', 'INVALID', 'None', ''] %}—
              {% else %}{{ s.replace('_', ' ') | title }}{% endif %}
            secondary: Charging
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_battery_hv_state_of_charge
            icon: mdi:battery-charging
            icon_color: green
            primary: >-
              {{ states('sensor.i4_m50_battery_hv_state_of_charge') | float(0) | round(0) }}%
            secondary: >-
              Target {{ states('sensor.i4_m50_battery_ev_target_state_of_charge')
                 | float(0) | round(0) }}%
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_battery_ev_charging_current_limit
            icon: mdi:current-ac
            icon_color: blue
            primary: >-
              {{ states('sensor.i4_m50_battery_ev_charging_current_limit')
                 | float(0) | round(0) }} A
            secondary: Current limit
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_charging_ev_predicted_state_of_charge
            icon: mdi:battery-clock
            icon_color: teal
            primary: >-
              {{ states('sensor.i4_m50_charging_ev_predicted_state_of_charge')
                 | float(0) | round(0) }}%
            secondary: Predicted
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_charging_port_plug_lock_state
            icon: mdi:lock
            icon_color: >-
              {% set s = states('sensor.i4_m50_charging_port_plug_lock_state') %}
              {% if 'NOT_LOCKED' in s %}disabled{% else %}amber{% endif %}
            primary: >-
              {% set s = states('sensor.i4_m50_charging_port_plug_lock_state') %}
              {% if s in ['unknown', 'unavailable', 'INVALID', 'None', ''] %}—
              {% else %}{{ s.replace('_', ' ') | title }}{% endif %}
            secondary: Plug lock
            layout: vertical
```

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 3: Commit + push**

```bash
git add dashboards/tablet/garage.yaml
git commit -m "feat(garage): add EV charging detail tiles"
git push
```

- [ ] **Step 4: Playwright verify**

Force-refetch, navigate to `/wall-tablet/garage`, screenshot. Expected: 5 tiles. SoC `80%`
secondary `Target 80%`; current limit `32 A`; charging state shows humanized text or `—`
(currently `NOCHARGING` → renders "Nocharging" — acceptable, no raw token); no card crash.

---

## Task 4: Tablet view — trip / range row

**Files:**
- Modify: `dashboards/tablet/garage.yaml`

- [ ] **Step 1: Append trip/range horizontal-stack**

Add after the charging stack in `dashboards/tablet/garage.yaml`:

```yaml
      - type: heading
        heading: Trip & Range
        heading_style: title
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_vehicle_mileage
            icon: mdi:counter
            icon_color: indigo
            primary: >-
              {{ '{:,}'.format(states('sensor.i4_m50_vehicle_mileage')
                 | float(0) | round(0) | int) }} km
            secondary: Odometer
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_range_ev_estimate_during_charging
            icon: mdi:map-marker-distance
            icon_color: green
            primary: >-
              {{ states('sensor.i4_m50_range_ev_estimate_during_charging')
                 | float(0) | round(0) }} km
            secondary: Range
            layout: vertical
          - type: custom:mushroom-template-card
            entity: sensor.i4_m50_trip_battery_charge_level_at_end_of_trip
            icon: mdi:battery-50
            icon_color: amber
            primary: >-
              {{ states('sensor.i4_m50_trip_battery_charge_level_at_end_of_trip')
                 | float(0) | round(0) }}%
            secondary: Last trip end
            layout: vertical
```

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 3: Commit + push**

```bash
git add dashboards/tablet/garage.yaml
git commit -m "feat(garage): add trip and range stats row"
git push
```

- [ ] **Step 4: Playwright verify full tablet view**

Force-refetch, navigate to `/wall-tablet/garage`, full-page screenshot to `.playwright-mcp/`.
Expected: full view — hero, garage door row, 5 charging tiles, 3 trip tiles. Mileage `22,239 km`,
range `261 km`. No layout fragmentation (all rows full-width), no error cards.

---

## Task 5: Phone view — full single-column page

**Files:**
- Create: `dashboards/phone/garage.yaml`
- Modify: `dashboards/phone.yaml` (add top-level include)

- [ ] **Step 1: Create the phone view**

Create `dashboards/phone/garage.yaml`:

```yaml
---
title: Garage
path: garage
icon: mdi:garage
type: sections
max_columns: 1
sections:
  - cards:
      - type: custom:bmw-cardata-vehicle-card
        device_id: 95997f834d22c4835e55ba4bc7524717

  - cards:
      - type: custom:mushroom-cover-card
        entity: cover.garage_door
        name: Garage Door
        show_buttons_control: true
        layout: horizontal
      - type: custom:mushroom-template-card
        entity: binary_sensor.garage_door
        icon: >-
          {% set t = states('input_select.garage_door_state') %}
          {% if t in ['opening', 'closing'] %}mdi:garage-alert
          {% elif is_state('binary_sensor.garage_door', 'on') %}mdi:garage-open
          {% else %}mdi:garage{% endif %}
        icon_color: >-
          {% set t = states('input_select.garage_door_state') %}
          {% if t in ['opening', 'closing'] %}amber
          {% elif is_state('binary_sensor.garage_door', 'on') %}red
          {% else %}green{% endif %}
        primary: >-
          {% set t = states('input_select.garage_door_state') %}
          {% if t == 'opening' %}Opening…
          {% elif t == 'closing' %}Closing…
          {% elif is_state('binary_sensor.garage_door', 'on') %}Open
          {% else %}Closed{% endif %}
        secondary: >-
          {{ as_timestamp(states.binary_sensor.garage_door.last_changed)
             | timestamp_custom('%a %H:%M') }}
        layout: horizontal
        tap_action:
          action: more-info

  - cards:
      - type: custom:mushroom-chips-card
        alignment: justified
        chips:
          - type: template
            entity: sensor.i4_m50_battery_hv_state_of_charge
            icon: mdi:battery-charging
            icon_color: green
            content: >-
              {{ states('sensor.i4_m50_battery_hv_state_of_charge')
                 | float(0) | round(0) }}% / {{
                 states('sensor.i4_m50_battery_ev_target_state_of_charge')
                 | float(0) | round(0) }}%
          - type: template
            entity: sensor.i4_m50_charging_ev_charging_state
            icon: mdi:ev-station
            icon_color: >-
              {% set s = states('sensor.i4_m50_charging_ev_charging_state') %}
              {% if s in ['unknown', 'unavailable', 'INVALID', 'NOCHARGING', 'None', ''] %}disabled
              {% else %}green{% endif %}
            content: >-
              {% set s = states('sensor.i4_m50_charging_ev_charging_state') %}
              {% if s in ['unknown', 'unavailable', 'INVALID', 'None', ''] %}—
              {% else %}{{ s.replace('_', ' ') | title }}{% endif %}
          - type: template
            entity: sensor.i4_m50_range_ev_estimate_during_charging
            icon: mdi:map-marker-distance
            icon_color: green
            content: >-
              {{ states('sensor.i4_m50_range_ev_estimate_during_charging')
                 | float(0) | round(0) }} km

  - cards:
      - type: custom:mushroom-chips-card
        alignment: justified
        chips:
          - type: template
            entity: sensor.i4_m50_vehicle_mileage
            icon: mdi:counter
            icon_color: indigo
            content: >-
              {{ '{:,}'.format(states('sensor.i4_m50_vehicle_mileage')
                 | float(0) | round(0) | int) }} km
          - type: template
            entity: sensor.i4_m50_trip_battery_charge_level_at_end_of_trip
            icon: mdi:battery-50
            icon_color: amber
            content: >-
              {{ states('sensor.i4_m50_trip_battery_charge_level_at_end_of_trip')
                 | float(0) | round(0) }}% last trip
```

- [ ] **Step 2: Wire the include into the phone entrypoint**

In `dashboards/phone.yaml`, add the garage view to the top-level list after `energy`,
before the room subviews:

```yaml
  - !include phone/energy.yaml
  - !include phone/garage.yaml
  - !include phone/rooms/living-room.yaml
```

- [ ] **Step 3: Lint**

Run: `uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 4: Commit + push**

```bash
git add dashboards/phone/garage.yaml dashboards/phone.yaml
git commit -m "feat(garage): add phone garage view"
git push
```

- [ ] **Step 5: Playwright verify phone view**

Force-refetch WS config, resize viewport to phone width (e.g. 414×896), navigate to
`http://homeassistant.local:8123/mobile-phone/garage`, screenshot to `.playwright-mcp/`.
Expected: single column — BMW card, garage cover + status, charging chip row, mileage/trip
chip row. No error cards, no raw `NOCHARGING`/`INVALID` tokens.

---

## Self-review notes

- **Spec coverage:** vehicle hero (T1), garage door control + status + transit + motion (T2),
  EV charging detail incl. plug lock (T3), trip/range (T4), phone condensed (T5), nav after
  outdoor (T1 step 2), tablet+phone targets (T1–T4 / T5). All spec sections covered.
- **Cover-only:** `switch.garage_door` not referenced anywhere. ✓
- **No new entities:** dashboard-only. ✓
- **Transit pattern:** single content-branching template card, no mutually-exclusive Mushroom
  visibility pairs. ✓
- **Guards:** every numeric attr uses `| float(0) | round(0)`; string states checked against the
  invalid-token set. ✓
- **Device_id consistency:** `95997f834d22c4835e55ba4bc7524717` identical in T1 and T5. ✓
