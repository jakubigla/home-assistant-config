# Ensuite Bathroom — Presence & Lighting Rebuild

**Date:** 2026-05-26
**Area package:** `packages/areas/first-floor/bedroom/` (ensuite lives inside the bedroom package)
**Status:** Design approved, pending spec review

## Problem

The ensuite presence/lighting logic is unreliable and feels chaotic. Investigation (live state + 12h history + logbook) found six distinct bugs:

1. **Stuck power relay.** Turn-ON targets `light.ensuite_bathroom_main_with_power` (relay + bulbs); turn-OFF targets `light.ensuite_bathroom` (bulbs only, no relay). The relay never gets cut, so the `_with_power` group reports `on` forever while the room is dark and empty. Observed live: occupancy off, all bulbs off, but `_with_power` = on.
2. **On/off scope asymmetry.** Three overlapping-but-different light groups used across on / off / vacancy-timeout paths → leftover state.
3. **Occupancy flapping.** `binary_sensor.ensuite_bathroom_occupancy = presence OR motion` with no debounce. mmWave presence drops the instant you sit still; history showed occupancy toggling 7× in 5 min, lights pulsing on a single visit.
4. **Wall switch fights presence.** No manual-override flag — a wall press is re-stomped by motion within seconds. Logbook showed the relay toggling off/on/off/off/on in 2s during a single visit.
5. **Reload/start triggers.** The lights automation triggers on `homeassistant start` and `automation_reloaded`, flipping lights on config reload.
6. **Two competing turn-off owners** (presence at 15s, vacancy-timeout at 10min), different scopes, neither cuts the relay.

### Hardware constraint (verified)

`light.ensuite_bathroom_main_power` ("Main") is an on/off-only relay that is the **hard power feed** for the six `light.en_suite_bulb_*` Zigbee bulbs (Sengled L610). History correlation is exact: every time the relay went `off`, all bulbs went `unavailable` within ~30s and dropped off the Zigbee mesh; they returned only after the relay went back `on`.

**Consequence:** the automation must NEVER cut the relay as part of "lights off" — that makes the bulbs unreachable. The relay stays on; bulb on/off is done with bulb commands. The stuck-`on` reporting is a grouping/display problem, fixed by reading room state from the bulb group, not by cutting power.

## Goals

- Stop the flapping: occupancy latches and survives stillness.
- Wall switch wins: a manual press is respected, with a safety timeout so it never sticks forever.
- No stuck-`on`: room "lights on/off" reflects the bulbs, not the relay.
- Smooth from any state: if the relay is off (restart / edge case), entry turns it on first, then drives bulbs.
- Adopt the prescribed area-patterns state machine (see `.claude/rules/area-patterns.md`).

## Non-goals

- Rewiring the relay out of the bulb feed (hardware change). The design works around smart-bulbs-on-a-relay.
- Touching bedroom lighting logic beyond the shared vacancy-timeout backstop.
- Changing the illuminance / `is_dark` bedroom-bleed override — it works and stays the shared dark signal.

## Entities

### Two physical sensors — complementary coverage zones (IMPORTANT)

The ensuite has **two** occupancy sensors, placed deliberately for different zones. This is not redundancy — each covers an area the other can't, so the design must use both and treat them by role.

- **mmWave — "Ensuite Sensor"** (mains-powered, on the wall where the door is). `binary_sensor.ensuite_bathroom_presence`. Covers the **shower + main room**; holds presence through stillness (person standing in shower, sitting on toilet). This is the **hold/exit** sensor — the one that knows the room is genuinely still occupied. Also the source of `sensor.ensuite_bathroom_illuminance` (lux for `is_dark`) + temperature + humidity. No battery (mains).
- **PIR — "ensuite_bathroom_motion"** (battery Zigbee, aimed at the **entrance**). `binary_sensor.ensuite_bathroom_motion`. Covers the **doorway** so it catches you entering the instant the door opens — mmWave couldn't be placed to cover both entrance and shower, and shower coverage was the priority, hence the separate PIR at the door. This is the **fast-entry** sensor. It does NOT reach the shower, so PIR going off means "left the doorway", NOT "left the room". Has its own separate `sensor.ensuite_bathroom_motion_illuminance` (different placement, reads higher) — not used by `is_dark`.

**Design rule from the layout:** PIR-off alone must NEVER clear the occupancy latch (you could be in the shower, out of PIR view). Only **mmWave-off AND PIR-off together** clear it. Entry/hold may use either; exit must require mmWave (`presence`) off.

