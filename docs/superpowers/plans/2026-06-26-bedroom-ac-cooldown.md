# Bedroom Evening AC Cooldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-cool the bedroom toward 22°C in the evening when hot, with hysteresis and a safety max-runtime auto-off.

**Architecture:** A template overlay sensor (`sensor.bedroom_temperature`) mirrors the chosen physical source (`sensor.bedroom_fp300_temperature`); all automations read the overlay so the source can be swapped in one place. Three automations (ON, OFF-target, safety-timeout) drive `climate.bedroom` in `cool` mode.

**Tech Stack:** Home Assistant YAML packages, Jinja2 templates, `climate` services.

## Global Constraints

- All files under `packages/areas/first-floor/bedroom/`.
- Automation filenames: `{area}_{action}_{trigger}.yaml`; each has a descriptive `alias` and a unique `id`.
- Automations use HA trigger/condition/action keys: `trigger:`, `condition:`, `action:` (singular `action:` for service calls, matching repo idiom in `bedroom_humidifier_on_off.yaml`).
- AC entity: `climate.bedroom` (modes include `off`, `cool`; setpoint range 16–31°C). May be `unavailable` off-season — automations must tolerate this.
- Source sensor: `sensor.bedroom_fp300_temperature`.
- Overlay entity_id: `sensor.bedroom_temperature`.
- Hysteresis: ON above 25°C, OFF at/below 23°C, setpoint 22°C. Active window 21:00–23:00. Safety cutoff 3h.
- Lint with `uv run yamllint .`; HA config check via `just check`.
- Never push to `main`. Current branch: `chore/june-features`.
- Reload HA config + check logs after push (errors invisible until reload).

---

### Task 1: Overlay temperature sensor

**Files:**
- Create: `packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`

**Interfaces:**
- Consumes: `sensor.bedroom_fp300_temperature` (state, °C).
- Produces: `sensor.bedroom_temperature` — `device_class: temperature`, `unit_of_measurement: °C`, `state_class: measurement`. Passes through `unknown`/`unavailable` from source. This is the single entity every AC automation reads.

- [ ] **Step 1: Create the overlay template sensor file**

```yaml
---
sensor:
  - name: bedroom_temperature
    unique_id: bedroom_temperature_overlay
    device_class: temperature
    unit_of_measurement: "°C"
    state_class: measurement
    # Overlay: swap the source entity_id below to change which physical
    # sensor drives bedroom temperature. All AC automations read
    # sensor.bedroom_temperature, never the raw source.
    state: >
      {{ states('sensor.bedroom_fp300_temperature') }}
    availability: >
      {{ states('sensor.bedroom_fp300_temperature') not in
         ['unknown', 'unavailable', 'none'] }}
    attributes:
      source: "sensor.bedroom_fp300_temperature"
```

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`
Expected: no errors (clean exit).

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml
git commit -m "feat(bedroom): overlay temperature sensor for AC cooldown"
```

- [ ] **Step 4: Push, reload, verify overlay renders**

```bash
git push
```

Reload core config (MCP `homeassistant.reload_template_entities` or `homeassistant.reload_core_config` via API). Then verify the overlay value matches the source:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/sensor.bedroom_temperature"
```

Expected: JSON with `"state"` equal to the current `sensor.bedroom_fp300_temperature` value (e.g. `"28.28"`), `device_class: temperature`. Run with `dangerouslyDisableSandbox: true`.

> NOTE: a new template sensor may require a template reload (or HA restart) to appear, not just `reload_core_config`. If the entity is missing after `reload_core_config`, call `homeassistant.reload_template_entities` (or restart HA). If still `unavailable`, confirm the source sensor itself is reporting.

---

### Task 2: ON automation (auto-cool when hot)

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`

**Interfaces:**
- Consumes: `sensor.bedroom_temperature` (Task 1), `climate.bedroom`.
- Produces: sets `climate.bedroom` to `cool` at 22°C when conditions met. Later tasks (OFF, safety) react to `climate.bedroom` being in `cool`.

- [ ] **Step 1: Create the ON automation file**

```yaml
---
alias: Bedroom AC evening cooldown - on
description: >-
  When the bedroom is over 25°C during the evening run-up to bedtime
  (21:00–23:00), set the AC to cool toward 22°C. Reads the overlay
  sensor.bedroom_temperature. Skips if the AC is unavailable or already
  cooling.
id: a1c3e5f7-1b2d-4a6c-8e0f-2a4c6e8b0d11

mode: single
max_exceeded: silent

trigger:
  - trigger: numeric_state
    entity_id: sensor.bedroom_temperature
    above: 25
    for:
      minutes: 5

condition:
  - condition: time
    after: "21:00:00"
    before: "23:00:00"
  - condition: not
    conditions:
      - condition: state
        entity_id: climate.bedroom
        state: "unavailable"
  - condition: not
    conditions:
      - condition: state
        entity_id: climate.bedroom
        state: "cool"

action:
  - action: climate.set_temperature
    target:
      entity_id: climate.bedroom
    data:
      temperature: 22
  - action: climate.set_hvac_mode
    target:
      entity_id: climate.bedroom
    data:
      hvac_mode: cool
```

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml
git commit -m "feat(bedroom): AC cooldown ON automation (>25°C evening)"
```

---

### Task 3: OFF automation (target reached, hysteresis)

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml`

