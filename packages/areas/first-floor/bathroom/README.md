# Bathroom

> Presence- and darkness-aware lighting for the first-floor bathroom.

**Package:** `bathroom` | **Path:** `packages/areas/first-floor/bathroom/`
**Floor:** First floor (Piętro) | **Area:** 5.92 m²

## How It Works

### Occupancy Lighting

The bathroom lights respond to presence, but only when the door is open. This is a deliberate guard against the hall motion sensor bleeding through into the bathroom presence zone -- without it, walking past in the hallway could flip the bathroom lights on.

When someone enters and the door is open, the automation picks a light based on time of day. After dark it switches on the ambient light for a softer feel; during the day it uses the brighter main ceiling light. If presence drops and stays off for 30 seconds, all lights -- main, ambient, and mirror -- are turned off together.

The automation runs in `restart` mode, so the 30-second off-delay resets every time presence returns. This prevents the lights from cutting out if the sensor briefly loses track of someone (e.g., sitting still).

## Gotchas

- The **door must be open** for lights to turn on automatically. If someone closes the door behind them, the automation will not activate lights on its own.
- The **mirror light** is never turned on automatically -- it is only turned off. It is expected to be switched on manually when needed.
- The 30-second vacancy delay applies to the presence sensor going off, not to the door closing. Closing the door alone does not trigger a light-off sequence.
- On Home Assistant restart or automation reload, the automation re-evaluates current state, so lights will snap to the correct state without waiting for a new trigger.

## Entities

**Lights:** `light.bathroom_main`, `light.bathroom_ambient`, `light.bathroom_mirror`
**Sensors:** `binary_sensor.bathroom_presence` (Zigbee), `binary_sensor.bathroom_door` (Zigbee contact sensor)

## Dependencies

- `binary_sensor.outdoor_is_dark` -- bootstrap template; darkness detection based on sun elevation

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/bathroom_lights_occupancy.yaml` | Presence- and door-gated lighting control |
