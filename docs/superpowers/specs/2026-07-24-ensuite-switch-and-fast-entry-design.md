# Ensuite switch pivot + bedroom→ensuite fast-entry — design

Date: 2026-07-24
Branch: `feat/irrigation-two-zones-vertical-garden`

Two independent behavior changes in the ensuite (bedroom package). No new
helpers; two existing automations edited in place.

## Part 1 — Switch pivot logic

File: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml`

Left wall button. Add a `hold_left` trigger alongside existing
`single_left` / `double_left`. Logic pivots on whether
`light.ensuite_bathroom_main` is already at 100% (`brightness >= 254`).

Behavior matrix (target = `light.ensuite_bathroom_main`):

| Press  | main OFF                     | main ON, <100%               | main ON, =100%              |
|--------|------------------------------|------------------------------|-----------------------------|
| single | on 100% + set override       | on 100% + set override       | off + clear override        |
| double | on 100% + set override       | on 100% + set override       | dim to 20%                  |
| hold   | off ALL + clear override     | off ALL + clear override     | off ALL + clear override    |

Rules:

- **"on 100%"** always: ensure relay (`light.ensuite_bathroom_main_power`
  on), set `input_boolean.ensuite_manual_override` on, then
  `light.ensuite_bathroom_main` at `brightness_pct: 100`.
- **single at 100%** → `light.turn_off` main + clear override.
- **double at 100%** → `light.ensuite_bathroom_main` `brightness_pct: 20`
  (no override change; already on/overridden).
- **hold, any state** → `light.turn_off` on the whole group
  `light.ensuite_bathroom` (6 bulbs + leds + mirror) + clear override.
  Hold is the dedicated "kill everything" press.

"=100%" test template: `state_attr('light.ensuite_bathroom_main',
'brightness') | int(0) >= 254`.

single and double are identical when the light is OFF or ON-<100% (both
jump to 100%); they diverge only at 100% (single = off, double = dim).

### Structure

`choose` on `trigger.payload`:

- `hold_left` branch: unconditional turn-off group + clear override.
- `single_left` branch: if at-100% → off + clear override; else → on 100%
  (relay + override + 100%).
- `double_left` branch: if at-100% → dim 20%; else → on 100% (relay +
  override + 100%).

`mode: single`, `max_exceeded: silent` unchanged.

## Part 2 — bedroom→ensuite fast-entry override

File: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml`

Existing turn-on branch night-dims to 1% (`light.en_suite_bulb_top_middle`)
when `sun below_horizon` OR `binary_sensor.sleeping_time` on; else main at
100%/20% by `light.bedroom_non_bed`.

New exception, highest priority in the turn-on sequence: if the person just
walked into the bedroom and stepped straight into the ensuite, skip the
comfort-dim and light the main fully.

"Fast entry" = `input_boolean.bedroom_occupied` is `on` AND its
`last_changed` is < 5 minutes ago when the ensuite turn-on fires.

New turn-on if/elif/else:

```
if bedroom_occupied on AND (now - bedroom_occupied.last_changed) < 5 min:
    light.ensuite_bathroom_main -> brightness_pct: 100
elif sun below_horizon OR sleeping_time on:
    light.en_suite_bulb_top_middle -> brightness_pct: 1
else:
    light.ensuite_bathroom_main -> brightness_pct: {{ 100 if bedroom_non_bed on else 20 }}
```

Template for the age check:
`(now() - states.input_boolean.bedroom_occupied.last_changed).total_seconds() < 300`
guarded by `is_state('input_boolean.bedroom_occupied', 'on')`.

Relay-ensure step (`light.ensuite_bathroom_main_power` on) stays first,
unchanged, ahead of the if/elif/else. Only the presence-driven turn-on
(`occupied` / `got_dark` triggers) is affected. `vacant` branch unchanged.
Manual override still skips the whole automation (top-level condition).

### Why the latch age works

`input_boolean.bedroom_occupied` latches on at bedroom entry and stays on
all night (60 s debounce, 30 min watchdog). `last_changed < 5 min` is true
only right after a fresh off→on entry. A mid-night toilet trip finds the
latch old → falls through to the 1% comfort-dim. Correct: fast-entry bright
only applies to someone who just arrived.

## Assumption to verify

The ensuite left button is assumed to emit `hold_left`
(device `a042eb964ead9c014809c93d2d7610de`). Same button model as
`bedroom_button_switch`, which already triggers on `subtype: hold_left`.
Verify at `just check` / HA reload; if the device does not emit it, drop the
hold trigger and branch.

## Out of scope

- No new input_booleans, timers, or template sensors.
- `ensuite_manual_override_timeout` safety automation unchanged (still
  clears a stuck override).
- No dashboard changes.
