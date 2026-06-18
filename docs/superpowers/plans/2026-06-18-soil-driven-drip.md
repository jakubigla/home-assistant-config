# Soil-Driven Drip (Smart Mode) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Smart mode, run drip on soil demand — driest flowerbed `< 40%` (hysteresis re-arm at `> 60%`), capped to a configurable days-between frequency, with rain/season/saturation/night vetoes; lawn and all non-Smart modes unchanged.

**Architecture:** Two new automations (arm/disarm + run) read the 3 probes inline (race-free), gated by a persistent `input_boolean` arm flag and an `input_number` frequency cap. A standalone state-based status sensor exposes why-or-why-not. `garden_scheduled_irrigation` excludes Smart from the drip path only. Reuses `script.garden_drip_irrigation`, `sensor.garden_drip_last_run`, and `drip_duration` from the profile.

**Tech Stack:** HA automations + template sensor (Jinja2) + input helpers. "Tests" = `/api/template` dry-runs via curl; live verification after merge to the HA-pulled branch.

**Reference:** spec at `docs/superpowers/specs/2026-06-18-soil-driven-drip-design.md`.

**Key facts the engineer needs:**
- Env vars `$HA_URL`, `$HA_TOKEN` preloaded (direnv). Sandbox blocks the HA host → EVERY curl needs `dangerouslyDisableSandbox: true`.
- git from working dir (no `git -C`). Commit per task; do NOT push (push/PR/merge is the final task). HA tracks the branch it pulls — live verification needs the change merged to the pulled branch.
- Lint: `uv run yamllint <file>` (line-length is `warning`, non-blocking; only errors block).
- Probes (`%`): `sensor.pergola_left_flowerbed_soil_moisture`, `sensor.pergola_right_flowerbed_soil_moisture`, `sensor.sona_flowerbed_soil_moisture`. sona excluded from the saturation cap.
- Constants: `START=40`, `STOP=60`, `SAT=85`. Season = month 5–9. Night-guard = 22:00–04:30.
- The driest/wettest inline filter chain (verified working live this session):
  `probes | map('states') | reject('in', ['unknown','unavailable','none','']) | map('float',-1) | reject('eq',-1) | list`
- `script.garden_drip_irrigation` opens `valve.drip_irrigation`, waits for auto-off (duration `drip_duration` applied by `garden_valve_auto_off`) or 90-min safety. Call it via `script.turn_on` (fire-and-forget) — calling it directly blocks the automation (knowledge leaf `script-call-blocks-automation`).
- `sensor.garden_drip_last_run` (device_class timestamp) holds last drip run time.
- Automation filename convention: `{area}_{action}_{trigger}.yaml`, descriptive `alias`, unique `id`.

---

## File Structure

- **Modify:** `packages/areas/outdoor/garden/config.yaml` — add `input_boolean.garden_drip_armed`, `input_number.garden_drip_min_days_between`.
- **Create:** `packages/areas/outdoor/garden/automations/garden_drip_soil_arm.yaml` — hysteresis arm.
- **Create:** `packages/areas/outdoor/garden/automations/garden_drip_soil_run.yaml` — demand run + skip-notify.
- **Create:** `packages/areas/outdoor/garden/templates/garden_drip_soil_status.yaml` — standalone status sensor.
- **Modify:** `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml` — exclude Smart from `run_drip`.
- **Modify (via skill, final task):** `knowledge/areas/garden-irrigation-schedule.md`.

---

### Task 1: Add the input helpers

**Files:**
- Modify: `packages/areas/outdoor/garden/config.yaml` (append to `input_number:` block ~line 53, and `input_boolean:` block ~line 56)

- [ ] **Step 1: Add the input_number**

In `config.yaml`, after `garden_lawn_minutes_july` (the last `input_number`, ending line 53), add:
```yaml
  garden_drip_min_days_between:
    name: Garden Drip Min Days Between
    min: 1
    max: 7
    step: 1
    unit_of_measurement: d
    icon: mdi:calendar-clock
```

- [ ] **Step 2: Add the input_boolean**

