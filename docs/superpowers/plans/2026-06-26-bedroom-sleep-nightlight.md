# Bedroom Sleep Nightlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faintly light the bed stripe (1% warm) for a night trip to the ensuite and back during sleep, without ever turning on a real light.

**Architecture:** One new HA automation (`mode: restart`) in the bedroom package. Two trigger paths — bedside motion (outbound, fixed 5 s pulse) and ensuite-door open (return, hold until both bedside sensors quiet, 2 min cap). Gated on sleep-time + all real bedroom lights and TV off. `bedroom_presence.yaml` is untouched so its "never auto-on during sleep" invariant stays clean.

**Tech Stack:** Home Assistant package YAML. No Python, no test framework. Verification is `just check` (HA config validation) + push/reload/live trace.

## Global Constraints

- Automation filename convention: `{area}_{action}_{trigger}.yaml` with descriptive `alias` and unique `id` — copied verbatim from CLAUDE.md.
- Never push to `main`; current branch is `chore/june-features`. Use it / a feature branch + PR.
- After any push: reload HA core config + check logs (errors stay invisible until reload).
- All entity IDs below are **live-verified 2026-06-26**. The two bedside motion sensors are named **asymmetrically**:
  - `binary_sensor.bedroom_jakub_side_motion`
  - `binary_sensor.bedroom_sona_side_motion_occupancy` (NOT `bedroom_sona_side_motion` — that does not exist)
- Light command at both phases: `brightness_pct: 1`, `color_temp_kelvin: 2700`, `target.entity_id: light.bed_stripe`.

---

