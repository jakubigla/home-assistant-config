# Soil-Driven Drip (Smart Mode) — Design

**Date:** 2026-06-18
**Status:** Approved, pending implementation
**Area:** `packages/areas/outdoor/garden/`
**Supersedes (partially):** the skip-gate wiring of `garden_drip_should_skip` for **Smart mode only**. Other modes keep schedule + skip-gate drip. Builds on PR #35/#36 (the `garden_drip_soil_skip` helper + 3 probes as triggers).

## Problem / Motivation

Drip currently runs on a schedule (04:00 daily + Seasonal AM), with soil only able to *veto* a scheduled run (`binary_sensor.garden_drip_should_skip`). For drip beds this is backwards: drip is a slow soak to the root zone — plants want water *when the soil is dry*, not on a calendar.

Pivot: in **Smart mode**, drip becomes **demand-based** — it runs when the driest flowerbed crosses a dry threshold, with hysteresis, a configurable days-between cap, and rain/season/saturation safety vetoes. Lawn in Smart stays schedule-based (no lawn probe). All non-Smart modes are unchanged.

This rework also resolves the eval-order race observed in PR #35/#36 (a co-triggered template sibling reading `garden_drip_soil_skip` saw its stale `unknown` state in the same trigger pass). The new control logic reads the probe sensors **inline**, never the helper entity — so the race cannot occur by construction.

## Known facts (verified against current config)

- Modes: `Manual / Eco / Standard / Intensive / Testing / Smart / Seasonal` (`input_select.garden_irrigation_mode`).
- **Smart drip currently fires at 04:00** — `garden_scheduled_irrigation` excludes only `Manual` and `Seasonal`, so Smart flows through the schedule path today. The design must add Smart to the *drip* exclusion (lawn in Smart still schedule-fires).
- Probes (all report `%`, 0–100): `sensor.pergola_left_flowerbed_soil_moisture`, `sensor.pergola_right_flowerbed_soil_moisture`, `sensor.sona_flowerbed_soil_moisture`. sona is structurally wetter (more emitters).
- Run mechanism: `script.garden_drip_irrigation` opens `valve.drip_irrigation`, waits for auto-off (closed) or 90-min safety. Auto-off duration = `drip_duration` from `sensor.garden_irrigation_profile`, applied by `garden_valve_auto_off`.
- `sensor.garden_drip_last_run` exists (timestamp of last drip run) — reuse for the days-between cap.
- Night-guard convention (Seasonal): block 22:00–04:30.
- Calling a long script inline blocks the automation — use `script.turn_on` to fire-and-forget (knowledge leaf `script-call-blocks-automation`).

## Decisions (locked during brainstorming)

1. **Scope = Smart mode only.** Soil-driven drip is what Smart does. Lawn-in-Smart stays scheduled; non-Smart modes untouched. Reverting = switch the selector away from Smart.
2. **Hysteresis on the driest bed.** `START = 40` (driest `<` → run), `STOP = 60` (driest must climb `>` to re-arm). Dead-band 40–60 = no action. Prevents noise/lag thrash.
3. **Run duration = existing `drip_duration`** (no new duration knob). Frequency cap = new `input_number.garden_drip_min_days_between` (default 1 = max once/day; 2 = every other day; range 1–7). Cap measured from `sensor.garden_drip_last_run`. No intra-day min-interval.
4. **Arm state = `input_boolean.garden_drip_armed`** (persistent). Control automation reads the 3 probes **inline** (not the helper entity) → race-free. Helper `garden_drip_soil_skip` demoted to dashboard/debug; control logic never reads it.
5. **Notify on run + skip-with-reason, plus a status sensor** `sensor.garden_drip_soil_status` exposing armed/driest/days/blocking-reason.
6. **Smart drip is purely soil-driven** — no 04:00 fallback. If soil never drops below 40 in Smart, drip simply never runs.

## Architecture

### New helpers — `packages/areas/outdoor/garden/config.yaml`

| Entity | Type | Default / Range | Purpose |
|---|---|---|---|
| `input_boolean.garden_drip_armed` | input_boolean | `on` | Hysteresis arm state; persists across reloads |
| `input_number.garden_drip_min_days_between` | input_number | default 1, min 1, max 7, step 1 | Min whole days between soil-driven drip runs |

Inline constants (Jinja, in the control automation): `START = 40`, `STOP = 60`, `SAT = 85`. Season = May–Sep. Night-guard 22:00–04:30.

### Component 1 — Arm/disarm automation: `automations/garden_drip_soil_arm.yaml`

- **Trigger:** state change on any of the 3 probes; `homeassistant` start.
- **Action:** compute `driest` inline (min of valid probe readings); if `driest > STOP(60)` → `input_boolean.garden_drip_armed` **on**. No watering here. (Disarm is done by the run automation immediately after it fires, so the bed must recover above 60 before the next run.)
- `mode: single`.

### Component 2 — Run automation: `automations/garden_drip_soil_run.yaml`

- **Trigger:** state change on any of the 3 probes; time_pattern `/30` safety tick.
- **`mode: single`.**
- **Conditions (ALL):**
  - `input_select.garden_irrigation_mode == 'Smart'`
  - `input_boolean.garden_drip_armed == 'on'`
  - inline `driest < START(40)` (computed from the 3 probes in-automation — **no `garden_drip_soil_skip` read**)
  - `days_since_last_run >= min_days_between` — `(now() - sensor.garden_drip_last_run) >= N days`; if `last_run` unknown → treat as eligible
  - **not raining** (`binary_sensor.raining` off)
  - **in season** (month 5–9)
  - **saturation veto** inline: `wettest_pergola < SAT(85)` (max of pergola L/R valid; sona excluded)
  - **night-guard:** not (22:00–04:30)
  - drip valve not already `open`
