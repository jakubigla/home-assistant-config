---
paths:
  - "packages/areas/**/*.yaml"
---

# Area Package Patterns

Reusable patterns for area automations. Apply these when motion sensors or physical switches need to coexist with presence-based logic.

## Occupancy Detection (motion drops during stillness)

When motion sensors lose presence during stillness (e.g., toilet), use a state-machine via `input_boolean`:

1. `input_boolean` holds occupancy state (persists across motion drops)
2. **Entry**: door opens + no recent motion → turn ON
3. **Exit**: door closes → wait 5s → if motion off → turn OFF
4. Template `binary_sensor` exposes the boolean with `device_class: occupancy`

Exit action — use a mid-sequence `condition` as a gate (no if/then needed):

```yaml
action:
  - delay: "00:00:05"
  - condition: state
    entity_id: binary_sensor.motion_sensor
    state: "off"
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.area_occupied
```

## Manual Override (physical switch overrides presence auto-off)

When a physical switch should override auto-off, use an `input_boolean` flag with a safety timeout:

1. `input_boolean.{area}_manual_override` tracks override state
2. Switch automation: ON for any "on" press, OFF for "off" press
3. Presence automation checks override is `off` before any auto-action
4. Safety automation clears override after 15 min of no presence

```yaml
input_boolean:
  hall_manual_override:
    name: Hall Manual Override
    initial: false
    icon: mdi:hand-back-right
```

Safety timeout (`mode: restart` so the timer resets on every presence event):

```yaml
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

Key points: override flag visible in UI for debugging; off-press always restores auto behavior.
