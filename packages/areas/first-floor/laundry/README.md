# Laundry Room

> Lights turn on when you walk in or open the door, and turn off when the door closes or after a safety timeout.

**Package:** `laundry` | **Path:** `packages/areas/first-floor/laundry/`

## How It Works

The laundry room uses a single automation that handles all lighting based on two physical inputs: a motion sensor and a door contact sensor.

When the occupancy sensor detects movement or the door opens, the light turns on (provided it is not already on). When the door closes, the light turns off immediately -- the assumption being that if you closed the door from outside, you have left the room.

As a safety net, if the occupancy sensor reports no movement for five consecutive minutes, the light turns off regardless of door state. This catches cases where someone leaves the room without closing the door. The automation runs in `restart` mode, so each new trigger event resets any pending timeout.

## Gotchas

- **Door close always turns off the light.** There is no check for whether someone is still inside. If you close the door while in the room, the light goes off. This works because the laundry room door is typically only closed from outside.
- **No darkness check.** The light turns on any time occupancy or door events fire, even during the day. This is intentional -- the laundry room has no windows.
- **The safety timeout is 5 minutes**, which is relatively short. If you are in the room with the door open and stay very still (e.g., sorting laundry on a table), the light may turn off. Any subsequent movement re-triggers it immediately.

## Entities

## Dependencies

- `binary_sensor.laundry_room_sensor_occupancy` -- motion/occupancy sensor in the laundry room
- `binary_sensor.laundry_doors` -- door contact sensor
- `light.laundry` -- laundry room ceiling light

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/laundry_room_lights_on_when_occupied.yaml` | Occupancy and door-driven light control with safety timeout |