In the `input_boolean:` block, after `garden_oneoff_armed` (or any existing entry), add:
```yaml
  garden_drip_armed:
    name: Garden Drip Armed
    icon: mdi:water-alert
    initial: true
```

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/config.yaml`
Expected: no errors.

- [ ] **Step 4: Commit**
```bash
git add packages/areas/outdoor/garden/config.yaml
git commit -m "feat(garden): add drip soil-driven helpers (armed flag, days-between)"
```

---

### Task 2: Standalone status sensor

**Files:**
- Create: `packages/areas/outdoor/garden/templates/garden_drip_soil_status.yaml`

This is a **state-based** template sensor (NOT trigger-based) — it re-evaluates whenever a referenced entity changes, so it never sits `unknown` after a reload. It is the single source of "why is/isn't Smart drip running", and the run automation reuses its `blocking_reason` for skip notifications.

- [ ] **Step 1: Dry-run the status logic against live values**

Confirm the expression renders before writing it. Run (with `dangerouslyDisableSandbox: true`):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" "$HA_URL/api/template" -d @- <<'JSON'
{"template": "{% set START=40 %}{% set SAT=85 %}{% set bad=['unknown','unavailable','none',''] %}{% set probes=['sensor.pergola_left_flowerbed_soil_moisture','sensor.pergola_right_flowerbed_soil_moisture','sensor.sona_flowerbed_soil_moisture'] %}{% set cap=['sensor.pergola_left_flowerbed_soil_moisture','sensor.pergola_right_flowerbed_soil_moisture'] %}{% set valid=probes|map('states')|reject('in',bad)|map('float',-1)|reject('eq',-1)|list %}{% set capv=cap|map('states')|reject('in',bad)|map('float',-1)|reject('eq',-1)|list %}driest={{ valid|min if valid|length>0 else 'NA' }} wettest={{ capv|max if capv|length>0 else 'NA' }} armed={{ states('input_boolean.garden_drip_armed') }} mode={{ states('input_select.garden_irrigation_mode') }}"}
JSON
```
Expected: real numbers, e.g. `driest=84.0 wettest=85.0 armed=on mode=...`.

- [ ] **Step 2: Write the sensor file**

Create `packages/areas/outdoor/garden/templates/garden_drip_soil_status.yaml`:
```yaml
---
# Soil-driven drip status (Smart mode). State-based (not trigger-based) so it
# never sits unknown after a reload. Single source of "why is/isn't Smart drip
# running"; the run automation reuses blocking_reason for skip notifications.
# Hysteresis START=40 / STOP=60, saturation cap SAT=85 (pergola L/R; sona out).
sensor:
  - name: Garden Drip Soil Status
    unique_id: garden_drip_soil_status
    icon: mdi:water-percent-alert
    state: >
      {% set START = 40 %}
      {% set SAT = 85 %}
      {% set bad = ['unknown', 'unavailable', 'none', ''] %}
      {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                       'sensor.pergola_right_flowerbed_soil_moisture',
                       'sensor.sona_flowerbed_soil_moisture'] %}
      {% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                           'sensor.pergola_right_flowerbed_soil_moisture'] %}
      {% set valid = probes | map('states') | reject('in', bad)
         | map('float', -1) | reject('eq', -1) | list %}
      {% set cap_valid = cap_probes | map('states') | reject('in', bad)
         | map('float', -1) | reject('eq', -1) | list %}
      {% set armed = is_state('input_boolean.garden_drip_armed', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set raining = is_state('binary_sensor.raining', 'on') %}
      {% set t = now().strftime('%H:%M') %}
      {% set night = t >= '22:00' or t < '04:30' %}
      {% set last = states('sensor.garden_drip_last_run') %}
      {% set min_days = states('input_number.garden_drip_min_days_between') | int(1) %}
      {% set days_since = ((now() - as_datetime(last)).total_seconds() / 86400)
         if last not in bad else 999 %}
      {% if valid | length == 0 %} no_data
      {% elif not in_season %} out_of_season
      {% elif not armed %} disarmed
      {% elif (valid | min) >= START %} armed_waiting
      {% elif raining %} vetoed_rain
      {% elif (cap_valid | length > 0) and (cap_valid | max) >= SAT %} vetoed_saturation
      {% elif days_since < min_days %} cooldown_days
      {% elif night %} night
      {% else %} ready {% endif %}
    attributes:
      driest: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {% set valid = probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (valid | min) if valid | length > 0 else None }}
      wettest: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                             'sensor.pergola_right_flowerbed_soil_moisture'] %}
        {% set cap_valid = cap_probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (cap_valid | max) if cap_valid | length > 0 else None }}
      armed: "{{ is_state('input_boolean.garden_drip_armed', 'on') }}"
      mode: "{{ states('input_select.garden_irrigation_mode') }}"
      min_days_between: "{{ states('input_number.garden_drip_min_days_between') | int(1) }}"
      days_since_run: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set last = states('sensor.garden_drip_last_run') %}
        {{ ((now() - as_datetime(last)).total_seconds() / 86400) | round(1)
           if last not in bad else None }}
      blocking_reason: "{{ states('sensor.garden_drip_soil_status') }}"
```
Note: `blocking_reason` mirrors the state (convenience for the run automation; HA resolves the self-reference to the prior computed state, which is fine for a label).

