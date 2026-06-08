# Garden Seasonal irrigation + smart rain-intensity skip — design

## Problem

A Claude-for-Desktop prompt asked for a from-scratch twice-daily sequential irrigation
system (on `switch.strefa_*`, soil sensors, `weather.home`). This repo already has a
richer system on `valve.lawn_sprinkler_zone_{1,2,3}` (Tuya valves) with mode profiles,
per-zone weights, split lawn/drip skip sensors, auto-off, watchdogs, cleanup, one-off,
and an on-demand slider button. Building the prompt as-is would create a conflicting
parallel system on wrong entity IDs.

This folds the prompt's *new ideas* into the existing system as a **new "Seasonal"
mode** (Smart and all other modes untouched):

- Twice-daily sessions in peak months, per a month/day table.
- Smarter rain skip based on **accumulated rainfall (mm)** from Open-Meteo
  (last 24h + next 12h), not a binary "is any hour rainy" — a few drops won't skip.
- A night guard, an already-on abort, skip-only notifications, and a disabled-ready
  soil-moisture hook for future hardware.

## Decisions (locked during brainstorm)

- **New mode, not a rewrite.** Add `Seasonal` to `input_select.garden_irrigation_mode`.
  Eco / Standard / Intensive / Smart / Testing / Manual are untouched.
- **Twice-daily table** (isoweekday days; durations are **z1 base**, z2/z3 = `round(z1 × 0.6)`):

  | Month | Days | AM | PM | z1 base | z1 / z2 / z3 |
  |-------|------|----|----|---------|--------------|
  | May (5) | Mon/Thu [1,4] | 05:00 | — | 15 | 15 / 9 / 9 |
  | Jun (6) | Mon/Wed/Fri [1,3,5] | 05:00 | 17:00 | 15 | 15 / 9 / 9 |
  | Jul (7) | Mon/Wed/Fri | 05:00 | 17:00 | 18 | 18 / 11 / 11 |
  | Aug (8) | Mon/Wed/Fri | 05:00 | 17:00 | 15 | 15 / 9 / 9 |
  | Sep (9) | Mon/Thu | 06:00 | — | 15 | 15 / 9 / 9 |
  | other | — | — | — | 0 | OFF |

- **Durations from helpers:** `input_number.garden_lawn_minutes_standard` (default 15) and
  `garden_lawn_minutes_july` (default 18). Seasonal z1 base = july helper in month 7,
  else standard helper. So durations are UI-tunable without YAML edits.
- **No cycle & soak in Seasonal** — plain single sequential pass. The profile sets
  `cycle_count: 1` for Seasonal so the existing `garden_lawn_irrigation` script runs one
  pass (it divides by cycle_count). Other modes keep their cycle&soak.
- **Rain-intensity skip (lawn):** skip if accumulated rain ≥ **3 mm** over (last 24h +
  next 12h), from a new Open-Meteo sensor. `binary_sensor.raining` (now) stays as an
  extra immediate guard. **Fail-open:** if the sensor is unknown/unavailable, treat
  accumulation as 0 mm (water) rather than block all irrigation on a dead API.
- **Drip skip unchanged-permissive:** drip uses raining-now + season only, NOT the 3 mm
  rule (foliage stays dry).
- **Drip 2×/week in Seasonal:** fixed **Mon + Thu**, 45 min, decoupled from lawn days.
- **Soil-moisture skip, disabled-ready:** references `sensor.garden_soil_moisture`
  (no hardware yet). While absent (state in unknown/unavailable/''), it contributes
  nothing. Threshold > 65%.
- **Night guard 22:00–04:30** on the Seasonal automation and the manual path. Scheduled
  times (05:00/06:00/17:00) are outside it; mainly bites manual runs.
- **Already-on abort:** if any lawn valve is already `open` when a session fires, abort +
  `persistent_notification`.
