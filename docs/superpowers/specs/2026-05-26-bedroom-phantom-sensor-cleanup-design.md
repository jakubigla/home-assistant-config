# Bedroom Phantom Presence-Sensor Cleanup

**Date:** 2026-05-26
**Area package:** `packages/areas/first-floor/bedroom/`
**Status:** Design approved, pending spec review

## Problem

Surfaced during the ensuite rebuild: the bedroom package references four `binary_sensor` presence entities that do not exist on the live HA instance (verified via template render — all return `unknown`, `is not none` = False):

- `binary_sensor.bedroom_presence` — whole-room presence
- `binary_sensor.bedroom_walking_area_presence` — walking-area zone
- `binary_sensor.presence_sensor_bedroom_jakub_side` — Jakub bed-side
- `binary_sensor.presence_sensor_bedroom_sona_side` — Sona bed-side

The bedroom FP2 device (E1A4) now exposes only one zone, `binary_sensor.bedroom_entrance_presence` ("Presence Sensor 3"), which the user confirms covers the **whole room**. The other FP2 zones and both bed-side sensors are gone from the device.

### Symptom impact (current, while phantoms absent)

- `bedroom_presence.yaml` — off-branch requires `bedroom_presence == off`; a phantom reads `unknown` (≠ `off`), so the off-branch never fires.
- `bedroom_bed_presence_sleeping.yaml` — every trigger/condition sensor is a gone-for-good phantom → fully dead.
- `bedroom_vacancy_timeout.yaml` — trigger + condition on `bedroom_presence` → never fires.
- `bedroom_humidifier_target_speed.yaml` — reads `bedroom_presence`; absent reads as not-occupied → always uses the vacant fan caps.

## Key constraint (drives the whole design)

**`bedroom_presence` is returning.** The user will re-add a whole-room presence sensor later under the **same entity id** `binary_sensor.bedroom_presence` (a single whole-room sensor, no zones). Therefore references to `bedroom_presence` must be **left untouched** — they are forward-compatible and will auto-revive when the sensor reappears. Do **not** substitute it with `bedroom_entrance_presence`.

The sensors that are **gone for good** (no plan to re-add): `bedroom_walking_area_presence`, `presence_sensor_bedroom_jakub_side`, `presence_sensor_bedroom_sona_side`. Only references to these are removed.

## Goals

- Repo no longer references the three gone-for-good sensors.
- All `bedroom_presence` references preserved verbatim, so the bedroom presence automation, vacancy timeout, and humidifier occupancy logic revive automatically when the whole-room sensor is re-added.
- One dead automation (`bedroom_bed_presence_sleeping.yaml`) removed — its only inputs are gone-for-good sensors and true bed-movement detection is impossible without bed-side sensors.

## Non-goals

- Re-adding any presence sensor (hardware / FP2 reconfig — user will do separately).
- Substituting `bedroom_presence` with the entrance zone (would require a revert later).
- Touching `home_ready_to_arm.yaml` — it already uses only real sensors (`bedroom_entrance_presence`, `bedroom_wardrobe_occupancy`); it was a false grep match, not a phantom user.

## Design

### 1. `automations/bedroom_presence.yaml` — remove `walking_area` only

Three edits, all dropping `binary_sensor.bedroom_walking_area_presence` and nothing else:

- **Trigger list 1** (off→on): entity_id list keeps `bedroom_entrance_presence` and `bedroom_presence`, drops `bedroom_walking_area_presence`.
- **Trigger list 2** (on→off, `for: 5s`): same drop.
- **Daytime branch OR condition**: keeps the `bedroom_entrance_presence == on` arm, drops the `bedroom_walking_area_presence == on` arm.

The off-branch (`bedroom_presence == off` AND `bedroom_entrance_presence == off` AND `ensuite_bathroom_occupancy == off`) is **unchanged** — both presence refs are valid (one real, one returning).

### 2. `automations/bedroom_bed_presence_sleeping.yaml` — delete

Remove the file. Its triggers and conditions reference only gone-for-good sensors. The sleeping-time bed-stripe nightlight is already covered by the sleeping-time branch of `bedroom_presence.yaml` (20% bed stripe on entrance presence during sleeping time).

### 3. `automations/bedroom_vacancy_timeout.yaml` — no change

Uses `binary_sensor.bedroom_presence` (returning). Leave as-is; revives with the sensor. (Already carries a NOTE comment about the phantom from the ensuite-rebuild decoupling.)

### 4. `templates/sensors/bedroom_humidifier_target_speed.yaml` — no change

Three reads of `binary_sensor.bedroom_presence` (state line, `max_speed` attr, `presence` attr). All forward-compatible; leave as-is.

### 5. `bootstrap/templates/binary_sensors/home_ready_to_arm.yaml` — no change

Already uses real sensors only.

### 6. `packages/areas/first-floor/bedroom/README.md` — update

- File Index: remove the `bedroom_bed_presence_sleeping.yaml` row.
- Dependencies: remove the three gone-for-good sensor lines (`bedroom_walking_area_presence`, `presence_sensor_bedroom_jakub_side`, `presence_sensor_bedroom_sona_side`). Keep `bedroom_presence`, re-labelled as "whole-room presence — temporarily absent, pending re-install under this same entity id".
- Gotchas: replace the ⚠️ phantom block with a concise note: `bedroom_presence` is intentionally absent pending a whole-room sensor re-install (refs kept so logic auto-revives); the gone-for-good bed-side/walking-area sensors have been removed from the config.
- "How It Works" sleeping/nightlight narrative: drop the mention of the deleted bed-movement nightlight (the entrance-driven sleeping-time bed stripe remains).

## Verification plan

1. `grep -rn 'walking_area_presence\|presence_sensor_bedroom_jakub_side\|presence_sensor_bedroom_sona_side' packages/` → **zero matches**.
2. `grep -rn 'binary_sensor.bedroom_presence' packages/` → still present in `bedroom_presence.yaml`, `bedroom_vacancy_timeout.yaml`, `bedroom_humidifier_target_speed.yaml` (intentional).
3. `uv run yamllint .` clean on edited files.
4. Push to feature branch, reload HA (`automation/reload` + `template/reload`), check `error_log` — no new errors; `bedroom_bed_presence_sleeping` automation entity gone.
5. Confirm `bedroom_presence.yaml` still loads and `bedroom_entrance_presence` drives the bedroom bed stripe (entrance presence → bed stripe on when dark + not sleeping + movie mode off).

## Risks / open items

- While `bedroom_presence` is absent, the vacancy timeout and humidifier occupied-cap stay dormant (vacancy never fires; humidifier always uses vacant caps = higher max fan when active). Accepted — reinstating the sensor restores both. Documented in the README.