- **Action:**
  1. `input_boolean.turn_off` `garden_drip_armed` (disarm — must recover >60 to re-arm)
  2. `script.turn_on` `script.garden_drip_irrigation` (fire-and-forget)
  3. notify run (persistent + `notify.mobile_app_iglofon`): "Drip ran — driest bed {{driest}}%"
- **Skip-with-reason branch:** if `mode==Smart and armed and driest<START` but a veto (rain / saturation / season / cap / night) blocked the run, notify skip-with-reason (mirrors `garden_seasonal_irrigation` notify style). Reason string from the status sensor's `blocking_reason`.

### Component 3 — Status sensor: `templates/garden_drip_soil_status.yaml`

Standalone template sensor (its OWN file / template block — NOT co-triggered with the control automations, so no race).

- **State:** one of `disarmed`, `armed_waiting` (armed, not yet dry), `ready` (armed + dry + all gates pass), `cooldown_days`, `vetoed_rain`, `vetoed_saturation`, `out_of_season`, `night`, `no_data`.
- **Attributes:** `driest`, `wettest`, `armed`, `days_since_run`, `min_days_between`, `next_eligible_days`, `blocking_reason`, `mode`.
- Dashboard-readable; the single place to see "why isn't Smart drip running right now".

### Component 4 — Smart mode wiring change

- `automations/garden_scheduled_irrigation.yaml`: add `Smart` to the **drip** exclusion only. Concretely, `run_drip` gains `and not is_state('input_select.garden_irrigation_mode','Smart')` (or the drip-bearing `choose` branches gate on mode != Smart). Lawn path in Smart is untouched — lawn still schedule-fires.
- `automations/garden_seasonal_irrigation.yaml`: already mode==Seasonal-gated, so Smart never reaches it. No change.

## Data flow

```
3 probes ──state change──┬─> garden_drip_soil_arm: driest>STOP(60) → armed=on
                         │
/30 safety tick ─────────┼─> garden_drip_soil_run (mode==Smart):
                         │     armed AND driest<START(40) AND days_since>=N
                         │     AND not raining AND in-season AND wettest_pergola<SAT
                         │     AND night-ok AND valve closed
                         │        → armed=off → script.turn_on garden_drip_irrigation → notify run
                         │        (else, if dry+armed but vetoed → notify skip w/ reason)
                         │
                         └─> garden_drip_soil_status (standalone): armed / driest / why-blocked
```

## Failure handling

| Scenario | Behavior |
|---|---|
| All 3 probes dead | `driest` undefined → run condition false → no run (fail-safe). Status = `no_data`. Lawn unaffected. |
| 1–2 probes dead | driest/wettest from valid ones (same filter as helper) |
| Valve offline | `script.garden_drip_irrigation` already aborts + notifies |
| Stuck-dry probe | days-between cap limits to 1 run / N days; arm-state (must recover >60) + saturation cap prevent runaway |
| Reload mid-cycle | `input_boolean` persists arm state; control reads probes inline (no unknown-on-reload race) |

## Testing / Verification

1. `/api/template` dry-run the inline `driest` + `wettest` + veto expression against live and mocked (all-dry / all-wet / one-dead / all-dead) values.
2. Set `input_select.garden_irrigation_mode = Smart`. Verify:
   - With beds wet (>60): `garden_drip_armed` on, status `armed_waiting`, no run.
   - Simulate a dry driest (<40): run automation fires → valve opens → armed flips off → run notification. (Simulate via a real dry reading or by temporarily lowering START for a test, then restore.)
   - After a run, confirm it won't re-fire until driest recovers >60 AND days_since >= N.
3. Regression: set mode back to `Standard` — confirm 04:00 schedule still fires drip (no regression from the exclusion change).
4. reload-after-push: `template.reload` + reload automations; check `/api/error_log`; verify entities live. HA tracks the current branch — merge to the pulled branch before live verification (see ops note below).

## Ops note (learned this session)

HA's git-pull addon tracks a specific branch. Config on a feature branch is NOT live until that branch is the pulled one (or merged into it). Live entity verification requires the change to be on the branch HA pulls. Reload alone is insufficient if the file isn't on the box.

Also: the skip/control sensors are **trigger-based** templates — they only evaluate on a trigger fire (probe change / `/30` / HA start), NOT on `template.reload`. After a reload they read `unknown` until the next trigger. The standalone status sensor should be a normal state-based template (evaluates on referenced-entity change) to avoid this.

## Out of scope

- Lawn soil control (no lawn probe — mower).
- ET / weather-forecast run adjustment (future `dynamic_adjust` hook).
- Variable run duration by dryness (capacitive probes too coarse to meter water).
- Removing `garden_drip_soil_skip` or the skip-gate sensors (still used by non-Smart modes + dashboard).

## Knowledge-layer follow-up

After implementation, update the `garden-irrigation-schedule` leaf: Smart mode now drives drip by soil demand (hysteresis START=40/STOP=60, days-between cap, inline probe reads, `input_boolean.garden_drip_armed`), distinct from the skip-gate model used by Eco/Standard/Intensive/Seasonal. Note the trigger-based-template "unknown until first trigger" gotcha and the inline-read race fix. Invoke `knowledge-author`.