- **Skip-only notifications:** notify (persistent + `notify.mobile_app_iglofon`) ONLY on
  skip/abort, with reason. No routine start/end notifications.
- **Manual run = reuse `garden_ondemand_lawn`** (built earlier today). Add skip +
  night-guard + already-on checks to it. No second parallel "run now" script. Duration
  stays the slider value (the slider IS the ad-hoc control).

## Architecture

```
input_number.garden_lawn_minutes_standard ─┐
input_number.garden_lawn_minutes_july ──────┤
input_select.garden_irrigation_mode=Seasonal┴─► sensor.garden_irrigation_profile
                                                  (Seasonal branch: durations, days,
                                                   AM/PM times, drip Mon/Thu, cycle_count 1)
                                                          │
Open-Meteo REST ─► sensor.garden_rain_accumulation_mm ─┐  │
binary_sensor.raining ─────────────────────────────────┤  │
sensor.garden_soil_moisture (future) ───────────────────┤  │
                                                         ▼  ▼
                                          binary_sensor.garden_lawn_should_skip
                                          binary_sensor.garden_drip_should_skip
                                                          │
automation.garden_seasonal_irrigation (05:00/06:00/17:00 triggers)
   guards: mode==Seasonal, valid time-for-month, night-guard, not already-on, not skip
   → script.garden_lawn_irrigation / garden_drip_irrigation / garden_full_irrigation
   → skip/abort → persistent_notification + mobile_app_iglofon
```

The existing `garden_scheduled_irrigation` (04:00, single session) stays and runs for the
non-Seasonal modes. Seasonal is handled by the new automation; the two are mutually
exclusive by a mode check (04:00 automation already excludes Manual; add an exclude for
Seasonal so they never double-fire).

### Components

**1. Helpers — `config.yaml`**

Add to `input_select.garden_irrigation_mode.options`: `Seasonal`. Add:

```yaml
input_number:
  garden_lawn_minutes_standard:
    name: Garden Lawn Minutes (standard)
    min: 5
    max: 30
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline
  garden_lawn_minutes_july:
    name: Garden Lawn Minutes (July)
    min: 5
    max: 30
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline
```

**2. Profile — `templates/garden_irrigation_profile.yaml`**

Add a `Seasonal` branch to each attribute (effective_mode, lawn_durations, lawn_today,
drip_today, drip_duration, drip_runs_per_day, cycle_count). Seasonal specifics:
- `lawn_durations`: z1 = (july helper if month==7 else standard helper) × 60 s; z2=z3 =
  `round(z1 × 0.6)`. Zero outside May–Sep.
- `lawn_today`: month→days map (May/Sep [1,4]; Jun/Jul/Aug [1,3,5]); false outside 5–9.
- `cycle_count`: **1** for Seasonal (single pass). Existing default `"2"` kept for others —
  make `cycle_count` mode-aware.
- New attributes for the automation: `am_time` ('05:00'/'06:00'), `pm_time`
  ('17:00' or '' if no PM this month). These let the automation know which sessions apply.
- `drip_today`: Seasonal → `dow in [1,4]` (Mon/Thu); other modes unchanged.
- `drip_duration`: Seasonal → 2700 (45 min) in season else 0.

**3. Rain accumulation sensor — `rest:` platform in the garden package** (new file)

A `rest:` platform sensor calling Open-Meteo (no API key). **Coords come from a secret,
not hardcoded** — `!secret` interpolates a whole value (not mid-string) and does NOT work
inside Jinja `resource_template`, so the cleanest fit (matching the existing
`twilio_calls_url` flat-URL secret pattern) is to store the **entire URL** as one secret:

```yaml
# secrets.yaml (gitignored) — real value:
garden_rain_url: "https://api.open-meteo.com/v1/forecast?latitude=52.2476&longitude=20.8362&hourly=precipitation&past_days=1&forecast_days=2&timezone=auto"
# secrets.fake.yaml — placeholder committed to git:
garden_rain_url: "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&hourly=precipitation&past_days=1&forecast_days=2&timezone=auto"
```

