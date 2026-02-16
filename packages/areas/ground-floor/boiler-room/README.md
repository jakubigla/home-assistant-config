# Boiler Room

> Presence-based lighting for the ground-floor boiler room.

**Package:** `boiler_room` | **Path:** `packages/areas/ground-floor/boiler-room/`
**Floor:** Ground floor (Parter) | **Area:** 3.33 m²

## How It Works

The boiler room is a utility space that only needs light when someone is physically present. A single automation handles both on and off behaviour using `mode: restart`.

When the occupancy sensor detects presence, the light turns on immediately. Once the sensor clears, a short 10-second grace period runs before the light switches off. Because the automation uses restart mode, any new occupancy event during that grace period cancels the pending off action and keeps the light on, preventing flicker during brief sensor gaps.

The automation dynamically builds the service call (`light.turn_on` / `light.turn_off`) from the trigger ID, so a single action block covers both directions.

## Gotchas

- The 10-second vacancy delay is intentionally short since this is a pass-through utility room, not a living space.
- There is no darkness check -- the light always turns on with presence, regardless of ambient light, because the boiler room has no windows.

## Entities

## Dependencies

- `binary_sensor.boiler_room_occupancy` -- occupancy sensor that triggers the automation
- `light.boiler_room` -- ceiling light controlled by the automation

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/boiler_room_lights_on_when_occupied.yaml` | Turns light on/off based on occupancy with a 10 s vacancy delay |
