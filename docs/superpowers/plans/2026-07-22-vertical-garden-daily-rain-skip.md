# Vertical Garden Daily Watering + Rain Skip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vertical garden (zone 3) waters every day at 06:15 unless it's raining; a 2-day guarantee overrides the rain skip so wet spells can't leave the pockets dry.

**Architecture:** Inline rain gate in the existing `garden_vertical_scheduled` automation (no new entities). `input_number.garden_vertical_days_between` is repurposed from cadence knob to rain-guarantee ceiling (7 → 2). `sensor.garden_vertical_next_run` becomes "next 06:15 slot". Spec: `docs/superpowers/specs/2026-07-22-vertical-garden-daily-rain-skip-design.md`.

**Tech Stack:** Home Assistant YAML (packages), Jinja2 templates, Mushroom dashboard cards.

## Global Constraints

- This is an HA config repo — no unit test framework. Per-task verification = `uv run yamllint <files>` + `just check` (HA config check against live instance). Live behavior verified in Task 4 after push.
- HA auto-pulls the current git branch (`feat/irrigation-two-zones-vertical-garden`). Local edits are NOT live until pushed. Never push to `main`.
- Run git from the working directory; do NOT use `git -C`.
- Sandbox blocks `homeassistant.local` — every `curl` to HA needs `dangerouslyDisableSandbox: true`. Env vars `$HA_URL`, `$HA_TOKEN` are preloaded (never read `.env`).
- `initial:` on `input_number` is NOT applied on reload — live value must be set explicitly via `input_number/set_value` (Task 4).
- Skip signals must match lawn/drip exactly: `binary_sensor.raining` on OR `sensor.garden_rain_accumulation >= 3` mm. No soil gate for vertical.
- Guarantee comparison uses `guarantee_days - 0.05` slack (stamp-at-open time would otherwise defer the guarantee a day per cycle).
- Keep the 06:15 trigger time (Seasonal September AM session fires 06:00; 06:15 lets it start first so the idle-wait handles it).

---

### Task 1: Rain gate + guarantee in `garden_vertical_scheduled`

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_vertical_scheduled.yaml`

**Interfaces:**
- Consumes: `binary_sensor.raining`, `sensor.garden_rain_accumulation`, `sensor.garden_vertical_last_run`, `input_number.garden_vertical_days_between` (all existing live entities).
- Produces: automation `garden-vertical-scheduled` that runs `script.garden_vertical_irrigation` daily unless rain-skipped. No other file reads this automation.

- [ ] **Step 1: Replace the file content**

Replace the ENTIRE file with:

```yaml
---
alias: Garden Vertical Scheduled Run
description: >
  Daily vertical garden watering (zone 3, drip). Checks daily at 06:15
  (NOT 06:00 — Seasonal's September AM session fires at 06:00 and
  aborts if a zone valve is already open; 06:15 lets it start first so
  we wait it out instead of killing it): runs every day unless it is
  raining now or rain accumulation >= 3mm (same signals the lawn/drip
  skip sensors use). The rain skip has a floor — when the last run is
  at least garden_vertical_days_between (2) days old the run fires
  anyway: the pockets get little rain even in wet spells, so a rain
  streak must not leave them dry. No soil gate — no probes in the
  pockets. Duration input_number.garden_vertical_minutes (20, tunable).
  Gates: Manual mode off, in season (May–Sep), controller idle (waits
  out a still-running 04:00/05:00 lawn+drip session). The -0.05 d slack
  keeps the stamp-at-open time from deferring the guarantee by a day
  each cycle.
id: garden-vertical-scheduled

mode: single

trigger:
  - platform: time
    at: "06:15:00"

condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.garden_irrigation_mode
        state: "Manual"
  - condition: template
    value_template: "{{ now().month >= 5 and now().month <= 9 }}"