### Existing (integration-sourced, not in repo)
- `binary_sensor.ensuite_door` — door open/close
- `light.ensuite_bathroom_main_power` ("Main") — on/off relay, hard feed for the 6 bulbs
- `light.en_suite_bulb_{top,bottom}_{left,middle,right}` — 6 Zigbee bulbs
- `sensor.ensuite_bathroom_illuminance` — mmWave lux (polluted by bedroom bleed; consumed only via `is_dark`)

### Existing (repo, kept)
- `binary_sensor.ensuite_bathroom_is_dark` — dark gate w/ bedroom-bleed override (unchanged)
- `light.ensuite_bathroom` group — `ensuite_bathroom_leds` + 6 bulbs + `ensuite_bathroom_mirror` (the OFF target)
- `light.ensuite_bathroom_main` group — the 6 bulbs only

### New
- `input_boolean.ensuite_occupied` — latch, single source of truth for "someone's in"
- `input_boolean.ensuite_manual_override` — wall-press override flag (visible in UI for debugging)

### Rewritten
- `binary_sensor.ensuite_bathroom_occupancy` — now mirrors `input_boolean.ensuite_occupied` (device_class: occupancy), instead of raw `presence OR motion`

### Retired (kept entity, no longer automation-driven for off)
- `light.ensuite_bathroom_main_with_power` group — no longer used as a target; was the source of the stuck-`on` bug. Left defined to avoid breaking any dashboard reference, but no automation reads/writes it.

## Design

### Layer 1 — Occupancy state machine

`input_boolean.ensuite_occupied` is the latch. A new automation `ensuite_occupancy_state_machine.yaml` (`mode: restart`, `max_exceeded: silent`) manages it.

- **Entry (set on):** `binary_sensor.ensuite_door` off→on, OR `ensuite_bathroom_motion` (PIR/entrance) off→on, OR `ensuite_bathroom_presence` (mmWave) off→on. Action: `input_boolean.turn_on ensuite_occupied`. (PIR at the doorway is the fast path — catches entry the moment the door opens.)
- **Hold:** no explicit action — the latch simply stays on while no exit condition fires. Any motion/presence event resets the restart-mode timers.
- **Exit gate (applies to both paths): mmWave `presence` off AND PIR `motion` off.** PIR-off alone is NOT sufficient — the PIR only covers the entrance, so a person in the shower registers no PIR but does register mmWave. The mmWave (shower/room coverage) is the authoritative "room is empty" signal.
- **Exit path (a) — door closed:** trigger door on→off. Action: `delay 15s` → `condition`: presence (mmWave) off AND motion (PIR) off → `input_boolean.turn_off ensuite_occupied`. (Mid-sequence condition as gate, per area-patterns.)
- **Exit path (b) — open-door safety:** trigger motion off `for: 10 min` AND presence off `for: 10 min` (or a combined template). Action: `condition` motion+presence still off → turn off latch. Backstop for "left the room, left the door open".

**Two-people-one-leaves:** door open/close events never clear the latch by themselves — exit (a) is gated on motion AND presence both off. While the remaining occupant moves or is seen by mmWave, the latch holds. When the last person leaves, the gate passes and the latch clears.

`binary_sensor.ensuite_bathroom_occupancy` template becomes:

```yaml
binary_sensor:
  - name: ensuite_bathroom_occupancy
    device_class: occupancy
    state: "{{ is_state('input_boolean.ensuite_occupied', 'on') }}"
```

### Layer 2 — Lights

Rewrite `ensuite_bathroom_presence.yaml`.

**Triggers:** `binary_sensor.ensuite_bathroom_occupancy` off→on and on→off. Door-open proactive-on folds into the occupancy latch (door open = latch on), so no separate door trigger needed. **Drop** `homeassistant start` and `automation_reloaded` triggers (Bug 5).

**Guard:** all branches first check `input_boolean.ensuite_manual_override == off`. If override on, do nothing (Layer 3 owns the lights).

**Relay-ensure (every ON path):**
1. `light.turn_on light.ensuite_bathroom_main_power`
2. short settle `delay` (~1s) so bulbs rejoin Zigbee if the relay had been off (restart/edge case)
3. then issue bulb brightness commands

