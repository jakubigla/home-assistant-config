---
summary: Schedule is ONE resolve_day macro (2 equal lawn zones); vertical garden + drip guarantee live OUTSIDE it.
before_action:
  - About to change the garden irrigation schedule (days, frequency, durations) or add a mode
  - About to edit the resolve_day macro, schedule_7day, or garden_next_run templates
  - About to change when lawn or drip irrigation skips (rain, soil moisture, season thresholds)
  - About to change the vertical garden (zone 3) watering cadence or duration
  - About to change a valve run duration or the max-open watchdog
on_symptom:
  - "garden 7-day schedule on tablet shows wrong days or durations"
  - "irrigation next-run sensor disagrees with the dashboard forecast"
  - "template error: can't compare offset-naive and offset-aware datetimes"
  - "schedule attribute renders as a quoted string / can't index resolve_day result"
  - "lawn or drip irrigation skipped (or ran) unexpectedly on a rainy/dry day"
  - "dashboard or garden_drip_next_run shows a drip/lawn day that never actually runs"
  - "drip ran on a rainy day"
  - "a long irrigation run closes early / never reaches its full duration"
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
- **When raising ANY run duration, TWO independent caps must move with it.** (1)
  `garden_valve_max_open_watchdog` per-valve caps (lawn 3300s / vertical 9300s / drip 3600s),
  sized above the longest legit open INCLUDING the Smart am_ratio 1.4 boost — a shared 30-min cap
  silently force-closed every 45-min drip run mid-water for weeks. (2) The
  `garden_open_zone_until_real_close` hold-wait timeout (160 min): on timeout the script's
  trailing safety close force-closes the valve, so any run longer than it gets cut with no error
  — its old 90-min value would have cut the 120-min vertical hot run to 90.

## Skip gating (rain/soil/season)

- **Brain has NO rain logic.** Lawn/drip skip gating lives entirely in
  `templates/garden_should_skip_irrigation.yaml`, NOT the schedule brain. The brain decides *what
  would run today*; the skip sensors decide *whether to actually fire*. (Vertical's rain gate is
  the exception: inline in `garden_vertical_scheduled`, not a skip sensor — see the zone 3
  bullet.)
- **Lawn and drip share IDENTICAL skip logic** (`garden_lawn_should_skip`,
  `garden_drip_should_skip`, + legacy alias `garden_should_skip_irrigation` — all the same expr):
  skip if not in season (May–Sep), `binary_sensor.raining` on, or `sensor.garden_rain_accumulation`
  >= 3mm. **Soil probes gate NOTHING** — observational only (alerts + dashboard); they read
  stuck-wet and drop off Zigbee silently.
- **Automations read the skip sensors, not the brain, for the go/no-go.**
  `garden_scheduled_irrigation` + `garden_seasonal_irrigation` compute
  `run_lawn = lawn_today and not lawn_skip` / `run_drip = drip_today and not drip_skip`. Changing a
  skip threshold (3mm, season) means editing the skip-sensor template only.
- **Skip gating has a floor: `garden_drip_weekly_guarantee` (06:30 daily) force-runs drip when
  `sensor.garden_drip_last_run` ≥ 6.95 d old, BYPASSING rain skips** (season + Manual +
  controller-idle gates kept). A drip run on a wet day ~7 d after the last one is this, not a skip
  bug. 6.95 not 7.0 — the stamp lands minutes after 06:30, an exact 7.0 defers a day per cycle.

## Schedule facts

- **Lawn = zones 1+2 ONLY, both EQUAL minutes in every mode** (2026-07 lawn resize; the old
  `z2=z3=round(z1×0.6)` weighting and the `weighted` key are GONE from resolve_day): Eco 2×/wk
  `[2,6]` 30m/zone; Standard 3×/wk `[2,4,6]` 30m; Intensive lawn `'daily'` 20m (drip stays
  `[1,2,4,5]`); Testing daily 0.5m. `durations` dict has 2 keys — do not re-add zone_3 to any
  lawn path.
- **Zone 3 = VERTICAL GARDEN, not in the brain at all — waters DAILY with a rain skip.**
  `garden_vertical_scheduled` fires 06:15 (not 06:00 — Seasonal Sep AM fires 06:00 and aborts on
  an open zone), runs `script.garden_vertical_irrigation` every day unless
  `binary_sensor.raining` on or `sensor.garden_rain_accumulation` ≥ 3mm (same signals as
  lawn/drip, read INLINE in the automation — not via the skip sensors). Duration =
  `sensor.garden_vertical_planned_minutes`: base `garden_vertical_minutes` (90), switching to
  `garden_vertical_minutes_hot` (120) when today's forecast high ≥ 31 (Scorcher threshold, read
  off `sensor.garden_forecast_today`), hot floored at base (`[hot, base] | max`). Base slider is
  deliberately 122 live — don't "restore" 90. Auto-off (`vertical` trigger id), the scheduler
  log and both dashboards read the planned SENSOR, not the helpers. The rain skip has a floor: a last
  run ≥ `garden_vertical_days_between` (2) days old fires ANYWAY (-0.2 d slack, stamp lands on
  CLOSE) — pockets get little rain even in wet spells. Still NO soil gate (the pocket probe
  reads pinned 100%).
