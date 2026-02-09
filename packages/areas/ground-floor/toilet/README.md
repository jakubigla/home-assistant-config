# Toilet

> Occupancy-aware lighting for a small room where motion sensors lose presence during stillness, solved with a door+motion state machine.

**Package:** `toilet` | **Path:** `packages/areas/ground-floor/toilet/`

## How It Works

The toilet is a classic problem room for motion-based automation: someone sits still, the motion sensor clears, and the lights turn off while the room is still occupied. To solve this, the package uses a **state-machine approach** built around an `input_boolean` that holds occupancy state independently of the motion sensor.

**Entry detection** fires when the door opens or motion is detected, but only if the room is not already marked as occupied. This sets `input_boolean.toilet_occupied` to `on`.

**Exit detection** fires when the door closes. After a 3-second settling delay, it checks whether motion has stopped. If motion is still active (someone closed the door from inside), the automation halts -- the mid-action condition acts as a gate and silently stops execution. If motion is off, the person has left, and the occupied flag is cleared.

**Lighting** reacts to the template sensor `binary_sensor.toilet_occupancy`, which mirrors the `input_boolean`. When the sensor turns on, ambient light comes on automatically. When it turns off, both ambient and main lights are switched off. Only ambient light is turned on automatically -- the main light is available for manual use but never forced on by automation.

**Safety fallback**: if the motion sensor reports no movement for 20 continuous minutes, the system force-clears the occupied flag and turns off all lights. This catches edge cases where someone leaves without triggering the normal exit sequence (e.g., door was left ajar).

## Gotchas

- The exit automation uses `mode: restart`, so rapid door open/close cycles reset the 3-second delay each time rather than stacking up duplicate runs.
- Only `light.toilet_ambient` is turned on automatically. `light.toilet_main` is only turned _off_ by automation -- turning it on is always manual.
- The 20-minute no-motion timeout also resets the `input_boolean`, not just the lights. Without this, a stale occupied flag could block the entry automation from firing on the next visit.
- The entry automation runs in `mode: single`, so a simultaneous door-open and motion event won't double-fire.

## Entities

**Lights:** `light.toilet` (group of `light.toilet_main` + `light.toilet_ambient`)
**Sensors:** `binary_sensor.toilet_occupancy` -- template sensor exposing occupancy with `motion_sensor`, `door_sensor`, and `door_open` attributes
**State:** `input_boolean.toilet_occupied` -- holds occupancy across motion gaps (default: off)

## Dependencies

- `binary_sensor.toilet_doors` -- door contact sensor (Zigbee device entity)
- `binary_sensor.toilet_presence` -- motion/presence sensor (Zigbee device entity)
- `light.toilet_main` -- main ceiling light (device entity, not defined in this package)
- `light.toilet_ambient` -- ambient light (device entity, not defined in this package)

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package root -- includes automations, templates, lights; defines `input_boolean.toilet_occupied` |
| `automations/toilet_occupancy_entry.yaml` | Sets occupied flag on door open or motion detected |
| `automations/toilet_occupancy_exit.yaml` | Clears occupied flag when door closes and motion stops |
| `automations/toilet_presence.yaml` | Turns lights on/off based on occupancy, with 20-min safety timeout |
| `lights/toilet.yaml` | Light group combining main and ambient lights |
| `templates/binary_sensors/toilet_occupancy.yaml` | Template binary sensor exposing the input_boolean as a proper occupancy entity |