**ON branch** (occupancy on AND `is_dark` on AND override off):
- night (after 23:00 OR before 07:30): `light.turn_on light.en_suite_bulb_top_middle` @ `brightness_pct: 1`
- else: `light.turn_on light.ensuite_bathroom_main` @ `brightness_pct: {{ 100 if is_state('light.bedroom','on') else 20 }}`

(Use `ensuite_bathroom_main` = the 6 bulbs, NOT `_with_power`, so we never re-introduce relay coupling on the target.)

**OFF branch** (occupancy off AND override off):
- `light.turn_off light.ensuite_bathroom` (bulbs + leds + mirror). Relay stays on.

### Layer 3 — Manual override

Rewrite `ensuite_bathroom_lights_switch.yaml` (wall button, MQTT device `23964fd4d7b9544d2d0bfe12a241178f`).

- **`single_right`** (full): `input_boolean.turn_on ensuite_manual_override` → relay-ensure → `light.turn_on light.ensuite_bathroom_main` @ 100%.
- **`single_left`** (toggle): if any ensuite bulbs on → turn them off + `input_boolean.turn_off ensuite_manual_override` (restore auto). If off → `input_boolean.turn_on ensuite_manual_override` → relay-ensure → turn on. (Off-press always clears the override so auto resumes.)

New automation `ensuite_manual_override_timeout.yaml` (`mode: restart`):
- triggers: override off→on, and presence/motion → on
- condition: override is on
- action: `delay 15 min` → condition presence off AND motion off → `input_boolean.turn_off ensuite_manual_override` (+ optionally turn off bulbs). Resumes auto behavior; never sticks forever.

### Layer 4 — Vacancy backstop

`bedroom_ensuite_vacancy_timeout.yaml` kept as the bedroom+ensuite 10-min sweep, but:
- ensuite target stays bulbs-only (`light.ensuite_bathroom`), never the relay.
- add `input_boolean.ensuite_manual_override == off` to its condition so it doesn't stomp a manual hold.

## Files

| File | Action |
|---|---|
| `packages/areas/first-floor/bedroom/config.yaml` | add `input_boolean.ensuite_occupied`, `input_boolean.ensuite_manual_override` |
| `.../templates/binary_sensors/ensuite_bathroom_occupancy.yaml` | rewrite → mirror `input_boolean.ensuite_occupied` |
| `.../automations/ensuite_occupancy_state_machine.yaml` | NEW — entry/exit latch |
| `.../automations/ensuite_bathroom_presence.yaml` | rewrite — override-aware, relay-ensure, drop reload/start triggers |
| `.../automations/ensuite_bathroom_lights_switch.yaml` | rewrite — set/clear override |
| `.../automations/ensuite_manual_override_timeout.yaml` | NEW — override safety timeout |
| `.../automations/bedroom_ensuite_vacancy_timeout.yaml` | edit — add override condition, keep bulbs-only |
| `.../templates/binary_sensors/ensuite_bathroom_is_dark.yaml` | unchanged |
| `.../lights/ensuite_bathroom*.yaml` | unchanged (groups kept; `_with_power` no longer targeted) |

## Verification plan

1. `just check` (HA config check) + `uv run yamllint .`.
2. Push to feature branch, reload HA core config, check logs (per reload-after-push leaf).
3. Live behavior checks (hass-cli / logbook):
   - **Flapping:** enter, sit still on toilet → occupancy latch stays on, lights steady (no pulse).
   - **Stuck relay:** leave, latch clears → bulbs off, `light.ensuite_bathroom` group reports off; relay stays on, bulbs stay `available`.
   - **Two people:** simulate one leaving (door close) while motion continues → latch holds.
   - **Open-door exit:** leave door open, no motion 10 min → latch clears.
   - **Wall switch:** press → override sets, motion does NOT re-stomp; off-press clears override; 15-min no-presence auto-clears override.
   - **Cold relay:** turn relay off manually, then trigger entry → relay turns on, settle, bulbs come on smoothly.
   - **Reload:** reload automations → lights do NOT flip.
4. Capture a knowledge leaf for the relay-feeds-bulbs gotcha (Zigbee bulbs go unavailable if relay cut) via knowledge-author.

## Risks / open items

- Settle delay (~1s) after relay-on may be too short for Zigbee rejoin from a true cold start; tune during verification.
- Open-door safety timeout (10 min) interacts with the bedroom vacancy timeout (also 10 min) — acceptable; both bulbs-only now.
- mmWave blind spot with both occupants dead-still could false-clear via exit (b); mitigated by the long timeout and any micro-movement re-holding.
