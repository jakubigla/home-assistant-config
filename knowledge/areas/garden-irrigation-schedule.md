---
summary: Schedule is ONE resolve_day macro in garden_schedule_brain; skip gating (rain/soil/season) is separate, lawn==drip.
before_action:
  - About to change the garden irrigation schedule (days, frequency, durations) or add a mode
  - About to edit the resolve_day macro, schedule_7day, or garden_next_run templates
  - About to change when lawn or drip irrigation skips (rain, soil moisture, season thresholds)
on_symptom:
  - "garden 7-day schedule on tablet shows wrong days or durations"
  - "irrigation next-run sensor disagrees with the dashboard forecast"
  - "template error: can't compare offset-naive and offset-aware datetimes"
  - "schedule attribute renders as a quoted string / can't index resolve_day result"
  - "lawn or drip irrigation skipped (or ran) unexpectedly on a rainy/dry day"
  - "Smart-mode drip never runs / runs at the wrong time / status sensor stuck"
---

# Garden irrigation schedule

## One source of truth

- **The whole schedule lives in ONE `resolve_day(mode, date)` macro** in
  `sensor.garden_schedule_brain` (defined in `templates/garden_irrigation_profile.yaml`). It returns
  a day's full dict (durations, cycles, am/pm, drip, sessions…). To change/add a mode, edit the
  `tbl` dict (static modes Eco/Standard/Intensive/Testing) or the Seasonal/Smart resolver — ONE
  place. No more per-consumer day maps.
- **Consumers READ, never re-derive.** `sensor.garden_irrigation_profile` is thin cross-sensor
  readers of the brain's `today` attribute (keeps old attr names for back-compat).
  `garden_next_run` and the dashboard 7-day table render the brain's `schedule_7day` attribute
  (next-7-days list). Change the macro → all three follow automatically.

## Jinja gotchas (these bit during the unification)

- **Macro must end `{{ result | tojson }}`; callers parse `| from_json`.** A bare `{{ dict }}`
  emits Python-repr (single quotes) — `from_json` can't parse it, and a macro result is text so you
  can't index it mid-template. `tojson` makes valid JSON that parses back to a real mapping.
- **`strptime(d, '%Y-%m-%d')` is tz-NAIVE** — comparing to `now()` (tz-aware) throws
  `can't compare offset-naive and offset-aware datetimes`. Attach `.replace(tzinfo=now().tzinfo)`.
- **Two sensors, not one, BECAUSE attributes can't read sibling attributes** (template-sensor
  eval-order / `this` staleness). Cross-SENSOR reads (`state_attr('sensor.garden_schedule_brain',
  'today')`) ARE safe — that's why the brain computes and the profile reads.
- **Durations are unconditional per-run capacity, NOT gated by `lawn_today`.** `auto-off` reads
  `lawn_durations`/`drip_duration` for ANY valve open (incl HomeKit), so they must always equal the
  per-run amount. Only `schedule_7day`'s display fields (`lawn_am_min`/`drip_min`/`sessions`) are
  day-gated.

## Skip gating (rain/soil/season)

- **Brain has NO rain logic.** Skip gating lives entirely in
  `templates/garden_should_skip_irrigation.yaml`, NOT the schedule brain. The brain decides *what
  would run today*; the skip sensors decide *whether to actually fire*.
- **Lawn and drip share IDENTICAL skip logic** (`garden_lawn_should_skip`,
  `garden_drip_should_skip`, + legacy alias `garden_should_skip_irrigation` — all the same expr):
  skip if not in season (May–Sep), `binary_sensor.raining` on, `sensor.garden_rain_accumulation`
  >= 3mm, or `sensor.garden_soil_moisture` > 65%. (Drip was once permissive — May–Oct, raining-now
  only; unified so both gate the same.)
- **Automations read the skip sensors, not the brain, for the go/no-go.**
  `garden_scheduled_irrigation` + `garden_seasonal_irrigation` compute
  `run_lawn = lawn_today and not lawn_skip` / `run_drip = drip_today and not drip_skip`. Changing a
  skip threshold (3mm, 65%, season) means editing the skip-sensor template only.
