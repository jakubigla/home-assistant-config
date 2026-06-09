# Garden

> Automated irrigation for 3 lawn zones and drip irrigation, driven by mode profiles with weather-aware scheduling.

**Package:** `garden` | **Path:** `packages/areas/outdoor/garden/`

## How It Works

### Scheduled Irrigation

<!-- svg:keep -->
<img src="docs/irrigation.svg" alt="Animated site plan: at 04:00 the lawn sprinkler zones spray (each head's circle scaled to its real throw radius), then the drip bed soaks, then the valves auto-close">
<!-- /svg:keep -->

Single daily trigger:

- **04:00** — picks lawn+drip (full), lawn-only, or drip-only based on profile + per-type skip sensors. Drip runs once per day on the same days as lawn.

A **one-off run** can be armed from the dashboard (pick type + datetime, tap Schedule). It fires once at the chosen time, independent of the recurring schedule and ignoring rain skip. It aborts if any valve is already open or any irrigation script is running, and disarms itself at fire time.

Per-type skip:

- **Lawn skip** — lawn season (May–Sep), raining now, **accumulated rain ≥ 3 mm** (Open-Meteo, last 24h + next 12h, via `sensor.garden_rain_accumulation`), or soil moisture > 65% (disabled-ready — activates once a `sensor.garden_soil_moisture` exists). The mm rule is **fail-open**: if Open-Meteo is unreachable the sensor reads `unavailable` and `float(0)` keeps it from forcing a skip (raining-now still guards active rain). A few drops (< 3 mm) won't skip.
- **Drip skip** — drip season (May–Oct) or raining now. No accumulation/forecast lookahead — drip OK with rain coming since foliage stays dry.

### Modes

`input_select.garden_irrigation_mode` controls everything. The mode persists across HA restarts. Named modes ignore the calendar month — they run as configured. Only Smart and Seasonal inspect the month.

**One source of truth.** Every mode's schedule (days, AM/PM times, per-zone durations, cycles, drip) is defined ONCE in a `resolve_day` macro inside `sensor.garden_schedule_brain` (in `garden_irrigation_profile.yaml`). The brain exposes `today` (current day's resolved dict) and `schedule_7day` (next 7 days). `sensor.garden_irrigation_profile` is a thin set of cross-sensor readers of `today` (keeps its old attribute names for back-compat). `garden_next_run` and the dashboard 7-day table render `schedule_7day` — none of them re-derive the schedule, so they can't drift. To change/add a mode, edit the `tbl` dict (or the Seasonal/Smart resolver) in the brain — one place.

| Mode | Per-zone lawn (z1 / z2 / z3) | Lawn total | Lawn freq | Drip dur | Drip freq |
|------|------|------|------|------|------|
| **Manual** | — | — | — | — | — |
| **Eco** | 30m / 18m / 18m | 1h06 | Tue + Sat (2×/wk) | 45m ×1/day | Tue + Sat |
| **Standard** | 30m / 18m / 18m | 1h06 | Tue + Thu + Sat (3×/wk) | 45m ×1/day | Tue + Thu + Sat |
| **Intensive** | 35m / 21m / 21m | 1h17 | Mon + Tue + Thu + Fri (4×/wk) | 45m ×1/day | Mon + Tue + Thu + Fri |
| **Testing** | 30s / 30s / 30s | 90s | daily | 30s ×1/day | daily |
| **Smart** | per month (see below) | — | per month | per month | per month |
| **Seasonal** | from helpers (see below) | — | per month, **twice daily** | 45m ×1/day | **Mon + Thu (2×/wk)** |

Eco and Standard share durations — they differ only in frequency (deep + infrequent vs steady summer). Intensive bumps both for peak heat. **Zone weighting is one shared rule:** z2 = z3 = `round(z1 × 0.6)` for every mode (Testing is flat — `weighted: false`). So Intensive z1=35 → 35/21/21.

**Seasonal mode** — a twice-daily May–Sep schedule, single pass (no cycle & soak), durations from the `input_number` helpers `garden_lawn_minutes_standard` (15m) and `garden_lawn_minutes_july` (18m). The helper value is **zone 1**; z2/z3 = `round(z1 × 0.6)` (preserves the south-slope weighting). `cycle_count` is forced to **1** for Seasonal (durations are single-pass totals).

| Month | Days | AM | PM | z1 / z2 / z3 |
|-------|------|----|----|--------------|
| May | Mon / Thu | 05:00 | — | 15 / 9 / 9 |
| Jun | Mon / Wed / Fri | 05:00 | 17:00 | 15 / 9 / 9 |
| Jul | Mon / Wed / Fri | 05:00 | 17:00 | 18 / 11 / 11 |
| Aug | Mon / Wed / Fri | 05:00 | 17:00 | 15 / 9 / 9 |
| Sep | Mon / Thu | 06:00 | — | 15 / 9 / 9 |

