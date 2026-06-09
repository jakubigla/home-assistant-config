# Garden unified irrigation schedule — design

## Problem

The garden irrigation modes grew organically and now follow disconnected logic. Each
mode invents its own duration source, day encoding, and session model, and that logic is
**re-implemented in 4 places** (the `garden-irrigation-schedule` knowledge leaf already
flags this):

| Dimension | Eco/Std/Int | Smart | Seasonal |
|-----------|-------------|-------|----------|
| Duration source | hardcoded literals (1800s…) | hardcoded via tier remap | `input_number` helpers |
| Day encoding | `dow in [2,4,6]` per tier | inherits tier days | own `[1,3,5]` month map |
| Sessions/day | 1 @ 04:00 | 1 @ 04:00 | 2 @ AM/PM |
| cycle_count | 2 | 2 | 1 |
| Zone weighting | explicit literals | explicit | base × 0.6 |
| Re-derived in | profile, next_run, dashboard, README | (same 4) | (same 4) |

Adding the asymmetric AM/PM top-up (deep 05:00 soak + light 17:00 top-up for the
sun-baked lawn) to this would add a 5th variation. Instead: **unify first** — one schema
per mode, defined once, read everywhere.

## Decisions (locked during brainstorm)

- **Single source of truth.** One Jinja `SCHEDULE` dict at the top of
  `garden_irrigation_profile.yaml` describes every static mode. All profile attributes
  read from it. `next_run`, the dashboard table, and the automation read the profile's
  exposed attributes — they STOP re-deriving.
- **One duration model.** Each mode expresses lawn as `z1_min` (zone-1 base minutes);
  z2/z3 = `round(z1 × 0.6)` via a single shared formula everywhere. Accepted drift:
  Intensive becomes 35/21/21 (was 35/20/20); Eco/Standard 30/18/18 unchanged.
- **One day encoding:** isoweekday list (`[2,4,6]`) or `'daily'`.
- **Sessions:** `am` always present; `pm` optional. `pm_ratio` (0.6) drives the
  asymmetric top-up — a first-class dict field, not a bolt-on. PM is single-pass (no soak).
- **Smart = dynamic resolver, NOT a dict row.** Smart resolves to a static mode's params
  via a month→mode lookup TODAY (May–Jun→Standard, Jul–Aug→Intensive, Sep→Eco,
  Oct→drip-only, else Off), preserving current behavior. A clearly-marked
  `dynamic_adjust` placeholder hook sits in the resolver — a no-op now, the seam where
  soil-moisture (sensors ordered, not yet connected) + forecast + ET logic plugs in later.
- **`schedule_7day` is the shared contract.** Profile exposes a 7-day forecast attribute
  (list of per-day `{date, lawn_am_min, lawn_pm_min, drip_min, sessions}`). Dashboard +
  next_run render it; can't drift.
- **One computed resolution, macro-shared (not sibling reads).** HA template sensors can't
  safely read a sibling attribute (`this.attributes` eval-order/staleness). So the dict +
  per-day resolution live in ONE macro `resolve_day(mode, date)` returning a day's full
  dict. The display attribute `today` calls it; each scalar attribute (`lawn_durations`,
  `cycle_count`, …) ALSO calls the same macro and plucks one field. Logic is defined once
  (the macro); attributes are thin one-call readers. `schedule_7day` calls `resolve_day`
  per day in a 7-loop. No cross-attribute reads.
- **Behavior-preserving migration.** All modes migrate into the model; each must resolve
  identically to the captured before-snapshot (only Intensive z2/z3 may differ, expected).

### Before-snapshot (live, 2026-06-09, for the after-diff)

```
Eco       1800/1080/1080  cyc2   (z1=30)
Standard  1800/1080/1080  cyc2   (z1=30)
Intensive 2100/1200/1200  cyc2   (z1=35)  → becomes 2100/1260/1260 (0.6 formula)
Testing     30/30/30      cyc1   (z1=0.5, flat — see note)
Smart     = Standard params (June → Standard tier)
Seasonal   900/540/540    cyc1   (z1=15, June)
```

Note: Testing is flat 30/30/30 (all zones equal, not weighted). Model this with an
explicit per-zone override OR a `weighted:false` flag on the Testing row so the 0.6
formula does not apply to it.

## Architecture

