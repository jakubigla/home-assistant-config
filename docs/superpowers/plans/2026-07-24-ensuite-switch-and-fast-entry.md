# Ensuite switch pivot + bedroom→ensuite fast-entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make any ensuite left-button press pivot the main light around 100% (single/double raise then toggle-off/dim, hold kills all), and light the ensuite fully when someone enters the bedroom then steps into the ensuite within 5 minutes.

**Architecture:** Two existing automations in the bedroom package edited in place — no new helpers. Verification is HA-native: `just check` config validation, then push → reload → log check → live test (this repo has no automation unit-test harness).

**Tech Stack:** Home Assistant YAML automations, Jinja2 templates, MQTT device triggers.

## Global Constraints

- Never push to `main`. Current branch: `feat/irrigation-two-zones-vertical-garden`.
- After push, reload HA config (`homeassistant.reload_core_config`) and check logs — errors invisible until reload.
- `curl` against HA needs `dangerouslyDisableSandbox: true`; env vars (`$HA_URL`, `$HA_TOKEN`) preloaded via direnv.
- Lint via `uv run` only, never `pip`. Config check: `just check`.
- Automation `id`/`alias` unchanged (editing in place, not replacing).
- Main-at-100% test template, used verbatim in both files: `state_attr('light.ensuite_bathroom_main', 'brightness') | int(0) >= 254`.

---

### Task 1: Switch pivot logic + hold

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml` (full rewrite of triggers + actions; keep `id`, `alias`)

**Interfaces:**
- Consumes: `light.ensuite_bathroom_main` (6-bulb group), `light.ensuite_bathroom_main_power` (relay), `light.ensuite_bathroom` (full group: 6 bulbs + leds + mirror), `input_boolean.ensuite_manual_override`, MQTT device `a042eb964ead9c014809c93d2d7610de` subtypes `single_left` / `double_left` / `hold_left`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Rewrite the file**

Replace entire contents of `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml` with:

```yaml
---
alias: En suite Bathroom lights switch
description: >
  Left wall button. Press pivots the main light around 100%: single/double
  first raise the main to 100% (and set manual override so presence stops
  driving the lights) whenever it is off or dimmed. Only once already at 100%
  do the two diverge — single turns off + clears override, double dims to 20%.
  Hold always kills every ensuite light and clears the override.
id: af54c161-50b6-4fd6-8839-2f2a2cd25fb7

mode: single
max_exceeded: silent

triggers:
  - domain: mqtt
    device_id: a042eb964ead9c014809c93d2d7610de
    type: action
    subtype: single_left
    trigger: device
  - domain: mqtt
    device_id: a042eb964ead9c014809c93d2d7610de
    type: action
    subtype: double_left
    trigger: device
  - domain: mqtt
    device_id: a042eb964ead9c014809c93d2d7610de
    type: action
    subtype: hold_left
    trigger: device

actions:
  - choose:
      # Hold: kill every ensuite light, clear override so presence resumes.
      - conditions:
          - condition: template
            value_template: "{{ trigger.payload == 'hold_left' }}"
        sequence:
          - action: light.turn_off
            target:
              entity_id: light.ensuite_bathroom
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.ensuite_manual_override
      # Single at 100% -> off + clear override.
      - conditions:
          - condition: template
            value_template: "{{ trigger.payload == 'single_left' }}"
          - condition: template
            value_template: >-
              {{ state_attr('light.ensuite_bathroom_main', 'brightness')
                 | int(0) >= 254 }}
        sequence:
          - action: light.turn_off
            target:
              entity_id: light.ensuite_bathroom_main
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.ensuite_manual_override
      # Double at 100% -> dim to 20% (stays on, override already set).
      - conditions:
          - condition: template
            value_template: "{{ trigger.payload == 'double_left' }}"
          - condition: template
            value_template: >-
              {{ state_attr('light.ensuite_bathroom_main', 'brightness')
                 | int(0) >= 254 }}
        sequence:
          - action: light.turn_on
            data:
              entity_id: light.ensuite_bathroom_main
              brightness_pct: 20
      # Single or double, main off or dimmed (<100%) -> raise to full.
      - conditions:
          - condition: template
            value_template: >-
              {{ trigger.payload in ['single_left', 'double_left'] }}
        sequence:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.ensuite_manual_override
          - action: light.turn_on
            target:
              entity_id: light.ensuite_bathroom_main_power
          - action: light.turn_on
            data:
              entity_id: light.ensuite_bathroom_main
              brightness_pct: 100
```

Note ordering: the two `=100%` branches sit before the catch-all `single/double` branch, so the catch-all only fires when the light is off or <100%.

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml`
Expected: no errors (clean exit).

- [ ] **Step 3: HA config check**

Run: `just check`
Expected: config valid, no new errors mentioning `ensuite_bathroom_lights_switch` or `af54c161`.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml
git commit -m "feat(ensuite): switch pivots main around 100%, hold kills all"
```

---

### Task 2: Bedroom→ensuite fast-entry override

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml` (turn-on branch only; keep `id`, `alias`, triggers, conditions, and the `vacant` branch)

