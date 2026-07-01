# Bedroom Occupancy-Driven Lights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make in-room mmWave occupancy the truth source for bedroom lights so stillness-in-bed never reads as vacant, while guaranteeing lights never auto-on during sleep.

**Architecture:** A new `input_boolean.bedroom_occupied` latch is driven by a state-machine automation (entry on entrance OR occupancy edge; exit on both-clear-60s; 30-min stuck-latch watchdog). Two existing automations (`bedroom_presence`, `bedroom_vacancy_timeout`) are rewired to read the latch instead of the bare entrance sensor.

**Tech Stack:** Home Assistant YAML packages. `input_boolean` helper, `automation` with `choose`/trigger-id pattern, `binary_sensor` mmWave + FP2. No Python.

## Global Constraints

- This is a HA YAML config repo — there is NO pytest/unit-test harness. "Test" = static validation (`just lint`, `just check`) plus post-push live verification against the running HA instance.
- Automation filenames: `{area}_{action}_{trigger}.yaml`; descriptive `alias`; unique `id`. (CLAUDE.md)
- Never push to `main`. Work on the current feature branch `chore/june-features`. (CLAUDE.md)
- After every push: reload HA core config (`homeassistant.reload_core_config`) AND check logs — errors stay invisible until reload. (reload-after-push leaf)
- Sandbox blocks `homeassistant.local`; any curl to HA needs `dangerouslyDisableSandbox: true`.
- Env vars (`$HA_URL`, `$HA_TOKEN`, `$API_ACCESS_TOKEN`) are preloaded via direnv — use directly, never read `.env`.
- Follow the area-pattern reference (`.claude/rules/area-patterns.md`) and the proven sibling `ensuite_occupancy_state_machine.yaml`.

---

### Task 1: Add the `bedroom_occupied` latch helper

**Files:**
- Modify: `packages/areas/first-floor/bedroom/config.yaml` (the `input_boolean:` block, after line 22)

**Interfaces:**
- Consumes: nothing.
- Produces: `input_boolean.bedroom_occupied` — the latch all later tasks read/write.

- [ ] **Step 1: Add the helper**

In `config.yaml`, inside the existing `input_boolean:` block, add a new entry alongside `ensuite_occupied`:

```yaml
  bedroom_occupied:
    name: Bedroom Occupied
    initial: false
    icon: mdi:bed
```

- [ ] **Step 2: Validate YAML**

Run: `just lint`
Expected: PASS (no yamllint errors).

- [ ] **Step 3: Validate HA config**

Run: `just check`
Expected: `Configuration valid!` (or equivalent success; no errors mentioning bedroom_occupied).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/config.yaml
git commit -m "feat(bedroom): add bedroom_occupied latch helper"
```

---

### Task 2: Create the occupancy state machine

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/bedroom_occupancy_state_machine.yaml`

**Interfaces:**
- Consumes: `binary_sensor.bedroom_entrance_presence`, `binary_sensor.bedroom_occupancy`, `input_boolean.bedroom_occupied` (Task 1).
- Produces: drives `input_boolean.bedroom_occupied` ON/OFF. Later tasks trigger off this boolean's state transitions.

- [ ] **Step 1: Write the automation file**

Create the file with exactly this content (mirrors `ensuite_occupancy_state_machine.yaml`):

```yaml
---
alias: Bedroom occupancy state machine
description: >
  Latch input_boolean.bedroom_occupied. Entry: entrance presence (FP2) OR
  in-room mmWave (bedroom_occupancy). Exit when BOTH are off for 60 s — the
  60 s debounce rides out mmWave still-gaps so lying still in bed never clears
  the latch. Watchdog clears a stuck latch after 30 min if mmWave is
  off/unavailable (HA restart, sensor drop missing the off-edge).
id: 2b7e4c10-9d33-4f5a-8c21-6a1f0e92d100

mode: restart
max_exceeded: silent

trigger:
  - platform: state
    entity_id: binary_sensor.bedroom_entrance_presence
    from: "off"
    to: "on"
    id: entry
  - platform: state
    entity_id: binary_sensor.bedroom_occupancy
    from: "off"
    to: "on"
    id: entry
  - platform: state
    entity_id:
      - binary_sensor.bedroom_entrance_presence
      - binary_sensor.bedroom_occupancy
    to: "off"
    for:
      seconds: 60
    id: exit
  # Watchdog: latch stuck on (HA restart / mmWave unavailable missed the
  # off-edge). Edge-independent — fires on duration. mode: restart resets the
  # 30 min on every real re-entry.
  - platform: state
    entity_id: input_boolean.bedroom_occupied
    to: "on"
    for:
      minutes: 30
    id: watchdog

condition: []

action:
  - choose:
      - conditions:
          - condition: trigger
            id: entry
        sequence:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.bedroom_occupied
      # Exit: only clear when BOTH sensors are off (the for:60s trigger fires
      # per-entity, so re-check the other one before clearing).
      - conditions:
          - condition: trigger
            id: exit
          - condition: state
            entity_id: binary_sensor.bedroom_entrance_presence
            state: "off"
          - condition: state
            entity_id: binary_sensor.bedroom_occupancy
            state: "off"
        sequence:
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.bedroom_occupied
      # Stuck-latch watchdog: clear if mmWave is off OR unavailable.
      - conditions:
          - condition: trigger
            id: watchdog
          - condition: not
            conditions:
              - condition: state
                entity_id: binary_sensor.bedroom_occupancy
                state: "on"
        sequence:
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.bedroom_occupied
```

