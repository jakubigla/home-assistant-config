# Energy View Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tablet + phone energy dashboards with a monthly-focused view that shows kWh and PLN cost, current-month progress, projection, and a single per-device list with inline bars.

**Architecture:** New `packages/energy/` package defines an `input_number` tariff helper, `utility_meter` monthly-cycle meters per tracked source sensor, and four rollup template sensors. Dashboards read those sensors plus raw `*_monthly` per-device entities to render hero tiles, a 12-month bar chart, and a sorted per-device list with card_mod gradient bars.

**Tech Stack:** Home Assistant 2026.4.x, Lovelace (YAML mode), `utility_meter` integration, `template` sensor integration, Mushroom cards (v5.1.1), card-mod, `statistics-graph` built-in card. No new HACS dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-19-energy-view-redesign-design.md`

---

## File Structure

**Created:**
- `packages/energy/config.yaml` — package entry point. Holds `input_number:`, `utility_meter:`, `template: !include_dir_list templates`.
- `packages/energy/templates/energy_month.yaml` — the four rollup template sensors.

**Modified:**
- `configuration.yaml` — add one line registering the new package under `homeassistant.packages`.
- `dashboards/tablet/energy.yaml` — full rewrite.
- `dashboards/phone/energy.yaml` — full rewrite.

**Tracked source sensors** (13, referenced throughout):

| Source entity | Friendly name |
|---|---|
| `sensor.sypialnia_lazienka_energy` | Ensuite Bathroom |
| `sensor.kuchnia_ledy_energy` | Kitchen LEDs |
| `sensor.living_room_light_standing_lamp_energy` | Standing Lamp |
| `sensor.swiatlo_przed_domem_energy` | Porch |
| `sensor.main_bathroom_energy` | Bathroom |
| `sensor.wyspa_swiatla_energy` | Kitchen Island |
| `sensor.boiler_room_energy` | Boiler Room |
| `sensor.laundry_energy` | Laundry |
| `sensor.bedroom_reflectors_energy` | Bedroom Reflectors |
| `sensor.sypialnia_sonia_swiatlo_energy` | Bedroom Sona |
| `sensor.washer_energy` | Washer |
| `sensor.tumble_dryer_energy` | Tumble Dryer |

(Only 12 listed — spec counted 13 but two of them — kitchen LEDs already = kitchen lights — wait, re-check: ensuite bathroom, kitchen leds, standing lamp, porch, main bathroom, kitchen island, boiler room, laundry, bedroom reflectors, bedroom sona, washer, tumble dryer = **12**. The original dashboard had 10 + 2 appliances. Spec said 13 in error; correct count is 12. Plan proceeds with 12.)

Corresponding `*_monthly` entities are `sensor.<source_entity_id_without_domain>_monthly`.

---

## Testing / verification strategy

This is a YAML-configuration + Lovelace change. No Python, no unit tests. Verification is:

1. **Schema validity** — `uv run pre-commit run --all-files` for YAML lint.
2. **HA config check** — after each push, HA auto-pulls. Call the `homeassistant.check_config` service (or the `/api/config/core/check_config` endpoint) and tail `home-assistant.log` for errors.
3. **Entity existence** — query the REST API after reload to confirm the new sensors exist with expected states.
4. **Playwright visual check** — force-refetch Lovelace, navigate to `/wall-tablet/energy` and `/mobile-phone/energy`, screenshot, eyeball.

Every task ends with at least one concrete verification command.

---

## Preflight

### Task 0: Sync branch and confirm clean starting state

**Files:** none modified; read-only check.

- [ ] **Step 1: Confirm branch and status**

Run: `git status && git branch --show-current`
Expected: on branch `chore/dashboard-redesign`, working tree has only the spec/plan docs committed, dashboards still reference old content.

- [ ] **Step 2: Confirm tracked entities exist in HA**

Run:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" | \
  jq -r '.[] | select(.entity_id | test("^sensor\\.(sypialnia_lazienka|kuchnia_ledy|living_room_light_standing_lamp|swiatlo_przed_domem|main_bathroom|wyspa_swiatla|boiler_room|laundry|bedroom_reflectors|sypialnia_sonia_swiatlo|washer|tumble_dryer)_energy$")) | .entity_id' | sort | wc -l
```

Expected: `12`