- [ ] **Step 3: Confirm the file is included by the package**

Garden templates are auto-included if `config.yaml`/package globs `templates/*.yaml`. Verify the existing templates are globbed (the other 4 template files load), so the new file is picked up automatically. Run: `grep -rn "templates" packages/areas/outdoor/garden/config.yaml || echo "check configuration.yaml package include"`. If templates are listed individually anywhere, add this file; if glob-included, no change needed. Report which.

- [ ] **Step 4: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_drip_soil_status.yaml`
Expected: no errors.

- [ ] **Step 5: Commit**
```bash
git add packages/areas/outdoor/garden/templates/garden_drip_soil_status.yaml
git commit -m "feat(garden): add garden_drip_soil_status sensor (soil-driven drip observability)"
```

---

### Task 3: Arm/disarm automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_drip_soil_arm.yaml`

- [ ] **Step 1: Write the automation**

Create the file:
```yaml
---
alias: Garden Drip Soil Arm
description: >
  Hysteresis arm for soil-driven drip. When the driest flowerbed recovers
  above STOP (60%), re-arm so a future dry spell can trigger a run. Disarm is
  performed by garden_drip_soil_run right after it fires, so a bed must climb
  back above 60% before the next soil-driven run. Reads probes inline.
id: garden-drip-soil-arm
mode: single

trigger:
  - platform: state
    entity_id:
      - sensor.pergola_left_flowerbed_soil_moisture
      - sensor.pergola_right_flowerbed_soil_moisture
      - sensor.sona_flowerbed_soil_moisture
  - platform: homeassistant
    event: start

action:
  - variables:
      STOP: 60
      driest: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {% set valid = probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (valid | min) if valid | length > 0 else -1 }}
  - condition: template
    value_template: "{{ driest | float(-1) >= STOP }}"
  - action: input_boolean.turn_on
    target:
      entity_id: input_boolean.garden_drip_armed
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_drip_soil_arm.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**
```bash
git add packages/areas/outdoor/garden/automations/garden_drip_soil_arm.yaml
git commit -m "feat(garden): add soil-driven drip arm automation (hysteresis re-arm at 60%)"
```

---

### Task 4: Run automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_drip_soil_run.yaml`

- [ ] **Step 1: Write the automation**