action:
  - variables:
      bad: "{{ ['unknown', 'unavailable', 'none', ''] }}"
      last_run: "{{ states('sensor.garden_vertical_last_run') }}"
      guarantee_days: >
        {{ states('input_number.garden_vertical_days_between') | int(2) }}
      days_since: >
        {{ ((now() - as_datetime(last_run)).total_seconds() / 86400)
           if last_run not in bad else 999 }}
      rain_skip: >
        {{ is_state('binary_sensor.raining', 'on')
           or states('sensor.garden_rain_accumulation') | float(0) >= 3 }}
  - if:
      - "{{ rain_skip and days_since | float(0) < guarantee_days - 0.05 }}"
    then:
      - action: logbook.log
        data:
          name: Garden Vertical Irrigation
          message: >
            Skipped — rain ({{ states('sensor.garden_rain_accumulation')
            | float(0) | round(1) }} mm accumulated), last run
            {{ days_since | float(0) | round(1) }} d ago
            (< {{ guarantee_days }} d guarantee).
      - stop: "Raining — vertical garden skipped, guarantee not due"
  # Wait out any in-progress irrigation — the Tuya controller runs one valve
  # at a time, and the zone-open helper is shared with the lawn zones. A
  # Seasonal 05:00 lawn+drip session can run past 06:45.
  - wait_template: >
      {{ expand('valve.lawn_sprinkler_zone_1',
                'valve.lawn_sprinkler_zone_2',
                'valve.lawn_sprinkler_zone_3',
                'valve.drip_irrigation')
         | selectattr('state', 'eq', 'open') | list | count == 0
         and expand('script.garden_lawn_irrigation',
                    'script.garden_full_irrigation',
                    'script.garden_drip_irrigation',
                    'script.garden_lawn_irrigation_pm',
                    'script.garden_ondemand_lawn')
            | selectattr('state', 'eq', 'on') | list | count == 0 }}
    timeout:
      minutes: 90
  - if:
      - "{{ not wait.completed }}"
    then:
      - action: persistent_notification.create
        data:
          notification_id: garden_vertical_scheduled_busy
          title: Vertical garden run skipped
          message: >
            Irrigation was still running 90 min after the 06:15 check —
            vertical garden run skipped today, will retry tomorrow.
      - stop: "Controller busy past timeout"
  # Fire-and-forget so this automation doesn't sit running for the whole
  # watering (see script-call-blocks-automation).
  - action: script.turn_on
    target:
      entity_id: script.garden_vertical_irrigation
  - action: logbook.log
    data:
      name: Garden Vertical Irrigation
      message: >
        Scheduled vertical garden run started —
        {{ states('input_number.garden_vertical_minutes') | int(20) }} min,
        {{ 'first run' if days_since | float(0) > 900
           else (days_since | float(0) | round(1) | string) + ' d since last'
        }}{{ ' (rain-guarantee run)' if rain_skip else '' }}.
```

What changed vs the old file: the `days_between` cadence stop (`days_since < days_between - 0.05` → stop "not due yet") is GONE; new `rain_skip` variable; new skip branch fires only when `rain_skip` AND guarantee not reached, and logs the skip to logbook; start logbook message tags rain-guarantee runs. Trigger, conditions, idle-wait, busy-notification, fire-and-forget are byte-identical to before.

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_vertical_scheduled.yaml`
Expected: no output (clean).

- [ ] **Step 3: HA config check**

Run: `just check`
Expected: exits 0, no errors mentioning `garden_vertical`.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_vertical_scheduled.yaml
git commit -m "feat(garden): vertical garden waters daily, skips rain, 2-day guarantee"
```

---

### Task 2: Repurpose guarantee helper + next-run sensor

**Files:**
- Modify: `packages/areas/outdoor/garden/config.yaml:63-81`
- Modify: `packages/areas/outdoor/garden/templates/garden_next_run.yaml:16-30,112-143`

**Interfaces:**
- Consumes: nothing from Task 1 (same entity ids, changed semantics only).
- Produces: `input_number.garden_vertical_days_between` (id unchanged, display name "Garden Vertical Rain Guarantee Days", `initial: 2`); `sensor.garden_vertical_next_run` = next 06:15 slot (timestamp). Dashboards (Task 3) read both.

- [ ] **Step 1: Edit `config.yaml` — comment, name, initial**

Replace:

```yaml
  # Vertical garden (valve.lawn_sprinkler_zone_3 — repurposed after the lawn
  # shrank to two zones). Baseline cadence under test: 20 min every 7 days;
  # both knobs tunable from the dashboard while calibrating.
  garden_vertical_minutes:
    name: Garden Vertical Minutes
    min: 5
    max: 60
    step: 1
    initial: 20
    unit_of_measurement: min
    icon: mdi:timer-outline
  garden_vertical_days_between:
    name: Garden Vertical Days Between
    min: 1
    max: 14
    step: 1
    initial: 7
    unit_of_measurement: d
    icon: mdi:calendar-clock
