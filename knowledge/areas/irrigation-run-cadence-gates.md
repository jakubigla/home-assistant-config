---
summary: Fixed-day single-fire scheduler makes a min-gap guard a deferral trap; stamp last_run on hold-duration not any open.
before_action:
  - About to add a min-gap / min-days-between guard to a fixed-day irrigation or scheduled run
  - About to change what stamps sensor.garden_lawn_last_run or any recency/last-run gate
on_symptom:
  - "scheduled lawn irrigation skipped a day / went ~90h between runs after a manual run"
  - "Smart-mode lawn didn't run, gap_ok was false, last run was under min_gap_hours"
  - "a short valve test or on-demand tap blocked the next scheduled run"
---

# Irrigation run-cadence gates

## A min-gap guard on a fixed-day, single-fire-time scheduler is a deferral trap

- **Don't add a `min_gap_hours` floor to a scheduler that fires once a day on fixed weekdays — the
  schedule days ARE the spacing.** `garden_scheduled_irrigation` fires only at 04:00 on the tier's
  day-set (Standard Mon/Wed/Fri = ≥48h apart). A 44h gap guard can therefore never bite the real
  cadence; it only fires after an OFF-schedule manual run desyncs `sensor.garden_lawn_last_run`
  from the 04:00 grid. Then — because the next attempt is the *next schedule day's 04:00*, not
  "44h after last run" — it defers to the following schedule day, turning a 44h floor into a ~90h
  gap (a floor silently became an unbounded ceiling). Dropped in 37e2d89:
  `run_lawn = lawn_today and not lawn_skip`.
  The general rule: a between-run guard only works on a scheduler that can RETRY at the
  moment the gap clears; a fixed daily fire-time can't, so the guard just skips the slot.
- `min_gap_hours` still computed on `sensor.garden_irrigation_profile` (Mild 44 / Hot 20) but is
  now **dead** — no consumer. Harmless; left in place.

## A last_run / recency gate must stamp on hold-duration, not any valve open

- **A `last_run` timestamp that stamps on ANY valve `open` conflates real watering with noise.** A
  few-second valve test, an on-demand "does it click" tap, and the open/close pulses of a
  `garden_open_zone_until_real_close` re-assert all stamp `last_run`, poisoning any recency gate
  that reads it. (Those sub-10s pulses were originally blamed on a Tuya "spurious close"; the real
  cause was a `wait_template` state-on-entry race in that helper — see
  [[wait-template-state-on-entry-race]] — not the device.)
  Fix (`templates/garden_last_run.yaml`):
  trigger on valve **CLOSE**, stamp only if the zone was open ≥120s
  (`(to_state.last_changed - from_state.last_changed) >= 120`). Real runs hold each zone minutes —
  the first zone past 120s stamps the run; tests/phantoms never reach it. No separate test button
  needed. Triggering on close is required: at open-time the hold duration is always 0.
- Only the **lawn** sensor is duration-gated. Drip is single-pass with no test path, so it still
  stamps on open. Don't blanket-apply the close trigger to every last-run sensor.
