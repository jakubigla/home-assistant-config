# Garden Irrigation Automation — Design Spec

**Date:** 2026-04-10
**Area package:** `packages/areas/outdoor/garden/`

## Overview

Automated irrigation system for a 4-zone Tuya sprinkler controller in Poland. Three lawn zones run sequentially (never simultaneously), followed by drip irrigation for flowers/plants. Behavior is driven by an `input_select` mode selector with a profile-based configuration system.

## Entities

### Valve Entities (existing, from Tuya Local)

| Entity ID | Purpose |
|---|---|
| `valve.lawn_sprinkler_zone_1` | Lawn zone 1 |
| `valve.lawn_sprinkler_zone_2` | Lawn zone 2 |
| `valve.lawn_sprinkler_zone_3` | Lawn zone 3 |
| `valve.drip_irrigation` | Drip irrigation (flowers/plants) |
| `valve.garden_all_valves` | All valves (not used by automation) |

Zones 5–8 are unused (controller only supports 4 physical zones).

### Helper Entities (new)

| Entity ID | Type | Purpose |
|---|---|---|
| `input_select.garden_irrigation_mode` | input_select | Mode selector: Eco, Standard, Intensive, Smart |

## Area Package Structure

```
packages/areas/outdoor/garden/
├── config.yaml
├── automations/
│   └── garden_scheduled_irrigation.yaml
├── scripts/
│   ├── garden_lawn_zone_1.yaml
│   ├── garden_lawn_zone_2.yaml
│   ├── garden_lawn_zone_3.yaml
│   ├── garden_lawn_irrigation.yaml
│   ├── garden_drip_irrigation.yaml
│   └── garden_full_irrigation.yaml
└── templates/
    ├── garden_irrigation_profile.yaml
    └── garden_should_skip_irrigation.yaml
```

## Config — `config.yaml`

```yaml
input_select:
  garden_irrigation_mode:
    name: Garden Irrigation Mode
    options:
      - Eco
      - Standard
      - Intensive
      - Smart
    icon: mdi:sprinkler
    # No 'initial' — HA persists last selected value across restarts
```

HomeKit exposure for on-demand control:

```yaml
homekit:
  filter:
    include_entities:
      - script.garden_full_irrigation
      - script.garden_lawn_irrigation
      - script.garden_drip_irrigation
      - script.garden_lawn_zone_1
      - script.garden_lawn_zone_2
      - script.garden_lawn_zone_3
```

## Skip Logic — `garden_should_skip_irrigation.yaml`

Binary sensor that gates whether irrigation should run. Returns `on` when irrigation should be **skipped**.

```yaml
- binary_sensor:
    - name: Garden Should Skip Irrigation
      unique_id: garden_should_skip_irrigation
      icon: mdi:water-off
      state: >
        {% set is_raining = is_state('binary_sensor.raining', 'on') %}
        {% set month = now().month %}
        {% set in_season = month >= 5 and month <= 9 %}
        {% set rain_forecast = state_attr('weather.forecast_home', 'forecast')
            | default([])
            | selectattr('datetime', 'le', (now() + timedelta(hours=6)).isoformat())
            | selectattr('condition', 'in', ['rainy', 'pouring', 'lightning-rainy'])
            | list
            | count > 0 %}
        {{ is_raining or rain_forecast or not in_season }}
      attributes:
        reason: >
          {% if not (now().month >= 5 and now().month <= 9) %}
            out_of_season
          {% elif is_state('binary_sensor.raining', 'on') %}
            raining_now
          {% elif state_attr('weather.forecast_home', 'forecast')
              | default([])
              | selectattr('datetime', 'le', (now() + timedelta(hours=6)).isoformat())
              | selectattr('condition', 'in', ['rainy', 'pouring', 'lightning-rainy'])
              | list
              | count > 0 %}
            rain_forecast_within_6h
          {% else %}
            none
          {% endif %}
```

Skip conditions:
- **Out of season:** Before May or after September
- **Currently raining:** Uses existing `binary_sensor.raining`
- **Rain forecasted within 6 hours:** Checks Met.no hourly forecast
- **Future-ready:** Add `{% set soil_too_wet = ... %}` when soil moisture sensor is available

Note: In HA 2024.x+, `forecast` is no longer a direct attribute — use `weather.get_forecasts` service call via a trigger-based template sensor or `action` in the template. During implementation, verify which approach the current HA version supports and adapt accordingly.

## Irrigation Profile — `garden_irrigation_profile.yaml`

Template sensor with a profiles dictionary for easy mode management.