```yaml
# templates/garden_rain_accumulation.yaml  (rest: lives under its own top-level key,
# so config.yaml needs `rest: !include_dir_merge_list rest` OR put this rest: block in
# config.yaml directly — decide at plan time; HA `rest:` is a top-level platform, not a
# template sensor. Simplest: add the rest: block to the garden config.yaml.)
rest:
  - resource: !secret garden_rain_url
    scan_interval: 1800
    sensor:
      - name: Garden Rain Accumulation
        unique_id: garden_rain_accumulation_mm
        unit_of_measurement: mm
        value_template: >
          {% set t = value_json.hourly.time %}
          {% set p = value_json.hourly.precipitation %}
          {% set lo = (now() - timedelta(hours=24)).isoformat() %}
          {% set hi = (now() + timedelta(hours=12)).isoformat() %}
          {% set ns = namespace(total=0.0) %}
          {% for i in range(t | count) %}
            {% if t[i] >= lo[:13] and t[i] <= hi[:13] %}
              {% set ns.total = ns.total + (p[i] | float(0)) %}
            {% endif %}
          {% endfor %}
          {{ ns.total | round(2) }}
```

- `sensor.garden_rain_accumulation_mm` — sum of hourly `precipitation` (mm) for
  timestamps within [now − 24h, now + 12h]. (Open-Meteo `time` is local `YYYY-MM-DDTHH:MM`
  with `timezone=auto`; compare on the `[:13]` `YYYY-MM-DDTHH` prefix.)
- Attributes `past_24h_mm` / `next_12h_mm` are nice-to-have; fold into the same template
  via a second sensor or `json_attributes` at plan time.
- On request failure the `rest:` sensor goes `unavailable` → skip logic fails open (`float(0)`).
- **NOTE:** confirm at plan time whether `config.yaml` already exposes a `rest:` include;
  if not, the `rest:` block goes directly in `config.yaml` (HA merges one `rest:` key).
- On request failure → sensor goes `unavailable`; skip logic fails open (treats as 0).

**4. Skip sensors — `templates/garden_should_skip_irrigation.yaml`**

Rework `garden_lawn_should_skip`:
- Replace the 6h "any rainy condition" forecast test with: accumulation ≥ 3 mm
  (`states('sensor.garden_rain_accumulation_mm') | float(0) >= 3`), fail-open via `float(0)`.
- Keep `binary_sensor.raining` immediate guard and season (May–Sep).
- Add disabled-ready soil test: if `sensor.garden_soil_moisture` has a usable numeric
  state, skip when `> 65`; otherwise contributes nothing.
- `reason` attribute gains: `rain_accumulation_3mm`, `soil_wet`. Existing reasons kept.

`garden_drip_should_skip` unchanged (raining-now + season 5–10). Legacy alias
`garden_should_skip_irrigation` follows the lawn rework.

**5. Seasonal automation — `automations/garden_seasonal_irrigation.yaml`** (new file)

- Triggers: `time` at `05:00:00`, `06:00:00`, `17:00:00`.
- Conditions (all): mode is `Seasonal`; **night guard** time not in [22:00, 04:30];
  the fired time matches the month's `am_time`/`pm_time` (a trigger that isn't a valid
  session for this month is a no-op).
- Action:
  - **Already-on abort:** if any of the 3 lawn valves is `open` → persistent_notification
    + `mobile_app_iglofon` + `stop`.
  - Resolve `lawn_today`/`drip_today`/skip exactly like `garden_scheduled_irrigation`.
  - **Skip notify:** if today is a run day but skip is on, send one notification with the
    skip `reason`, then stop.
  - Otherwise `choose` → full / lawn / drip script (PM session is lawn-only; drip only on
    its AM Mon/Thu run to honor 2×/week).
