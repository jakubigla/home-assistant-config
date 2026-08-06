# Vertical Garden Daily Watering with Rain Skip — Design

**Date:** 2026-07-22
**Status:** Approved

## Problem

The vertical garden (zone 3, drip) waters on a 7-day cadence
(`garden_vertical_scheduled`, deliberately no rain/soil gating). The pockets
dry out much faster than the lawn or flowerbeds — they need water **every
day**, except when it is raining.

## Decisions (user-confirmed)

1. **"Sunny" = not raining.** Water daily unless it is raining now
   (`binary_sensor.raining`) or rain accumulation ≥ 3 mm
   (`sensor.garden_rain_accumulation`) — the same signals lawn/drip skip
   logic uses. Overcast-but-dry days still water. No forecast/UV gate.
2. **Rain-streak guarantee: 2 days.** Pockets get little rain even during wet
   spells (established design note). If the last run is ≥ 2 days old, run at
   06:15 regardless of rain. `input_number.garden_vertical_days_between` is
   repurposed as this guarantee knob (7 → 2).
3. **Duration unchanged.** `input_number.garden_vertical_minutes` stays at
   20 min, tunable from the dashboard after observing the plants.

## Approach

Inline gate in the existing `garden_vertical_scheduled` automation (approach
A). No new entities, no new automations. The automation is time-triggered
(06:15) and `mode: single`, so reading rain sensors inline is safe — the
trigger-based-helper eval-order race documented for drip does not apply.

Rejected: dedicated `garden_vertical_should_skip` sensor + separate guarantee
automation (more moving parts, single consumer); folding zone 3 into the
schedule brain (zone 3 is deliberately outside it — see
`knowledge/areas/garden-irrigation-schedule.md`).

## Changes

### `automations/garden_vertical_scheduled.yaml`

- Keep: 06:15 trigger (Seasonal Sep 06:00 interplay), Manual-mode gate,
  May–Sep season gate, 90-min controller-idle wait, fire-and-forget script
  call, logbook entry.
- Remove: the 7-day cadence stop (`days_since < days_between - 0.05`).
- Add: `rain_skip` variable = raining now OR rain accumulation ≥ 3 mm.
  Stop (with logbook skip entry) only when `rain_skip` AND
  `days_since < guarantee_days − 0.05`. The −0.05 slack keeps the
  stamp-at-open time from deferring the guarantee by a day each cycle.
- Effect: dry day → runs every day; rainy day with last run < 2 d → skip;
  rainy day with last run ≥ 2 d → guarantee run.

### `config.yaml` (garden package)

- `garden_vertical_days_between`: `initial: 7` → `2`; display name
  "Garden Vertical Days Between" → "Garden Vertical Rain Guarantee Days"
  (entity id unchanged — YAML key stays).

### `templates/garden_next_run.yaml` — `sensor.garden_vertical_next_run`

- Cadence math (`last_run + days_between` at 06:15) → next 06:15 slot daily.
  One-off (`Vertical` type), Manual, and out-of-season branches unchanged.
  Rain skip is not predictable ahead of time; next 06:15 is the honest
  answer.

### Post-push (live HA)

- `input_number.set_value` → `garden_vertical_days_between` = 2 (reload never
  applies `initial:`).
- Reload core config + template entities; check logs.

### Docs / knowledge (after code verified)

- `scripts/garden_vertical_irrigation.yaml` description wording ("every N
  days" → daily + rain skip + guarantee).
- `templates/garden_irrigation_profile.yaml` header comment wording.
- Dashboard chips (tablet `outdoor.yaml`, phone `rooms/garden.yaml`) if they
  describe the cadence.
- Garden README via `/ha-area-docs`.
- Knowledge leaf `garden-irrigation-schedule.md` via knowledge-author (leaf
  currently documents "deliberately NO rain gating, 7 d cadence" — stale
  after this change).

## Error handling (unchanged, inherited)

- Controller offline → script aborts + persistent notification.
- Controller busy past 90-min wait → skip today, notify, retry tomorrow.
- Zone-helper busy (manual lawn run) → script aborts + notification.
- Auto-off closes the valve after `garden_vertical_minutes`; max-open
  watchdog cap (vertical 3900 s) unchanged — duration not raised.
- Missing/invalid `garden_vertical_last_run` → `days_since = 999` → always
  ≥ guarantee → runs (fail-open, same as today).

## Verification

- `just lint`, `just check`.
- Push branch → HA pulls → reload → check error log.
- `/api/template`: render `rain_skip` expression and
  `sensor.garden_vertical_next_run` — next run must be the next 06:15.
- Confirm live `input_number.garden_vertical_days_between` reads 2.
