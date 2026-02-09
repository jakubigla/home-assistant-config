# Vestibule

> Presence-based lighting for the ground-floor entry/mudroom area.

**Package:** `vestibule` | **Path:** `packages/areas/ground-floor/vestibule/`

## How It Works

The vestibule has four ceiling bulbs grouped as a single controllable light. A single automation manages them based on presence and outdoor darkness.

When the vestibule presence sensor detects someone and it is dark outside (determined by `binary_sensor.garden_is_dark`), the lights turn on. Once presence clears for 5 seconds, the lights turn off regardless of darkness state. The automation also re-evaluates on Home Assistant start and automation reload so that lights always reflect the current state after a restart.

The automation runs in `restart` mode, meaning each new trigger cancels any in-progress action sequence. This keeps behavior snappy -- if someone walks in and out quickly, the 5-second vacancy delay resets correctly.

## Gotchas

- The automation controls `light.mudroom`, not the light group `light.vestibule_bulbs` defined in this package. `light.mudroom` is the HA device entity that represents the same physical fixture.
- Lights only turn on when it is dark outside, but they always turn off when presence clears -- even if it became dark while someone was present and then they left.
- The 5-second vacancy delay is short by design; the vestibule is a pass-through space, not a room where people linger.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `light.vestibule_bulbs` | Light group | Groups the four vestibule ceiling bulbs into one entity |

## Dependencies

| Entity | Source | Role |
|--------|--------|------|
| `binary_sensor.vestibule_presence` | Zigbee2MQTT | Hardware presence sensor that triggers the automation |
| `binary_sensor.garden_is_dark` | Outdoor templates | Gates daytime light activation |
| `light.mudroom` | HA device | The physical vestibule light controlled by the automation |

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point -- includes automations and light definitions |
| `automations/vestibule_presence.yaml` | Turns lights on/off based on presence and darkness |
| `lights/vestibule_bulbs.yaml` | Groups four vestibule ceiling bulbs into `light.vestibule_bulbs` |
