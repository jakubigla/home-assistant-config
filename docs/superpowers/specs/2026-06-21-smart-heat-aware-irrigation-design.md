# Smart-Mode Heat-Aware Lawn Irrigation — Design

**Date:** 2026-06-21
**Scope:** Smart mode only, lawn only. Eco / Standard / Intensive / Seasonal / Testing modes and all drip logic are **untouched**.

## Problem

Smart mode (`garden_schedule_brain` → `smart_target(month)`) routes purely by calendar
month. In June it picks `Standard` params: lawn Tue/Thu/Sat 04:00, z1=30 min, no evening
session ever. During a 29–31 °C heatwave this is wrong in two ways:

1. **Cadence too slow** — fixed Tue/Thu/Sat means up to a 2-day gap. In sustained heat
   one rest day is plenty; two is too long.
2. **No evening relief** — on a hot, sunny day a single 04:00 run isn't enough; the lawn
   wants a short evening top-up. Smart mode has no PM session at all.

The fix: make Smart mode **heat-aware** — read today's forecast and flex cadence,
morning duration, and an optional evening top-up off a heat tier.

## Decisions (locked with user)

| # | Decision |
|---|----------|
| Q1 | Heat signal = **forecast daily high + UV index** (predictive, morning-decided). |
| Q2 | **3 heat tiers**: Mild / Hot / Scorcher. Temp cuts **26 °C / 31 °C**. |
| Q3/Q4 | Tier drives **cadence** (max-gap, day-of-year derived — not fixed weekdays), morning duration, and evening top-up. |
| Q5 | **Scorcher** = every-2nd-day morning **+** evening top-up. **Min-gap guard** via `sensor.garden_lawn_last_run`. |
| Q6 | Evening = **40% of morning**, single pass (no cycle-soak), ~17:00, gated. |
| Q7 | **Smart-only, lawn-only.** Drip stays on existing soil-demand logic; Smart still disables scheduled drip. |

## Heat tiers

Computed from **today's forecast daily high** (`high`) and **UV index** (`uv`):

| Tier | Condition | Cadence (max-gap) | Morning z1 | Evening top-up |
|------|-----------|-------------------|-----------|----------------|
| **Mild** | `high < 26` | every 3rd day (`yday % 3 == 0`) | base (Standard z1, e.g. 30) | none |
| **Hot** | `26 <= high < 31` | every 2nd day (`yday % 2 == 0`, 1 rest day) | base | **yes IF sunny**: condition in `[sunny, partlycloudy]` **and** `uv >= 6` |
| **Scorcher** | `high >= 31` | every 2nd day (`yday % 2 == 0`) | base + bump (e.g. +5 min, capped) | **yes, always** (no sunny check) |

- **Base z1** = current Smart-for-month value (June→Standard 30, July→Intensive 35, etc.).
  Heat tier modifies on top of base; it does **not** replace the month routing for the
  base number. Scorcher adds a small morning bump.
- **Cadence is day-of-year parity**, so it adapts instantly when the tier changes
  day-to-day — no fixed weekday list.
- **Sunny check (Hot only):** forecast `condition in [sunny, partlycloudy]` AND `uv >= 6`.
  Scorcher skips the sunny check — hot enough regardless.

### Min-gap guard (anti-double-water)

Day-of-year parity can flip when the tier changes mid-week, which could schedule two
mornings in a row. Guard at fire time in the automation:

- Read `sensor.garden_lawn_last_run` (timestamp, `restore: true` — already exists).
- Never run the morning lawn if `now - last_run < min_gap_hours`.
  - Mild → `min_gap_hours = 44` (enforces ≥ ~2-day spacing).
  - Hot / Scorcher → `min_gap_hours = 20` (allows next-day, blocks same-day double).
- Evening top-up is **exempt** from the guard (it's the same-day partner of the morning).

## Architecture

Single source of truth stays the **schedule brain**. No new top-level structure.

### 1. Forecast helper (extend existing skip sensor's trigger)

`garden_should_skip_irrigation.yaml` already calls `weather.get_forecasts` (type:
`hourly`) in its trigger action. Add a **second** `weather.get_forecasts` call (type:
`daily`) in that same trigger action, and add one template sensor exposing today's
forecast as attributes:

```
sensor.garden_forecast_today
  state:        <today's forecast high °C>   (number, for dashboards/debug)
  attributes:
    high:       today's daily-high temp (°C)
    uv:         today's uv_index
    condition:  today's condition string (sunny/partlycloudy/rainy/…)
```

Fail-safe: if the daily forecast is missing/empty, `high`/`uv` resolve to a neutral
default that yields **Mild** tier + no evening (never escalate watering on bad data).

> The brain is a plain template sensor and **cannot** call `weather.get_forecasts`
> itself — that's why the service call lives in the skip sensor's trigger action and the
> brain reads the resulting `sensor.garden_forecast_today` attributes.

### 2. Schedule brain — heat-aware Smart branch

In `garden_schedule_brain` `today` macro (and the verbatim copy in `schedule_7day`):

- Add a `heat_tier(high, uv)` macro → returns `Mild` | `Hot` | `Scorcher`.
- In `resolve_day`, when `eff == 'Smart'` (after `smart_target` picks the base
  month-tier params), apply the heat overlay:
  - **Cadence:** replace fixed `days` list with day-of-year parity per tier. `lawn_today`
    becomes `yday % N == 0` (N = 3 Mild, 2 Hot/Scorcher) instead of `dow in days`.
  - **Morning duration:** base z1 from month tier; Scorcher adds bump.
  - **Evening:** set `pm`, `pm_ratio = 0.4`, and `durations_pm` when the tier+sunny gate
    says evening runs today. Otherwise `pm = ''`, `durations_pm` all zero (current
    behavior).
- `schedule_7day` uses the **same** logic so dashboard chips + `next_run` reflect heat —
  BUT future-day forecast isn't available per-day from one call. **Decision:** the 7-day
  projection assumes **today's tier persists** for cadence/evening (best-effort; the chip
  is advisory, the automation re-decides at fire time with fresh forecast). Documented
  limitation, acceptable — `next_run` is already described as advisory.

