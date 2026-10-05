# Attic Bathroom

> Presence lights the room on entry (full by day, dim strip + mirror at night), and the left wall rocker also drives the mirror LEDs.

**Package:** `attic_bathroom` | **Path:** `packages/areas/attic/bathroom/`
**Floor:** Attic

## How It Works

### Presence Lighting

The room has no window, so there is no darkness gate: every entry lights it, at any hour. Two
Matter sensors drive it — an Aqara FP300 presence sensor (mmWave, holds presence while you sit
still) and an Aqara P2 door sensor.

Opening the door lights the room immediately, before the FP300 has registered you; presence alone
does the same if the door was already open. What lights up depends on `binary_sensor.sleeping_time`:

| Mode | Lights |
|------|--------|
| Day | Ceiling on + LED strip and mirror at the day preset (default 100 %, 4000 K) |
| Sleeping time | LED strip and mirror at the night preset (default 5 %, 2200 K) — no ceiling, so a night trip doesn't wake you up |

The mode is picked once, on entry, and kept for the whole visit — if sleeping time starts or ends
while you're inside, the lights don't change under you. Entry never re-commands lights that are
already on, so a manual tweak mid-visit survives.

If the door opens but nobody comes in (presence never trips within 15 s), the lights go off again.
Leaving switches off the ceiling, strip **and** mirror the moment the FP300 clears. The sensor's
hold time (set to 60 s on the device) is the only exit delay, so lights go off ~60 s after you walk
out. It was raised from 10 s because the sensor lost a standing person mid-visit at 10 s.

The four presets are UI sliders shared by the strip and mirror. Moving one re-applies it live to whichever is on in that mode,
so you can tune by eye; the visit's mode is read from the ceiling (on = day visit, off = night).

Wall switch presses aren't tracked — there's no manual override. Switch the ceiling on by hand and
it still goes off on exit. A restart or config reload only ever turns lights off (when the room is
empty), never on.

### Mirror LED Switch

The bathroom has an Aqara H1 double-rocker wall switch. The **right rocker is left in
`control_relay` mode**, so it behaves like a normal wall switch and physically drives the ceiling
light. The **left rocker is set to `decoupled`** — pressing it switches nothing directly and only
emits a Zigbee button event, which this package turns into mirror-LED control.

| Gesture | Behavior |
|---------|----------|
| Single press | Toggle the mirror LEDs — on at full brightness, warm white (2700 K), or off if already on |
| Double press | Toggle brightness between 100% and 20%, keeping the light on |

A double press while the mirror is off turns it on directly at 20%, so a dim entry is one gesture
rather than two. Warm white is applied only on the turn-on paths; the brightness toggle deliberately
leaves colour temperature untouched.

## Gotchas

- **The exit delay lives on the device, not in YAML.** `number.office_bathroom_attic_bathroom_hold_time`
  (60 s) and `..._sensitivity` (3, max) are FP300 settings. If the sensor is re-paired or reset they
  fall back to defaults (10 s), and lights will start cutting out mid-visit again.
- **Don't use the FP300's illuminance** — it reads ~1 lx regardless. The room is treated as always
  dark anyway (see the `fp2-lux-unreliable` knowledge leaf).
- **The ceiling light is on/off only** (`light.attic_bathroom_right` wraps the relay) — never send
  it brightness; all dimming lives on the strip.
- **This switch model has no hold action.** Its device triggers expose only `single_*`, `double_*`
  and `single_both`. All functionality has to fit on single and double press.
- **Use `color_temp_kelvin:`, never the legacy `kelvin:` shorthand.** On the MiBoxer mirror
  controller `kelvin:` silently turns the light **off** (see `kelvin-shorthand-turns-light-off`).
- **The relay entity names are inverted relative to their IDs.** `switch.attic_bathroom_ambient` is
  the **left** relay and `switch.attic_bathroom_main` is the **right**. The left rocker is decoupled,
  so `switch.attic_bathroom_ambient` is unused.
- **The lights and switch aren't assigned to an HA area** (only the two Matter sensors sit in the
  *Office Bathroom* area). Address them by `entity_id`, never by area/floor.
- The bathroom presence counts toward `binary_sensor.attic_occupied`, so the attic-wide 15-minute
  vacancy sweep won't kill the lights while someone sits in here.

## Entities

**Lights:** `light.attic_bathroom_right` (ceiling, on/off), `light.attic_bathroom_leds` (Tuya
RGB+CCT strip — presence-driven), `light.attic_bathroom_mirror` (MiBoxer RGB+CCT — presence + left rocker)
**Sensors:** `binary_sensor.office_bathroom_attic_bathroom_occupancy` — FP300 presence;
`binary_sensor.office_bathroom_attic_bathroom_door_sensor_door` — P2 door contact
**Presets:** `input_number.attic_bathroom_{day,night}_{brightness,color_temp}` — strip + mirror levels per mode
**Switch:** `select.attic_bathroom_operation_mode_left` (`decoupled`),
`select.attic_bathroom_operation_mode_right` (`control_relay`)

## Dependencies

- `binary_sensor.sleeping_time` — house-wide "humans asleep" flag, picks night mode
- `binary_sensor.attic_occupied` (attic `_floor` package) — includes this room's presence; drives
  the attic all-off safety net

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; day/night strip + mirror preset sliders |
| `automations/attic_bathroom_lights_presence.yaml` | Presence + door driven ceiling/strip/mirror, exit off |
| `automations/attic_bathroom_mirror_switch.yaml` | Left-rocker single/double press control for the mirror LEDs |