```yaml
- sensor:
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
                          'lawn_days': [1, 2, 3, 4, 5, 6, 7], 'drip_days': [1, 2, 3, 4, 5, 6, 7]},
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

### Adding a New Mode

To add a new irrigation mode (e.g., "Seedling"):

1. **Add the profile** to the `profiles` attribute dictionary in `garden_irrigation_profile.yaml`:
   ```yaml
   'Seedling': {'lawn_duration': 5, 'drip_duration': 20,
                'lawn_days': [1, 2, 3, 4, 5, 6, 7], 'drip_days': [1, 2, 3, 4, 5, 6, 7]},
   ```
2. **Add the option** to `input_select.garden_irrigation_mode` in `config.yaml`:
   ```yaml
   options:
     - Eco
     - Standard
     - Intensive
     - Seedling    # ← new
     - Smart
   ```

That's it. The resolved attributes (`lawn_duration`, `drip_duration`, `lawn_today`, `drip_today`) automatically pick up the new profile. Scripts and automations require no changes.

### Profile Reference

| Mode | Lawn days | Lawn min/zone | Drip days | Drip min |
|---|---|---|---|---|
| Eco | Mon, Thu | 10 | Mon, Wed, Fri | 30 |
| Standard | Mon, Wed, Fri | 15 | Weekdays | 45 |
| Intensive | Daily | 20 | Daily | 60 |
| Smart | Season + temp driven | Season + temp driven | Season + temp driven | Season + temp driven |

### Smart Mode Logic

Smart mode dynamically selects durations and days based on current month and temperature:

| Condition | Lawn duration | Lawn days | Drip duration | Drip days |
|---|---|---|---|---|
| Temp ≥ 30°C (heatwave) | 20 min | Daily | 60 min | Daily |
| July | 20 min | Mon–Fri | 60 min | Daily |
| June, August | 15 min | Mon, Wed, Fri | 45 min | Weekdays |
| May, September | 10 min | Mon, Thu | 30 min | Mon, Wed, Fri |
| Default (fallback) | 15 min | Mon, Wed, Fri | 45 min | Mon, Wed, Fri |

## Scripts

### Individual Zone Scripts

Each zone has its own script for HomeKit/on-demand control. Pattern (zone 1 shown):

```yaml
garden_lawn_zone_1:
  alias: Garden Lawn Zone 1
  icon: mdi:sprinkler
  mode: single
  sequence:
    - variables:
        duration: "{{ state_attr('sensor.garden_irrigation_profile', 'lawn_duration') | int(15) }}"
    - action: valve.open
      target:
        entity_id: valve.lawn_sprinkler_zone_1
    - delay:
        minutes: "{{ duration }}"
    - action: valve.close
      target:
        entity_id: valve.lawn_sprinkler_zone_1
```

Zones 2 and 3 follow the same pattern with their respective entities.

### Sequential Lawn Script — `garden_lawn_irrigation.yaml`

Chains zones 1→2→3 by calling individual zone scripts:

```yaml
garden_lawn_irrigation:
  alias: Garden Lawn Irrigation
  icon: mdi:sprinkler
  mode: single
  sequence:
    - action: script.garden_lawn_zone_1
    - action: script.garden_lawn_zone_2
    - action: script.garden_lawn_zone_3
```

### Drip Script — `garden_drip_irrigation.yaml`

```yaml
garden_drip_irrigation:
  alias: Garden Drip Irrigation
  icon: mdi:water-outline
  mode: single
  sequence:
    - variables:
        duration: "{{ state_attr('sensor.garden_irrigation_profile', 'drip_duration') | int(45) }}"
    - action: valve.open
      target:
        entity_id: valve.drip_irrigation
    - delay:
        minutes: "{{ duration }}"
    - action: valve.close
      target:
        entity_id: valve.drip_irrigation
```

### Full Irrigation Script — `garden_full_irrigation.yaml`

Lawn then drip, chained (drip starts after lawn finishes):

```yaml
garden_full_irrigation:
  alias: Garden Full Irrigation
  icon: mdi:watering-can
  mode: single
  sequence:
    - action: script.garden_lawn_irrigation
    - action: script.garden_drip_irrigation
```

## Scheduled Automation — `garden_scheduled_irrigation.yaml`

Fires at 6 AM daily. Checks skip conditions, then checks which parts should run today.

```yaml
- id: garden_scheduled_irrigation
  alias: Garden Scheduled Irrigation
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

## HomeKit Integration

Exposed as switches in HomeKit for Siri/Home app control:

| HomeKit Name | Script | Use Case |
|---|---|---|
| Garden Full Irrigation | `script.garden_full_irrigation` | "Hey Siri, turn on Garden Full Irrigation" |
| Garden Lawn Irrigation | `script.garden_lawn_irrigation` | All 3 lawn zones sequential |
| Garden Lawn Zone 1/2/3 | `script.garden_lawn_zone_{1,2,3}` | Individual zone on-demand |
| Garden Drip Irrigation | `script.garden_drip_irrigation` | Drip only on-demand |

## Design Decisions

1. **Script-centric approach** — scripts handle sequencing and durations, automations handle scheduling and conditions. Clean separation of *when* vs *what*.
2. **Profile dictionary** — single place to define mode parameters. Adding a mode is a 2-line change (dict entry + input_select option).
3. **Smart mode in templates** — no separate automation to switch modes. Smart computes values dynamically from season and temperature.
4. **Shared skip logic** — one binary sensor gates both lawn and drip. Both skip for rain, forecast, and out-of-season.
5. **mode: single on all scripts** — prevents overlapping runs (hardware limitation: valves can't run simultaneously).
6. **Composable scripts** — individual zone scripts are called by the sequential script. On-demand and scheduled use the same scripts.
7. **Future soil moisture** — skip logic sensor is ready for an additional condition when a moisture sensor is added.

## Out of Scope

- Dashboard cards for irrigation (can be added later)
- Notifications (e.g., "irrigation skipped due to rain")
- Water usage tracking
- Soil moisture sensor integration (designed for, not implemented)