**Interfaces:**
- Consumes: `sensor.bedroom_temperature` (Task 1), `climate.bedroom`.
- Produces: turns `climate.bedroom` off when cooled. Only fires while in `cool` (won't fight manual heat/fan).

- [ ] **Step 1: Create the OFF automation file**

```yaml
---
alias: Bedroom AC evening cooldown - off (target reached)
description: >-
  When the bedroom cools to 23°C or below, turn the AC off. 2°C hysteresis
  band below the 25°C on-threshold prevents rapid cycling. Only acts while
  the AC is cooling, so it won't fight manual heat/fan use.
id: b2d4f6a8-2c3e-4b7d-9f1a-3b5d7f9c1e22

mode: single
max_exceeded: silent

trigger:
  - trigger: numeric_state
    entity_id: sensor.bedroom_temperature
    below: 23.1
    for:
      minutes: 5

condition:
  - condition: state
    entity_id: climate.bedroom
    state: "cool"

action:
  - action: climate.turn_off
    target:
      entity_id: climate.bedroom
```

> NOTE: `below: 23.1` implements "at or below 23°C" — `numeric_state below` is strict (`<`), so 23.0 must satisfy it. 23.1 makes 23.0 trigger while 23.2+ does not.

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml
git commit -m "feat(bedroom): AC cooldown OFF automation (<=23°C hysteresis)"
```

---

### Task 4: Safety max-runtime auto-off

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`

**Interfaces:**
- Consumes: `climate.bedroom`.
- Produces: turns `climate.bedroom` off 3h after it enters `cool`, restarting the timer on every new cool session.

- [ ] **Step 1: Create the safety timeout automation file**

```yaml
---
alias: Bedroom AC safety max-runtime
description: >-
  Hard backstop: 3h after the AC enters cool mode, turn it off. Protects
  against a stuck or wrong temperature sensor that never reaches the 23°C
  off-threshold. mode restart resets the timer each time cooling (re)starts.
  Applies to any cool session, manual or automatic.
id: c3e5a7b9-3d4f-4c8e-a02b-4c6e8a0d2f33

mode: restart
max_exceeded: silent

trigger:
  - trigger: state
    entity_id: climate.bedroom
    to: "cool"

action:
  - delay:
      hours: 3
  - action: climate.turn_off
    target:
      entity_id: climate.bedroom
```

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml
git commit -m "feat(bedroom): AC safety max-runtime auto-off (3h)"
```

---

### Task 5: Validate, deploy, verify end-to-end

**Files:** none (deploy + verification only).

- [ ] **Step 1: Full HA config check**

Run: `just check`
Expected: config valid, no errors. (If `just check` unavailable, run `uv run pre-commit run --all-files` then rely on post-push log check.)

- [ ] **Step 2: Lint everything**

Run: `uv run yamllint .`
Expected: no errors.

- [ ] **Step 3: Push**

```bash
git push
```

- [ ] **Step 4: Reload HA and check logs**

Reload core config + template entities (MCP `homeassistant.reload_core_config` / `homeassistant.reload_template_entities`, or via API). Then fetch the error log:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" | tail -40
```

Run with `dangerouslyDisableSandbox: true`. Expected: no new errors mentioning `bedroom_ac`, `bedroom_temperature`, or the new automation ids.

- [ ] **Step 5: Verify entities exist**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/sensor.bedroom_temperature"
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.bedroom_ac_evening_cooldown_on"
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.bedroom_ac_evening_cooldown_off_target_reached"
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.bedroom_ac_safety_max_runtime"
```

Run with `dangerouslyDisableSandbox: true`. Expected: each returns state `on` (automations enabled) and the overlay returns a numeric temperature.

> NOTE: automation entity_ids are slugified from the `alias`. If a lookup 404s, list automations to find the exact slug:
> `curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" | python3 -c "import sys,json;[print(e['entity_id']) for e in json.load(sys.stdin) if 'bedroom_ac' in e['entity_id']]"`

- [ ] **Step 6: Manual trigger test of ON path (optional, in-window only)**

If `climate.bedroom` is available and time is within 21:00–23:00, trigger the ON automation manually and confirm the AC goes to `cool` @ 22°C:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"automation.bedroom_ac_evening_cooldown_on"}' \
  "$HA_URL/api/services/automation/trigger"
```

Then check `climate.bedroom` state. Expected: `cool`, `temperature: 22`. If AC is `unavailable` (off-season), skip — the condition correctly prevents action; verify via the automation trace that it stopped at the unavailable condition.

---

### Task 6: Regenerate bedroom README

**Files:**
- Modify: `packages/areas/first-floor/bedroom/README.md`

- [ ] **Step 1: Regenerate area docs**

Invoke the `/ha-area-docs` skill for the bedroom area. It documents the new overlay sensor and three automations.

- [ ] **Step 2: Commit**

```bash
git add packages/areas/first-floor/bedroom/README.md
git commit -m "docs(bedroom): document AC evening cooldown automation"
git push
```

---

## Self-Review

**Spec coverage:**
- Overlay sensor → Task 1 ✓
- ON >25°C, evening window, setpoint 22 → Task 2 ✓
- OFF target ≤23°C hysteresis → Task 3 ✓
- Safety 3h max-runtime → Task 4 ✓
- AC-unavailable tolerance → Task 2 condition + Task 5 trace check ✓
- README regenerate → Task 6 ✓

**Placeholder scan:** none — all files have complete YAML, all commands concrete.

**Type consistency:** overlay entity_id `sensor.bedroom_temperature` consistent across Tasks 1–3 & 5. `climate.bedroom` consistent. Hysteresis values (25 / 23.1 / 22) consistent with spec.

**Edge note:** OFF uses `below: 23.1` to make 23.0 satisfy the strict `<` comparison — documented inline in Task 3.
