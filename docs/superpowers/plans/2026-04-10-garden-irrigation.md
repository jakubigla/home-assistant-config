# Garden Irrigation Automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automated irrigation system with mode-driven profiles, weather-aware skip logic, auto-off valve control, HomeKit integration, and sequential scripting for a 4-zone Tuya sprinkler in Poland.

**Architecture:** Auto-off automation is the single source of truth for valve durations. Scripts are pure sequencers that open valves and wait for them to close. A profile template sensor maps modes to durations/days. A skip logic binary sensor gates scheduled runs based on rain and season.

**Tech Stack:** Home Assistant YAML packages, Jinja2 templates, Tuya Local valves, HomeKit integration, Met.no weather

**Spec:** `docs/superpowers/specs/2026-04-10-garden-irrigation-design.md`

---

### Task 1: Create area package skeleton and config

**Files:**
- Create: `packages/areas/outdoor/garden/config.yaml`
- Create: `packages/areas/outdoor/garden/automations/` (directory)
- Create: `packages/areas/outdoor/garden/scripts/` (directory)
- Create: `packages/areas/outdoor/garden/templates/` (directory)
- Modify: `configuration.yaml:26` (add garden package include)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p packages/areas/outdoor/garden/{automations,scripts,templates}
```

- [ ] **Step 2: Create config.yaml**

Create `packages/areas/outdoor/garden/config.yaml`:

```yaml
---
automation: !include_dir_list automations
template: !include_dir_list templates
script: !include_dir_merge_named scripts

input_select:
  garden_irrigation_mode:
    name: Garden Irrigation Mode
    options:
      - Eco
      - Standard
      - Intensive
      - Smart
    icon: mdi:sprinkler
```

Note: `!include_dir_merge_named` is used for scripts because each script file defines a named script (key: value), unlike automations/templates which use list format.

- [ ] **Step 3: Add garden package to configuration.yaml**

In `configuration.yaml`, add after the `gate` line (line 26):

```yaml
    garden: !include packages/areas/outdoor/garden/config.yaml
```

- [ ] **Step 4: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/config.yaml
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/config.yaml configuration.yaml
git commit -m "feat(garden): add irrigation area package skeleton with input_select"
```

---

### Task 2: Create skip logic template sensor

