# Party Mode — design

Date: 2026-09-16. Status: approved in chat, pending spec review.

## Goal

A single house-wide flag that (a) stops automations from interrupting guests
(curtains moving, lights sweeping off, screens blanking, pergola closing) and
(b) makes the kitchen wall tablet read-only so guests cannot drive the house.
Basic, no fancy features. No music, wifi, AC, notification or humidifier changes.

## Mechanism

`input_boolean.party_mode` (package `packages/misc/`). Every gated automation
gets a `condition: state … party_mode: "off"` — self-healing, restart-safe, no
on/off state to restore. No `automation.turn_off` anywhere.

Activation: toggle on the phone dashboard Home view. Deactivation: same toggle
or the hard auto-off at 06:00 every day (safety net so the house is never left
in party mode).

## Gated automations (top-level condition unless noted)

| Automation | File | Why |
|---|---|---|
| Living room curtains | `packages/areas/ground-floor/living-room/automations/living_room_curtains.yaml` | no cover moves |
| Kitchen presence | `packages/areas/ground-floor/kitchen/automations/kitchen_presence.yaml` | no motion-driven LED flicker |
| Kitchen dashboard screen | `packages/areas/ground-floor/kitchen/automations/kitchen_dashboard_screen.yaml` | screen stays on |
| Living Room Scene Cube | `packages/areas/ground-floor/living-room/automations/living_room_scene_cube.yaml` | knocked cube must not flip scene |
| Presence - ground floor absent 5 min | `packages/presence/automations/presence_ground_floor_with_5_min_threshold.yaml` | no light sweep |
| Presence - no one at home | `packages/presence/automations/presence_turn_off_lights_and_media_when_away.yaml` | hosts' phones leaving must not darken house |
| Garden lights from terrace doors | `packages/areas/outdoor/garden/automations/garden_lights_terrace_doors.yaml` | no on/off flicker at doors / presence drop |
| Pergola roof control — **sunset-close branch only** | `packages/areas/outdoor/terrace/automations/pergola_roof_control.yaml` | roof must not close over guests; rain-close and morning-open stay active |

Not gated, deliberately:
- `pergola_zip_right_open_after_midnight` — wind safety; retracting a side blind at 00:30 is not an interruption.
- `terrace_door_trigger` — targets `light.terrace_wall`, which does not exist (already a no-op).
- Toilet / vestibule / hall presence — guests benefit from these.
- Notifications — go to hosts' phones, do not affect guests.

Condition is evaluated at trigger time, so a 5-min `for:` timer already running
when party mode turns on is still suppressed when it fires.

## Tablet read-only

Reuse the existing screensaver view `/wall-tablet/clock` (`type: panel`,
markdown only, nothing tappable). One new automation
`packages/misc/automations/misc_party_mode_tablet_lock.yaml`:

- Trigger A: `input_boolean.party_mode` off→on → wake screen
  (`switch.kitchen_dashboard_screen` on), wait for
  `sensor.<tablet_browser_id>_browser_path` to leave `unavailable` (≤15 s),
  `browser_mod.navigate` to `/wall-tablet/clock`. Same wake-first order as the
  doorbell automation (see `tablet-browser-mod-navigate` leaf).
- Trigger B: `sensor.<tablet_browser_id>_browser_path` state change while party
  on and new path not in `[/wall-tablet/clock, /wall-tablet/doorbell]` →
  navigate back to `/wall-tablet/clock`. Guests tapping a tab get snapped back.
- Trigger C: `input_boolean.party_mode` on→off → navigate to `/wall-tablet/home`.

`tablet_browser_id` is a `variables:` entry copied from the doorbell automation
(`browser_mod_c6830995_0bc293d0`). It rotates on cache clear; verify with the
useragent sensor while the screen is on before testing.

Doorbell automation (`porch_doorbell_notify_tablet.yaml`): its final
"return to home" navigate becomes templated —
`/wall-tablet/clock` when party mode is on, else `/wall-tablet/home`.

## One-shot actions

`packages/misc/automations/misc_party_mode_lights.yaml`:
- party on → `light.kitchen_led` on (on/off-only light, no brightness); if
  `binary_sensor.outdoor_is_dark` on → `light.garden_lights` on.
- party off → nothing for kitchen (presence automation resumes on next edge);
  `light.garden_lights` off (its own off-edge was suppressed all night).

`packages/misc/automations/misc_party_mode_auto_off.yaml`: time trigger 06:00,
condition party on → `input_boolean.turn_off`.

## Phone dashboard

`dashboards/phone/home.yaml`: one `mushroom-entity-card` for
`input_boolean.party_mode` (icon `mdi:party-popper`, tap toggles) in the
first section under the alarm card.

## Files

New: `packages/misc/automations/misc_party_mode_tablet_lock.yaml`,
`misc_party_mode_lights.yaml`, `misc_party_mode_auto_off.yaml`;
`input_boolean:` block in `packages/misc/config.yaml`.
Edited: 8 automations above (condition lines), doorbell automation (template
path), `dashboards/phone/home.yaml`.

## Reload / test

- New helper needs `input_boolean.reload`; automations need `automation.reload`
  (reload-after-push leaf). Then check logs.
- Box pointed at `feat/party-mode` over SSH; SHA verified.
- Non-invasive test: toggle party mode on with the user's OK (tablet navigates —
  visible but harmless), confirm via `/api/states` that the tablet path sensor
  reads `/wall-tablet/clock`, force a path change by navigating the tablet to
  `/wall-tablet/home` via browser_mod and confirm snap-back within seconds,
  inspect traces of two gated automations to confirm the condition short-circuits,
  toggle off and confirm tablet returns home. Garden light one-shot only fires when
  dark; kitchen LED staying on is the only other physical effect.
- Phone view: Playwright screenshot into `.playwright-mcp/`.