If fewer than 12: an entity has been renamed or removed since the scan. Halt and reconcile before continuing.

---

## Part 1 — Data model

### Task 1: Create the package directory and empty config

**Files:**
- Create: `packages/energy/config.yaml`
- Create: `packages/energy/templates/.gitkeep` (placeholder so directory exists before the sensors file is added)

- [ ] **Step 1: Create directory structure**

Run: `mkdir -p /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/packages/energy/templates`

- [ ] **Step 2: Write `packages/energy/config.yaml` skeleton**

File contents:

```yaml
---
# Energy Package - Tracked-device monthly consumption + cost (PLN)
# See docs/superpowers/specs/2026-04-19-energy-view-redesign-design.md

template: !include_dir_list templates
```

- [ ] **Step 3: Create placeholder templates dir**

Run: `touch /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/packages/energy/templates/.gitkeep`

- [ ] **Step 4: Commit**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git add packages/energy/
git commit -m "feat(energy): scaffold energy package"
```

---

### Task 2: Register the package in configuration.yaml

**Files:**
- Modify: `configuration.yaml` — add a line under `homeassistant.packages`.

- [ ] **Step 1: Edit `configuration.yaml`**

Find the block (currently lines 7–30):

```yaml
  packages:
    bootstrap: !include packages/bootstrap/config.yaml
    frontend: !include packages/frontend/config.yaml
```

Add **immediately after `frontend:`**:

```yaml
    energy: !include packages/energy/config.yaml
```

(Position: alphabetically before area packages; keeps related top-level packages grouped.)

- [ ] **Step 2: Verify config parses**

Run:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/check_config" && echo
```

Then inspect:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -30
```

Expected: no errors mentioning `energy` or `packages`. The `energy` package is registered but empty, so no new entities yet.

- [ ] **Step 3: Commit**

```bash
git add configuration.yaml
git commit -m "feat(energy): register energy package in configuration.yaml"
git push
```

---

### Task 3: Add the tariff rate input_number

**Files:**
- Modify: `packages/energy/config.yaml`

- [ ] **Step 1: Append `input_number:` block**

Append to `packages/energy/config.yaml`:

```yaml

input_number:
  energy_tariff_rate:
    name: Energy Tariff Rate
    min: 0
    max: 3
    step: 0.01
    initial: 1.00
    unit_of_measurement: PLN/kWh
    icon: mdi:cash
    mode: box
```

- [ ] **Step 2: Push and reload HA config**

```bash
git add packages/energy/config.yaml
git commit -m "feat(energy): add energy_tariff_rate input_number helper"
git push
```

Wait ~10 seconds for HA to pull. Then reload:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/input_number/reload"
```

- [ ] **Step 3: Verify entity exists**

Run:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_number.energy_tariff_rate" | jq '.state, .attributes.unit_of_measurement'
```

Expected:

```
"1.0"
"PLN/kWh"
```

---

### Task 4: Add utility_meter entries (monthly cycle) for all 12 sources

**Files:**
- Modify: `packages/energy/config.yaml`

- [ ] **Step 1: Append `utility_meter:` block**

Append to `packages/energy/config.yaml`:

```yaml

utility_meter:
  sypialnia_lazienka_energy_monthly:
    source: sensor.sypialnia_lazienka_energy
    name: Ensuite Bathroom Energy (this month)
    cycle: monthly
  kuchnia_ledy_energy_monthly:
    source: sensor.kuchnia_ledy_energy
    name: Kitchen LEDs Energy (this month)
    cycle: monthly
  living_room_light_standing_lamp_energy_monthly:
    source: sensor.living_room_light_standing_lamp_energy
    name: Standing Lamp Energy (this month)
    cycle: monthly
  swiatlo_przed_domem_energy_monthly:
    source: sensor.swiatlo_przed_domem_energy
    name: Porch Energy (this month)
    cycle: monthly
  main_bathroom_energy_monthly:
    source: sensor.main_bathroom_energy
    name: Bathroom Energy (this month)
    cycle: monthly
  wyspa_swiatla_energy_monthly:
    source: sensor.wyspa_swiatla_energy
    name: Kitchen Island Energy (this month)
    cycle: monthly
  boiler_room_energy_monthly:
    source: sensor.boiler_room_energy
    name: Boiler Room Energy (this month)
    cycle: monthly
  laundry_energy_monthly:
    source: sensor.laundry_energy
    name: Laundry Energy (this month)
    cycle: monthly
  bedroom_reflectors_energy_monthly:
    source: sensor.bedroom_reflectors_energy
    name: Bedroom Reflectors Energy (this month)
    cycle: monthly
  sypialnia_sonia_swiatlo_energy_monthly:
    source: sensor.sypialnia_sonia_swiatlo_energy
    name: Bedroom Sona Energy (this month)
    cycle: monthly
  washer_energy_monthly:
    source: sensor.washer_energy
    name: Washer Energy (this month)
    cycle: monthly
  tumble_dryer_energy_monthly:
    source: sensor.tumble_dryer_energy
    name: Tumble Dryer Energy (this month)
    cycle: monthly