### Task 1: Sleep nightlight automation

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/bedroom_sleep_nightlight.yaml`

**Interfaces:**
- Consumes (existing entities, no new ones created):
  - `binary_sensor.bedroom_jakub_side_motion` (motion, off→on)
  - `binary_sensor.bedroom_sona_side_motion_occupancy` (occupancy, off→on)
  - `binary_sensor.ensuite_door` (door, off→on)
  - `binary_sensor.sleeping_time`
  - `light.bedroom_non_bed` (group: leds + main + reflectors)
  - `light.bedroom_bed` (group: jakub + sona)
  - `light.bed_stripe` (target)
  - `media_player.bedroom_tv`
  - `input_boolean.bedroom_movie_mode`
- Produces: nothing consumed by later tasks (single-task plan).

- [ ] **Step 1: Create the automation file**

Write `packages/areas/first-floor/bedroom/automations/bedroom_sleep_nightlight.yaml` exactly:

```yaml
---
alias: Bedroom sleep nightlight
description: >
  Sleep-time bed-stripe nightlight for ensuite trips. Outbound: a bedside
  motion sensor fires while the room is dark and asleep -> bed stripe to 1%
  warm for a fixed 5 s pulse so you can walk to the ensuite. Return: the
  ensuite door opens -> bed stripe to 1% warm, held a min 5 s, then off once
  BOTH bedside sensors read no motion (you've climbed back in), capped at
  2 min so a stuck sensor can't leave it lit all night. Gated on sleeping_time
  + all real bedroom lights + TV off + not movie mode. Deliberately separate
  from bedroom_presence, which never auto-ons during sleep; this is the
  isolated exception. Off is unconditional at the end of both phases.
id: 7c2e9a14-3f8b-4d6e-9a05-1b7c4e2f8d31

mode: restart
max_exceeded: silent

trigger:
  - platform: state
    entity_id: binary_sensor.bedroom_jakub_side_motion
    from: "off"
    to: "on"
    id: trip
  - platform: state
    entity_id: binary_sensor.bedroom_sona_side_motion_occupancy
    from: "off"
    to: "on"
    id: trip
  - platform: state
    entity_id: binary_sensor.ensuite_door
    from: "off"
    to: "on"
    id: return

conditions: []

action:
  - choose:
      # Outbound: bedside motion during sleep, everything dark -> 5 s pulse.
      - alias: "Outbound trip - 5 s bed-stripe pulse"
        conditions:
          - condition: trigger
            id: trip
          - condition: state
            entity_id: binary_sensor.sleeping_time
            state: "on"
          - condition: state
            entity_id: light.bedroom_non_bed
            state: "off"
          - condition: state
            entity_id: light.bedroom_bed
            state: "off"
          - condition: state
            entity_id: light.bed_stripe
            state: "off"
          - condition: state
            entity_id: media_player.bedroom_tv
            state: "off"
          - condition: state
            entity_id: input_boolean.bedroom_movie_mode
            state: "off"
        sequence:
          - alias: "Bed stripe to 1% warm"
            action: light.turn_on
            data:
              brightness_pct: 1
              color_temp_kelvin: 2700
            target:
              entity_id: light.bed_stripe
          - delay: "00:00:05"
          - alias: "Bed stripe off"
            action: light.turn_off
            target:
              entity_id: light.bed_stripe

      # Return: ensuite door opens during sleep, everything else dark -> hold
      # until both bedside sensors quiet, 2 min cap. (No bed_stripe-off gate:
      # the outbound pulse has ended by now and a strict check would race it.)
      - alias: "Return from ensuite - hold until both bedside sensors quiet"
        conditions:
          - condition: trigger
            id: return
          - condition: state
            entity_id: binary_sensor.sleeping_time
            state: "on"
          - condition: state
            entity_id: light.bedroom_non_bed
            state: "off"
          - condition: state
            entity_id: light.bedroom_bed
            state: "off"
          - condition: state
            entity_id: media_player.bedroom_tv
            state: "off"
          - condition: state
            entity_id: input_boolean.bedroom_movie_mode
            state: "off"
        sequence:
          - alias: "Bed stripe to 1% warm"
            action: light.turn_on
            data:
              brightness_pct: 1
              color_temp_kelvin: 2700
            target:
              entity_id: light.bed_stripe
          - alias: "Minimum 5 s hold"
            delay: "00:00:05"
          - alias: "Wait until both bedside sensors quiet (2 min cap)"
            wait_template: >
              {{ is_state('binary_sensor.bedroom_jakub_side_motion', 'off')
                 and is_state('binary_sensor.bedroom_sona_side_motion_occupancy', 'off') }}
            timeout: "00:02:00"
            continue_on_timeout: true
          - alias: "Bed stripe off"
            action: light.turn_off
            target:
              entity_id: light.bed_stripe
```

- [ ] **Step 2: Lint the YAML**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_sleep_nightlight.yaml`
Expected: no output (clean), exit 0.

- [ ] **Step 3: HA config check**

Run: `just check`
Expected: HA config valid; no error referencing `bedroom_sleep_nightlight`. If the recipe needs the live instance and is unavailable, fall back to Step 4 (push + reload + logs) as the real check.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_sleep_nightlight.yaml
git commit -m "feat(bedroom): sleep nightlight - bed stripe glow for ensuite night trips"
```

- [ ] **Step 5: Push + reload + check logs**

Push the branch. Then reload HA core config (`homeassistant.reload_core_config` via MCP/API) and check the log for errors mentioning the new automation. `curl` against HA needs `dangerouslyDisableSandbox: true`.
Expected: automation `automation.bedroom_sleep_nightlight` exists and is `on`; no config errors in the log.

- [ ] **Step 6: Live trace — outbound**

Set the gate live: confirm `binary_sensor.sleeping_time` is `on` (or temporarily force it), all of `light.bedroom_non_bed`, `light.bedroom_bed`, `light.bed_stripe` off, `media_player.bedroom_tv` off, `input_boolean.bedroom_movie_mode` off. Trip a bedside sensor (walk past, or fire its off→on).
Expected: `light.bed_stripe` goes to 1% warm, then off ~5 s later. Confirm via the automation trace (Settings → Automations → Bedroom sleep nightlight → Traces) that the **outbound** branch ran.

- [ ] **Step 7: Live trace — return**

With the same gate, fire `binary_sensor.ensuite_door` off→on (open the door).
Expected: `light.bed_stripe` to 1% warm; stays on at least 5 s; turns off once both bedside sensors read off, or after 2 min, whichever first. Confirm via trace the **return** branch ran and which exit path (wait satisfied vs timeout) was taken.

---

## Self-Review

**1. Spec coverage:**
- Outbound 5 s pulse → Step 1 outbound branch ✓
- Return hold-until-both-quiet + 2 min cap → Step 1 return branch, `wait_template` + `timeout` + `continue_on_timeout` ✓
- Gate (sleeping_time + non_bed + bed + bed_stripe[outbound] + tv + movie_mode) → both branches' `conditions` ✓
- 1% @ 2700K → both `light.turn_on` calls ✓
- New file, presence untouched → only file created is `bedroom_sleep_nightlight.yaml` ✓
- Asymmetric sensor names → used `bedroom_sona_side_motion_occupancy` throughout ✓
- Unconditional off → both branches end with `light.turn_off`, return uses `continue_on_timeout: true` ✓
- Edge cases (partner light, stuck sensor, restart, prior color) → handled by gate / timeout / forced color_temp; no extra code needed ✓

**2. Placeholder scan:** none. Full YAML inline, exact paths, exact commands.

**3. Type consistency:** trigger ids (`trip`, `return`) match the `condition: trigger` checks in both branches. Entity IDs match the live-verified Global Constraints list.
