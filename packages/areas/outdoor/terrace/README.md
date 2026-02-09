# Terrace

> Presence-based outdoor lighting for the terrace and garden area.

**Package:** `terrace` | **Path:** `packages/areas/outdoor/terrace/`

## How It Works

The terrace package controls a single light (`light.terrace_wall`) based on whether someone is in the garden and whether it is dark outside.

When `binary_sensor.garden_presence` turns on and `binary_sensor.garden_is_dark` is also on, the terrace wall light switches on. When presence clears, the light turns off after a 30-second grace period. This delay prevents the light from flickering during brief gaps in motion detection. During daylight, presence is detected but the light stays off because the darkness condition gates the turn-on branch.

The automation runs in `restart` mode and also re-evaluates on Home Assistant start and automation reload, so the light always reflects the current state after a restart.

## Gotchas

- The turn-off delay is only 30 seconds. If the presence sensor has long gaps between detections, the light may briefly cycle off and back on.
- There is no darkness check on the turn-off branch. If the sun rises while someone is still in the garden, the light will stay on until presence clears.
- No manual override exists for this area. The light is fully automated.

## Entities

| Entity | Type | Role |
|--------|------|------|
| `light.terrace_wall` | Light | Controlled output |
| `binary_sensor.garden_presence` | Binary sensor | Presence trigger |
| `binary_sensor.garden_is_dark` | Binary sensor | Darkness gate |

## Dependencies

All entities used by this package are defined outside of it:

- `binary_sensor.garden_presence` -- garden occupancy sensor, primary trigger
- `binary_sensor.garden_is_dark` -- darkness condition shared with other outdoor areas
- `light.terrace_wall` -- physical light entity provided by the integration (e.g. Zigbee2MQTT)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/garden_presence.yaml` | Turns terrace wall light on/off based on garden presence and darkness |