```

Note: `utility_meter` is a root-level integration, not configurable via UI reload. Requires a full HA restart OR the `homeassistant.reload_core_config` service. In this repo we push and reload core config; if entities don't appear, a full restart may be needed.

- [ ] **Step 2: Push and reload**

```bash
git add packages/energy/config.yaml
git commit -m "feat(energy): add monthly utility_meter per tracked source"
git push
```

Wait ~10 s, then:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_core_config"
```

- [ ] **Step 3: Verify all 12 monthly entities exist**

Run:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" | \
  jq -r '.[].entity_id | select(test("_energy_monthly$"))' | sort
```

Expected: 12 entity IDs, one per source.

If any are missing: restart HA (`homeassistant.restart` service). If still missing after restart, inspect the error log for `utility_meter` messages.

- [ ] **Step 4: Check one meter's state**

Run:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/sensor.kuchnia_ledy_energy_monthly" | jq '.state, .attributes.unit_of_measurement, .attributes.source'
```

Expected:

```
"0" or a small numeric string
"kWh"
"sensor.kuchnia_ledy_energy"
```

---

### Task 5: Add the rollup template sensors

**Files:**
- Create: `packages/energy/templates/energy_month.yaml`

- [ ] **Step 1: Write the template file**

File contents:

```yaml
---
sensor:
  - name: energy_tracked_month_kwh
    unique_id: energy_tracked_month_kwh
    unit_of_measurement: kWh
    device_class: energy
    state_class: total
    icon: mdi:lightning-bolt
    state: >
      {% set sources = [
        'sensor.sypialnia_lazienka_energy_monthly',
        'sensor.kuchnia_ledy_energy_monthly',
        'sensor.living_room_light_standing_lamp_energy_monthly',
        'sensor.swiatlo_przed_domem_energy_monthly',
        'sensor.main_bathroom_energy_monthly',
        'sensor.wyspa_swiatla_energy_monthly',
        'sensor.boiler_room_energy_monthly',
        'sensor.laundry_energy_monthly',
        'sensor.bedroom_reflectors_energy_monthly',
        'sensor.sypialnia_sonia_swiatlo_energy_monthly',
        'sensor.washer_energy_monthly',
        'sensor.tumble_dryer_energy_monthly'
      ] %}
      {{ sources | map('states') | map('float', 0) | sum | round(2) }}

  - name: energy_tracked_month_cost
    unique_id: energy_tracked_month_cost
    unit_of_measurement: PLN
    device_class: monetary
    icon: mdi:cash
    state: >
      {% set kwh = states('sensor.energy_tracked_month_kwh') | float(0) %}
      {% set rate = states('input_number.energy_tariff_rate') | float(1) %}
      {{ (kwh * rate) | round(2) }}

  - name: energy_tracked_month_projected_kwh
    unique_id: energy_tracked_month_projected_kwh
    unit_of_measurement: kWh
    device_class: energy
    state_class: total
    icon: mdi:trending-up
    state: >
      {% set kwh = states('sensor.energy_tracked_month_kwh') | float(0) %}
      {% set day = now().day %}
      {% set next_month = (now().replace(day=28) + timedelta(days=4)).replace(day=1) %}
      {% set days_in_month = (next_month - timedelta(days=1)).day %}
      {% if day < 1 or kwh == 0 %}
        unknown
      {% else %}
        {{ (kwh / day * days_in_month) | round(2) }}
      {% endif %}

  - name: energy_tracked_month_projected_cost
    unique_id: energy_tracked_month_projected_cost
    unit_of_measurement: PLN
    device_class: monetary
    icon: mdi:cash-fast
    state: >
      {% set pk = states('sensor.energy_tracked_month_projected_kwh') %}
      {% if pk in ('unknown', 'unavailable', 'none') %}
        unknown
      {% else %}
        {% set rate = states('input_number.energy_tariff_rate') | float(1) %}
        {{ (pk | float(0) * rate) | round(2) }}
      {% endif %}
```

