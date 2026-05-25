# Garden one-off irrigation run — design

## Problem

The garden has a recurring schedule (Smart mode → Tue/Fri lawn + drip at 04:00) and
immediate "Run Scripts" buttons on the tablet Outdoor view. There is no way to
schedule a **single, time-delayed** run — e.g. "run the lawn once at 04:00 tomorrow"
without firing it now or editing the recurring schedule.

This adds a dashboard control to arm a one-off run: pick what (Lawn / Drip / Full)
and when (date + time), tap Schedule. It fires once at that time, then auto-disarms.
The recurring Tue/Fri schedule is untouched.

## Decisions (locked during brainstorm)

- **Time input:** `input_datetime` picker (date + time) — any day, any hour.
- **Run type:** selectable Lawn / Drip / Full, parity with the immediate buttons.
- **Rain skip:** **always run.** The one-off ignores `garden_lawn_should_skip` /
  `garden_drip_should_skip`. User decides based on weather when arming.
- **Arming:** explicit. Tap Schedule → armed. Fires once → auto-disarms. Cancel
  button disarms early. Setting the picker alone does nothing while disarmed.

## Architecture

Three input helpers + one automation, wired to the three existing scripts. All
native HA — survives restarts, no custom timers (a script `delay` would be lost on
reload, which is why that approach was rejected).

```
input_datetime.garden_oneoff_at   ─┐
input_select.garden_oneoff_type    ├─► automation garden_oneoff_run ─► script.garden_{lawn,drip,full}_irrigation
input_boolean.garden_oneoff_armed ─┘                                └─► input_boolean.garden_oneoff_armed = off
```

### Components

**1. Helpers — `packages/areas/outdoor/garden/config.yaml`** (next to `garden_irrigation_mode`)

```yaml
input_datetime:
  garden_oneoff_at:
    name: Garden One-off Run At
    has_date: true
    has_time: true
input_select:
  garden_oneoff_type:
    name: Garden One-off Type
    options: [Lawn, Drip, Full]
    icon: mdi:sprinkler-variant
input_boolean:
  garden_oneoff_armed:
    name: Garden One-off Armed
    icon: mdi:timer-sand
```

**2. Automation — `packages/areas/outdoor/garden/automations/garden_oneoff_run.yaml`**

- Trigger: `platform: time`, `at: input_datetime.garden_oneoff_at` (HA native datetime
  trigger — re-evaluates whenever the picker changes; fires at that wall-clock time).
- Condition: `input_boolean.garden_oneoff_armed` is `on` (gate — editing the picker
  while disarmed is a no-op).
- Action: `choose` on `input_select.garden_oneoff_type` → `script.turn_on` the matching
  script (`garden_lawn_irrigation` / `garden_drip_irrigation` / `garden_full_irrigation`),
  then `input_boolean.turn_off` armed.
- No rain-skip condition (always-run decision).
- Filename + `id` follow the `{area}_{action}_{trigger}` convention.

**3. Dashboard — `dashboards/tablet/outdoor.yaml`**, Garden section, new "Schedule One-off"
block **after** the existing "Run Scripts" buttons (which stay, unchanged):

- `mushroom-select-card` → `input_select.garden_oneoff_type` (What).
- native `entities` card → `input_datetime.garden_oneoff_at` (When). Mushroom has no
  datetime card, so the native card is used deliberately.
- `horizontal-stack` of two `mushroom-template-card`s:
  - **Schedule** — `tap_action` turns armed `on`. Primary text switches "Schedule" →
    "Armed"; secondary shows `<type> @ <day HH:MM>` when armed, "Tap to arm" otherwise;
    icon_color grey → orange.
  - **Cancel** — turns armed `off`.
- One always-visible status button switching content (not a mutually-exclusive
  visibility pair) — per the mushroom-visibility gotcha.

## Data flow

1. User sets `garden_oneoff_type` + `garden_oneoff_at`, taps **Schedule** →
   `garden_oneoff_armed = on`.
2. Wall clock reaches `garden_oneoff_at` → time trigger fires.
3. Armed condition passes → `choose` runs the matching script → armed set `off`.
4. Dashboard reflects idle again. Cancel before fire-time disarms early.

## Error handling / edge cases

- **Disarmed picker edits:** no-op (armed gate).
- **Past time while armed:** native time trigger only fires forward; a past time never
  fires. User re-picks a future time. (Acceptable — matches HA datetime-trigger semantics.)
- **HA restart while armed:** all three helpers persist; the time trigger re-arms on the
  same `input_datetime`. Survives.
- **Valve conflict:** the existing auto-off + cleanup automations and sequential scripts
  handle concurrency. The one-off reuses the same scripts, so no new valve logic.
- **Rain:** intentionally ignored (always-run).

## Testing / verification

- `just check` (HA config valid) + `just lint`.
- Push branch, reload HA (`homeassistant.reload_core_config` + reload automations &
  template entities), check logs for errors.
- Functional: set picker to now+2 min, type=Lawn, tap Schedule → confirm armed chip,
  watch the script fire and armed auto-off.
- Playwright visual check on `/wall-tablet` Outdoor view (dashboard-validate rule).

## Also update

- `packages/areas/outdoor/garden/README.md` — add the three helpers + automation to
  Entities and the File Index.
- The `garden-irrigation-schedule` knowledge leaf is **not** touched — the one-off
  does not change the day-of-week (`dow`) schedule logic.

## Out of scope (YAGNI)

- Multiple queued one-offs (single slot only).
- Rain-aware one-off (explicitly always-run).
- Phone dashboard (tablet only for now).
- Per-zone one-off (reuses whole-lawn script).