```

with:

```yaml
  # Vertical garden (valve.lawn_sprinkler_zone_3 — repurposed after the lawn
  # shrank to two zones). Waters DAILY at 06:15 unless raining;
  # days_between is the rain-streak guarantee ceiling — a last run this
  # many days old fires even in rain (pockets get little rain). Both
  # knobs tunable from the dashboard. NOTE: initial is not applied on
  # reload — live value set via input_number.set_value at rollout.
  garden_vertical_minutes:
    name: Garden Vertical Minutes
    min: 5
    max: 60
    step: 1
    initial: 20
    unit_of_measurement: min
    icon: mdi:timer-outline
  garden_vertical_days_between:
    name: Garden Vertical Rain Guarantee Days
    min: 1
    max: 14
    step: 1
    initial: 2
    unit_of_measurement: d
    icon: mdi:calendar-clock
```

- [ ] **Step 2: Edit `garden_next_run.yaml` — drop stale triggers**

The vertical sensor will no longer read `sensor.garden_vertical_last_run` or `input_number.garden_vertical_days_between`, and no other sensor in this file reads them either. In the `trigger:` block replace:

```yaml
      - input_select.garden_oneoff_type
      - sensor.garden_vertical_last_run
      - input_number.garden_vertical_days_between
```

with:

```yaml
      - input_select.garden_oneoff_type
```

(The `/5` time_pattern still rolls the vertical chip past 06:15.)

- [ ] **Step 3: Edit `garden_next_run.yaml` — vertical sensor state**

Replace the `Garden Vertical Next Run` sensor's comment + state (lines 116-143):

```yaml
    # Vertical garden cadence is days-since-based (garden_vertical_scheduled
    # checks daily at 06:15), so next run = last run + days_between at the
    # next 06:15 slot — no 7-day schedule scan. A one-off of type Vertical
    # takes priority like the lawn/drip chips.
    state: >
      {% set mode = states('input_select.garden_irrigation_mode') %}
      {% set bad = ['unknown', 'unavailable', 'none', ''] %}
      {% set oneoff = is_state('input_boolean.garden_oneoff_armed', 'on') %}
      {% set ootype = states('input_select.garden_oneoff_type') %}
      {% set ooat = state_attr('input_datetime.garden_oneoff_at', 'timestamp') %}
      {% if oneoff and ootype == 'Vertical'
            and ooat is number and ooat > now().timestamp() %}
        {{ as_datetime(ooat) | as_local }}
      {% elif mode == 'Manual' or not (now().month >= 5 and now().month <= 9) %}
        none
      {% else %}
        {% set last = states('sensor.garden_vertical_last_run') %}
        {% set dbetween = states('input_number.garden_vertical_days_between') | int(7) %}
        {% set today6 = now().replace(hour=6, minute=15, second=0, microsecond=0) %}
        {% set next6 = today6 if now() < today6 else today6 + timedelta(days=1) %}
        {% if last in bad %}
          {{ next6.isoformat() }}
        {% else %}
          {% set due = (as_datetime(last) | as_local + timedelta(days=dbetween))
             .replace(hour=6, minute=15, second=0, microsecond=0) %}
          {{ (due if due > now() else next6).isoformat() }}
        {% endif %}
      {% endif %}
```

with:

```yaml
    # Vertical garden waters DAILY at 06:15 (rain skip is a same-day
    # go/no-go the automation checks at fire time — not predictable
    # ahead, so the chip always shows the next 06:15 slot). A one-off
    # of type Vertical takes priority like the lawn/drip chips.
    state: >
      {% set mode = states('input_select.garden_irrigation_mode') %}
      {% set oneoff = is_state('input_boolean.garden_oneoff_armed', 'on') %}
      {% set ootype = states('input_select.garden_oneoff_type') %}
      {% set ooat = state_attr('input_datetime.garden_oneoff_at', 'timestamp') %}
      {% if oneoff and ootype == 'Vertical'
            and ooat is number and ooat > now().timestamp() %}
        {{ as_datetime(ooat) | as_local }}
      {% elif mode == 'Manual' or not (now().month >= 5 and now().month <= 9) %}
        none
      {% else %}
        {% set today6 = now().replace(hour=6, minute=15, second=0, microsecond=0) %}
        {{ (today6 if now() < today6 else today6 + timedelta(days=1)).isoformat() }}
      {% endif %}