**Interfaces:**
- Consumes: `input_boolean.bedroom_occupied` (`last_changed` age), `light.ensuite_bathroom_main`, `light.en_suite_bulb_top_middle`, `light.bedroom_non_bed`, `sun.sun`, `binary_sensor.sleeping_time`, `light.ensuite_bathroom_main_power`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Replace the night-dim if/else with a three-way if/elif/else**

In `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml`, inside the turn-on branch sequence, the relay-ensure `light.turn_on` on `light.ensuite_bathroom_main_power` stays first, unchanged. Replace the block that starts at the `- if:` (the sun-down / sleeping_time dim) through the end of its `else:` with:

```yaml
          # Fast-entry: person just walked into the bedroom and stepped
          # straight into the ensuite (latch flipped on < 5 min ago) -> light
          # the main fully, skipping the comfort-dim. Latch stays on all night,
          # so a mid-night toilet trip finds it old and falls through to 1%.
          - if:
              - condition: state
                entity_id: input_boolean.bedroom_occupied
                state: "on"
              - condition: template
                value_template: >
                  {{ (now() -
                     states.input_boolean.bedroom_occupied.last_changed
                     ).total_seconds() < 300 }}
            then:
              - action: light.turn_on
                data:
                  entity_id: light.ensuite_bathroom_main
                  brightness_pct: 100
            else:
              # Night-dim when the sun is down OR it's sleeping_time. Sun alone
              # is too coarse in summer: at a 04:40 toilet trip the sun is up
              # (~04:30 sunrise) but it's still the middle of the humans' night,
              # so the room must stay at the 1% middle bulb, not the bright main.
              - if:
                  - condition: or
                    conditions:
                      - condition: state
                        entity_id: sun.sun
                        state: below_horizon
                      - condition: state
                        entity_id: binary_sensor.sleeping_time
                        state: "on"
                then:
                  - action: light.turn_on
                    data:
                      entity_id: light.en_suite_bulb_top_middle
                      brightness_pct: 1
                else:
                  # Use bedroom_non_bed (ceiling/wall lights), NOT the
                  # light.bedroom group: the group includes bed_stripe, which
                  # the sleep nightlight pulses to 1% on an ensuite-door trip —
                  # that would flip this to 100% mid-trip. non_bed only reads
                  # true when the room is really lit.
                  - action: light.turn_on
                    data:
                      entity_id: light.ensuite_bathroom_main
                      brightness_pct: >
                        {{ 100 if is_state('light.bedroom_non_bed', 'on') else 20 }}
```

The `vacant` branch (turn off `light.ensuite_bathroom`) below is untouched.

- [ ] **Step 2: Lint the file**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml`
Expected: no errors.

- [ ] **Step 3: HA config check**

Run: `just check`
Expected: config valid, no new errors mentioning `ensuite_bathroom_presence` or `067898ef`.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml
git commit -m "feat(ensuite): bedroom fast-entry (<5min) lights main to 100%"
```

---

### Task 3: Deploy + verify live

**Files:** none (deploy + runtime verification).

- [ ] **Step 1: Push the branch**

```bash
git push
```

- [ ] **Step 2: Reload HA config**

Reload via MCP/API: call `homeassistant.reload_core_config` (or restart if trigger-set changed require it). Then re-check the reloaded config picked up the branch (per repo memory: no pull lag — if not live, the addon branch is wrong, not lagging).

- [ ] **Step 3: Check logs for errors**

Query HA error log (API `/api/error_log` or MCP). Expected: no errors referencing `ensuite_bathroom_lights_switch`, `ensuite_bathroom_presence`, `af54c161`, or `067898ef`.

**`hold_left` verification (spec assumption):** confirm the automation loaded with all three triggers and that pressing hold fires it. If the device does not emit `hold_left`, the automation still loads but hold does nothing — check the automation trace / logbook after a physical hold press. If hold never fires, report back: the `hold_left` trigger + branch must be dropped from Task 1.

- [ ] **Step 4: Live behavior check**

Verify (physical presses + `GetLiveContext` / logbook), reporting results:
- main OFF → single → main 100%, override on.
- main OFF → double → main 100%, override on.
- main 20% → single → main 100% (NOT off).
- main 100% → single → main off, override off.
- main 100% → double → main 20%.
- hold (any state) → all ensuite lights off, override off.
- Fast-entry: with sun down or sleeping_time on, enter bedroom (latch flips on) then trigger ensuite occupancy within 5 min → main 100%, not 1%.
- Mid-night: latch already old (>5 min) + sun down → ensuite occupancy → 1% top_middle (unchanged).

---

## Notes for the implementer

- No unit tests: HA automations aren't unit-testable in this repo. Verification is `yamllint` + `just check` + live runtime check.
- Do NOT rename `alias`/`id` — presence of the existing id keeps HA's automation registry stable.
- If `just check` isn't available or fails for unrelated reasons, fall back to `uv run yamllint .` for syntax and rely on the reload log check.
