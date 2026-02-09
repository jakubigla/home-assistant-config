# CLAUDE.md

This file provides guidance to Claude Code when working with this Home Assistant configuration repository.

## Interacting with Home Assistant

When you need to query or control Home Assistant (entity states, service calls, registry operations), follow this escalation order:

1. **MCP tools first** — use the HomeAssistant MCP tools (`HassTurnOn`, `HassTurnOff`, `GetLiveContext`, `HassLightSet`, `HassClimateSetTemperature`, etc.) and ha-config-analyzer MCP tools (`find_entity_usages`, `analyze_automation`, `search_config`, etc.) for direct device control, state queries, and config analysis
2. **`/cli` skill second** — use `hass-cli` when MCP tools don't cover the operation (e.g., bulk state queries, entity registry, detailed history)
3. **`/api` skill third** — fall back to REST/WebSocket API (`curl`/`websocat`) when neither MCP nor CLI can do what's needed (e.g., registry updates, template rendering, event subscriptions)
4. **Playwright as last resort** — only use browser automation when all above are insufficient (e.g., UI-only operations, dashboard debugging, visual verification)

## Project Overview

Home Assistant configuration for a smart home in Poland, using a modular, package-based architecture.

## Commands

- Always use `uv` to run Python scripts and tools (e.g., `uv run python script.py`, `uv run yamllint .`). Do not use `pip` or `pip3` directly.
- When running git commands, use the working directory directly. Do NOT use `git -C <path>`.

### Linting

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Lint YAML files only
uv run yamllint .
```

## Architecture

### Package-Based Organization

The configuration is split into modular packages in `/packages/`:

- **Areas**: Each room has its own package in `/packages/areas/{floor}/{area}/`
- **Bootstrap**: Core system configurations and templates in `/packages/bootstrap/`
- **Frontend**: UI customizations and themes
- **Presence**: Occupancy detection logic
- **Homekit**: Apple HomeKit integration

### Area Package Structure

Areas are organized by floor, matching the Home Assistant floor/area hierarchy:

```text
packages/areas/
├── ground-floor/
│   ├── _floor/            # Floor-level aggregation (scripts, templates, lights)
│   ├── kitchen/
│   ├── living-room/
│   ├── toilet/
│   ├── vestibule/
│   └── boiler-room/
├── first-floor/
│   ├── bedroom/
│   ├── bathroom/
│   ├── laundry/
│   └── hall/
└── outdoor/
    ├── porch/
    └── terrace/
```

Each area package follows a consistent structure:

```text
packages/areas/{floor}/{area}/
├── config.yaml      # Main area configuration
├── automations/     # Area-specific automations
├── lights/          # Light group configurations
└── templates/       # Dynamic sensors and binary sensors
```

### Area Package Documentation

When any area package is added or modified, generate or update its README using the `/ha-area-docs` skill. Every area package must have a README.md documenting its devices, automations, and configuration.

### Key Configuration Patterns

1. **Presence Detection**: Multiple sensors (motion, door, illuminance) combined with Bayesian probability sensors for accurate occupancy detection.

2. **Light Automation**: Lights controlled based on area occupancy, darkness state (sun elevation + illuminance), and manual overrides via input_booleans.

3. **Template Sensors**: Jinja2 templates for dynamic sensor creation, particularly in `/packages/bootstrap/templates/`.

4. **Secrets Management**: Real secrets in `secrets.yaml` (gitignored). Use `secrets.fake.yaml` as a template.

### Important Files

- `configuration.yaml`: Main entry point that includes all packages
- `.yamllint`: YAML linting rules
- `.github/workflows/home-assistant.yml`: CI/CD pipeline
- `blueprints/`: Reusable automation templates

### Common Tasks

When adding a new automation:

1. Place it in the appropriate area package under `automations/`
2. Follow naming convention: `{area}_{action}_{trigger}.yaml`
3. Include descriptive `alias` and unique `id`

When adding a new device:

1. Add device configuration to the appropriate area's `config.yaml`
2. Create associated automations if needed
3. Update any relevant light groups or templates

### Occupancy Detection Pattern (Toilet Example)

For areas where motion sensors lose presence during stillness (e.g., sitting on toilet), use a state-machine approach:

1. **input_boolean** holds the occupancy state (persists regardless of motion)
2. **Entry automation**: Door opens + no recent motion → turn ON input_boolean
3. **Exit automation**: Door closes → wait 5s → if motion off → turn OFF input_boolean
4. **Template binary_sensor** exposes the input_boolean with `device_class: occupancy`

Key pattern for exit detection:

```yaml
action:
  - delay: "00:00:05"
  - condition: state  # Acts as gate - stops automation if false
    entity_id: binary_sensor.motion_sensor
    state: "off"
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.area_occupied
```

The `condition` in middle of action sequence stops execution if false - no need for if/then.

### Manual Override Pattern (Hall Example)

For areas where physical switches should override presence-based auto-off behavior, use an `input_boolean` flag with a safety timeout:

1. **input_boolean** tracks manual override state (e.g., `input_boolean.hall_manual_override`)
2. **Switch automation** sets override ON for any "on" button press, OFF for "off" button
3. **Presence automation** checks override flag before auto-on and auto-off actions
4. **Safety automation** clears override after extended period of no movement

```yaml
# config.yaml - Define the override flag:
input_boolean:
  hall_manual_override:
    name: Hall Manual Override
    initial: false
    icon: mdi:hand-back-right
```

```yaml
# Switch automation - Set/clear override on button press:
# On button press (any except off): set override
- action: input_boolean.turn_on
  target:
    entity_id: input_boolean.hall_manual_override

# Off button press: clear override
- action: input_boolean.turn_off
  target:
    entity_id: input_boolean.hall_manual_override
```

```yaml
# Presence automation - Check override before auto-actions:
- condition: state
  entity_id: input_boolean.hall_manual_override
  state: "off"
```

```yaml
# Safety timeout automation - Force off after extended inactivity:
mode: restart

trigger:
  - platform: state
    entity_id: input_boolean.hall_manual_override
    from: "off"
    to: "on"
  - platform: state
    entity_id: binary_sensor.presence_sensor
    to: "on"

condition:
  - condition: state
    entity_id: input_boolean.hall_manual_override
    state: "on"

action:
  - delay:
      minutes: 15
  - condition: state
    entity_id: binary_sensor.presence_sensor
    state: "off"
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.hall_manual_override
  - action: light.turn_off
    target:
      entity_id: light.area_lights
```

Key design decisions:

- `mode: restart` ensures the timer resets whenever presence is detected
- Safety timeout only executes if presence is still off
- Override flag is visible in UI for debugging
- Off button always clears override, restoring normal automation behavior
