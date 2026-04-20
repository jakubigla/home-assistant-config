# Living Room Floor Heating — Abstract Climate Wrapper

## Problem

`climate.floor_heating` is a Bosch boiler entity exposed by the Bosch
integration. It drives the living-room underfloor loop, but has two issues
that make it unsuitable as the room's user-facing climate entity:

1. **Wrong `current_temperature`.** The attribute mirrors `climate.main_heating`
   exactly (currently 22.8 °C on both). It is a boiler-side/supply value, not
   the living room's air temperature.
2. **Unreliable `hvac_action`.** The entity always reports
   `hvac_action: heating`. The underlying boiler does not actually report a
   demand/active-heating signal, so this value is fabricated and misleading
   in the UI.

The zigbee hygrometer `sensor.living_room_hygro_temperature` is a trustworthy
source for the room's air temperature and should feed the displayed
`current_temperature` instead. And because the hardware cannot tell us
whether it is heating, the wrapper should simply not advertise
`hvac_action` at all.

## Goal

Create an abstract climate entity that:

- Presents the living room's true air temperature as `current_temperature`.
- Passes control (set temperature / hvac_mode / preset_mode) through to
  `climate.floor_heating`.
- Exposes no `hvac_action` attribute.
- Mirrors the underlying entity's supported `hvac_modes` and `preset_modes`.
- Becomes unavailable when its upstream sources (hygro sensor or Bosch
  climate) are unavailable.

## Non-goals

- Implementing any bang-bang / hysteresis control logic. The Bosch
  integration retains full responsibility for deciding when the boiler
  runs.
- Per-room wrappers for other rooms. This spec covers the living room only;
  the design leaves room to generalise later but does not do so now.
- Replacing or hiding `climate.floor_heating` from Home Assistant. The
  original entity continues to exist; this is purely a wrapper.

## Approach