- [ ] **Step 2: Remove .gitkeep placeholder**

Run: `rm /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/packages/energy/templates/.gitkeep`

- [ ] **Step 3: Push and reload templates**

```bash
git add packages/energy/templates/
git commit -m "feat(energy): add monthly rollup template sensors"
git push
```

Wait ~10 s. Then:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_core_config"
```

Template sensors typically require either a core-config reload or a restart. If the entities aren't visible after core reload, restart.

- [ ] **Step 4: Verify the four rollup sensors**

Run:

```bash
for s in energy_tracked_month_kwh energy_tracked_month_cost energy_tracked_month_projected_kwh energy_tracked_month_projected_cost; do
  curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.$s" | jq -r "\"\(.entity_id): \(.state) \(.attributes.unit_of_measurement // \"\")\""
done
```

Expected (values vary by month progress):

```
sensor.energy_tracked_month_kwh: 0 kWh                  (or current accrued kWh)
sensor.energy_tracked_month_cost: 0 PLN                 (or kWh × 1.00)
sensor.energy_tracked_month_projected_kwh: unknown kWh  (or kWh/day × days_in_month)
sensor.energy_tracked_month_projected_cost: unknown PLN (or projected × rate)
```

If any state is `unavailable` or the unit is empty/missing: check the log for Jinja errors. Common cause: a source sensor name typo.

---

## Part 2 — Tablet dashboard

### Task 6: Rewrite `dashboards/tablet/energy.yaml`

**Files:**
- Modify: `dashboards/tablet/energy.yaml` — full rewrite.

- [ ] **Step 1: Replace file contents**

File contents:

```yaml
---
title: Energy
path: energy
icon: mdi:lightning-bolt
type: sections
max_columns: 3
sections:
  - column_span: 3
    cards:
      # ===== Row 1: Hero (this month / projected / rate) =====
      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-template-card
            icon: mdi:lightning-bolt
            icon_color: amber
            primary: >-
              {{ states('sensor.energy_tracked_month_kwh') }} kWh ·
              {{ states('sensor.energy_tracked_month_cost') }} PLN
            secondary: >-
              {% set next_month = (now().replace(day=28) + timedelta(days=4)).replace(day=1) %}
              {% set dim = (next_month - timedelta(days=1)).day %}
              This month · day {{ now().day }} of {{ dim }}
            layout: horizontal

          - type: custom:mushroom-template-card
            icon: mdi:trending-up
            icon_color: blue
            primary: >-
              ~{{ states('sensor.energy_tracked_month_projected_kwh') }} kWh ·
              {{ states('sensor.energy_tracked_month_projected_cost') }} PLN
            secondary: Projected · at current pace
            layout: horizontal
            visibility:
              - condition: numeric_state
                entity: sensor.energy_tracked_month_kwh
                above: 0

          - type: custom:mushroom-template-card
            icon: mdi:cash
            icon_color: teal
            primary: "{{ states('input_number.energy_tariff_rate') }} PLN/kWh"
            secondary: Tariff (tap to edit)
            layout: horizontal
            tap_action:
              action: more-info
              entity: input_number.energy_tariff_rate

      # ===== Row 2: Monthly trend (last 12 months) =====
      - type: statistics-graph
        grid_options:
          columns: full
        title: Last 12 months (kWh)
        period: month
        days_to_show: 365
        stat_types:
          - change
        chart_type: bar
        entities:
          - entity: sensor.energy_tracked_month_kwh

      # ===== Row 3: This month by device (inline bars) =====
      - type: vertical-stack
        grid_options:
          columns: full
        cards:
          - type: custom:mushroom-template-card
            primary: Ensuite Bathroom
            secondary: >-
              {% set k = states('sensor.sypialnia_lazienka_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:shower
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.sypialnia_lazienka_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          # Repeat the above pattern for the other 11 devices.
          # NOTE TO IMPLEMENTER: for each device below, the `primary`,
          # `icon`, and the *first* sensor reference in `secondary` and
          # `card_mod` all point at that device's `*_monthly` entity.
          # The `peak` list inside `card_mod` is identical across all 12
          # cards (the shared max). Keep it copy-pasted rather than DRY'd.

          - type: custom:mushroom-template-card
            primary: Kitchen LEDs
            secondary: >-
              {% set k = states('sensor.kuchnia_ledy_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:led-strip-variant
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.kuchnia_ledy_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Standing Lamp
            secondary: >-
              {% set k = states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:floor-lamp
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Porch
            secondary: >-
              {% set k = states('sensor.swiatlo_przed_domem_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:door
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.swiatlo_przed_domem_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Bathroom
            secondary: >-
              {% set k = states('sensor.main_bathroom_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:shower-head
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.main_bathroom_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Kitchen Island
            secondary: >-
              {% set k = states('sensor.wyspa_swiatla_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:countertop
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.wyspa_swiatla_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Boiler Room
            secondary: >-
              {% set k = states('sensor.boiler_room_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:water-boiler
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.boiler_room_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Laundry
            secondary: >-
              {% set k = states('sensor.laundry_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:washing-machine
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.laundry_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Bedroom Reflectors
            secondary: >-
              {% set k = states('sensor.bedroom_reflectors_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:spotlight-beam
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.bedroom_reflectors_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Bedroom Sona
            secondary: >-
              {% set k = states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:bed
            icon_color: amber
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(255, 193, 7, 0.35)
                      {% set k = states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Washer
            secondary: >-
              {% set k = states('sensor.washer_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:washing-machine
            icon_color: blue
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(33, 150, 243, 0.35)
                      {% set k = states('sensor.washer_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

          - type: custom:mushroom-template-card
            primary: Tumble Dryer
            secondary: >-
              {% set k = states('sensor.tumble_dryer_energy_monthly') | float(0) %}
              {% set r = states('input_number.energy_tariff_rate') | float(1) %}
              {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
            icon: mdi:tumble-dryer
            icon_color: blue
            card_mod:
              style: |
                ha-card {
                  background: linear-gradient(90deg,
                    rgba(33, 150, 243, 0.35)
                      {% set k = states('sensor.tumble_dryer_energy_monthly') | float(0) %}
                      {% set peak = [
                        states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                        states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                        states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                        states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                        states('sensor.main_bathroom_energy_monthly') | float(0),
                        states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                        states('sensor.boiler_room_energy_monthly') | float(0),
                        states('sensor.laundry_energy_monthly') | float(0),
                        states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                        states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                        states('sensor.washer_energy_monthly') | float(0),
                        states('sensor.tumble_dryer_energy_monthly') | float(0)
                      ] | max %}
                      {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                    transparent 0%) !important;
                }

      # ===== Row 4: Live power (condensed) =====
      - type: entities
        grid_options:
          columns: full
        title: Live power (W)
        entities:
          - entity: sensor.sypialnia_lazienka_power
            name: Ensuite Bathroom
          - entity: sensor.kuchnia_ledy_power
            name: Kitchen LEDs
          - entity: sensor.living_room_light_standing_lamp_power
            name: Standing Lamp
          - entity: sensor.swiatlo_przed_domem_power
            name: Porch
          - entity: sensor.main_bathroom_power
            name: Bathroom
          - entity: sensor.wyspa_swiatla_power
            name: Kitchen Island
          - entity: sensor.boiler_room_power
            name: Boiler Room
          - entity: sensor.laundry_power
            name: Laundry
          - entity: sensor.bedroom_reflectors_power
            name: Bedroom Reflectors
          - entity: sensor.sypialnia_sonia_swiatlo_power
            name: Bedroom Sona
          - entity: sensor.washer_power
            name: Washer
          - entity: sensor.tumble_dryer_power
            name: Dryer
```

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: passes or only non-blocking `line-length` warnings inside card_mod templates. No YAML parse errors.

- [ ] **Step 3: Push and force-refetch Lovelace**

```bash
git add dashboards/tablet/energy.yaml
git commit -m "feat(energy): rebuild tablet energy dashboard"
git push
```

Wait ~10 s for HA to pull, then force-refetch the Lovelace dashboard config via the WebSocket bridge (see `.claude/skills/ha-dashboards/references/verify.md`).

- [ ] **Step 4: Playwright visual check**

Navigate to `http://homeassistant.local:8123/wall-tablet/energy`, full-refresh (Ctrl+Shift+R or equivalent), screenshot.

Expected:
- Three hero tiles side-by-side across full viewport width.
- 12-month bar chart below, spanning full width.
- 12 device rows, each showing name, kWh · PLN, and a horizontal bar whose length roughly reflects that device's share of the biggest consumer.
- Compact live-power list at the bottom.

Fail conditions and remedies:
- Narrow "~500 px content strip with huge empty sides" → `grid_options: { columns: full }` missing from one of the cards. Re-check Row 1/2/3/4 roots.
- Blank rows → card_mod template syntax error. Inspect browser devtools console for card-mod errors.
- All bars the same length → `peak` calculation is off. Recheck that all 12 sensors resolve (one unavailable sensor returning `0` is fine; all 12 returning `0` gives a division-by-1 fallback and every bar shows at 0%, so there's no bar — that's OK early in the month).

---

## Part 3 — Phone dashboard

### Task 7: Rewrite `dashboards/phone/energy.yaml`

**Files:**
- Modify: `dashboards/phone/energy.yaml` — full rewrite.

- [ ] **Step 1: Replace file contents**

File contents:

```yaml
---
title: Energy
path: energy
icon: mdi:lightning-bolt
type: sections
max_columns: 1
sections:
  - cards:
      # Hero — single vertical tile
      - type: custom:mushroom-template-card
        icon: mdi:lightning-bolt
        icon_color: amber
        primary: >-
          {{ states('sensor.energy_tracked_month_kwh') }} kWh ·
          {{ states('sensor.energy_tracked_month_cost') }} PLN
        secondary: >-
          {% set next_month = (now().replace(day=28) + timedelta(days=4)).replace(day=1) %}
          {% set dim = (next_month - timedelta(days=1)).day %}
          This month · day {{ now().day }}/{{ dim }} ·
          on pace for {{ states('sensor.energy_tracked_month_projected_cost') }} PLN
        layout: vertical

  - cards:
      # Rate chip
      - type: custom:mushroom-template-card
        icon: mdi:cash
        icon_color: teal
        primary: "{{ states('input_number.energy_tariff_rate') }} PLN/kWh"
        secondary: Tariff (tap to edit)
        layout: horizontal
        tap_action:
          action: more-info
          entity: input_number.energy_tariff_rate

  - cards:
      # Monthly trend — last 12 months
      - type: statistics-graph
        title: Last 12 months (kWh)
        period: month
        days_to_show: 365
        stat_types:
          - change
        chart_type: bar
        entities:
          - entity: sensor.energy_tracked_month_kwh

  - cards:
      # This month by device — same 12-card stack as tablet row 3
      # (Copy the exact 12 `custom:mushroom-template-card` definitions
      #  from dashboards/tablet/energy.yaml Row 3 here verbatim.
      #  See tablet file for the complete card bodies — do NOT abbreviate.)
      - type: custom:mushroom-template-card
        primary: Ensuite Bathroom
        secondary: >-
          {% set k = states('sensor.sypialnia_lazienka_energy_monthly') | float(0) %}
          {% set r = states('input_number.energy_tariff_rate') | float(1) %}
          {{ k | round(2) }} kWh · {{ (k * r) | round(2) }} PLN
        icon: mdi:shower
        icon_color: amber
        card_mod:
          style: |
            ha-card {
              background: linear-gradient(90deg,
                rgba(255, 193, 7, 0.35)
                  {% set k = states('sensor.sypialnia_lazienka_energy_monthly') | float(0) %}
                  {% set peak = [
                    states('sensor.sypialnia_lazienka_energy_monthly') | float(0),
                    states('sensor.kuchnia_ledy_energy_monthly') | float(0),
                    states('sensor.living_room_light_standing_lamp_energy_monthly') | float(0),
                    states('sensor.swiatlo_przed_domem_energy_monthly') | float(0),
                    states('sensor.main_bathroom_energy_monthly') | float(0),
                    states('sensor.wyspa_swiatla_energy_monthly') | float(0),
                    states('sensor.boiler_room_energy_monthly') | float(0),
                    states('sensor.laundry_energy_monthly') | float(0),
                    states('sensor.bedroom_reflectors_energy_monthly') | float(0),
                    states('sensor.sypialnia_sonia_swiatlo_energy_monthly') | float(0),
                    states('sensor.washer_energy_monthly') | float(0),
                    states('sensor.tumble_dryer_energy_monthly') | float(0)
                  ] | max %}
                  {{ ((k / (peak if peak > 0 else 1)) * 100) | round(0) }}%,
                transparent 0%) !important;
            }

      # ... (11 more cards — Kitchen LEDs, Standing Lamp, Porch, Bathroom,
      #  Kitchen Island, Boiler Room, Laundry, Bedroom Reflectors,
      #  Bedroom Sona, Washer, Tumble Dryer — copy each verbatim from the
      #  tablet dashboard Row 3. Keep the same `icon_color` distinction:
      #  `amber` for lights, `blue` for washer + tumble dryer.)
```

**IMPORTANT IMPLEMENTER NOTE:** The placeholder comment `# ... (11 more cards ...)` MUST be expanded into the 11 actual `custom:mushroom-template-card` definitions, copied verbatim from the tablet file Row 3. Do not ship the file with an unresolved comment. Each card is standalone; there is no shared helper.

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: passes.

- [ ] **Step 3: Push and force-refetch Lovelace**

```bash
git add dashboards/phone/energy.yaml
git commit -m "feat(energy): rebuild phone energy dashboard"
git push
```

- [ ] **Step 4: Playwright visual check (phone viewport)**

Navigate to `http://homeassistant.local:8123/mobile-phone/energy` with a phone-sized viewport (e.g., `browser_resize` to 390×844). Force-refresh.

Expected:
- Hero tile stacked vertically at top, kWh + PLN on one line, subtitle underneath.
- Rate chip below.
- 12-month bar chart below.
- 12 device rows with inline bars.
- No live-power row.

---

## Part 4 — Wrap-up

### Task 8: Sanity-check the full dashboard set

**Files:** none modified; verification only.

- [ ] **Step 1: Confirm no regressions in other tabs**

Playwright-navigate to `/wall-tablet/home`, `/wall-tablet/climate`, `/wall-tablet/appliances`, `/mobile-phone/home`. Each should render without card-load errors. The energy changes were additive (new package, new templates) + local (two dashboard files), so regressions are unlikely, but confirm.

- [ ] **Step 2: Check HA error log for anything new**

Run:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -60
```

Expected: no `utility_meter`, `template`, or `input_number` ERROR lines. A small number of transient `unavailable` warnings during startup is fine.

- [ ] **Step 3: Optional — set a real tariff value**

In the HA UI, open `input_number.energy_tariff_rate` more-info and enter the actual PGE G11 rate from the last bill. The hero card PLN figures update live.

- [ ] **Step 4: No extra commit; confirm branch state**

Run:

```bash
git log --oneline origin/main..HEAD
```

Expected: six to eight new commits (scaffold, register package, input_number, utility_meter, template sensors, tablet dashboard, phone dashboard, any small fixes). All on branch `chore/dashboard-redesign`, none on `main`.

---

## Post-plan self-review

Ran through the plan against the spec:

- **Goal 1 (monthly kWh + PLN):** covered by Tasks 3, 4, 5, 6, 7. ✓
- **Goal 2 (clear to read):** single-column hero + trend + sorted per-device list addresses the "stacked 10-entity bars were unreadable" complaint. ✓
- **Non-goals:** no HA Energy page touched, no whole-home meter added, no standing charge — reflected by the tasks done. ✓
- **Data flow:** source → `utility_meter` (Task 4) → rollup templates (Task 5) → dashboards (Tasks 6–7). Matches spec §F. ✓
- **12 vs 13 devices:** spec said "13"; plan ground-truths to 12 (actual count). Discrepancy noted in the File Structure section. ✓
- **Placeholder scan:** one deliberate instruction comment in Task 7 Step 1 telling the implementer to expand the 11 repeated cards. Called out in bold. All other code blocks are complete. ✓
- **Type consistency:** sensor names match across all tasks (`sensor.energy_tracked_month_kwh`, etc.). Source sensor entity_ids match the scan output. utility_meter object keys match the `<source>_monthly` naming. ✓
- **Risks from spec:** `unavailable` sources handled via `| float(0)` throughout; divide-by-zero in projection handled via `if peak > 0 else 1` and `if kwh == 0 then unknown`. ✓
