# Terrace

> Presence-based outdoor lighting for the terrace and garden area.

**Package:** `terrace` | **Path:** `packages/areas/outdoor/terrace/`

## How It Works

The terrace package controls a single light (`light.terrace_wall`) based on whether someone is in the garden, whether a terrace door is being opened, and whether it is dark outside.

When `binary_sensor.garden_presence` turns on and `binary_sensor.garden_is_dark` is also on, the terrace wall light switches on. When presence clears, the light turns off after a 30-second grace period. This delay prevents the light from flickering during brief gaps in motion detection. During daylight, presence is detected but the light stays off because the darkness condition gates the turn-on branch.

In addition, opening either terrace door (`binary_sensor.terrace_left_door` or `binary_sensor.terrace_main_door`) after dark turns the light on immediately. The off-path is owned solely by the presence-based automation -- the door trigger never turns the light off.

The presence automation runs in `restart` mode and also re-evaluates on Home Assistant start and automation reload, so the light always reflects the current state after a restart.

## Gotchas

- The turn-off delay is only 30 seconds. If the presence sensor has long gaps between detections, the light may briefly cycle off and back on.
- There is no darkness check on the turn-off branch. If the sun rises while someone is still in the garden, the light will stay on until presence clears.
- If a terrace door is opened but no one steps outside (so `binary_sensor.garden_presence` never registers), the light will stay on until presence eventually fires and then clears. There is no safety timer on the door trigger.
- No manual override exists for this area. The light is fully automated.

## Entities

| Entity | Type | Role |
|--------|------|------|
| `light.terrace_wall` | Light | Controlled output |
| `binary_sensor.garden_presence` | Binary sensor | Presence trigger |
| `binary_sensor.garden_is_dark` | Binary sensor | Darkness gate |
| `binary_sensor.terrace_left_door` | Binary sensor | Door trigger |
| `binary_sensor.terrace_main_door` | Binary sensor | Door trigger |

## Dependencies

All entities used by this package are defined outside of it:

- `binary_sensor.garden_presence` -- garden occupancy sensor, primary trigger
- `binary_sensor.garden_is_dark` -- darkness condition shared with other outdoor areas
- `binary_sensor.terrace_left_door` -- Satel zone, door trigger
- `binary_sensor.terrace_main_door` -- Satel zone, door trigger
- `light.terrace_wall` -- physical light entity provided by the integration (e.g. Zigbee2MQTT)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/garden_presence.yaml` | Turns terrace wall light on/off based on garden presence and darkness |
| `automations/terrace_door_trigger.yaml` | Turns terrace wall light on when a terrace door opens after dark (off is handled by the presence automation) |