Create the file. The run gate is computed inline (no `garden_drip_soil_skip` read → race-free). On a dry+armed-but-vetoed pass, it notifies skip-with-reason using the status sensor's state.
```yaml
---
alias: Garden Drip Soil Run
description: >
  Soil-driven drip for Smart mode. When the driest flowerbed is below START
  (40%) and armed, runs the drip line — gated by days-between cap, rain,
  season, saturation, night-guard, and valve state. Disarms on fire so the
  bed must recover above 60% (handled by garden_drip_soil_arm) before the
  next run. Notifies on run and on dry-but-vetoed skip. Reads probes inline.
id: garden-drip-soil-run
mode: single

trigger:
  - platform: state
    entity_id:
      - sensor.pergola_left_flowerbed_soil_moisture
      - sensor.pergola_right_flowerbed_soil_moisture
      - sensor.sona_flowerbed_soil_moisture
  - platform: time_pattern
    minutes: "/30"

condition:
  - condition: state
    entity_id: input_select.garden_irrigation_mode
    state: "Smart"
  - condition: state
    entity_id: input_boolean.garden_drip_armed
    state: "on"

action:
  - variables:
      START: 40
      SAT: 85
      bad: "{{ ['unknown', 'unavailable', 'none', ''] }}"
      driest: >
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {% set valid = probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (valid | min) if valid | length > 0 else -1 }}
      wettest: >
        {% set cap = ['sensor.pergola_left_flowerbed_soil_moisture',
                      'sensor.pergola_right_flowerbed_soil_moisture'] %}
        {% set cv = cap | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (cv | max) if cv | length > 0 else -1 }}
      raining: "{{ is_state('binary_sensor.raining', 'on') }}"
      month: "{{ now().month }}"
      in_season: "{{ now().month >= 5 and now().month <= 9 }}"
      t: "{{ now().strftime('%H:%M') }}"
      night: "{{ now().strftime('%H:%M') >= '22:00' or now().strftime('%H:%M') < '04:30' }}"
      min_days: "{{ states('input_number.garden_drip_min_days_between') | int(1) }}"
      last_run: "{{ states('sensor.garden_drip_last_run') }}"
      days_since: >
        {{ ((now() - as_datetime(last_run)).total_seconds() / 86400)
           if last_run not in bad else 999 }}
      valve_open: "{{ is_state('valve.drip_irrigation', 'open') }}"
      is_dry: "{{ driest | float(-1) >= 0 and driest | float(-1) < START }}"
  # Only proceed if the bed is actually dry; otherwise nothing to do.
  - if:
      - "{{ not is_dry }}"
    then:
      - stop: "Driest bed not below START — no soil-driven run"
  - variables:
      blocked: >
        {% if raining %} rain
        {% elif not in_season %} out_of_season
        {% elif wettest | float(-1) >= SAT %} saturation
        {% elif days_since | float(0) < min_days | float(1) %} cooldown_days
        {% elif night %} night
        {% elif valve_open %} valve_open
        {% else %} none {% endif %}
      blocked_clean: "{{ blocked | trim }}"
  - choose:
      # Dry + all gates pass → run.
      - conditions:
          - "{{ blocked_clean == 'none' }}"
        sequence:
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.garden_drip_armed
          - action: script.turn_on
            target:
              entity_id: script.garden_drip_irrigation
          - action: persistent_notification.create
            data:
              notification_id: garden_drip_soil_run
              title: Drip irrigation (soil-driven)
              message: >
                Drip ran — driest bed {{ driest }}%. Disarmed until it recovers
                above 60%.
          - action: notify.mobile_app_iglofon
            data:
              title: Drip irrigation (soil-driven)
              message: "Drip ran — driest bed {{ driest }}%."
    # Dry but vetoed → notify skip with reason (no run).
    default:
      - action: persistent_notification.create
        data:
          notification_id: garden_drip_soil_skip
          title: Drip soil-driven skipped
          message: >
            Driest bed {{ driest }}% is dry but drip was skipped — reason:
            {{ blocked_clean }}.
      - action: notify.mobile_app_iglofon
        data:
          title: Drip soil-driven skipped
          message: "Dry ({{ driest }}%) but skipped — {{ blocked_clean }}."
```

- [ ] **Step 2: Dry-run the gate expression**

Validate the `blocked` logic renders against live values (with `dangerouslyDisableSandbox: true`):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" "$HA_URL/api/template" -d @- <<'JSON'
{"template": "{% set SAT=85 %}{% set bad=['unknown','unavailable','none',''] %}{% set cap=['sensor.pergola_left_flowerbed_soil_moisture','sensor.pergola_right_flowerbed_soil_moisture'] %}{% set cv=cap|map('states')|reject('in',bad)|map('float',-1)|reject('eq',-1)|list %}{% set wettest=(cv|max if cv|length>0 else -1) %}raining={{ is_state('binary_sensor.raining','on') }} in_season={{ now().month>=5 and now().month<=9 }} wettest={{ wettest }} sat_block={{ wettest>=SAT }} last={{ states('sensor.garden_drip_last_run') }}"}
JSON
```
Expected: renders cleanly with booleans + numbers (no template error).

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_drip_soil_run.yaml`
Expected: no errors.

