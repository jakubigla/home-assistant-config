# Bedroom AC occupancy-gated safety + threshold recalibration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the bedroom AC turn off on real room temperature, and only apply the 3h hard-stop when the room is empty.

**Architecture:** Three YAML-only changes in the bedroom package: (1) extend the existing `sensor.bedroom_temperature` overlay to blend hygro (accurate, fresh) with a bias-corrected FP300 fallback; (2) recalibrate the on/off/setpoint numbers into the now-real temperature band; (3) gate the safety timeout on the debounced `input_boolean.bedroom_occupied` latch. No new entities — the overlay is the seam every AC automation already reads.

**Tech Stack:** Home Assistant template sensors (Jinja2), automations YAML. Verification via `uv run yamllint`, `just check` (HA config check), `/api/template` render, HA reload + logbook/trace.

## Global Constraints

- **Never push to `main`.** Work on branch `feat/bedroom-ac-occupancy-safety` (already created), PR to `main`.
- After every push: reload HA core config (`homeassistant.reload_core_config`) + check logs — errors stay invisible until reload.
- Sandbox blocks `homeassistant.local` — curl against HA needs `dangerouslyDisableSandbox: true`.
- Use `uv` for all Python tooling. Run git from the working directory (no `git -C`).
- All AC automations read `sensor.bedroom_temperature` (the overlay), never a raw physical sensor. Preserve that contract.
- Env vars preloaded via direnv: `$HA_URL`, `$HA_TOKEN`. Never read the dotenv file.
- Local time = Europe/Warsaw (CEST = UTC+2). Quote times local.
- Measured constants (from 5-day history, do not re-derive): FP300−hygro bias mean **1.3°C**; hygro cadence ~25 min median, 110 min max gap; hygro 5-day floor **24.5°C**.

---

### Task 1: Blend the control-temp overlay (hygro fresh → FP300 fallback)

**Files:**
- Modify: `packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`

**Interfaces:**
- Consumes: `sensor.bedroom_hygro_temperature` (Zigbee, accurate), `sensor.bedroom_fp300_temperature` (Matter, ~1.3°C hot).
- Produces: `sensor.bedroom_temperature` — now true room-air temp; adds attribute `source` = `"hygro"` or `"fp300_fallback"`. Downstream (Tasks 2–3) read this entity and the recalibrated thresholds assume it reads real room temp.

- [ ] **Step 1: Replace the overlay body**

Overwrite the whole file with:

```yaml
---
sensor:
  - name: bedroom_temperature
    unique_id: bedroom_temperature_overlay
    device_class: temperature
    unit_of_measurement: "°C"
    state_class: measurement
    # Overlay: the single seam every bedroom AC automation reads. Blends the
    # accurate battery hygro (Zigbee) with a bias-corrected FP300 (Matter)
    # fallback so control keeps working when the hygro goes silent-stale.
    #   - hygro when its last update is < 45 min old (covers ~25 min cadence)
    #   - else fp300 - 1.3  (measured mean bias, 141 paired samples 2026-06-27..07-02)
    state: >
      {% set hy = states('sensor.bedroom_hygro_temperature') %}
      {% set hy_age = (now() - states.sensor.bedroom_hygro_temperature.last_updated).total_seconds()
                      if states.sensor.bedroom_hygro_temperature is not none else 999999 %}
      {% set fp = states('sensor.bedroom_fp300_temperature') %}
      {% if hy not in ['unknown','unavailable','none'] and hy_age < 2700 %}
        {{ hy | float }}
      {% elif fp not in ['unknown','unavailable','none'] %}
        {{ (fp | float - 1.3) | round(1) }}
      {% else %}
        unavailable
      {% endif %}
    availability: >
      {% set hy = states('sensor.bedroom_hygro_temperature') %}
      {% set hy_age = (now() - states.sensor.bedroom_hygro_temperature.last_updated).total_seconds()
                      if states.sensor.bedroom_hygro_temperature is not none else 999999 %}
      {% set fp = states('sensor.bedroom_fp300_temperature') %}
      {{ (hy not in ['unknown','unavailable','none'] and hy_age < 2700)
         or fp not in ['unknown','unavailable','none'] }}
    attributes:
      source: >
        {% set hy = states('sensor.bedroom_hygro_temperature') %}
        {% set hy_age = (now() - states.sensor.bedroom_hygro_temperature.last_updated).total_seconds()
                        if states.sensor.bedroom_hygro_temperature is not none else 999999 %}
        {% if hy not in ['unknown','unavailable','none'] and hy_age < 2700 %}hygro{% else %}fp300_fallback{% endif %}
```

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml`
Expected: no errors (clean exit).

- [ ] **Step 3: Render-test the template logic against live HA (before pushing)**

The overlay isn't live until pushed, but the *logic* can be validated now by rendering the same expression against current sensor values via the template API:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -X POST "$HA_URL/api/template" -d '{"template": "hygro={{ states(\"sensor.bedroom_hygro_temperature\") }} age={{ (now() - states.sensor.bedroom_hygro_temperature.last_updated).total_seconds() | int }}s fp300={{ states(\"sensor.bedroom_fp300_temperature\") }} -> control={% set hy = states(\"sensor.bedroom_hygro_temperature\") %}{% set a = (now() - states.sensor.bedroom_hygro_temperature.last_updated).total_seconds() %}{% set fp = states(\"sensor.bedroom_fp300_temperature\") %}{% if hy not in [\"unknown\",\"unavailable\",\"none\"] and a < 2700 %}{{ hy | float }}{% else %}{{ (fp | float - 1.3) | round(1) }}{% endif %}"}'
```

Run with `dangerouslyDisableSandbox: true`.
Expected: prints hygro value, its age in seconds, fp300 value, and a `control=` result. Sanity-check: if hygro age < 2700s, control == hygro; the control value should be **~1.3 below** fp300. Confirms the blend math before it goes live.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/templates/sensors/bedroom_temperature.yaml
git commit -m "feat(bedroom-ac): blend control-temp overlay — hygro fresh, FP300-1.3 fallback"
```

---

### Task 2: Recalibrate on/off thresholds + setpoint

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml`
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`

**Interfaces:**
- Consumes: `sensor.bedroom_temperature` (now true room temp, from Task 1).
- Produces: off fires at ≤25.0°C real; on arms at >26.5°C real; setpoint 23°C. 1.5°C hysteresis band.

- [ ] **Step 1: Edit the off-automation threshold**

In `bedroom_ac_cooldown_off.yaml`, the trigger currently uses `below: 23.1` with a comment about 23.0. Replace the trigger block and description to target 25.0°C. Change:

```yaml
description: >-
  When the bedroom cools to 25°C or below, turn the AC off. Reads the blended
  sensor.bedroom_temperature (true room air). ~1.5°C hysteresis below the
  26.5°C on-threshold prevents rapid cycling. Only acts while the AC is
  cooling, so it won't fight manual heat/fan use. Note: this room floors around
  24.5°C even running flat out, so 25.0 is the reachable "comfortably cool" off
  point — 23.1 (the old value) never fired.
```

and the trigger:

```yaml
trigger:
  # below is strict (<); 25.05 makes 25.0 trigger while 25.1+ does not,
  # implementing "at or below 25.0°C".
  - trigger: numeric_state
    entity_id: sensor.bedroom_temperature
    below: 25.05
    for:
      minutes: 5
