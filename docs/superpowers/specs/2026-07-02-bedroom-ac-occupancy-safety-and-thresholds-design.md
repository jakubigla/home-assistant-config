# Bedroom AC: occupancy-gated safety timeout + threshold/sensor recalibration

**Date:** 2026-07-02
**Area:** `packages/areas/first-floor/bedroom/`

## Problem

Two coupled defects surfaced from a real complaint ("AC reached 24°C and was still
running; this morning felt too cold, and it shouldn't"):

1. **The AC never shuts off on temperature.** `bedroom_ac_evening_cooldown_off_target_reached`
   has `last_triggered = None` — it has *never* fired since deploy. Its off-threshold
   (`sensor.bedroom_temperature <= 23.1°C`) is physically unreachable: the sensor it reads
   is the **FP300** (Matter mmWave presence unit), whose temp probe runs **~1.3°C hot**
   (measured mean over 141 paired samples; range 0.4–2.4°C). Over 5 days the FP300 never
   dropped below 26.7°C; the true room air (hygro) never below 24.5°C. So the only thing
   that ever stops the AC is the **3h safety timeout** — visible as a run of exactly-3.0h
   cool sessions in history.

2. **The 3h safety timeout fires even while occupied.** It is meant as a backstop for a
   stuck sensor / empty room, but currently applies unconditionally. Combined with #1 it
   became the *primary* off mechanism, chopping cooling into 3h blocks regardless of whether
   someone is asleep in the room.

**Why this morning felt cold (root cause, evidenced):** on a typical night (06-29) the AC
had off-gaps and the room *recovered* to ~27.5°C (hygro) by 05:14 before waking. Last night
(07-01→02) the AC ran near-continuously 21:00→06:06 (three back-to-back ~3h sessions), so
the hygro rode *down* all night and hit its **coldest point, 25.0°C, at 05:43** — right at
waking, with no recovery. Prior nights' coldest point was around midnight (asleep). Cold at
the wrong time = felt.

## Goals

- **Safety timeout only fires when the bedroom is empty.** When occupied, off is
  temperature-based only (user decision: option A — do not add a time cap while occupied).
- **Make temperature-based off actually reachable and accurate**, using the most reliable
  temp signal available, degrading safely when it drops out.
- Stop the pre-dawn over-cool.

## Non-goals

- No change to *on* timing window (21:00–23:00 arm) or the on-automation's trigger/level-check
  structure — that was already fixed and is correct.
- No dashboard work. No new occupancy plumbing (the latch already exists).

## Sensor decision (evidenced)

Three temperature sources exist; none is reliable alone:

| Source | Entity | Protocol | Cadence | Bias / issue |
|---|---|---|---|---|
| FP300 | `sensor.bedroom_fp300_temperature` (aliased by `sensor.bedroom_temperature`) | **Matter** (mains) | rigid **58 min** | reads **~1.3°C hot** (electronics self-heat); always available |
| Hygro | `sensor.bedroom_hygro_temperature` | Zigbee (battery, 100% / 3067 mV) | **~25 min** median, max gap 110 min | true free-air temp; battery device can go **silent-stale** (never flips to `unavailable`) |
| AC probe | `climate.bedroom` `current_temperature` | Tuya | only on AC activity | reads its own **return/intake air**, integer-only → circular, unusable for control |

**Decision:** hygro when fresh, FP300 (bias-corrected) as fallback. Hygro is the most
accurate + responsive control signal; FP300 guarantees availability when the battery sensor
goes quiet. The 3h empty-room safety timeout remains the ultimate backstop if both fail.

## Design

### 1. Control-temp overlay (extend existing sensor)

`sensor.bedroom_temperature` is already an overlay whose stated purpose is "swap the source
to change which physical sensor drives bedroom temperature; all AC automations read
`sensor.bedroom_temperature`, never the raw source." Extend that overlay's `state` template
(no new entity, no automation entity_id changes):

```
state:
  hygro   if hygro is a valid number AND its reading is < 45 min old
  else    (fp300 - 1.3)   # bias-corrected fallback, rounded to 1 decimal
availability:
  true if EITHER hygro (fresh) OR fp300 is a valid number
attributes:
  source: "hygro" | "fp300_fallback"   # for debugging which path is live
```

Freshness = `now() - states.sensor.bedroom_hygro_temperature.last_updated < 45 min`.
The 45-min window comfortably covers the hygro's ~25-min median cadence (and its observed
110-min max gap will correctly trip the fallback — desired). Keeps the existing overlay
contract intact: automations keep reading `sensor.bedroom_temperature`.

