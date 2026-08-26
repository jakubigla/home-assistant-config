# Attic Bathroom

> Wall-switch control for the mirror LEDs — the left rocker drives lighting scenes instead of its relay.

**Package:** `attic_bathroom` | **Path:** `packages/areas/attic/bathroom/`
**Floor:** Attic

## How It Works

### Mirror LED Switch

The bathroom has an Aqara H1 double-rocker wall switch. The **right rocker is left in
`control_relay` mode**, so it behaves like a normal wall switch and physically drives the ceiling
light. The **left rocker is set to `decoupled`** — pressing it switches nothing directly and only
emits a Zigbee button event, which this package turns into mirror-LED control.

That gives the left rocker two gestures:

| Gesture | Behavior |
|---------|----------|
| Single press | Toggle the mirror LEDs — on at full brightness, warm white (2700 K), or off if already on |
| Double press | Toggle brightness between 100% and 20%, keeping the light on |

A double press while the mirror is off turns it on directly at 20%, so a dim entry is one gesture
rather than two. Warm white is applied only on the turn-on paths; the brightness toggle deliberately
leaves colour temperature untouched, so any colour set by hand from the app or dashboard survives a
dim/bright cycle.

There is no automatic or presence-driven behavior in this room yet — the mirror LEDs are manual
only, and the ceiling light is purely relay-driven.

## Gotchas

- **This switch model has no hold action.** Home Assistant's device triggers for the Aqara H1 EU
  double rocker expose only `single_*`, `double_*` and `single_both` — there is no `hold_left`. All
  functionality has to fit on single and double press. (The equivalent ensuite automation carries a
  `hold_left` trigger on this same hardware; that branch cannot fire.)
- **Use `color_temp_kelvin:`, never the legacy `kelvin:` shorthand.** On the MiBoxer controller
  driving these LEDs, `kelvin:` silently turns the light **off** — Zigbee2MQTT reports the command
  accepted, the automation trace looks healthy, and the lamp just stays dark. See the
  `kelvin-shorthand-turns-light-off` knowledge leaf.
- **The relay entity names are inverted relative to their IDs.** `switch.attic_bathroom_ambient` is
  the **left** relay and `switch.attic_bathroom_main` is the **right**. Because the left rocker is
  decoupled, `switch.attic_bathroom_ambient` is currently unused and inert.
- **The devices are not assigned to an HA area.** An `Attic` floor exists (with Balcony, Gym and
  Office), but there is no *Attic Bathroom* area and the switch, mirror and LED strip are all
  unassigned. Area- or floor-scoped targeting will not reach them; address them by `entity_id`.
- The brightness pivot reads `light.attic_bathroom_mirror` directly rather than a light group, which
  avoids the group-average misread that makes threshold pivots unreliable when a member is offline.

## Entities

**Lights:** `light.attic_bathroom_mirror` (MiBoxer 5-in-1, RGB + CCT 2000–6535 K — driven by this
package), `light.attic_bathroom_leds` (Tuya RGB+CCT strip, not yet automated),
`light.attic_bathroom_right` (ceiling light, on/off only)
**Switch relays:** `switch.attic_bathroom_main` (right rocker), `switch.attic_bathroom_ambient`
(left rocker — decoupled, unused)
**Rocker modes:** `select.attic_bathroom_operation_mode_left` (`decoupled`),
`select.attic_bathroom_operation_mode_right` (`control_relay`)

## Dependencies

None — this package is self-contained and references no entities from other areas.

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point; includes the automations directory |
| `automations/attic_bathroom_mirror_switch.yaml` | Left-rocker single/double press control for the mirror LEDs |