```

Leave the `condition` (`state: cool`) and `action` (`climate.turn_off`) unchanged.

- [ ] **Step 2: Edit the on-automation thresholds + setpoint**

In `bedroom_ac_cooldown_on.yaml`:

- Update the `numeric_state` **trigger** `above: 25` → `above: 26.5`.
- Update the `numeric_state` **condition** `above: 25` → `above: 26.5`.
- Update the `climate.set_temperature` action `temperature: 22` → `temperature: 23`.
- Update the description first paragraph to reflect the new numbers: "over 26.5°C ... set the AC to cool toward 23°C." Keep the second paragraph (the level-vs-edge explanation) intact — it's still accurate.

Concretely, the three value changes:

```yaml
# trigger
  - trigger: numeric_state
    entity_id: sensor.bedroom_temperature
    above: 26.5
    for:
      minutes: 5
```

```yaml
# condition
  - condition: numeric_state
    entity_id: sensor.bedroom_temperature
    above: 26.5
```

```yaml
# action
  - action: climate.set_temperature
    target:
      entity_id: climate.bedroom
    data:
      temperature: 23
```

And the description opening:

```yaml
description: >-
  When the bedroom is over 26.5°C during the evening run-up to bedtime
  (21:00–23:00), set the AC to cool toward 23°C. Reads the overlay
  sensor.bedroom_temperature (true room air). Skips if the AC is unavailable or
  already cooling.
```
(keep the existing second paragraph unchanged)

- [ ] **Step 3: Lint both files**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_off.yaml \
        packages/areas/first-floor/bedroom/automations/bedroom_ac_cooldown_on.yaml
git commit -m "feat(bedroom-ac): recalibrate thresholds — off<=25.0, on>26.5, setpoint 23"
```

---

### Task 3: Gate the safety timeout on empty room

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`

**Interfaces:**
- Consumes: `input_boolean.bedroom_occupied` (debounced authoritative occupancy latch from `bedroom_occupancy_state_machine`), `climate.bedroom`.
- Produces: 3h hard-off fires **only when the room is empty**; occupied → no-op (temperature-based off handles it).

- [ ] **Step 1: Add the occupancy gate after the 3h delay**

Rewrite the file to add a mid-sequence condition. Do NOT use raw `binary_sensor.bedroom_occupancy` (it flaps during stillness — would fire on a sleeping person). Use the debounced `input_boolean.bedroom_occupied`.

```yaml
---
alias: Bedroom AC safety max-runtime
description: >-
  Hard backstop for an EMPTY room: 3h after the AC enters cool mode, turn it
  off — but only if nobody is in the bedroom. When the room is occupied, the
  temperature-based off (sensor.bedroom_temperature <= 25.0°C) is the only
  stop, so a sleeper isn't cut off after 3h. Protects against a stuck sensor /
  AC left running in an empty room. mode restart resets the timer each time
  cooling (re)starts. Occupancy source is input_boolean.bedroom_occupied — the
  debounced latch that rides out mmWave still-gaps — NOT the raw mmWave sensor.
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
  # Only hard-stop an empty room. If occupied at the 3h mark, end without
  # acting — temperature-based off owns the occupied case.
  - condition: state
    entity_id: input_boolean.bedroom_occupied
    state: "off"
  - action: climate.turn_off
    target:
      entity_id: climate.bedroom
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ac_safety_timeout.yaml
git commit -m "feat(bedroom-ac): safety 3h hard-off only when room empty"
```

---

### Task 4: Config check, push, reload, live verification

**Files:** none (integration + verification).

- [ ] **Step 1: Full HA config check**

Run: `just check`
Expected: config valid, no errors. (If `just check` unavailable, use the HA `check_config` service.)

- [ ] **Step 2: Full pre-commit sweep**

Run: `uv run pre-commit run --all-files`
Expected: all hooks Pass/Skip, none Failed.

- [ ] **Step 3: Push the branch**

```bash
git push -u origin feat/bedroom-ac-occupancy-safety
```

- [ ] **Step 4: Reload HA core config + check logs**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -X POST "$HA_URL/api/services/homeassistant/reload_core_config" -d '{}'
```
Then reload automations + template entities (or restart if template platform needs it):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -X POST "$HA_URL/api/services/automation/reload" -d '{}'
curl -s -H "Authorization: Bearer $HA_TOKEN" -X POST "$HA_URL/api/services/template/reload" -d '{}'
```
Run all with `dangerouslyDisableSandbox: true`. Then fetch the error log:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -30
```
Expected: no new errors referencing `bedroom_temperature`, `bedroom_ac_*`, or template render.