```

- [ ] **Step 4: Lint + config check**

Run: `uv run yamllint packages/areas/outdoor/garden/config.yaml packages/areas/outdoor/garden/templates/garden_next_run.yaml && just check`
Expected: yamllint clean; config check exits 0.

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/config.yaml packages/areas/outdoor/garden/templates/garden_next_run.yaml
git commit -m "feat(garden): days_between becomes rain-guarantee knob; next-run chip shows next 06:15"
```

---

### Task 3: Wording — script/profile comments + dashboard chips

**Files:**
- Modify: `packages/areas/outdoor/garden/scripts/garden_vertical_irrigation.yaml:4-12`
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml:18-20`
- Modify: `dashboards/tablet/outdoor.yaml:148-153`
- Modify: `dashboards/phone/rooms/garden.yaml:62-63`

**Interfaces:**
- Consumes: `input_number.garden_vertical_days_between` new semantics (Task 2), `sensor.garden_vertical_next_run` (Task 2).
- Produces: display text only — no entity changes.

- [ ] **Step 1: Script description**

In `garden_vertical_irrigation.yaml` replace:

```yaml
    input_number.garden_vertical_minutes. Scheduled by
    garden_vertical_scheduled (every garden_vertical_days_between days);
    also runnable on demand or via a one-off.
```

with:

```yaml
    input_number.garden_vertical_minutes. Scheduled DAILY by
    garden_vertical_scheduled (skips rain; a garden_vertical_days_between-
    day-old last run fires even in rain); also runnable on demand or via
    a one-off.
```

- [ ] **Step 2: Profile header comment**

In `garden_irrigation_profile.yaml` replace:

```yaml
# Zone 3 now feeds the VERTICAL GARDEN and is NOT part of this profile —
# it has its own cadence (garden_vertical_scheduled automation +
# garden_vertical_minutes / garden_vertical_days_between helpers).
```

with:

```yaml
# Zone 3 now feeds the VERTICAL GARDEN and is NOT part of this profile —
# it waters daily with a rain skip (garden_vertical_scheduled automation;
# garden_vertical_minutes duration, garden_vertical_days_between rain
# guarantee).
```

- [ ] **Step 3: Tablet chip**

In `dashboards/tablet/outdoor.yaml` replace:

```yaml
          {% set vnext = states('sensor.garden_vertical_next_run') %}
          _Vertical garden: {{ states('input_number.garden_vertical_minutes') | int }}m
          every {{ states('input_number.garden_vertical_days_between') | int }}d{%
          if vnext not in ['unknown', 'unavailable', 'none', ''] %} · next
          {{ vnext | as_timestamp | timestamp_custom('%a %H:%M') }}{% endif %}._
```

with:

```yaml
          {% set vnext = states('sensor.garden_vertical_next_run') %}
          _Vertical garden: {{ states('input_number.garden_vertical_minutes') | int }}m
          daily, skips rain ({{ states('input_number.garden_vertical_days_between') | int }}d
          guarantee){% if vnext not in ['unknown', 'unavailable', 'none', ''] %} · next
          {{ vnext | as_timestamp | timestamp_custom('%a %H:%M') }}{% endif %}._
```

- [ ] **Step 4: Phone chip**

In `dashboards/phone/rooms/garden.yaml` replace:

```yaml
          {{ states('input_number.garden_vertical_minutes') | int }} min drip ·
          every {{ states('input_number.garden_vertical_days_between') | int }}d
```

with:

```yaml
          {{ states('input_number.garden_vertical_minutes') | int }} min drip ·
          daily, skips rain
