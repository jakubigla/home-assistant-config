# Bedroom Evening AC Cooldown — Design

**Date:** 2026-06-26
**Area:** `packages/areas/first-floor/bedroom/`

## Goal

Cool the bedroom to a comfortable temperature before bedtime (~22:00). The AC
turns on automatically in the evening when the room is hot, and turns off
automatically once cooled or after a safety timeout.

## Requirements

- Cool toward 22°C in the evening run-up to bedtime.
- Trigger when the room is over 25°C.
- Read room temperature through an **overlay sensor** so the underlying physical
  sensor can be swapped without touching the automations.
- Turn off automatically for both logical (target reached) and safety
  (max-runtime) reasons.

## Entities

### AC

- `climate.bedroom` — bedroom AC unit. Supports `cool` mode, setpoint range
  16–31°C. May report `unavailable` out of season; automations must tolerate
  this.

### Source sensor

- `sensor.bedroom_fp300_temperature` — FP300 presence-sensor ambient
  temperature (renamed by user). The chosen real-ambient source.
  - Note: most other bedroom `*_device_temperature` sensors are Zigbee chip
    temps that run hot (38–42°C) and are NOT valid room-ambient readings.

## Components

### 1. Overlay sensor

**File:** `packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`

A template sensor that mirrors the chosen source.

- `sensor.bedroom_temperature` → mirrors `sensor.bedroom_fp300_temperature`.
- `device_class: temperature`, `unit_of_measurement: °C`, `state_class: measurement`.
- Single source of truth for "bedroom temperature". All AC automations read
  this overlay, never the raw fp300 sensor.
- To change the physical source later: edit the one source line in this template.
  Automations stay untouched.
- Must pass through `unknown`/`unavailable` gracefully (return source state as-is
  so downstream conditions can guard).

### 2. ON automation

**File:** `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`

- **Trigger:** `sensor.bedroom_temperature` above 25°C, sustained `for: 5 min`
  (debounce sensor noise).
- **Conditions:**
  - Time is within 21:00–23:00.
  - `climate.bedroom` is not `unavailable`.
  - `climate.bedroom` is not already in `cool` mode (don't re-issue).
- **Action:**
  - `climate.set_temperature` → 22°C on `climate.bedroom`.
  - `climate.set_hvac_mode` → `cool` on `climate.bedroom`.

### 3. OFF automation — target reached (hysteresis)

**File:** `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml`

- **Trigger:** `sensor.bedroom_temperature` at or below 23°C, sustained `for: 5 min`.
- **Condition:** `climate.bedroom` state is `cool` (only act if we are cooling).
- **Action:** `climate.turn_off` on `climate.bedroom`.

Hysteresis band: ON above 25°C, OFF at/below 23°C. The 2°C gap prevents rapid
on/off cycling.

### 4. Safety max-runtime

**File:** `packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`

- `mode: restart` (timer resets if cooling restarts).
- **Trigger:** `climate.bedroom` changes to `cool`.
- **Action:** `delay: 3h` → `climate.turn_off` on `climate.bedroom`.

Hard backstop: if the source sensor is stuck/wrong and the room never reaches
23°C, the AC still shuts off after 3 hours. Applies regardless of who started
cooling (manual or automatic).

## Behavior / edge cases

- **AC unavailable:** ON automation's `not unavailable` condition skips silently —
  no error, no action. Safe when AC is off-season.
- **Active window end (23:00):** only blocks new auto-*on*. If already cooling at
  23:00, the hysteresis OFF and safety timeout still apply — no abrupt boundary
  cutoff.
- **Manual control respected:** OFF-target automation only fires when state is
  `cool`. If the user manually sets the AC to `heat`/`fan_only`, auto-off won't
  fight it. Safety timeout still applies to any `cool` session (safe by design,
  confirmed acceptable).
- **Hysteresis:** ON >25°C, OFF ≤23°C, setpoint 22°C.

## Out of scope

- No input_select source picker (overlay template is the indirection layer).
- No bedtime/fixed-time off (hysteresis + safety cover shutdown).
- No window/door-open off (no bedroom contact sensor).

## Files touched

| File | Action |
|------|--------|
| `templates/sensors/bedroom_temperature.yaml` | new — overlay sensor |
| `automations/bedroom_ac_cooldown_on.yaml` | new |
| `automations/bedroom_ac_cooldown_off.yaml` | new |
| `automations/bedroom_ac_safety_timeout.yaml` | new |
| `bedroom/README.md` | regenerate via `/ha-area-docs` |