**Files:**
- Create: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`

- [ ] **Step 1: Create the skip logic binary sensor**

Create `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`:

```yaml
---
# Garden Should Skip Irrigation
#
# Returns 'on' when irrigation should be SKIPPED.
# Checks: season (May-Sep only), current rain, rain forecast (6h lookahead).
# Future: add soil moisture check when sensor is available.
binary_sensor:
  - name: Garden Should Skip Irrigation
    unique_id: garden_should_skip_irrigation
    icon: mdi:water-off
    state: >
      {% set is_raining = is_state('binary_sensor.raining', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set rain_conditions = ['rainy', 'pouring', 'lightning-rainy'] %}
      {% set forecast = state_attr('weather.forecast_home', 'forecast') | default([]) %}
      {% set cutoff = (now() + timedelta(hours=6)).isoformat() %}
      {% set rain_forecast = forecast
          | selectattr('datetime', 'le', cutoff)
          | selectattr('condition', 'in', rain_conditions)
          | list
          | count > 0 %}
      {{ is_raining or rain_forecast or not in_season }}
    attributes:
      reason: >
        {% set month = now().month %}
        {% set in_season = month >= 5 and month <= 9 %}
        {% set rain_conditions = ['rainy', 'pouring', 'lightning-rainy'] %}
        {% set forecast = state_attr('weather.forecast_home', 'forecast') | default([]) %}
        {% set cutoff = (now() + timedelta(hours=6)).isoformat() %}
        {% if not in_season %}
          out_of_season
        {% elif is_state('binary_sensor.raining', 'on') %}
          raining_now
        {% elif forecast
            | selectattr('datetime', 'le', cutoff)
            | selectattr('condition', 'in', rain_conditions)
            | list
            | count > 0 %}
          rain_forecast_within_6h
        {% else %}
          none
        {% endif %}
```

- [ ] **Step 2: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): add skip logic binary sensor with rain and season checks"
```

---

### Task 3: Create irrigation profile template sensor

**Files:**
- Create: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

- [ ] **Step 1: Create the profile sensor**

Create `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`:

```yaml
---
# Garden Irrigation Profile
#
# Maps the selected irrigation mode to durations (minutes) and schedule days.
# The 'profiles' attribute is a dictionary — the single source of truth
# for all non-Smart mode parameters.
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │ HOW TO ADD A NEW MODE                                              │
# │                                                                    │
# │ 1. Add an entry to the 'profiles' dict below with:                │
# │    - lawn_duration: minutes per lawn zone                          │
# │    - drip_duration: minutes for drip irrigation                    │
# │    - lawn_days: list of ISO weekdays (1=Mon, 7=Sun)                │
# │    - drip_days: list of ISO weekdays (1=Mon, 7=Sun)                │
# │                                                                    │
# │ 2. Add the option to input_select.garden_irrigation_mode           │
# │    in config.yaml                                                  │
# │                                                                    │
# │ That's it — resolved attributes pick up the new profile            │
# │ automatically. Scripts and automations need no changes.            │
# │                                                                    │
# │ Profile reference:                                                 │
# │   Eco:       lawn 10min 2x/wk, drip 30min 3x/wk                  │
# │   Standard:  lawn 15min 3x/wk, drip 45min weekdays                │
# │   Intensive: lawn 20min daily,  drip 60min daily                   │
# │   Smart:     auto-selects based on month + temperature             │
# └─────────────────────────────────────────────────────────────────────┘
sensor:
  - name: Garden Irrigation Profile
    unique_id: garden_irrigation_profile
    icon: mdi:sprinkler-variant
    state: "{{ states('input_select.garden_irrigation_mode') }}"
    attributes:
      profiles: >
        {{ {
          'Eco':       {'lawn_duration': 10, 'drip_duration': 30,
                        'lawn_days': [1, 4],       'drip_days': [1, 3, 5]},
          'Standard':  {'lawn_duration': 15, 'drip_duration': 45,
                        'lawn_days': [1, 3, 5],    'drip_days': [1, 2, 3, 4, 5]},
          'Intensive': {'lawn_duration': 20, 'drip_duration': 60,
                        'lawn_days': [1, 2, 3, 4, 5, 6, 7],
                        'drip_days': [1, 2, 3, 4, 5, 6, 7]},
        } }}
      lawn_duration: >
        {% set mode = states('input_select.garden_irrigation_mode') %}
        {% set profiles = state_attr('sensor.garden_irrigation_profile', 'profiles') %}
        {% if mode == 'Smart' %}
          {% set temp = state_attr('weather.forecast_home', 'temperature') | float(20) %}
          {% set month = now().month %}
          {% if temp >= 30 %} 20
          {% elif month in [5, 9] %} 10
          {% elif month in [6, 8] %} 15
          {% elif month == 7 %} 20
          {% else %} 15 {% endif %}
        {% else %}
          {{ profiles.get(mode, profiles['Standard'])['lawn_duration'] }}
        {% endif %}
      drip_duration: >
        {% set mode = states('input_select.garden_irrigation_mode') %}
        {% set profiles = state_attr('sensor.garden_irrigation_profile', 'profiles') %}
        {% if mode == 'Smart' %}
          {% set temp = state_attr('weather.forecast_home', 'temperature') | float(20) %}
          {% set month = now().month %}
          {% if temp >= 30 %} 60
          {% elif month in [5, 9] %} 30
          {% elif month in [6, 8] %} 45
          {% elif month == 7 %} 60
          {% else %} 45 {% endif %}
        {% else %}
          {{ profiles.get(mode, profiles['Standard'])['drip_duration'] }}
        {% endif %}
      lawn_today: >
        {% set mode = states('input_select.garden_irrigation_mode') %}
        {% set profiles = state_attr('sensor.garden_irrigation_profile', 'profiles') %}
        {% set dow = now().isoweekday() %}
        {% if mode == 'Smart' %}
          {% set temp = state_attr('weather.forecast_home', 'temperature') | float(20) %}
          {% set month = now().month %}
          {% if temp >= 30 %} true
          {% elif month in [5, 9] %} {{ dow in [1, 4] }}
          {% elif month in [6, 8] %} {{ dow in [1, 3, 5] }}
          {% elif month == 7 %} {{ dow in [1, 2, 3, 4, 5] }}
          {% else %} {{ dow in [1, 3, 5] }} {% endif %}
        {% else %}
          {{ dow in profiles.get(mode, profiles['Standard'])['lawn_days'] }}
        {% endif %}
      drip_today: >
        {% set mode = states('input_select.garden_irrigation_mode') %}
        {% set profiles = state_attr('sensor.garden_irrigation_profile', 'profiles') %}
        {% set dow = now().isoweekday() %}
        {% if mode == 'Smart' %}
          {% set temp = state_attr('weather.forecast_home', 'temperature') | float(20) %}
          {% set month = now().month %}
          {% if temp >= 30 %} true
          {% elif month in [5, 9] %} {{ dow in [1, 3, 5] }}
          {% elif month in [6, 8] %} {{ dow in [1, 2, 3, 4, 5] }}
          {% elif month == 7 %} true
          {% else %} {{ dow in [1, 3, 5] }} {% endif %}
        {% else %}
          {{ dow in profiles.get(mode, profiles['Standard'])['drip_days'] }}
        {% endif %}
```

- [ ] **Step 2: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git commit -m "feat(garden): add irrigation profile sensor with mode-driven durations and days"
```

---

### Task 4: Create valve auto-off automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml`

- [ ] **Step 1: Create the auto-off automation**

Create `packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml`:

```yaml
---
alias: Garden Valve Auto Off
description: >
  Automatically closes any irrigation valve after the profile-driven
  duration. This is the main duration controller — scripts just open
  valves and wait for this automation to close them. Also serves as
  a safety net for manually opened valves via HomeKit.
id: garden-valve-auto-off

mode: parallel
max: 4

trigger:
  - platform: state
    entity_id:
      - valve.lawn_sprinkler_zone_1
      - valve.lawn_sprinkler_zone_2
      - valve.lawn_sprinkler_zone_3
    to: "open"
    id: "lawn"
  - platform: state
    entity_id: valve.drip_irrigation
    to: "open"
    id: "drip"

action:
  - variables:
      duration: >
        {% if trigger.id == 'lawn' %}
          {{ state_attr('sensor.garden_irrigation_profile', 'lawn_duration') | int(15) }}
        {% else %}
          {{ state_attr('sensor.garden_irrigation_profile', 'drip_duration') | int(45) }}
        {% endif %}
  - delay:
      minutes: "{{ duration }}"
  - action: valve.close
    target:
      entity_id: "{{ trigger.entity_id }}"
```

- [ ] **Step 2: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml
git commit -m "feat(garden): add valve auto-off automation as single duration controller"
```

---

### Task 5: Create irrigation scripts

**Files:**
- Create: `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml`
- Create: `packages/areas/outdoor/garden/scripts/garden_drip_irrigation.yaml`
- Create: `packages/areas/outdoor/garden/scripts/garden_full_irrigation.yaml`

- [ ] **Step 1: Create sequential lawn irrigation script**

Create `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml`:

```yaml
---
garden_lawn_irrigation:
  alias: Garden Lawn Irrigation
  description: >
    Runs lawn zones 1→2→3 sequentially. Opens each valve and waits
    for the auto-off automation to close it before moving to the next.
  icon: mdi:sprinkler
  mode: single
  sequence:
    - action: valve.open
      target:
        entity_id: valve.lawn_sprinkler_zone_1
    - wait_for_trigger:
        - platform: state
          entity_id: valve.lawn_sprinkler_zone_1
          to: "closed"
      timeout:
        minutes: 30
    - delay:
        seconds: 5
    - action: valve.open
      target:
        entity_id: valve.lawn_sprinkler_zone_2
    - wait_for_trigger:
        - platform: state
          entity_id: valve.lawn_sprinkler_zone_2
          to: "closed"
      timeout:
        minutes: 30
    - delay:
        seconds: 5
    - action: valve.open
      target:
        entity_id: valve.lawn_sprinkler_zone_3
    - wait_for_trigger:
        - platform: state
          entity_id: valve.lawn_sprinkler_zone_3
          to: "closed"
      timeout:
        minutes: 30
```

- [ ] **Step 2: Create drip irrigation script**

Create `packages/areas/outdoor/garden/scripts/garden_drip_irrigation.yaml`:

```yaml
---
garden_drip_irrigation:
  alias: Garden Drip Irrigation
  description: >
    Opens drip irrigation valve and waits for auto-off to close it.
  icon: mdi:water-outline
  mode: single
  sequence:
    - action: valve.open
      target:
        entity_id: valve.drip_irrigation
    - wait_for_trigger:
        - platform: state
          entity_id: valve.drip_irrigation
          to: "closed"
      timeout:
        minutes: 90
```

- [ ] **Step 3: Create full irrigation script**

Create `packages/areas/outdoor/garden/scripts/garden_full_irrigation.yaml`:

```yaml
---
garden_full_irrigation:
  alias: Garden Full Irrigation
  description: >
    Runs complete irrigation sequence: all 3 lawn zones followed by
    drip irrigation. Each step waits for the previous to finish.
  icon: mdi:watering-can
  mode: single
  sequence:
    - action: script.garden_lawn_irrigation
    - delay:
        seconds: 5
    - action: script.garden_drip_irrigation
```

- [ ] **Step 4: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml packages/areas/outdoor/garden/scripts/garden_drip_irrigation.yaml packages/areas/outdoor/garden/scripts/garden_full_irrigation.yaml
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/scripts/
git commit -m "feat(garden): add lawn, drip, and full irrigation scripts"
```

---

### Task 6: Create scheduled irrigation automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`

- [ ] **Step 1: Create the scheduled automation**

Create `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`:

```yaml
---
alias: Garden Scheduled Irrigation
description: >
  Fires daily at 6 AM. Checks skip conditions (rain, season), then
  checks which parts (lawn, drip) should run today based on the
  active irrigation profile.
id: garden-scheduled-irrigation

mode: single

trigger:
  - platform: time
    at: "06:00:00"

condition:
  - condition: state
    entity_id: binary_sensor.garden_should_skip_irrigation
    state: "off"

action:
  - variables:
      lawn_today: "{{ state_attr('sensor.garden_irrigation_profile', 'lawn_today') }}"
      drip_today: "{{ state_attr('sensor.garden_irrigation_profile', 'drip_today') }}"
  - choose:
      - conditions:
          - "{{ lawn_today }}"
          - "{{ drip_today }}"
        sequence:
          - action: script.garden_full_irrigation
      - conditions:
          - "{{ lawn_today }}"
        sequence:
          - action: script.garden_lawn_irrigation
      - conditions:
          - "{{ drip_today }}"
        sequence:
          - action: script.garden_drip_irrigation
```

- [ ] **Step 2: Verify YAML is valid**

```bash
uv run yamllint packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml
git commit -m "feat(garden): add scheduled irrigation automation with weather-aware skip logic"
```

---

### Task 7: Add HomeKit integration

**Files:**
- Modify: `packages/homekit/config.yaml:88-89` (add valve and script entities to include list)
- Modify: `packages/homekit/config.yaml:206-207` (add entity_config entries)

- [ ] **Step 1: Add entities to HomeKit include list**

In `packages/homekit/config.yaml`, after the existing `# Garden` section (line 88-89), replace:

```yaml
      # Garden
      - lawn_mower.garden
```

with:

```yaml
      # Garden
      - lawn_mower.garden
      - valve.lawn_sprinkler_zone_1
      - valve.lawn_sprinkler_zone_2
      - valve.lawn_sprinkler_zone_3
      - valve.drip_irrigation
      - script.garden_lawn_irrigation
      - script.garden_full_irrigation
```

- [ ] **Step 2: Add entity_config entries**

In `packages/homekit/config.yaml`, after the `lawn_mower.garden` entity_config entry (line 207), add:

```yaml
    valve.lawn_sprinkler_zone_1:
      name: Lawn Zone 1
    valve.lawn_sprinkler_zone_2:
      name: Lawn Zone 2
    valve.lawn_sprinkler_zone_3:
      name: Lawn Zone 3
    valve.drip_irrigation:
      name: Drip Irrigation
    script.garden_lawn_irrigation:
      name: Lawn Irrigation
    script.garden_full_irrigation:
      name: Full Irrigation
```

- [ ] **Step 3: Verify YAML is valid**

```bash
uv run yamllint packages/homekit/config.yaml
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add packages/homekit/config.yaml
git commit -m "feat(garden): expose irrigation valves and scripts to HomeKit"
```

---

### Task 8: Lint all files and push

**Files:**
- All files created/modified in tasks 1-7

- [ ] **Step 1: Run full lint check**

```bash
uv run yamllint .
```

Expected: no errors from garden files

- [ ] **Step 2: Run pre-commit hooks**

```bash
uv run pre-commit run --all-files
```

Expected: all checks pass

- [ ] **Step 3: Push branch**

```bash
git push origin feature/sprinkle
```

---

### Task 9: Generate area README

- [ ] **Step 1: Generate README using ha-area-docs skill**

Run `/ha-area-docs` skill for the garden area package to generate `packages/areas/outdoor/garden/README.md`.

- [ ] **Step 2: Commit**

```bash
git add packages/areas/outdoor/garden/README.md
git commit -m "docs(garden): add area README for irrigation package"
```