- [ ] **Step 4: Commit**
```bash
git add packages/areas/outdoor/garden/automations/garden_drip_soil_run.yaml
git commit -m "feat(garden): add soil-driven drip run automation (Smart mode, inline probe reads)"
```

---

### Task 5: Exclude Smart from scheduled drip

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml` (the `run_drip` variable, line 36)

- [ ] **Step 1: Gate run_drip on non-Smart**

Replace line 36:
```yaml
      run_drip: "{{ drip_today and not drip_skip }}"
```
with:
```yaml
      run_drip: >
        {{ drip_today and not drip_skip
           and not is_state('input_select.garden_irrigation_mode', 'Smart') }}
```
This leaves `run_lawn` (line 35) untouched — lawn in Smart still schedule-fires. In Smart, `run_drip` is always false here; drip is owned by `garden_drip_soil_run`.

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`
Expected: no errors.

- [ ] **Step 3: Confirm lawn path intact**

Run: `grep -n "run_lawn\|run_drip\|Smart" packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`
Expected: `run_lawn` unchanged; `run_drip` now references Smart; the `choose` branches (run_lawn / run_drip) unchanged.

- [ ] **Step 4: Commit**
```bash
git add packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml
git commit -m "feat(garden): exclude Smart mode from scheduled drip (now soil-driven)"
```

---

### Task 6: Push, merge, reload, verify live

**Files:** none (deploy + verification)

- [ ] **Step 1: Push the branch**

Confirm branch: `git branch --show-current` (expect `feat/soil-driven-drip`; never main). Run: `git push -u origin feat/soil-driven-drip`

- [ ] **Step 2: Open + merge PR** (HA tracks the pulled branch; merge so it deploys)
```bash
gh pr create --title "feat(garden): soil-driven drip (Smart mode)" --body "Demand-based drip in Smart mode — see docs/superpowers/specs/2026-06-18-soil-driven-drip-design.md. Hysteresis 40/60, days-between cap, rain/season/saturation/night vetoes, inline probe reads (race-free), arm input_boolean, status sensor + notifications. Lawn and non-Smart modes unchanged."
```
Then squash-merge the returned PR number: `gh pr merge <N> --squash --delete-branch=false`. Confirm: `git fetch origin main -q && git log origin/main --oneline -1`.

- [ ] **Step 3: Reload templates + automations**

Wait for the HA pull to land (poll; do not assume lag — if it never lands, the pull/branch is wrong, not slow). Then (curl needs `dangerouslyDisableSandbox: true`):
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload" -d '{}'
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload" -d '{}'
```

- [ ] **Step 4: Check error log**
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | grep -iE "drip_soil|garden_drip|flowerbed|garden_scheduled" | tail -20
```
Expected: no new errors.

- [ ] **Step 5: Verify entities exist + status sensor populates**

The status sensor is state-based → populates immediately on reload (unlike the trigger-based skip sensors).
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_drip_soil_status" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);a=d['attributes'];print('state=',d['state']);print('driest=',a.get('driest'),'wettest=',a.get('wettest'),'armed=',a.get('armed'),'days_since=',a.get('days_since_run'),'mode=',a.get('mode'))"
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/input_boolean.garden_drip_armed" | python3 -c "import sys,json;print('armed=',json.load(sys.stdin)['state'])"
```
Expected: status sensor has a real state (e.g. `armed_waiting` since beds are wet today), real driest/wettest numbers, `mode=` current mode.

- [ ] **Step 6: Functional check (Smart mode)**

Set Smart and observe (do NOT force a fake dry run on live valves unless intended):
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" "$HA_URL/api/services/input_select/select_option" -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Smart"}'
sleep 2
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_drip_soil_status" | python3 -c "import sys,json;d=json.load(sys.stdin);print('Smart status=',d['state'])"
```
Expected (beds wet today): `armed_waiting` (armed, driest >= 40 so not yet dry). Confirms gating without triggering a real run. **Restore the mode afterward** to the user's prior mode unless they want Smart left on.

- [ ] **Step 7: Regression — non-Smart scheduled drip intact**

