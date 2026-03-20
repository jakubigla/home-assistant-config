# Toilet

> Presence-aware lighting that picks ambient or main light based on outdoor darkness.

**Package:** `toilet` | **Path:** `packages/areas/ground-floor/toilet/`
**Floor:** Ground floor (Parter) | **Area:** 2.51 m²

## How It Works

A true presence sensor (`binary_sensor.toilet_presence`) detects occupancy continuously -- no state-machine workarounds needed. When someone enters, lighting adapts to time of day: ambient light comes on when it's dark outside, main ceiling light when it's bright. Both lights turn off when the room becomes vacant.

The automation runs in `mode: restart`, so rapid presence state changes (e.g., someone stepping out and back in) cleanly cancel any in-flight action sequence.

## Gotchas

- During darkness, only `light.toilet_ambient` is turned on automatically. During daytime, only `light.toilet_main`. The other light is always available for manual use.
- The presence sensor replaces the old state-machine pattern (input_boolean + door/motion automations). If the sensor ever needs replacing with a motion-only sensor, that pattern would need to be re-introduced.

## Entities

**Lights:** `light.toilet` (group of `light.toilet_main` + `light.toilet_ambient`)
**Sensors:** `binary_sensor.toilet_presence` -- true presence sensor (Zigbee device entity)

## Dependencies

- `binary_sensor.outdoor_is_dark` -- darkness state from bootstrap templates
- `light.toilet_main` -- main ceiling light (device entity)
- `light.toilet_ambient` -- ambient light (device entity)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package root -- includes automations and lights |
| `automations/toilet_presence.yaml` | Turns lights on/off based on presence and darkness |
| `lights/toilet.yaml` | Light group combining main and ambient lights |