Drip runs **Mon + Thu only** (2×/week, decoupled from lawn frequency), 45m, on the AM session. PM sessions are lawn-only. Handled by `automation.garden_seasonal_irrigation` (separate from the 04:00 `garden_scheduled_irrigation`, which excludes Seasonal so they never double-fire).

**Smart mode by month:**

| Month | Inherits | Lawn freq | Drip freq |
|-------|----------|-----------|-----------|
| May–Jun | Standard | Tue + Thu + Sat | Tue + Thu + Sat |
| Jul–Aug | Intensive | Mon + Tue + Thu + Fri | Mon + Tue + Thu + Fri |
| Sep | Eco | Tue + Sat | Tue + Sat |
| Oct | drip-only | — | 45m every 3 days |
| Nov–Apr | OFF | — | — |

`zone_1` runs longest (biggest / sunniest, south slope); `zone_2` and `zone_3` are equal (`round(z1 × 0.6)`).

**Cycle & soak:** lawn runs zones 1→2→3, repeated `cycle_count` (2) times with a `soak_minutes` (15m) pause between cycles. `lawn_durations` is the TOTAL per-run water — auto-off divides each valve open by `cycle_count` so the sum across cycles equals it. Soak lets water sink in on the slope instead of running off. Drip stays single-pass.

### How Valves Are Controlled

The **auto-off automation** is the single source of truth for durations. Any valve that opens — schedule, script, or HomeKit — gets automatically closed after the profile-driven duration. Scripts open valves and wait for them to close.

The **lawn irrigation script** runs zones sequentially. The **full irrigation script** chains lawn → drip.

### Cleanup Safety

The cleanup automation closes all valves when an irrigation script ends. To avoid killing the parent during chained runs, it skips when `script.garden_full_irrigation` is still running.

### On-Demand Control

All 4 valves and 3 sequence scripts are exposed to **HomeKit**:

- Open any individual valve — auto-off handles the duration
- Close any valve — stops immediately
- Trigger `script.garden_lawn_irrigation` — runs all 3 zones sequentially
- Trigger `script.garden_drip_irrigation` — drip only
- Trigger `script.garden_full_irrigation` — lawn zones then drip

### Run Lawn Now (on-demand, slider duration)

The dashboards (tablet Outdoor + phone Garden room) carry a **Run Lawn Now** block: one Minutes-per-zone slider (`input_number.garden_ondemand_minutes`, 1–25 min) and a single **Run Lawn** button. Tap it → the whole lawn runs zones 1→2→3 sequentially (one pass, no soak), each zone for the slider's minutes, regardless of the profile durations.

`script.garden_ondemand_lawn` (`mode: single`) owns the timing: it sets `input_boolean.garden_ondemand_active`, then for each zone opens the valve, waits the slider duration, closes it (5s gap between zones), and clears the flag at the end. While that flag is on, **auto-off skips lawn valves** (the gate at the top of `garden_valve_auto_off`) so the slider duration wins instead of the profile duration. Drip, profile-driven lawn runs, and HomeKit-manual opens are unaffected. The button shows which zone is currently watering while it runs.

- One at a time — `mode: single`, so a second tap mid-run is ignored.
- Always runs — no rain skip; you decide based on weather.
- Aborts + notifies if any lawn zone valve is `unavailable`.
- Each single valve open is the slider duration (≤25 min < the 30-min max-open watchdog cap), so a healthy run never trips it; a crash mid-run is still backstopped by the watchdog, and `garden_valve_startup_close` clears the flag on every boot.

## Gotchas

- **Valves can't run simultaneously** — the Tuya controller doesn't support it.
- **Auto-off reads duration at valve-open time** — changing mode mid-run won't affect an already-running valve.
- **Zones 5-8 on the Tuya controller are unused** — hardware supports 4 zones.

## Entities

**Valves:** `valve.lawn_sprinkler_zone_1`, `valve.lawn_sprinkler_zone_2`, `valve.lawn_sprinkler_zone_3`, `valve.drip_irrigation`

**Mode:** `input_select.garden_irrigation_mode` — Manual / Eco / Standard / Intensive / Testing / Smart / Seasonal

**One-off run:**
- `input_select.garden_oneoff_type` — Lawn / Drip / Full
- `input_datetime.garden_oneoff_at` — when the one-off fires
- `input_boolean.garden_oneoff_armed` — on = armed; auto-clears at fire time

**On-demand lawn run:**
- `input_number.garden_ondemand_minutes` — per-zone run duration, 1–25 min
- `input_boolean.garden_ondemand_active` — on while an on-demand run owns the lawn valves; gates auto-off off for lawn valves