Confirm the exclusion didn't break the schedule path: render `run_drip` for a non-Smart mode.
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" "$HA_URL/api/template" -d '{"template": "smart_blocks_drip={{ is_state(\"input_select.garden_irrigation_mode\",\"Smart\") }}"}'
```
Expected: when mode != Smart → false (drip not blocked by the new clause). Sanity-confirm the scheduled automation still has its lawn + drip choose branches.

---

### Task 7: Update the knowledge leaf

**Files:**
- Modify (via skill): `knowledge/areas/garden-irrigation-schedule.md`

- [ ] **Step 1: Invoke knowledge-author**

Do NOT edit inline. Invoke `knowledge-author` with:
> Smart mode now drives drip by **soil demand**, not schedule. New automations `garden_drip_soil_arm` + `garden_drip_soil_run` (in garden/automations) run the drip line when the driest flowerbed probe `< 40%` (hysteresis: re-arm only after driest recovers `> 60%`, held in `input_boolean.garden_drip_armed`), capped by `input_number.garden_drip_min_days_between` (days since `sensor.garden_drip_last_run`), and vetoed by rain / out-of-season / pergola saturation (`>=85`, sona excluded) / night 22:00–04:30 / valve already open. `garden_scheduled_irrigation` now excludes Smart from `run_drip` (lawn in Smart still schedules). Control automations read the 3 probes **inline** — never `binary_sensor.garden_drip_soil_skip` — to avoid the trigger-based-template same-pass staleness race. Observability: `sensor.garden_drip_soil_status` (state-based; armed/driest/days/blocking_reason). Non-Smart modes keep the schedule + skip-gate drip unchanged. Also note: trigger-based template sensors read `unknown` until their first trigger after a reload — use state-based templates for anything that must be fresh on reload.

- [ ] **Step 2: Confirm INDEX rebuilt + committed**

knowledge-author owns rebuild/commit. Verify: `git log --oneline -1` shows the knowledge commit; `grep -n garden-irrigation knowledge/INDEX.md` resolves.

---

## Self-Review

**1. Spec coverage:**
- Smart-only scope → Task 4 (mode==Smart condition) + Task 5 (exclude Smart from schedule) ✅
- Hysteresis START=40/STOP=60 → Task 3 (arm at >60) + Task 4 (run at <40, disarm on fire) ✅
- Run duration = drip_duration (reused, untouched) → no task needed; `script.garden_drip_irrigation` + existing auto-off unchanged ✅
- Days-between cap (input_number, from last_run) → Task 1 + Task 4 (`days_since >= min_days`) ✅
- Arm via input_boolean, inline probe reads (race-free) → Task 1 + Tasks 3/4 (no helper entity read) ✅
- Notify on run + skip-with-reason → Task 4 (choose/default branches) ✅
- Status sensor (state-based, observability) → Task 2 ✅
- Vetoes rain/season/saturation/night/valve → Task 4 `blocked` ✅
- Fail-safe all-probes-dead → Task 4 (`is_dry` false when driest=-1 → stop) + Task 2 (`no_data`) ✅
- Eval-order race fix → inline reads in Tasks 3/4; helper never read by control ✅
- Smart purely soil-driven (no 04:00) → Task 5 ✅
- Verification + reload-after-push + merge-to-pulled-branch → Task 6 ✅
- Knowledge follow-up → Task 7 ✅

**2. Placeholder scan:** No TBD/TODO; all YAML + commands concrete. Task 2 Step 3 is a conditional check with a concrete command + report, not a placeholder.

**3. Type/name consistency:** Entity ids consistent across tasks — `input_boolean.garden_drip_armed`, `input_number.garden_drip_min_days_between`, `sensor.garden_drip_soil_status`, automations `garden-drip-soil-arm` / `garden-drip-soil-run`. START=40/STOP=60/SAT=85 consistent. `driest`/`wettest` filter chain identical to the verified PR #35 helper. `script.turn_on script.garden_drip_irrigation` (fire-and-forget) per the knowledge leaf.

**Note — disarm/run ordering:** the run automation disarms (`armed=off`) BEFORE firing the script. The arm automation only re-arms when driest > 60. So after a run, even though watering raises moisture, re-arm waits until driest exceeds 60 — exactly the hysteresis intent. The `/30` tick + probe-change triggers re-evaluate; `mode: single` prevents overlap.

**Note — days_since when last_run unknown:** treated as 999 (eligible) so a first-ever run isn't blocked by a missing timestamp.