> **Constraint:** `today` and `schedule_7day` are independent attribute strings with no
> shared scope — every macro (`smart_target`, `resolve_day`, new `heat_tier`) must be
> **copied verbatim into both**. This is the existing pattern; keep both copies in sync.

### 3. Morning run — `garden_scheduled_irrigation` (04:00)

Add the **min-gap guard** to `run_lawn`:

```
run_lawn = lawn_today and not lawn_skip and (now - last_run >= min_gap_hours)
```

`min_gap_hours` read from a new profile attribute (`min_gap_hours`, tier-derived). Drip
gate unchanged (Smart still disables scheduled drip).

### 4. Evening run — 17:00 trigger (Smart)

Smart needs a 17:00 trigger. **Reuse the existing `garden_lawn_irrigation_pm` script**
verbatim — it already runs zones 1→2→3 single-pass off `lawn_durations_pm`. Two options
for the trigger (decide in plan):

- **(a)** Add a 17:00 trigger + a Smart branch to `garden_scheduled_irrigation`
  (rename its scope from "04:00 only"), OR
- **(b)** A new small automation `garden_smart_evening.yaml` (17:00, gated `mode==Smart`,
  mirrors Seasonal-PM's guards: night-guard N/A, no-valve-already-open, morning-ran-today,
  not-raining).

Lean **(b)** — keeps the 04:00 automation single-purpose and mirrors the existing
Seasonal split (separate `garden_seasonal_irrigation` owns Seasonal's 17:00). Evening
gate:

```
fire IF mode == Smart
   AND profile.pm_time == '17:00'  (brain decided evening runs today)
   AND lawn ran this morning (last_run is today AND after 03:00)
   AND not raining now / drip_should_skip-style rain veto
   AND no lawn valve already open
```

### 5. Profile sensor — new thin attributes

`sensor.garden_irrigation_profile` gains thin cross-reads of the brain's `today` dict:

- `heat_tier` (Mild/Hot/Scorcher) — for dashboard chip.
- `min_gap_hours` — consumed by the morning guard.
- `pm_time`, `lawn_durations_pm` — already exist; now populated in Smart mode.

## Data flow

```
weather.get_forecasts(daily)         [skip-sensor trigger action]
        │
        ▼
sensor.garden_forecast_today  (high, uv, condition)
        │
        ▼
sensor.garden_schedule_brain.today   [heat_tier + Smart overlay]
        │
        ├──► sensor.garden_irrigation_profile (heat_tier, min_gap_hours,
        │        lawn_durations, lawn_durations_pm, pm_time, …)
        │
        ├──► garden_scheduled_irrigation (04:00)  → +min-gap guard → morning
        │
        ├──► garden_smart_evening (17:00)         → garden_lawn_irrigation_pm
        │
        └──► garden_lawn_next_run / schedule_7day (advisory chips)
```

## Error handling / fail-safes

- **Bad/missing forecast** → Mild tier, no evening (never over-water on bad data).
- **Min-gap guard** → blocks accidental same-day double morning on tier transitions.
- **Valve already open** → evening aborts (mirrors Seasonal-PM guard).
- **Controller offline** → `garden_lawn_irrigation_pm` already aborts + notifies.
- **Rain veto** → existing skip sensors still gate both morning and evening.
- **Out of season** (month not May–Sep) → skip sensor already forces skip; Smart
  `smart_target` returns Off Nov–Apr / DripOnly Oct → no lawn anyway.

## Testing / verification

1. **Template render** via `/api/template`: feed synthetic high/uv → assert tier,
   cadence (`lawn_today`), durations, `pm_time`, `min_gap_hours` for Mild/Hot/Scorcher
   × sunny/cloudy.
2. **Min-gap guard**: simulate `last_run` = this morning, tier flips → morning blocked.
3. **Evening gate**: assert fires only when morning ran + sunny/scorcher + not raining.
4. **Regression**: Eco/Standard/Intensive/Seasonal/Testing render identical to before
   (heat overlay is `eff == 'Smart'`-gated).
5. **Dashboard**: Playwright check the Outdoor view chips show heat_tier + correct
   next-run after push (per repo dashboard-validation rule).
6. **Push → reload core config → check logs** (per repo deploy rule).

## Out of scope (YAGNI)

- Live-temp confirmation at 17:00 (chose forecast-only, option A).
- Heat-flex for non-Smart modes.
- Per-zone lawn soil sensors (don't exist; lawn stays forecast-driven).
- Drip changes (stays on soil-demand).
- Continuous duration scaling (chose 3 discrete tiers).