- [ ] **Step 2: Validate YAML**

Run: `just lint`
Expected: PASS.

- [ ] **Step 3: Validate HA config**

Run: `just check`
Expected: `Configuration valid!`; no error referencing the new automation `id` or entities.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_occupancy_state_machine.yaml
git commit -m "feat(bedroom): occupancy state machine latch (entrance OR mmWave)"
```

---

### Task 3: Rewire `bedroom_presence` to the latch + sleep never-on + 5-min off

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml` (whole file rewrite)

**Interfaces:**
- Consumes: `input_boolean.bedroom_occupied` (Task 1/2), `binary_sensor.bedroom_is_dark`, `binary_sensor.sleeping_time`, `input_boolean.bedroom_movie_mode`, `light.bedroom`, `light.bed_stripe`.
- Produces: drives `light.bed_stripe` (daytime on at entry; off 5 min after latch clears). Tier-2 whole-group off is Task 4.

- [ ] **Step 1: Rewrite the file**

Replace the entire contents of `bedroom_presence.yaml` with:

```yaml
---
alias: Bedroom presence
description: >
  Drive bed_stripe from the bedroom_occupied latch (entrance OR mmWave, via
  bedroom_occupancy_state_machine). On entry during the day, warm-dim the bed
  stripe. NEVER auto-on during sleeping_time — a re-latch or HA restart at
  night must not wake anyone. Tier-1 auto-off: bed_stripe off 5 min after the
  latch clears. (Tier-2 whole-group off lives in bedroom_vacancy_timeout.)
id: 13b5c7e1-409e-485e-b52b-b4f07adbe059

mode: restart
max_exceeded: silent

trigger:
  - trigger: homeassistant
    event: start
  - trigger: event
    event_type: automation_reloaded
  - platform: state
    entity_id: input_boolean.bedroom_occupied
    from: "off"
    to: "on"
    id: occupied
  - platform: state
    entity_id: input_boolean.bedroom_occupied
    from: "on"
    to: "off"
    for:
      minutes: 5
    id: vacated

conditions: []
action:
  - choose:
      # Daytime entry — warm dim the bed stripe.
      - alias: "Daytime occupied - warm dim bed stripe"
        conditions:
          - condition: trigger
            id: occupied
          - condition: state
            entity_id: binary_sensor.sleeping_time
            state: "off"
          - condition: state
            entity_id: binary_sensor.bedroom_is_dark
            state: "on"
          - condition: state
            entity_id: light.bedroom
            state: "off"
          - condition: state
            entity_id: input_boolean.bedroom_movie_mode
            state: "off"
        sequence:
          - alias: "Turn on bed stripe with warm dim light"
            action: light.turn_on
            data:
              brightness_pct: 50
              color_temp_kelvin: 2951
            target:
              entity_id: light.bed_stripe

      # Sleeping time — never auto-on. (No sequence: the occupied trigger
      # during sleep matches neither branch, so nothing happens.)

      # Tier-1 auto-off — bed_stripe off 5 min after the latch clears.
      - alias: "Vacated 5 min - turn off bed stripe"
        conditions:
          - condition: trigger
            id: vacated
          - condition: state
            entity_id: input_boolean.bedroom_occupied
            state: "off"
        sequence:
          - alias: "Turn off bed stripe"
            action: light.turn_off
            target:
              entity_id: light.bed_stripe
```

- [ ] **Step 2: Validate YAML**

Run: `just lint`
Expected: PASS.

- [ ] **Step 3: Validate HA config**

Run: `just check`
Expected: `Configuration valid!`.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml
git commit -m "feat(bedroom): drive bed_stripe from occupied latch, never auto-on during sleep"
```

---

### Task 4: Rewire `bedroom_vacancy_timeout` to the latch (tier-2 whole-group off)

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_vacancy_timeout.yaml` (whole file rewrite)

**Interfaces:**
- Consumes: `input_boolean.bedroom_occupied` (Task 1/2), `light.bedroom_leds`, `light.bedroom_main`, `light.bedroom_reflectors`, `light.bed_stripe`.
- Produces: whole-group off 10 min after the latch clears.

- [ ] **Step 1: Rewrite the file**

Replace the entire contents of `bedroom_vacancy_timeout.yaml` with:

```yaml
---
alias: Bedroom vacancy timeout
description: >
  Tier-2 whole-group auto-off. Keys off the bedroom_occupied latch (entrance
  OR mmWave) so lying still in bed never trips it — the latch only clears
  after both sensors are off 60 s, then this waits a further 10 min. Ensuite
  is intentionally NOT swept here; it self-manages its own lights.
id: a8f3c9d2-7e41-4b2a-9c1e-5d8f2b4e6a3c

mode: single
max_exceeded: silent

trigger:
  - platform: state
    entity_id: input_boolean.bedroom_occupied
    to: "off"
    for:
      minutes: 10

conditions:
  - condition: state
    entity_id: input_boolean.bedroom_occupied
    state: "off"

action:
  - alias: "Turn off all bedroom lights"
    action: light.turn_off
    target:
      entity_id:
        - light.bedroom_leds
        - light.bedroom_main
        - light.bedroom_reflectors
        - light.bed_stripe
```

- [ ] **Step 2: Validate YAML**

Run: `just lint`
Expected: PASS.

- [ ] **Step 3: Validate HA config**

Run: `just check`
Expected: `Configuration valid!`.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_vacancy_timeout.yaml
git commit -m "feat(bedroom): key whole-group vacancy timeout off occupied latch"
```

---

### Task 5: Deploy, reload, and live-verify

**Files:** none (deployment + verification only).

**Interfaces:**
- Consumes: all of Tasks 1-4.
- Produces: confirmed-live behaviour on the running HA instance.

- [ ] **Step 1: Push the branch**

```bash
git push
```
Expected: push succeeds to `chore/june-features` (NOT main).

- [ ] **Step 2: Reload HA core config**

Use MCP `HassTurnOn`-style service call OR API. Via API:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/homeassistant/reload_core_config" --data '{}'
```
(Use `dangerouslyDisableSandbox: true` for the Bash call since HA host is sandbox-blocked.)
Expected: HTTP 200, empty/`[]` body.

Note: `reload_core_config` reloads core; automations come from `automation: !include_dir_list`. If the new automation does not appear, reload automations too:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/automation/reload" --data '{}'
```

- [ ] **Step 2b: Check logs for errors**

Query the error log via API:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -40
```
Expected: no new errors referencing `bedroom_occupied`, `bedroom_occupancy_state_machine`, `bedroom_presence`, or `bedroom_vacancy_timeout`.

- [ ] **Step 3: Verify the latch tracks occupancy**

Confirm entities exist and the latch is sane:

```bash
hass-cli state get input_boolean.bedroom_occupied
hass-cli state get binary_sensor.bedroom_occupancy
hass-cli state get binary_sensor.bedroom_entrance_presence
```
Expected: `input_boolean.bedroom_occupied` exists. If `bedroom_occupancy` is `on`, the latch should be `on` (or flip on within seconds of the next entry edge).

- [ ] **Step 4: Verify entry latches (manual, while standing in the room)**

With `sleeping_time` OFF and `bedroom_is_dark` ON, confirm presence drives the latch and bed_stripe:
- Walk in → `input_boolean.bedroom_occupied` → `on`.
- `light.bed_stripe` → `on` at 50 % / 2951 K (only if `light.bedroom` was off and movie mode off).

Check via:
```bash
hass-cli state get input_boolean.bedroom_occupied light.bed_stripe 2>/dev/null \
  || for e in input_boolean.bedroom_occupied light.bed_stripe; do hass-cli state get "$e"; done
```

- [ ] **Step 5: Verify sleep never-on (manual)**

Set `sleeping_time` ON (or wait for it), trigger an entrance edge. Expected: `light.bed_stripe` does NOT turn on. The latch may flip on; lights stay off.

- [ ] **Step 6: Verify the watchdog clears a stuck latch**

If after a restart the latch is `on` while you are demonstrably out and `bedroom_occupancy` is `off`, the watchdog clears it within 30 min. (Spot-check by reading the automation trace in HA UI if needed; full 30-min wait is optional.)

- [ ] **Step 7: Note bed_stripe availability caveat**

`light.bed_stripe` and the Sona/Tapo bulbs were observed `unavailable` during planning (Zigbee/cloud drop). If verification shows `unavailable`, that is a device/connectivity issue, NOT an automation bug — re-verify once the bulb is back online. Record this in the verification notes rather than treating it as a failure.

---

## Notes for the implementer

- The state machine's `exit` trigger lists BOTH sensors with `for: 60s`; HA fires it per-entity when that entity hits 60 s off, so the exit branch re-checks the OTHER sensor via mid-sequence conditions before clearing. This is the same shape as ensuite (which only had one mmWave sensor and so needed no cross-check) — here the cross-check is required.
- `bedroom_lights_exclusivity.yaml` is intentionally untouched — it governs manual bed-vs-non-bed mutual exclusivity, orthogonal to presence.
- All four automation `id`s are preserved where they already existed (`bedroom_presence`, `bedroom_vacancy_timeout`) so traces/history stay continuous; the state machine gets a fresh unique `id`.
- After the area package changes land, consider running `/ha-area-docs` to regenerate the bedroom README (per CLAUDE.md convention) — optional, not blocking.