- Filename/id follow `{area}_{action}_{trigger}` convention.

**6. Manual path — extend `scripts/garden_ondemand_lawn.yaml`**

Add, before opening valves: night-guard check (22:00–04:30 → notify + stop), already-on
abort (reuse), and a lawn-skip check (≥3 mm / raining / soil) → notify reason + stop.
Duration stays the slider value. No new script.

**7. Exclude Seasonal from the 04:00 automation — `automations/garden_scheduled_irrigation.yaml`**

Add `Seasonal` to the `condition: not / state` list (alongside Manual) so the 04:00 daily
automation never double-fires when Seasonal mode is active.

## Data flow

1. Mode = Seasonal. Profile resolves month → durations (from helpers), days, AM/PM times,
   drip Mon/Thu, cycle_count 1.
2. Open-Meteo sensor refreshes accumulation mm every ~30 min; lawn skip sensor recomputes.
3. At 05:00/06:00/17:00, the Seasonal automation checks mode, night guard, valid session,
   already-on, skip → dispatches the matching existing script or notifies the skip reason.
4. Manual slider button runs the same guards before opening valves.

## Error handling / edge cases

- **Open-Meteo down:** accumulation `unavailable` → `float(0)` → lawn waters (fail-open).
  `binary_sensor.raining` still guards active rain.
- **Soil sensor absent:** soil test contributes nothing until a numeric state appears.
- **Double-fire:** 04:00 automation excludes Seasonal; Seasonal automation excludes other
  modes via mode check. Mutually exclusive.
- **Invalid session trigger:** a 17:00 trigger in May (no PM) fails the time-for-month
  condition → no-op.
- **Already-on / unavailable valves:** abort + notify (reuses existing patterns).
- **Night guard vs scheduled times:** 05:00/06:00/17:00 all outside 22:00–04:30 — never
  blocks a scheduled session; only manual runs in the window.
- **cycle_count mode-awareness:** ensure non-Seasonal modes still read `2`; only Seasonal
  forces `1`. Auto-off divides by cycle_count, so a wrong value would halve/double water.

## Testing / verification

- `just check` + `just lint`.
- Push branch, reload HA (core config + template + automation + script + input_number +
  input_select reload), check logs.
- Profile: set mode Seasonal, render `sensor.garden_irrigation_profile` attributes for a
  simulated month (verify z1/z2/z3, days, am/pm times, cycle_count 1, drip Mon/Thu).
- Rain sensor: confirm `sensor.garden_rain_accumulation_mm` populates (mm) with sane
  past/next attributes; force a high value and confirm lawn skip flips with reason
  `rain_accumulation_3mm`; set sensor unavailable and confirm fail-open (no skip).
- Automation functional: with Testing-short durations or a near-future time trigger,
  confirm a session runs sequentially; confirm already-on abort and skip-notify paths.
- Night guard: attempt manual run inside 22:00–04:30 → blocked + notified.
- Confirm Smart/Eco/Standard still resolve unchanged (regression).

## Also update

- `secrets.yaml` (gitignored) + `secrets.fake.yaml` (committed) — add `garden_rain_url`
  (full Open-Meteo URL with real coords in secrets.yaml, zeroed placeholder in the fake).
- `packages/areas/outdoor/garden/README.md` — Seasonal mode, helpers, rain sensor, new
  automation, guard/skip changes. Run `/ha-area-docs`.
- `garden-irrigation-schedule` knowledge leaf — Seasonal is a new schedule source; update
  the "duplicated across N files" note (now also the rain sensor + seasonal automation).

## Out of scope (YAGNI)

- Soil-moisture hardware (logic is disabled-ready only).
- Twice-daily for non-peak months beyond the table.
- Replacing or removing existing modes.
- Dashboard cards for Seasonal (separate task if wanted).
- Per-session routine start/end notifications (skip-only).
- A second profile-duration manual script (reuse the slider path).
