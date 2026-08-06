# AC + Presence Automation — Design

**Date:** 2026-08-06
**Status:** Approved

## Goal

Stop air conditioners running in empty rooms, and stop the bedroom AC blasting
high fan at someone who just walked in during the pre-sleep cooldown.

Two behaviours:

1. **Vacancy auto-off** — AC turns off 5 minutes after the room goes empty.
   Applies to the bedroom and the living room.
2. **Fan drop on entry** — bedroom only. If the AC is cooling on anything
   louder than `quiet` and the room becomes occupied, drop the fan to `quiet`.

## Context

### Existing bedroom AC automations (unchanged by this work)

| File | Behaviour |
| --- | --- |
| `bedroom_ac_cooldown_on.yaml` | 21:00–23:00 **or** `binary_sensor.sleeping_time` on, and room above `input_number.bedroom_ac_night_threshold` → `cool` @ 23 °C, fan `quiet`. |
| `bedroom_ac_cooldown_off.yaml` | Room ≤ 25.0 °C for 5 min while cooling → AC off. |
| `bedroom_ac_safety_timeout.yaml` | 3 h after cooling starts → off, **only if the room is empty**. |

The living room AC has no presence or schedule logic at all today.

### Entities

| Entity | Notes |
| --- | --- |
| `climate.bedroom` | Tuya. Fan modes: `auto`, `quiet`, `low`, `medlow`, `medium`, `medhigh`, `high`, `strong`. |
| `climate.living_room` | Midea. Fan modes: `silent`, `low`, `medium`, `high`, `full`, `auto`. |
| `input_boolean.bedroom_occupied` | Debounced latch (entrance FP2 **or** in-room mmWave; clears after both off 60 s). Rides out mmWave still-gaps. |
| `binary_sensor.living_room_presence` | FP2 main zone. `living_room_sofa_presence` is a sub-zone of it and is therefore ignored. |
| `binary_sensor.sleeping_time` | 23:00 → 07:30 weekdays / 11:00 weekends. |

The two ACs use **different fan vocabularies** — `quiet` vs `silent`. Only the
bedroom gets fan logic, so only `quiet` is used.

## Design

Three new automations. No new helpers. No edits to existing automations.

### 1. `packages/areas/ground-floor/living-room/automations/living_room_ac_off_when_vacant.yaml`

- **Trigger:** `binary_sensor.living_room_presence` → `off` for 5 min
- **Conditions:** `climate.living_room` is not `off` and not `unavailable`
- **Action:** `climate.turn_off`
- **Mode:** `single`, `max_exceeded: silent`

The sofa sub-zone is deliberately not consulted — it is a subset of the main
zone, so it can never be `on` while the main zone is `off`.

### 2. `packages/areas/first-floor/bedroom/automations/bedroom_ac_off_when_vacant.yaml`

- **Trigger:** `input_boolean.bedroom_occupied` → `off` for 5 min
- **Conditions:**
  - `climate.bedroom` is not `off` and not `unavailable`
  - **Not** in the cooldown window: fails if the time is 21:00–23:00 **or**
    `binary_sensor.sleeping_time` is `on`
- **Action:** `climate.turn_off`
- **Mode:** `single`, `max_exceeded: silent`

Triggering off the latch rather than the raw mmWave sensor is essential —
`binary_sensor.bedroom_occupancy` drops during stillness, and the latch is what
absorbs that.

**Why the cooldown window is exempt.** The 21:00–23:00 pre-cool exists
precisely to chill an *empty* room before bed; a vacancy rule that killed it
would defeat its purpose. Overnight is likewise exempt because the mmWave
sensor loses a sleeper and the latch eventually clears. The night is already
owned by the ≤ 25 °C cooldown-off and the 3 h safety timeout, both of which
stay as they are.

The exempt condition mirrors the union in `bedroom_ac_cooldown_on.yaml`, so the
two automations agree on what "cooldown period" means.

**Known edge case.** Leaving at 20:50 lets the 5-minute timer fire at 20:55 and
turn the AC off; `bedroom_ac_cooldown_on.yaml` then re-arms it at 21:00 if the
room is still above the threshold. This wastes at most ~5 minutes of cooling.
Accepted: widening the exempt window to start at 20:00 just moves the same
boundary an hour earlier.

### 3. `packages/areas/first-floor/bedroom/automations/bedroom_ac_fan_low_when_occupied.yaml`

- **Trigger:** `input_boolean.bedroom_occupied` → `on`
- **Conditions:**
  - `climate.bedroom` state is `cool`
  - current `fan_mode` is not already `quiet`
  - `binary_sensor.sleeping_time` is `off`
- **Action:** `climate.set_fan_mode` → `quiet`
- **Mode:** `single`, `max_exceeded: silent`

This **does** run during the 21:00–23:00 pre-cool window — that is the main
scenario. The AC is pre-cooling hard on `high`; walking in at 22:00 drops it to
`quiet`.

Sleeping time is excluded because `bedroom_ac_cooldown_on.yaml` already sets
`quiet` for the night, making the rule redundant there.

**No restore on exit.** The fan is not raised again when the room empties. The
AC turns off 5 minutes later outside the cooldown window anyway, and inside the
window the next cooldown-on cycle sets its own fan mode. Restoring `high` for a
short window would be pointless churn on the device.

**Not applied to the living room.** Nothing pre-cools it, so the
blast-on-entry scenario does not arise. Adding the rule there would instead
fight the user: manually setting `high` on a hot day, stepping out, and
returning would silently drop it to `silent`.

## Rejected options

- **Manual-override helpers** (`input_boolean.*_ac_override`) to suspend
  vacancy-off. Rejected as YAGNI — the automation itself can be toggled off
  from the dashboard on the rare occasion someone wants to pre-chill an empty
  living room.
- **Grace period measured from AC turn-on** (e.g. skip vacancy-off if the AC
  started less than 20 min ago). Same purpose as above, more moving parts.
- **Requiring both the main and sofa living-room zones to be clear.**
  Unnecessary given the sub-zone relationship.
- **Restoring a high fan on vacancy.** See above.

## Verification

- `uv run yamllint .` and `just check` pass.
- Push to the feature branch, reload HA config, confirm no errors in the log.
- Confirm all three automations appear as entities and that every entity they
  reference resolves.

Behaviour is time- and presence-dependent, so end-to-end confirmation means
checking the wiring and letting the automations run in real use — the 5-minute
timers are not waited out during verification.