```

- [ ] **Step 5: Lint + commit**

```bash
uv run yamllint packages/areas/outdoor/garden/scripts/garden_vertical_irrigation.yaml packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml dashboards/tablet/outdoor.yaml dashboards/phone/rooms/garden.yaml
git add packages/areas/outdoor/garden/scripts/garden_vertical_irrigation.yaml packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml dashboards/tablet/outdoor.yaml dashboards/phone/rooms/garden.yaml
git commit -m "docs(garden): daily + rain-skip wording — script, profile, dashboard chips"
```

---

### Task 4: Push, reload, set live helper, verify live

**Files:** none (operational). Orchestrator/inline task — needs live HA + `dangerouslyDisableSandbox: true` on every curl.

**Interfaces:**
- Consumes: everything from Tasks 1–3, pushed.
- Produces: live HA running the new config; `input_number.garden_vertical_days_between` = 2.

- [ ] **Step 1: Push**

```bash
git push -u origin feat/irrigation-two-zones-vertical-garden
```

- [ ] **Step 2: Wait for HA pull, then reload changed domains**

HA pulls the branch continuously (no lag — if a later check shows stale config, the addon/branch is broken; fix, don't wait). Reload (each needs `dangerouslyDisableSandbox: true`):

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload"
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload"
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/input_number/reload"
```

Expected: each returns `[]` or a JSON list, no error object.

- [ ] **Step 3: Set live guarantee value (reload does NOT apply `initial:`)**

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id": "input_number.garden_vertical_days_between", "value": 2}' \
  "$HA_URL/api/services/input_number/set_value"
```

Then confirm:

```bash
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/input_number.garden_vertical_days_between"
```

Expected: `"state": "2.0"` and `"friendly_name": "Garden Vertical Rain Guarantee Days"`.

- [ ] **Step 4: Verify templates live**

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template": "next={{ states(\"sensor.garden_vertical_next_run\") }} rain_skip={{ is_state(\"binary_sensor.raining\", \"on\") or states(\"sensor.garden_rain_accumulation\") | float(0) >= 3 }}"}' \
  "$HA_URL/api/template"
```

Expected: `next=` is the next 06:15 local timestamp (today if before 06:15, else tomorrow); `rain_skip=` True/False matching current weather.

- [ ] **Step 5: Check error log**

```bash
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -40
```

Expected: no new errors mentioning `garden_vertical`, `garden_next_run`, or template render failures.

- [ ] **Step 6: Playwright-validate both dashboards (user rule: visual check required after dashboard edits)**

Navigate to `http://homeassistant.local:8123/wall-tablet/outdoor` and the phone dashboard's garden room view; force-refresh so the cached lovelace parse is bypassed; screenshot each into `.playwright-mcp/` (never repo root). Confirm the vertical garden chip reads "daily, skips rain (2d guarantee) · next <time>" on tablet and "min drip · daily, skips rain" on phone, and neither section is broken by a template error.

---

### Task 5: README + knowledge leaf

**Files:**
- Regenerate: `packages/areas/outdoor/garden/README.md`
- Update: `knowledge/areas/garden-irrigation-schedule.md` (via skill — NEVER edit inline)

Orchestrator/inline task — both steps are skill invocations, not subagent work.

- [ ] **Step 1: Regenerate garden README**

Invoke the `ha-area-docs` skill for `packages/areas/outdoor/garden` (CLAUDE.md: run after modifying an area package). Follow the skill; commit whatever it produces.

- [ ] **Step 2: Update knowledge leaf**

Invoke the `knowledge-author` skill. The leaf `knowledge/areas/garden-irrigation-schedule.md` states zone 3 has "days-since check … deliberately NO rain/soil gating" on a 7-day cadence — now wrong. New facts for the leaf: vertical waters DAILY at 06:15, skips when `binary_sensor.raining` on or rain accumulation ≥ 3mm (same signals as lawn/drip, read inline), `garden_vertical_days_between` (now 2) is a rain-streak guarantee floor that BYPASSES the rain skip (mirrors the drip weekly guarantee pattern), still no soil gate, still outside the schedule brain, `garden_vertical_next_run` = next 06:15 slot. The skill owns dedup/frontmatter/INDEX rebuild/commit.

---

## Self-Review Notes

- Spec coverage: automation gate (Task 1), helper + next_run (Task 2), wording incl. both dashboards (Task 3), post-push rollout + live verify + Playwright (Task 4), README + knowledge (Task 5). Error-handling section of spec = inherited behavior, untouched by any task — verified Task 1 keeps idle-wait/busy-stop byte-identical.
- No placeholders; every edit shows exact before/after text.
- Type consistency: entity ids identical across tasks (`garden_vertical_days_between`, `garden_vertical_next_run`); new display name used only in Task 2 config and Task 4 verification.
