# Hall (First Floor)

> Presence-based corridor and stairway lighting with a wall switch that overrides automation.

**Package:** `hall` | **Path:** `packages/areas/first-floor/hall/`

## How It Works

### Lighting

When someone enters the first-floor corridor and it's dark, the hall bulbs turn on at minimal brightness (level 2 out of 255). They turn off 5 seconds after the corridor clears. Darkness is determined by first-floor illuminance with hysteresis (on below 5 lux, off above 8 lux) — or immediately if it's dark outside.

The stairway light follows a similar pattern but uses a 20-second vacancy delay and considers darkness from either the living room or the hall (whichever is closer to the stairs).

### Manual Override

A dual-button MQTT wall switch provides direct control and disables presence automation:

| Button | Press | Effect |
|--------|-------|--------|
| Left | Single | Off, resumes auto mode |
| Right | Single | On at default brightness, overrides auto |
| Left | Double | On at 5%, overrides auto |
| Right | Double | On at 100%, overrides auto |

While override is active, the presence automation won't touch the lights. A 15-minute safety timeout clears the override if no movement is detected — preventing lights being stuck on if someone forgets.

## Gotchas

- The presence automation only turns lights **on** if they're currently off — it won't re-adjust brightness if the lights are already on from a switch press
- The safety timeout timer **restarts** on every new corridor presence detection, so lights stay on as long as someone is moving around periodically
- Stairway light checks darkness from two areas (living room OR hall) — either being dark is enough to justify turning on the stairway light

## Entities

**Lights:** `light.hall_bulbs` (8 bulbs), `light.stairway`
**Sensors:** `binary_sensor.hall_is_dark`, `binary_sensor.stairway_presence` (combines two stair sensors)
**State:** `input_boolean.hall_manual_override`

## Dependencies

- `binary_sensor.first_floor_corridor_presence` — hardware presence sensor
- `binary_sensor.first_floor_stairs_presence` — first-floor stair sensor
- `binary_sensor.ground_floor_stairs_presence` — ground-floor stair sensor
- `sensor.first_floor_illuminance` — illuminance for darkness template
- `binary_sensor.outdoor_is_dark` — outdoor darkness (bootstrap)
- `binary_sensor.living_room_is_dark` — used by stairway automation

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Manual override input_boolean, includes |
| `automations/hall_presence.yaml` | Corridor presence → hall bulbs |
| `automations/stairway_presence.yaml` | Stairway presence → stairway light |
| `automations/hall_switch.yaml` | Wall switch button mappings |
| `automations/hall_manual_override_safety.yaml` | 15-min override safety timeout |
| `lights/hall_bulbs.yaml` | Light group (8 hall bulbs) |
| `templates/binary_sensors/hall_is_dark.yaml` | Darkness detection with hysteresis |
| `templates/binary_sensors/stairway_occupied.yaml` | Combined stairway occupancy |