```
                 SCHEDULE dict (one definition, static modes)
                          │
        Smart resolver ───┤  (month→mode today; dynamic_adjust placeholder for soil/forecast)
                          ▼
   sensor.garden_irrigation_profile  (reads dict, exposes the public API)
     ├─ effective_mode, lawn_durations (AM), lawn_durations_pm (AM×pm_ratio)
     ├─ cycle_count, soak_minutes, drip_duration, drip_runs_per_day
     ├─ lawn_today, drip_today, am_time, pm_time
     └─ schedule_7day  ── list[{date, lawn_am_min, lawn_pm_min, drip_min, sessions}]
                          │
        ┌─────────────────┼──────────────────────────┐
        ▼                 ▼                           ▼
  garden_next_run    dashboard 7-day table     garden_seasonal_irrigation
  (reads             (renders schedule_7day;   (AM→lawn_durations,
   schedule_7day)     macros DELETED)           PM→lawn_durations_pm)
```

All native HA Jinja. No new dependencies.

### Components

**1. `SCHEDULE` dict + `resolve_day` macro — `templates/garden_irrigation_profile.yaml`**

The dict AND the per-day resolution logic live in ONE macro, `resolve_day(mode, date)`,
which returns a day's full resolved dict: `{date, dow, effective_mode, lawn_am_min,
lawn_pm_min, lawn_durations, lawn_durations_pm, cycles, soak, am, pm, drip_min,
drip_today, sessions}`. Every attribute calls this same macro (one call, pluck one field)
— the logic is defined once; no attribute re-implements days/durations and none reads a
sibling attribute. The `sched()` dict literal is a sub-macro `resolve_day` calls.

```jinja
{% macro sched() %}{{
  {
    'Eco':       {'days':[2,6],     'am':'04:00','pm':none,'z1':30,'cycles':2,'soak':15,'drip_days':[2,6],    'drip':45,'weighted':true},
    'Standard':  {'days':[2,4,6],   'am':'04:00','pm':none,'z1':30,'cycles':2,'soak':15,'drip_days':[2,4,6],  'drip':45,'weighted':true},
    'Intensive': {'days':[1,2,4,5], 'am':'04:00','pm':none,'z1':35,'cycles':2,'soak':15,'drip_days':[1,2,4,5],'drip':45,'weighted':true},
    'Testing':   {'days':'daily',   'am':'04:00','pm':none,'z1':0.5,'cycles':1,'soak':0,'drip_days':'daily', 'drip':0.5,'weighted':false},
  }
}}{% endmacro %}
```

Seasonal is month-dependent (per-month z1 + am/pm), so it is a small separate resolver
(month→params) rather than one static row; durations come from
`input_number.garden_lawn_minutes_standard` / `_july` (existing helpers). Its `pm_ratio`
is 0.6, `pm` set in months 6–8.

Shared zone formula (applied unless `weighted:false`):
`z2 = z3 = round(z1 × 0.6)`. Seconds = `min × 60`.

**Smart resolver** — a macro `smart_target(month)` returning a mode key + (for Oct) a
drip-only marker. `dynamic_adjust(params)` is a pass-through placeholder documented as the
soil/forecast hook; returns `params` unchanged until sensors exist.

**2. Exposed attributes** — each is a thin `resolve_day(mode, today)` reader (one call,
pluck one field). All consumers keep their existing attribute names (no consumer rewrite
needed beyond next_run/dashboard which move to `schedule_7day`):
- `today` — the full resolved dict for the current day (display/debug; the one "big"
  attribute). Other attributes do NOT read it (sibling-read unsafe) — they call the macro.
- `effective_mode` — Smart→resolved key, else mode.
- `lawn_durations` — AM per-zone seconds dict (keys `valve.lawn_sprinkler_zone_1/2/3`).
- `lawn_durations_pm` — `round(am_seconds × pm_ratio)` per zone; `{...:0}` when no PM.
- `cycle_count` — from the row (1 Testing/Seasonal, 2 others). Auto-off divides by this;
  must stay correct (a wrong value halves/doubles water).
- `soak_minutes`, `drip_duration` (seconds), `drip_runs_per_day`.
- `lawn_today` / `drip_today` — `dow` ∈ row days (or 'daily').
- `am_time` / `pm_time` — from row; `''` when not applicable.
- `schedule_7day` — `resolve_day` called per day over the next 7, each:
  `{date:'YYYY-MM-DD', dow, lawn_am_min, lawn_pm_min, drip_min, sessions}` where
  `lawn_*_min` are zone-1 minutes for that day (0 if not a run day), `sessions` ∈ {0,1,2}.

**3. `garden_next_run.yaml`** — replace both lawn/drip blocks with a scan over
`schedule_7day`: first future day with `lawn_am_min>0` → AM slot at that day's `am_time`
(+ consider `pm` slot the same day); drip → first future day with `drip_min>0` at its AM
time. Honors skip via the existing `garden_lawn_should_skip`/`drip` gates. All per-mode
day maps deleted.

**4. Dashboard 7-day table — `dashboards/tablet/outdoor.yaml`** — delete the
`lawn_total`/`lawn_zones`/`lawn_cycles`/`drip_dur`/`drip_runs`/`lawn_run`/`drip_run`
macros. Iterate `schedule_7day` directly. Lawn cell when `sessions==2`:
`✓ AM {{lawn_am_min}}m + PM {{lawn_pm_min}}m`; when 1 session: `✓ {{lawn_am_min}}m`; else
`—`. Zones cell from the shared formula. Footer notes single-pass / soak per mode.

**5. `garden_seasonal_irrigation.yaml`** — AM session dispatches the deep run
(`lawn_durations`, cycle&soak via existing `garden_lawn_irrigation`); PM session runs a
single-pass top-up using `lawn_durations_pm`. PM needs its own open/wait/close (the
existing `garden_lawn_irrigation` reads AM `lawn_durations`, and auto-off also reads AM) —
so add a small **`garden_lawn_irrigation_pm` script** mirroring `garden_ondemand_lawn`'s
pattern (sets `garden_ondemand_active` flag so auto-off skips, opens/waits pm seconds/closes
each zone single-pass, clears flag). PM is lawn-only (no drip).

**6. Docs** — README modes table + Seasonal section; `garden-irrigation-schedule`
knowledge leaf rewritten: the schedule is now ONE definition (the dict + Smart resolver)
with 3 dumb readers, not 4 duplicated derivations.

## Data flow

1. Mode selected. Profile resolves the row (Smart → resolver → row; Seasonal → month
   params). Shared formula yields per-zone AM + PM seconds. `schedule_7day` computed once.
2. Automations/next_run/dashboard read the profile attributes — none re-derive.
3. Seasonal AM → deep cycle&soak run + drip (Mon/Thu); PM → single-pass 60% top-up,
   lawn-only.

## Error handling / edge cases

- **`cycle_count` correctness** — verify per mode after refactor (auto-off divisor).
- **Testing flat zones** — `weighted:false` must bypass the 0.6 formula (stays 30/30/30).
- **Smart Oct drip-only** — resolver returns a drip-only marker → lawn 0, drip on.
- **Smart dynamic placeholder** — `dynamic_adjust` is a no-op now; must not alter output
  until soil sensors exist. No `sensor.garden_soil_moisture` today (confirmed absent).
- **schedule_7day cost** — one 7-iteration loop in a 30s/start-triggered sensor; cheap.
- **Behavior diff** — re-render all 6 modes post-refactor, diff vs the before-snapshot;
  only Intensive z2/z3 (1200→1260) may change. Anything else = regression.

## Testing / verification

- `just lint` (no local `hass` for `just check`; HA validates on reload).
- Push, reload (core + template + automation + script), check supervisor log.
- **Behavior diff:** render `lawn_durations`/`cycle_count`/`lawn_today`/`drip_today` for
  all 6 modes, compare to the before-snapshot. Intensive z2/z3 → 1260 expected; all else
  identical.
- Render `schedule_7day` for Seasonal + Smart; verify days/sessions/durations match the
  intended table.
- Functional: Seasonal AM deep run + PM 60% top-up (short helper values), confirm PM uses
  pm durations and runs single-pass.
- Dashboard: Playwright the 7-day table — Seasonal shows `AM + PM` cells; Smart/Eco/etc
  unchanged. Force-refresh lovelace cache first.
- next_run chips populate correctly for Seasonal (AM/PM) and a single-session mode.

## Also update

- `packages/areas/outdoor/garden/README.md` — unified model, modes table, Seasonal AM/PM.
- `garden-irrigation-schedule` knowledge leaf — rewrite: one definition + readers, not 4
  duplicated spots. Note the `schedule_7day` contract + Smart dynamic placeholder.

## Out of scope (YAGNI)

- The real soil-moisture / forecast / ET Smart logic (placeholder + seam only now).
- Collapsing Eco/Standard into one parametrized mode (migrate as-is).
- Dry-patch hardware diagnosis (coverage/soil — watch first, separate).
- Per-mode PM for non-Seasonal modes (only Seasonal has PM).
- Heat-triggered PM (every Jun–Aug watering day gets PM, per decision).