**Seasonal mode:**
- `input_number.garden_lawn_minutes_standard` — zone-1 base minutes for Seasonal (default 15); z2/z3 = round(×0.6)
- `input_number.garden_lawn_minutes_july` — zone-1 base minutes in July (default 18)

**Sensors:**
- `binary_sensor.garden_lawn_should_skip` — on = skip lawn (season / raining / rain ≥3mm / soil >65%); `reason` attribute names the cause
- `binary_sensor.garden_drip_should_skip` — on = skip drip
- `binary_sensor.garden_should_skip_irrigation` — legacy alias of lawn skip
- `sensor.garden_rain_accumulation` — Open-Meteo summed precipitation (mm) over last 24h + next 12h; drives the lawn ≥3mm skip; fail-open if the API is down. URL from `!secret garden_rain_url` (NOTE: `secrets.yaml` is gitignored — the key must also exist in HA's own `/config/secrets.yaml` or config load 500s)
- `sensor.garden_lawn_next_run` / `sensor.garden_drip_next_run` — next scheduled run (Seasonal-aware: AM/PM slots, Mon/Thu drip)
- `sensor.garden_schedule_brain` — the single source of truth (the `resolve_day` macro). Attributes: `today` (current day's full resolved dict), `schedule_7day` (list of next-7-days `{date, dow, lawn_am_min, lawn_pm_min, drip_min, sessions}`).
- `sensor.garden_irrigation_profile` — thin cross-sensor reader of the brain's `today`. Attributes: `effective_mode`, `lawn_durations` (per-zone seconds, unconditional per-run capacity), `lawn_durations_pm` (≈60% PM top-up, Seasonal only), `cycle_count` (1 for Seasonal, else 2), `soak_minutes`, `drip_duration`, `drip_runs_per_day`, `lawn_today`, `drip_today`, `am_time`, `pm_time`

**Scripts:**
- `script.garden_lawn_irrigation` — zones 1→2→3 sequential
- `script.garden_drip_irrigation` — drip only
- `script.garden_full_irrigation` — lawn then drip
- `script.garden_ondemand_lawn` — whole lawn, zones 1→2→3 sequential, each for the slider duration

## Dependencies

- `binary_sensor.raining` — current rain state
- `weather.forecast_home` — Met.no, hourly forecast fetch (drip skip + legacy)
- Open-Meteo free API (no key) — via `!secret garden_rain_url`, powers `sensor.garden_rain_accumulation`
- `notify.mobile_app_iglofon` — skip/abort notifications from the Seasonal automation + manual run

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry; helpers (input_select/number/datetime/boolean) + the `rest:` Open-Meteo rain sensor |
| `automations/garden_valve_auto_off.yaml` | Auto-closes valves after profile duration; skips lawn valves while an on-demand run is active |
| `automations/garden_scheduled_irrigation.yaml` | 04:00 trigger with per-type skip (excludes Manual + Seasonal) |
| `automations/garden_seasonal_irrigation.yaml` | Seasonal mode twice-daily (05:00/06:00/17:00) sessions; night guard, already-open abort, skip-only notify |
| `automations/garden_oneoff_run.yaml` | Fires a single armed run (Lawn/Drip/Full) at the chosen datetime, then disarms. Aborts if already irrigating. Ignores rain skip. |
| `automations/garden_irrigation_cleanup.yaml` | Closes all valves on script end (skips when parent full irrigation running) |
| `automations/garden_valve_startup_close.yaml` | Force-closes all valves + clears the on-demand flag on HA boot |
| `automations/garden_valve_max_open_watchdog.yaml` | Every 5 min, force-closes any valve open longer than 30 min |
| `automations/garden_valve_offline_watchdog.yaml` | Notifies when sprinkler valves go offline |
| `scripts/garden_lawn_irrigation.yaml` | Sequential zones 1→2→3 |
| `scripts/garden_drip_irrigation.yaml` | Drip valve with wait-for-close |
| `scripts/garden_full_irrigation.yaml` | Chains lawn + drip |
| `scripts/garden_ondemand_lawn.yaml` | Whole lawn (zones 1→2→3) for the slider duration; manual path with night-guard + already-open + skip checks |
| `scripts/garden_lawn_irrigation_pm.yaml` | Seasonal PM top-up — zones 1→2→3 single pass at `lawn_durations_pm` (≈60% of AM) |
| `templates/garden_should_skip_irrigation.yaml` | Lawn (rain ≥3mm / soil / season) + drip skip sensors |
| `templates/garden_irrigation_profile.yaml` | **Both** sensors: `garden_schedule_brain` (the `resolve_day` macro = single source) + `garden_irrigation_profile` (thin readers) |
| `templates/garden_next_run.yaml` | Next lawn/drip run — scans the brain's `schedule_7day` (no per-mode maps) |