- [ ] **Step 5: Verify the overlay reads real room temp**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.bedroom_temperature" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('state=',d['state'],'source=',d['attributes'].get('source'))"
```
Expected: `state` ≈ current hygro value (not FP300); `source=hygro` (assuming hygro fresh). Compare against `sensor.bedroom_hygro_temperature` — should match within rounding.

- [ ] **Step 6: Verify off-automation can now trigger (threshold reachable)**

Render the off-condition against the live control temp:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -X POST "$HA_URL/api/template" -d '{"template": "control={{ states(\"sensor.bedroom_temperature\") }} would_off_at_25={{ states(\"sensor.bedroom_temperature\") | float <= 25.0 }}"}'
```
Run with `dangerouslyDisableSandbox: true`.
Expected: prints the control temp and whether it's already ≤25.0. The point: the value now lives in the 24.5–30 band, so ≤25.0 is reachable on a cooled night — unlike the old 23.1.

- [ ] **Step 7: Confirm automation entities loaded (no unavailable/None)**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" | python3 -c "
import sys,json
want={'automation.bedroom_ac_evening_cooldown_off_target_reached','automation.bedroom_ac_evening_cooldown_on','automation.bedroom_ac_safety_max_runtime'}
for s in json.load(sys.stdin):
    if s['entity_id'] in want: print(s['entity_id'],'=',s['state'])"
```
Expected: all three `on` (loaded, enabled), none `unavailable`.

- [ ] **Step 8: Open a PR**

```bash
gh pr create --base main --head feat/bedroom-ac-occupancy-safety \
  --title "Bedroom AC: occupancy-gated safety + threshold recalibration" \
  --body "See docs/superpowers/specs/2026-07-02-bedroom-ac-occupancy-safety-and-thresholds-design.md. Off now fires on real room temp (blended hygro/FP300 overlay, off<=25.0, on>26.5, setpoint 23). 3h hard-off only when room empty (input_boolean.bedroom_occupied)."
```

- [ ] **Step 9: Overnight trace check (next morning)**

After one night, pull the logbook/trace for the three automations. Confirm:
- `..._cooldown_off_target_reached` **fired on temperature** (not None anymore) if the room reached ≤25.0 while occupied.
- `..._safety_max_runtime` did **not** turn off the AC while `input_boolean.bedroom_occupied` was `on`.
- No pre-dawn over-cool below ~25°C on the hygro at waking.

---

## Post-implementation: capture knowledge

- [ ] If the sensor-bias / unreachable-threshold gotcha isn't already covered by the existing `numeric-state-trigger-edge-not-level` leaf, invoke `knowledge-author` to add: "bedroom control temp is an overlay blending hygro + bias-corrected FP300; a mmWave/Matter temp probe reads ~1.3°C hot, so thresholds set against it are unreachable." Cross-link the two leaves.

---

## Self-review notes

- **Spec coverage:** overlay blend (Task 1) ✓, thresholds off/on/setpoint (Task 2) ✓, occupancy-gated safety (Task 3) ✓, config-check/reload/verify (Task 4) ✓, knowledge capture ✓.
- **Constants consistent:** bias 1.3, freshness 2700s (=45min), off 25.0 (below:25.05), on 26.5, setpoint 23 — same everywhere.
- **No new entity:** overlay contract preserved; all AC autos keep reading `sensor.bedroom_temperature`.
- **Occupancy source:** `input_boolean.bedroom_occupied` (debounced), explicitly NOT raw `binary_sensor.bedroom_occupancy` — called out in Task 3 to prevent the reviewer "simplifying" to the raw sensor.