### 2. Recalibrated thresholds

Because the overlay now yields **true room-air temp** (~24.5–30°C observed band), thresholds
move into the reachable range:

| Automation | Old | New | Rationale |
|---|---|---|---|
| `..._cooldown_off_target_reached` | `<= 23.1` (never fires) | **`<= 25.0` for 5 min** | Reachable (~3% of samples); stops before the 24.5°C over-cool that chilled the user. |
| `..._cooldown_on` setpoint | `22` | **`23`** | Below the 25.0 off so the AC still pulls toward target; less compressor overshoot. |
| `..._cooldown_on` on-threshold | `> 25` (FP300) | **`> 26.5`** (control temp) | ~1.5°C hysteresis above off; 26.5 real = genuinely warm. Prior `>25` on FP300 ≈ `>23.7` real — too eager. |

On/off keep a clean 1.5°C hysteresis band (off 25.0 ↔ on 26.5), preventing rapid cycling.

### 3. Occupancy-gated safety timeout

`bedroom_ac_safety_timeout.yaml` (`automation.bedroom_ac_safety_max_runtime`) becomes:
after 3h in cool mode, turn AC off **only if the bedroom is empty**; if occupied, do nothing
(let the temperature-based off handle it).

- Occupancy source: **`input_boolean.bedroom_occupied`** — the authoritative, debounced
  latch from `bedroom_occupancy_state_machine`. It rides out 60 s mmWave still-gaps (so
  lying still in bed never reads empty), survives HA restart/reload (startup-sync branch),
  and self-heals via a 30-min watchdog. Do **not** use raw `binary_sensor.bedroom_occupancy`
  (flaps during stillness) — using it would let the safety timeout fire on a sleeping person.
- Keep `mode: restart` (timer resets on each real re-entry to cool) and the `state to: cool`
  trigger unchanged.
- Add a mid-sequence condition after the 3h delay: `input_boolean.bedroom_occupied` is
  `off`. If occupied at the 3h mark, the automation simply ends without turning off.

**Edge case — hygro dies while occupied:** if the control overlay is on FP300-fallback and
the room is occupied, temperature-based off still works (fallback is bias-corrected, so
`<= 25.0` remains meaningful). If *both* sensors fail, the overlay goes `unavailable`, temp-off
can't fire — but an occupied person can always turn the AC off manually / via HomeKit, and on
becoming empty the 3h backstop applies. Acceptable.

## Files touched

- `packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`
  — extend overlay to hygro-fresh / FP300-fallback blend + `source` attribute.
- `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml`
  — off-threshold `23.1 → 25.0` (keep `for: 5min`, keep `state: cool` guard).
- `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`
  — on-threshold `25 → 26.5` (trigger + condition), setpoint `22 → 23`, refresh description.
- `packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`
  — add `input_boolean.bedroom_occupied == off` gate after the 3h delay; refresh description.

## Verification

1. `uv run yamllint .` + `just check` (HA config check) pass.
2. Push to feature branch → PR → reload HA core config → check logs (no errors).
3. `sensor.bedroom_temperature` now reports ~true room temp (≈ hygro when fresh); flip a
   test by checking `source` attribute. Confirm value tracks hygro, not FP300+1.3.
4. Confirm `automation.bedroom_ac_evening_cooldown_off_target_reached` can now trigger:
   template-render its off-condition against current control temp; it should be within a
   plausible night's reach (≤25.0), unlike 23.1.
5. Trace/logbook check over the next night: temp-off fires (not the 3h cap) when occupied;
   3h cap only fires when `bedroom_occupied` is off.
6. Capture the sensor-bias + unreachable-threshold gotcha via `knowledge-author` if not
   already covered by the existing `numeric-state-trigger-edge-not-level` leaf.

## Regressions considered

- **Wrong-sensor swap breaks other consumers:** overlay contract says *all* AC autos read
  `sensor.bedroom_temperature`; grep confirmed no automation reads the raw FP300/hygro
  directly for AC control. Extending the overlay is transparent to them.
- **Hygro stale mid-cool:** fallback keeps off-logic working; verified bias correction (1.3)
  from real paired data, not a guess.
- **`mode: restart` + occupancy gate:** an occupant leaving resets nothing (timer keyed on
  cool state, not occupancy); on the next 3h tick after they leave, the empty condition is
  now true → off. No thrash (see `restart-mode-pulse-thrash` — trigger is a single state
  change to `cool`, not a flappy source).
