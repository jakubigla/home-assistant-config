# Garden on-demand per-zone lawn run — design

## Problem

The garden has recurring/profile-driven lawn runs (`garden_lawn_irrigation`, cycle &
soak from `sensor.garden_irrigation_profile`) and a time-delayed one-off
(`garden_oneoff_*`). Neither lets the user water **a single lawn zone, right now, for
an arbitrary duration**. Tapping a zone valve directly in HomeKit works, but
`garden_valve_auto_off` then closes it after the **profile** duration — not a
user-chosen time — so there is no clean "run zone 2 for 8 minutes now" control.

This adds dashboard buttons (tablet + phone) to run any single lawn zone on demand
for a duration set by a shared slider. Profile-driven runs, drip, and the one-off are
untouched.

## Decisions (locked during brainstorm)

- **Duration model:** one shared `input_number` slider (minutes). Tap a zone button →
  runs that zone for the slider's minutes.
- **Slider range:** 1–25 min, step 1. Stays under the 30-min max-open watchdog cap, so
  no safety-cap change is needed.
- **Auto-off conflict:** flag + skip. An `input_boolean.garden_ondemand_active` flag is
  set while an on-demand run owns the valve; `garden_valve_auto_off` skips lawn valves
  while the flag is on, so the slider duration wins instead of the profile duration.
- **Concurrency:** one at a time. The script is `mode: single`; tapping a second zone
  mid-run is ignored. (Sprinkler controller + water pressure favor one zone anyway.)
- **Zone selection:** one parametrized script with a `zone` field (`1`/`2`/`3`), not
  three near-duplicate scripts.
- **Dashboards:** both tablet (`dashboards/tablet/outdoor.yaml`, Garden section) and
  phone (`dashboards/phone/rooms/garden.yaml`).
- **Rain skip:** none — on-demand always runs. User decides based on weather.

## Architecture

```
input_number.garden_ondemand_minutes ─┐
                                       ├─► script.garden_ondemand_zone(zone)
zone button (tablet + phone) ──────────┘        │
                                                 ├─► input_boolean.garden_ondemand_active = on
                                                 ├─► valve.open_valve  zone N
                                                 ├─► delay  <slider> min
                                                 ├─► valve.close_valve zone N
                                                 └─► input_boolean.garden_ondemand_active = off

garden_valve_auto_off ── skips lawn valves while garden_ondemand_active is on
garden_valve_startup_close ── also clears garden_ondemand_active on HA start
garden_valve_max_open_watchdog ── unchanged 30-min backstop (slider max 25 < 30)
```

All native HA, no custom timers.

### Components

**1. Helpers — `packages/areas/outdoor/garden/config.yaml`** (next to `garden_oneoff_*`)

```yaml
input_number:
  garden_ondemand_minutes:
    name: Garden On-demand Minutes
    min: 1
    max: 25
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline

input_boolean:
  garden_ondemand_active:
    name: Garden On-demand Active
    icon: mdi:water-pump
```

`garden_ondemand_minutes` persists its last value across restarts (input_number
default), so the slider keeps the last duration.

**2. Script — `packages/areas/outdoor/garden/scripts/garden_ondemand_zone.yaml`**

- `mode: single` (one-at-a-time; second tap mid-run ignored).
- `fields.zone` — `1` / `2` / `3`; resolves to `valve.lawn_sprinkler_zone_{{ zone }}`.
- Sequence:
  1. Abort + persistent-notification if the target zone valve is `unavailable`
     (reuse the offline-abort pattern from `garden_lawn_irrigation`). Without it the
     `valve.open_valve` is a silent no-op on an offline controller.
  2. `input_boolean.turn_on garden_ondemand_active`.
  3. `valve.open_valve` the target zone.
  4. `delay: { minutes: {{ states('input_number.garden_ondemand_minutes') | int }} }`.
  5. `valve.close_valve` the target zone.
  6. `input_boolean.turn_off garden_ondemand_active`.
- The flag is turned off in a final step that runs even on normal completion. (A crash
  mid-run is covered by the startup-clear + watchdog below.)

**3. Auto-off skip — `packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml`**

Add a gate so the profile timer does not also race to close an on-demand valve:

```yaml
action:
  - if:
      - "{{ trigger.id == 'lawn'
            and is_state('input_boolean.garden_ondemand_active', 'on') }}"
    then:
      - stop: "On-demand run owns this lawn valve — auto-off skipped"
  # ...existing duration logic unchanged below...
```

Drip (`trigger.id == 'drip'`), profile-driven lawn runs, and HomeKit-manual lawn opens
are unaffected: the gate only triggers when the on-demand flag is on.

**4. Flag-clear safety — `packages/areas/outdoor/garden/automations/garden_valve_startup_close.yaml`**

Add `input_boolean.turn_off garden_ondemand_active` to the startup sequence, so a crash
or restart mid-run cannot leave the flag stuck `on` (which would otherwise make
profile-driven lawn runs skip auto-off indefinitely). The existing startup valve-close
already handles orphaned-open valves.

**5. Watchdog — unchanged.** `garden_valve_max_open_watchdog` force-closes any valve
open > 30 min. Slider max is 25 min, so a healthy on-demand run never trips it; a
crashed run (flag skips auto-off) is still backstopped within 5 min of crossing 30 min.

**6. Dashboards** — new "Run a zone now" block in both views, after the existing
irrigation controls:

- One `input_number` slider card → `input_number.garden_ondemand_minutes` (How long).
- `horizontal-stack` of three `mushroom-template-card`s: **Zone 1 / Zone 2 / Zone 3**.
  - `tap_action` → `script.turn_on script.garden_ondemand_zone` with `data: { zone: N }`.
  - Each card switches content (not a visibility pair, per the mushroom-visibility
    gotcha): when its valve is `open`, icon_color → blue and secondary → "Running";
    otherwise grey + "{{ slider }} min".
- Tablet: `dashboards/tablet/outdoor.yaml`, Garden section.
- Phone: `dashboards/phone/rooms/garden.yaml` (currently a single status card; the
  block is added there).

## Data flow

1. User sets `garden_ondemand_minutes`, taps **Zone N**.
2. Script (single): valve-unavailable check → flag on → open zone N → wait slider min →
   close zone N → flag off.
3. `garden_valve_auto_off` fires on the valve-open but the gate sees the flag and stops,
   leaving the on-demand script as the sole closer.
4. Dashboard zone card shows "Running" (valve open) → back to idle on close.

## Error handling / edge cases

- **Second zone tapped mid-run:** ignored (`mode: single`).
- **Target valve unavailable:** abort + persistent notification; flag never set.
- **HA restart mid-run:** `garden_valve_startup_close` clears the flag and closes
  orphaned valves; max-open watchdog is the secondary backstop.
- **Flag stuck on (crash before step 6):** cleared on next HA start; meanwhile the
  watchdog still force-closes the valve at 30 min.
- **Slider untouched:** uses its persisted last value.
- **Rain:** intentionally ignored (always-run).

## Testing / verification

- `just check` (HA config valid) + `just lint`.
- Push branch, reload HA (`homeassistant.reload_core_config` + reload automations,
  scripts, template entities), check logs for errors.
- Functional: set slider to 1 min, tap Zone 2 → confirm flag on, valve 2 opens, "Running"
  on the card, auto-off does NOT close it early, script closes at ~1 min, flag off.
- Confirm a profile-driven lawn run still auto-closes at profile duration (flag off path
  unchanged).
- Tap a second zone mid-run → confirm ignored.
- Playwright visual check on `/wall-tablet` Outdoor view and the phone garden room
  (dashboard-validate rule).

## Also update

- `packages/areas/outdoor/garden/README.md` — add the two helpers, the script, and the
  auto-off/startup changes to Entities and the File Index. Run `/ha-area-docs`.
- `garden-irrigation-schedule` knowledge leaf is **not** touched — on-demand does not
  change the dow/profile schedule logic.

## Out of scope (YAGNI)

- Per-zone separate sliders (one shared slider).
- Queueing a second zone (single-slot, ignore).
- Preset duration buttons (slider only).
- Drip on-demand (lawn zones only).
- Rain-aware on-demand (always-run).
- Raising the watchdog cap (slider capped at 25 < 30 min).