Use the HACS custom integration
[`jcwillox/hass-template-climate`](https://github.com/jcwillox/hass-template-climate),
which provides `platform: climate_template`. It supports templated state
attributes plus action blocks for write operations, and — crucially for
goal #3 — omits `hvac_action` from the entity whenever
`hvac_action_template` is not defined.

Alternatives considered and rejected:

- **HA built-in `template:` integration.** Does not support the `climate`
  domain. Supported: alarm_control_panel, binary_sensor, button, cover,
  event, fan, image, light, lock, number, select, sensor, switch, update,
  vacuum, weather.
- **`input_number` + `input_select` + scripts.** Does not produce a real
  `climate.*` entity; breaks HomeKit, thermostat cards, and voice
  assistants.
- **In-repo `custom_components/`.** Python maintenance burden and HA
  restarts required for changes. Overkill for one entity.

## Architecture

### New entity

- Entity ID: `climate.living_room_floor_heating`
- Friendly name: `Living Room Floor Heating`
- Unique ID: `living_room_floor_heating`

### File layout

```
packages/areas/ground-floor/living-room/
├── config.yaml         # add  climate: !include climate.yaml
└── climate.yaml        # NEW — the climate_template entity
```

`climate.yaml` sits next to `config.yaml` rather than under `templates/`,
because the legacy `climate:` platform is a top-level domain list and does
not live inside the `template:` block. Mirrors how `lights/`, `automations/`
are separated by domain in other area packages.

### Data flow

```
            ┌──────────────────────────────────┐
  READ ◄─── │ climate.living_room_floor_heating│
            │  (climate_template wrapper)      │
            └──────────────┬───────────────────┘
                           │
     ┌─────────────────────┼────────────────────┐
     ▼                     ▼                    ▼
 current_temp           hvac_mode           target_temp
 preset_mode
     │                     │                    │
     ▼                     ▼                    ▼
sensor.living_room_    states(climate.       state_attr(
hygro_temperature      floor_heating)        climate.floor_heating,
                                             'temperature')

  WRITE ──► set_temperature / set_hvac_mode / set_preset_mode
           │
           └─► forward 1:1 to climate.floor_heating

  hvac_action: not templated → absent from the wrapper
```

## Detailed design

### YAML (`packages/areas/ground-floor/living-room/climate.yaml`)

```yaml
- platform: climate_template
  name: Living Room Floor Heating
  unique_id: living_room_floor_heating

  modes: ["off", "auto"]
  preset_modes: ["none", "away"]
  min_temp: 16
  max_temp: 30
  temp_step: 0.5

  current_temperature_template: >-
    {{ states('sensor.living_room_hygro_temperature') | float(none) }}
  target_temperature_template: >-
    {{ state_attr('climate.floor_heating', 'temperature') | float(none) }}
  hvac_mode_template: "{{ states('climate.floor_heating') }}"
  preset_mode_template: "{{ state_attr('climate.floor_heating', 'preset_mode') }}"

  availability_template: >-
    {{ states('sensor.living_room_hygro_temperature') not in
       ['unknown', 'unavailable', 'none', '']
       and states('climate.floor_heating') not in ['unknown', 'unavailable'] }}

  set_temperature:
    - action: climate.set_temperature
      target:
        entity_id: climate.floor_heating
      data:
        temperature: "{{ temperature }}"

  set_hvac_mode:
    - action: climate.set_hvac_mode
      target:
        entity_id: climate.floor_heating
      data:
        hvac_mode: "{{ hvac_mode }}"

  set_preset_mode:
    - action: climate.set_preset_mode
      target:
        entity_id: climate.floor_heating
      data:
        preset_mode: "{{ preset_mode }}"
```

### `packages/areas/ground-floor/living-room/config.yaml` — one added line

```yaml
climate: !include climate.yaml
```

The existing file uses a mix of `!include_dir_list` directives
(`automation`, `media_player`, `light`, `template`) and inline
configuration (`cover`). A single-file `!include` is consistent with the
single-entity scope; add the line near the other domain-level includes
at the top of the file. Existing ordering is not alphabetical — match
the current grouping rather than re-sort.

### Design choices and rationale

- **No `hvac_action_template`.** Explicitly omitting this attribute is what
  makes the wrapper hide the fabricated "heating" signal. This is the whole
  point of the wrapper; any future edit must not add an
  `hvac_action_template` without revisiting the requirement.
- **Availability gates on both sources.** If the zigbee sensor is stale,
  there is no trustworthy current temperature to show. If the Bosch entity
  is unavailable, write-through would silently fail. Both conditions mark
  the wrapper unavailable — honest failure beats half-working UI.
- **`float(none)`** in templates returns `None` when the state is a
  non-numeric value, which Home Assistant surfaces as "unavailable" on
  the attribute rather than throwing a template error.
- **Modes/presets mirror the underlying entity exactly.** Advertising modes
  the Bosch does not support would let the UI issue calls that the
  downstream action cannot honour.
- **`temp_step: 0.5`.** Matches the typical HA thermostat card; the Bosch
  entity exposes no explicit step. If the `climate_template` component
  rejects this key on the installed version, drop it (the default is
  acceptable) — do not introduce a workaround.

## Prerequisites

Manual, one-time install of the HACS integration. The spec records the
click-path so future maintainers do not have to guess:

1. HACS → Integrations → three-dot menu → **Custom repositories**.
2. Add `https://github.com/jcwillox/hass-template-climate` with category
   **Integration**.
3. Search for "Template Climate" in HACS → Download.
4. Restart Home Assistant.

Verification: Developer Tools → Services → the `climate.set_temperature`
service should list `climate.living_room_floor_heating` as a valid target
after the next step.

## Testing

After pushing the branch and letting HA pull:

1. Reload Home Assistant YAML config. Check `home-assistant.log` for
   `climate_template`-related errors.
2. Developer Tools → States. Confirm `climate.living_room_floor_heating`
   exists, is not `unavailable`, and has **no** `hvac_action` attribute.
3. Confirm `current_temperature` equals
   `sensor.living_room_hygro_temperature`'s value at that moment (within
   rounding).
4. Confirm `temperature`, `hvac_modes`, `preset_modes`, `hvac_mode`, and
   `preset_mode` all match the corresponding values on
   `climate.floor_heating`.
5. Call `climate.set_temperature` on the wrapper with a test value →
   confirm `climate.floor_heating.temperature` updates to the same value
   within a few seconds.
6. Call `climate.set_hvac_mode` with `off` then `auto` → confirm the Bosch
   entity follows.
7. Simulate availability loss: either wait for the hygro to report
   `unavailable`, or temporarily rename the sensor in the template to a
   non-existent entity → wrapper becomes unavailable.

## Risks and mitigations

- **HACS component drift.** `climate_template` is community-maintained and
  could break on a Home Assistant core bump. Mitigation: if it breaks,
  fallback plan is Approach C (in-repo `custom_components/`), which this
  spec has already scoped out. Add a short note to the living-room README
  so the dependency is discoverable.
- **Preset passthrough when Bosch reports an unexpected preset.** The
  wrapper's `preset_mode` would render empty/unavailable. Acceptable — the
  UI simply shows no preset until the Bosch reports a known value.
- **`float(none)` in target_temperature_template.** If the Bosch reports a
  non-numeric temperature for any reason, the wrapper's target shows
  unavailable rather than a stale number. Intentional.

## Out of scope (explicit)

- Dashboard integration (Mushroom/thermostat-card wiring) — handled in a
  follow-up plan if desired.
- HomeKit exposure changes — `packages/homekit/config.yaml` already lists
  `climate.living_room` (the AC unit). Adding the wrapper there is a
  future decision.
- A shared per-area template or blueprint to generate these wrappers for
  other rooms.