- **`garden_drip_soil_skip` thresholds are tunable, not hardcoded.** Its DRY ("moist enough, skip
  scheduled drip") reads `garden_drip_soil_stop` (60) and SAT reads `garden_drip_soil_sat` (70) —
  same tunables the Smart `garden_drip_soil_status` sensor uses, so dashboard + scheduled-drip gate
  agree (was hardcoded DRY=50/SAT=85; the 50→60 shift means non-Smart scheduled drip skips at a
  slightly wetter bed). Only feeds NON-Smart scheduled drip; Smart reads probes inline (below).

## Schedule facts

- **Tiers, own day set, shared weighting** `z2=z3=round(z1×0.6)` (Testing flat, `weighted:false`):
  Eco 2×/wk `[2,6]` 30/18/18; Standard 3×/wk `[2,4,6]` 30/18/18; Intensive 4×/wk `[1,2,4,5]`
  35/21/21; Testing daily 0.5min flat.
- **Single-pass, NO cycle-and-soak.** `cycle_count` 1 / `soak` 0 for all tbl tiers + Seasonal
  (was 2/15 for Eco/Standard/Intensive/Testing — dropped, loam doesn't need it). Auto-off divides
  each valve open by `cycle_count`, so with 1 the full per-zone duration runs in one pass.
- **Smart routes LAWN by month** (May–Jun→Standard, Jul–Aug→Intensive, Sep→Eco, Oct→drip-only
  `yday % 3`, Nov–Apr Off); `dynamic_adjust(row)` still a no-op seam. **Smart DRIP is NOT
  schedule-driven — see below.**
- **Smart lawn = ONE morning run, no evening session.** `sessions` max 1; `pm`/`pm_ratio` always
  `''`/0. Hot days (`Scorcher`, or `Hot`+sunny) deepen the 04:00 run via **`am_ratio` 1.4**
  (z1 30→42m, sides 18→25m) instead of a 17:00 top-up (avoids evening leaf-wetness). `am_ratio` is
  on the brain `today` attr, each `schedule_7day` row, and a profile attr. (`garden_smart_evening`
  17:00 automation DELETED; Scorcher still also +5min z1, stacking under the ratio.) Only Smart
  dropped its evening; Seasonal PM 17:00 (`garden_lawn_irrigation_pm`) unchanged.

## Smart soil-driven drip

- **Smart drip is demand-based, not scheduled.** `garden_drip_soil_run` opens the line when driest
  flowerbed probe `< START` (`input_number.garden_drip_soil_start`, default/currently 35);
  `garden_drip_soil_arm` re-arms only after driest recovers `> STOP`
  (`input_number.garden_drip_soil_stop`, 60) — hysteresis state in
  `input_boolean.garden_drip_armed`, disarmed on fire. Frequency cap
  `input_number.garden_drip_min_days_between` (days since `sensor.garden_drip_last_run`, default 1).
  Vetoes: rain, out-of-season, pergola saturation `>= SAT`
  (`input_number.garden_drip_soil_sat`, 70 — **sona excluded**, wetter/more emitters), night
  22:00–04:30, valve open.
- **`garden_scheduled_irrigation` excludes Smart from `run_drip`** (lawn in Smart still schedules;
  non-Smart modes keep schedule + skip-gate drip).
- **Control automations read the 3 probes INLINE, never `binary_sensor.garden_drip_soil_skip`.** That
  helper is trigger-based; a co-triggered sibling reads its stale `unknown` same-pass (eval-order
  race). Inline dodges it. Helper + `sensor.garden_drip_soil_status` are observability only.
- **Seasonal** (May–Sep, durations from `input_number.garden_lawn_minutes_standard`/`_july`):
  twice-daily Jun–Aug (AM 05:00 deep + PM 17:00 ~60% top-up via `script.garden_lawn_irrigation_pm`),
  AM-only May/Sep; drip Mon/Thu only. Handled by `garden_seasonal_irrigation`; the 04:00
  `garden_scheduled_irrigation` excludes Seasonal (no double-fire).

## Verify

- Profile + next_run + brain are template sensors → `template.reload` after push. Diff all modes
  via `/api/template` against the prior values. The dashboard card is not a sensor — frontend cache
  means Playwright force-refetch is the only proof. See **reload-after-push**,
  **playwright-validate-dashboards**.