- **Vertical season is May–OCT, unlike lawn/drip (May–Sep).** October = autumn branch keyed on
  `now().month == 10` in FOUR places that must agree: `garden_vertical_scheduled` (cadence
  `_autumn_days_between` 3, guarantee `_autumn_guarantee_days` 6, frost skip next-24h low ≤ 2 °C
  from `garden_forecast_today.low_24h` — frost beats the guarantee), `garden_vertical_planned`
  (`_minutes_autumn` 60), `garden_vertical_next_run` (cadence-aware slot, none in Nov), and the
  tablet footer text. Changing the autumn months → touch all four.
- **Single-pass, NO cycle-and-soak.** `cycle_count` 1 / `soak` 0 for all tbl tiers + Seasonal
  (was 2/15 for Eco/Standard/Intensive/Testing — dropped, loam doesn't need it). Auto-off divides
  each valve open by `cycle_count`, so with 1 the full per-zone duration runs in one pass.
- **Smart routes by month** (May–Jun→Standard, Jul–Aug→Intensive, Sep→Eco, Oct–Apr Off);
  `dynamic_adjust(row)` still a no-op seam. **Never give the brain a month row outside the skip
  sensors' May–Sep season** — it renders on the dashboard + `garden_*_next_run` but the skip gate
  vetoes every run (Oct `DripOnly` advertised phantom drip days until 3db405a removed it). Extend
  the skip-sensor season AND the guarantee/vertical season gates together, or don't add the row.
- **Smart lawn = ONE morning run, no evening session.** `sessions` max 1; `pm`/`pm_ratio` always
  `''`/0. Hot days (`Scorcher`, or `Hot`+sunny) deepen the 04:00 run via **`am_ratio` 1.4**
  (both zones 30→42m) instead of a 17:00 top-up (avoids evening leaf-wetness). **Intensive
  exception: daily cadence gets a gentler overlay — boost 1.2, NO +5min Scorcher z1 bump**
  (20m→24m; was 35m ×1.4 = 49m/zone daily pre the 2026-08 trim). `am_ratio` is on the
  brain `today` attr, each `schedule_7day` row, and a profile attr. (`garden_smart_evening`
  17:00 automation DELETED; Eco/Standard Scorcher still also +5min z1, stacking under the ratio.)
  Only Smart dropped its evening; Seasonal PM 17:00 (`garden_lawn_irrigation_pm`) unchanged.
- **Heat changes DEPTH, never frequency.** Smart lawn fires on the fixed tier day-set (Standard
  `[1,3,5]` Mon/Wed/Fri = 3×/wk) regardless of weather. An old `yday % parity` heat gate that
  thinned the day-set to ~2 scattered days was REMOVED — heat only raises `z1`/`am_ratio`.
- **Each schedule day sizes heat off ITS OWN forecast.** `resolve_day(mode, d, fc)` takes a per-day
  forecast dict; `sensor.garden_forecast_today` exposes `forecast_7day` (per-day high/uv/condition,
  `tojson`), and the `schedule_7day` loop matches each day by date. `today` passes day-0 (live).
  Days past the ~6-day forecast horizon get `fc=none` → Mild/no-boost. (Was: every future day reused
  today's forecast, so the dashboard 🔥 badge showed identical heat all week.)

## Seasonal

- **Seasonal** (May–Sep, durations from `input_number.garden_lawn_minutes_standard`/`_july`):
  twice-daily Jun–Aug (AM 05:00 deep + PM 17:00 ~60% top-up via `script.garden_lawn_irrigation_pm`),
  AM-only May/Sep; drip Mon/Thu only. Handled by `garden_seasonal_irrigation`; the 04:00
  `garden_scheduled_irrigation` excludes Seasonal (no double-fire).

## Verify

- Profile + next_run + brain are template sensors → `template.reload` after push. Diff all modes
  via `/api/template` against the prior values. The dashboard card is not a sensor — frontend cache
  means Playwright force-refetch is the only proof. See **reload-after-push**,
  **playwright-validate-dashboards**.
