# Ensuite Presence & Lighting Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild ensuite presence/lighting as a three-layer state machine that stops occupancy flapping, respects the wall switch, and never leaves the power relay (which feeds the Zigbee bulbs) stuck on.

**Architecture:** Layer 1 = an `input_boolean` occupancy latch driven by door + two coverage-zone sensors (PIR at entrance, mmWave at shower). Layer 2 = a lights automation that reads occupancy + `is_dark` + manual-override and always ensures the power relay is on before commanding bulbs. Layer 3 = a manual-override `input_boolean` set by the wall switch with a safety timeout. A vacancy backstop sweeps after 10 min.

**Tech Stack:** Home Assistant YAML packages (`packages/areas/first-floor/bedroom/`), `input_boolean`, template `binary_sensor`, automations (`!include_dir_list automations`, one automation per file). Verification via `just check`, push to feature branch, `homeassistant.reload_core_config` + automation reload, then `hass-cli` / logbook live checks. No unit-test framework — "tests" are HA config-check + observed live behavior.

**Spec:** `docs/superpowers/specs/2026-05-26-ensuite-presence-lighting-rebuild-design.md`

**Branch:** already on `chore/may-fixes` (feature branch). Never push to `main`.

---

## Conventions for every task

- One automation per file (matches existing `automations/` convention; `!include_dir_list` makes each file a list item — keep each file a single YAML doc with one automation).
- After any YAML change: `just check` (HA config validity) and `uv run yamllint .` must pass before commit.
- "Verify live" steps require the change to be **pushed and reloaded** first — local edits are not live on HA until pushed (HA auto-pulls the branch). After push, reload and check logs (see reload-after-push knowledge leaf).
- Sandbox blocks `homeassistant.local`; all `curl`/`hass-cli` against HA from this plan assume the env vars (`$HA_URL`, `$HA_TOKEN`) and, for `curl`, `dangerouslyDisableSandbox: true`.
- mmWave = `binary_sensor.ensuite_bathroom_presence` (shower/room, holds through stillness). PIR = `binary_sensor.ensuite_bathroom_motion` (entrance, fast). **Exit must require mmWave off; PIR-off alone never clears the latch.**

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `packages/areas/first-floor/bedroom/config.yaml` | declares the two new `input_boolean`s | Modify |
| `.../templates/binary_sensors/ensuite_bathroom_occupancy.yaml` | occupancy sensor mirrors the latch | Rewrite |
| `.../automations/ensuite_occupancy_state_machine.yaml` | Layer 1 — entry/exit latch | Create |
| `.../automations/ensuite_bathroom_presence.yaml` | Layer 2 — lights (override-aware, relay-ensure) | Rewrite |
| `.../automations/ensuite_bathroom_lights_switch.yaml` | Layer 3 — wall switch sets/clears override | Rewrite |
| `.../automations/ensuite_manual_override_timeout.yaml` | Layer 3 — override safety timeout | Create |
| `.../automations/bedroom_ensuite_vacancy_timeout.yaml` | backstop — add override guard, bulbs-only | Modify |

---

## Task 1: Declare the two `input_boolean`s

**Files:**
- Modify: `packages/areas/first-floor/bedroom/config.yaml`

- [ ] **Step 1: Add the booleans under the existing `input_boolean:` block**

In `config.yaml`, the `input_boolean:` block currently ends with `bedroom_humidification_active`. Add two entries after it:

```yaml
  ensuite_occupied:
    name: Ensuite Occupied
    initial: false
    icon: mdi:account
  ensuite_manual_override:
    name: Ensuite Manual Override
    initial: false
    icon: mdi:hand-back-right
```

The block becomes:

```yaml
input_boolean:
  bedroom_movie_mode:
    name: Bedroom Movie Mode
    initial: false
    icon: mdi:movie-open
  bedroom_humidification_active:
    name: Bedroom Humidification Active
    initial: true
    icon: mdi:water-check
  ensuite_occupied:
    name: Ensuite Occupied
    initial: false
    icon: mdi:account
  ensuite_manual_override:
    name: Ensuite Manual Override
    initial: false
    icon: mdi:hand-back-right
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/first-floor/bedroom/config.yaml`
Expected: no output (pass).

- [ ] **Step 3: Config check**

Run: `just check`
Expected: `Configuration valid!` (no errors). A fresh `input_boolean` needs an HA restart/reload to register the entity, so it will not appear live until a reload — that's expected here; we verify live after a later push+reload.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/bedroom/config.yaml
git commit -m "feat(ensuite): add occupancy latch + manual-override booleans"
```

---

## Task 2: Rewrite the occupancy sensor to mirror the latch

**Files:**
- Rewrite: `packages/areas/first-floor/bedroom/templates/binary_sensors/ensuite_bathroom_occupancy.yaml`

Currently the sensor is `presence OR motion` (the flapping source). It must instead reflect `input_boolean.ensuite_occupied`.

- [ ] **Step 1: Replace file contents**

```yaml
---
binary_sensor:
  - name: ensuite_bathroom_occupancy
    device_class: occupancy
    state: "{{ is_state('input_boolean.ensuite_occupied', 'on') }}"
```

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/templates/binary_sensors/ensuite_bathroom_occupancy.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/templates/binary_sensors/ensuite_bathroom_occupancy.yaml
git commit -m "refactor(ensuite): occupancy sensor mirrors latch boolean (was presence OR motion)"
```

> Note: After Task 3 is live, this sensor follows the latch. Until then (between commits) it will read the boolean's initial `off`. That's fine — nothing breaks because the lights automation (Task 4) is rewritten in the same push cycle.

---

## Task 3: Layer 1 — occupancy state machine

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/ensuite_occupancy_state_machine.yaml`

Drives `input_boolean.ensuite_occupied`. Entry on door-open / PIR / mmWave. Exit (a) door-close + 15s + both sensors off. Exit (b) open-door safety: both sensors off for 10 min.

- [ ] **Step 1: Create the file**

```yaml
---
alias: Ensuite occupancy state machine
description: >
  Latch input_boolean.ensuite_occupied. Entry: door open OR PIR (entrance)
  OR mmWave (shower). Exit only when BOTH PIR and mmWave are off — PIR alone
  cannot clear (it does not cover the shower).
id: 1f3c8a90-6b21-4e44-9a7c-2d5e8f10c001

mode: restart
max_exceeded: silent

trigger:
  # --- Entry triggers ---
  - platform: state
    entity_id: binary_sensor.ensuite_door
    from: "off"
    to: "on"
    id: entry
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_motion
    from: "off"
    to: "on"
    id: entry
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_presence
    from: "off"
    to: "on"
    id: entry
  # --- Exit (a): door closed ---
  - platform: state
    entity_id: binary_sensor.ensuite_door
    from: "on"
    to: "off"
    id: exit_door_closed
  # --- Exit (b): open-door safety, both sensors quiet for 10 min ---
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_motion
    to: "off"
    for:
      minutes: 10
    id: exit_safety
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_presence
    to: "off"
    for:
      minutes: 10
    id: exit_safety

condition: []

action:
  - choose:
      # Entry — latch on
      - conditions:
          - condition: trigger
            id: entry
        sequence:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.ensuite_occupied

      # Exit (a): door closed — wait 15s, clear only if BOTH sensors off
      - conditions:
          - condition: trigger
            id: exit_door_closed
        sequence:
          - delay: "00:00:15"
          - condition: state
            entity_id: binary_sensor.ensuite_bathroom_presence
            state: "off"
          - condition: state
            entity_id: binary_sensor.ensuite_bathroom_motion
            state: "off"
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.ensuite_occupied

      # Exit (b): open-door safety — both sensors off 10 min, re-confirm then clear
      - conditions:
          - condition: trigger
            id: exit_safety
        sequence:
          - condition: state
            entity_id: binary_sensor.ensuite_bathroom_presence
            state: "off"
          - condition: state
            entity_id: binary_sensor.ensuite_bathroom_motion
            state: "off"
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.ensuite_occupied
```

> Why `mode: restart`: every fresh entry/exit trigger cancels an in-flight exit delay. Walking back in during the 15s door-close delay re-fires an entry trigger, restarts the automation, and the pending `turn_off` is abandoned — latch stays on.

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_occupancy_state_machine.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_occupancy_state_machine.yaml
git commit -m "feat(ensuite): occupancy latch state machine (door + PIR + mmWave)"
```

---

## Task 4: Layer 2 — lights automation (override-aware, relay-ensure)

**Files:**
- Rewrite: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml`

Drops the `homeassistant start` / `automation_reloaded` triggers. Triggers only on occupancy on→off / off→on. Guards on manual-override off. Every ON path ensures the relay is on + settles before bulb commands. OFF turns off bulbs only (relay stays on).

- [ ] **Step 1: Replace file contents**

```yaml
---
alias: En suite Bathroom lights
description: >
  Drive ensuite bulbs from the occupancy latch. Never cuts the power relay
  (it feeds the Zigbee bulbs); relay is ensured on before any bulb command.
  Skips entirely while manual override is set.
id: 067898ef-0474-4733-b2c9-763d270d432b

mode: restart
max_exceeded: silent

trigger:
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_occupancy
    from: "off"
    to: "on"
    id: occupied
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_occupancy
    from: "on"
    to: "off"
    id: vacant

conditions:
  - condition: state
    entity_id: input_boolean.ensuite_manual_override
    state: "off"

action:
  - choose:
      # Occupied + dark -> ensure relay, settle, then bulbs
      - conditions:
          - condition: trigger
            id: occupied
          - condition: state
            entity_id: binary_sensor.ensuite_bathroom_is_dark
            state: "on"
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.ensuite_bathroom_main_power
          - delay: "00:00:01"
          - if:
              - condition: or
                conditions:
                  - condition: time
                    after: "23:00:00"
                  - condition: time
                    before: "07:30:00"
            then:
              - action: light.turn_on
                data:
                  entity_id: light.en_suite_bulb_top_middle
                  brightness_pct: 1
            else:
              - action: light.turn_on
                data:
                  entity_id: light.ensuite_bathroom_main
                  brightness_pct: >
                    {{ 100 if is_state('light.bedroom', 'on') else 20 }}

      # Vacant -> bulbs off, relay stays on
      - conditions:
          - condition: trigger
            id: vacant
        sequence:
          - alias: "Turn off the bulbs (relay stays on so Zigbee bulbs remain reachable)"
            action: light.turn_off
            target:
              entity_id: light.ensuite_bathroom
```

> The ON branch targets `light.ensuite_bathroom_main` (the 6 bulbs), never `light.ensuite_bathroom_main_with_power` — that group's relay coupling caused the stuck-on bug. The OFF branch targets `light.ensuite_bathroom` (bulbs + leds + mirror) so any of those left on get cleared.

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_bathroom_presence.yaml
git commit -m "refactor(ensuite): lights from latch, relay-ensure, drop reload/start triggers"
```

---

## Task 5: Layer 3 — wall switch sets/clears override

**Files:**
- Rewrite: `packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml`

Right press = full + set override. Left press = toggle: if bulbs on, turn off + clear override (resume auto); if off, set override + relay-ensure + turn on.

- [ ] **Step 1: Replace file contents**

```yaml
---
alias: En suite Bathroom lights switch
description: >
  Wall button. Any "on" press sets manual override so presence stops
  driving the lights; an "off"/toggle-off press clears the override and
  restores auto behaviour. Relay is ensured on before turning bulbs on.
id: af54c161-50b6-4fd6-8839-2f2a2cd25fb7

mode: single

triggers:
  - domain: mqtt
    device_id: 23964fd4d7b9544d2d0bfe12a241178f
    type: action
    subtype: single_right
    trigger: device
  - domain: mqtt
    device_id: 23964fd4d7b9544d2d0bfe12a241178f
    type: action
    subtype: single_left
    trigger: device

actions:
  - choose:
      # Right press -> full on, set override
      - conditions:
          - condition: template
            value_template: "{{ trigger.payload == 'single_right' }}"
        sequence:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.ensuite_manual_override
          - action: light.turn_on
            target:
              entity_id: light.ensuite_bathroom_main_power
          - delay: "00:00:01"
          - action: light.turn_on
            data:
              entity_id: light.ensuite_bathroom_main
              brightness_pct: 100

      # Left press -> toggle
      - conditions:
          - condition: template
            value_template: "{{ trigger.payload == 'single_left' }}"
        sequence:
          - if:
              - condition: state
                entity_id: light.ensuite_bathroom_main
                state: "on"
            then:
              # Currently on -> turn off and hand control back to auto
              - action: light.turn_off
                target:
                  entity_id: light.ensuite_bathroom
              - action: input_boolean.turn_off
                target:
                  entity_id: input_boolean.ensuite_manual_override
            else:
              # Currently off -> manual on
              - action: input_boolean.turn_on
                target:
                  entity_id: input_boolean.ensuite_manual_override
              - action: light.turn_on
                target:
                  entity_id: light.ensuite_bathroom_main_power
              - delay: "00:00:01"
              - action: light.turn_on
                target:
                  entity_id: light.ensuite_bathroom_main
```

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_bathroom_lights_switch.yaml
git commit -m "feat(ensuite): wall switch sets/clears manual override"
```

---

## Task 6: Layer 3 — manual-override safety timeout

**Files:**
- Create: `packages/areas/first-floor/bedroom/automations/ensuite_manual_override_timeout.yaml`

Clears the override after 15 min of no presence/motion so a manual press never sticks forever.

- [ ] **Step 1: Create the file**

```yaml
---
alias: Ensuite manual override safety timeout
description: >
  Clear input_boolean.ensuite_manual_override after 15 min with no presence
  or motion, so a manual wall press never disables auto lighting forever.
id: 1f3c8a90-6b21-4e44-9a7c-2d5e8f10c002

mode: restart
max_exceeded: silent

trigger:
  - platform: state
    entity_id: input_boolean.ensuite_manual_override
    from: "off"
    to: "on"
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_presence
    to: "on"
  - platform: state
    entity_id: binary_sensor.ensuite_bathroom_motion
    to: "on"

condition:
  - condition: state
    entity_id: input_boolean.ensuite_manual_override
    state: "on"

action:
  - delay:
      minutes: 15
  - condition: state
    entity_id: binary_sensor.ensuite_bathroom_presence
    state: "off"
  - condition: state
    entity_id: binary_sensor.ensuite_bathroom_motion
    state: "off"
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.ensuite_manual_override
```

> `mode: restart` + presence/motion triggers: every movement resets the 15-min timer, so the override only clears after the room has been genuinely quiet for 15 min.

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/ensuite_manual_override_timeout.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/ensuite_manual_override_timeout.yaml
git commit -m "feat(ensuite): manual override safety timeout (15 min)"
```

---

## Task 7: Vacancy backstop — add override guard, keep bulbs-only

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_ensuite_vacancy_timeout.yaml`

The existing automation already targets `light.ensuite_bathroom` (bulbs, not relay) for the ensuite — leave that. Add a manual-override guard so a held manual press isn't stomped.

- [ ] **Step 1: Add the override condition**

Change the `conditions:` block from:

```yaml
conditions:
  - condition: and
    conditions:
      - condition: state
        entity_id: binary_sensor.bedroom_presence
        state: "off"
      - condition: state
        entity_id: binary_sensor.ensuite_bathroom_occupancy
        state: "off"
```

to:

```yaml
conditions:
  - condition: and
    conditions:
      - condition: state
        entity_id: binary_sensor.bedroom_presence
        state: "off"
      - condition: state
        entity_id: binary_sensor.ensuite_bathroom_occupancy
        state: "off"
      - condition: state
        entity_id: input_boolean.ensuite_manual_override
        state: "off"
```

Leave the `trigger:` and `action:` blocks unchanged (action already targets `light.ensuite_bathroom`, bulbs only — confirm it does NOT list `light.ensuite_bathroom_main_power`).

- [ ] **Step 2: Lint + config check**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_ensuite_vacancy_timeout.yaml && just check`
Expected: yamllint clean; `Configuration valid!`.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_ensuite_vacancy_timeout.yaml
git commit -m "fix(ensuite): vacancy backstop respects manual override"
```

---

## Task 8: Push, reload, and verify the new entities exist

**Files:** none (deploy + verify)

- [ ] **Step 1: Push the branch**

```bash
git push
```

- [ ] **Step 2: Wait for HA to pull, then reload**

HA's pull addon lags ~3–6 min after push. Confirm the latest commit is on HA's disk before reloading (per the ha-pull-lag knowledge leaf). Then reload config + automations.

Reload core config (MCP `homeassistant.reload_core_config` or REST). For new `input_boolean` + template sensor + automations, also reload those domains, or do a full config reload via Developer Tools. New `input_boolean` entities require a `homeassistant.reload_core_config` (or restart) to register.

REST example (needs `dangerouslyDisableSandbox: true`):

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_core_config"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/automation/reload"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/template/reload"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/input_boolean/reload"
```

- [ ] **Step 3: Check logs for errors after reload**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -40
```
Expected: no new errors referencing `ensuite`, the new automation ids, or `input_boolean.ensuite_*`.

- [ ] **Step 4: Verify the new entities registered**

```bash
cat > /tmp/ens_verify.tpl <<'EOF'
occupied:        {{ states('input_boolean.ensuite_occupied') }}
manual_override: {{ states('input_boolean.ensuite_manual_override') }}
occupancy:       {{ states('binary_sensor.ensuite_bathroom_occupancy') }}
EOF
uv run hass-cli template /tmp/ens_verify.tpl
```
Expected: all three resolve (not `unknown`/`unavailable`); `occupancy` equals `occupied`.

---

## Task 9: Live behavior verification

**Files:** none (observe). Use the logbook to correlate. For each check, perform the physical action (or note it can only be confirmed in-person) and read state via `hass-cli` / logbook.

- [ ] **Step 1: Flapping — sit still**

Enter ensuite, then stand/sit still ~1 min. Read:
```bash
cat > /tmp/c.tpl <<'EOF'
latch: {{ states('input_boolean.ensuite_occupied') }} | mmwave: {{ states('binary_sensor.ensuite_bathroom_presence') }} | pir: {{ states('binary_sensor.ensuite_bathroom_motion') }}
EOF
uv run hass-cli template /tmp/c.tpl
```
Expected: `latch on` and stays on through stillness (mmWave holds). Logbook shows bulbs turned on once, no pulsing.

- [ ] **Step 2: Stuck relay — leave room**

Leave, close door, wait >15s. Read:
```bash
cat > /tmp/r.tpl <<'EOF'
latch: {{ states('input_boolean.ensuite_occupied') }}
ensuite_group: {{ states('light.ensuite_bathroom') }}
relay: {{ states('light.ensuite_bathroom_main_power') }}
top_mid_bulb: {{ states('light.en_suite_bulb_top_middle') }}
EOF
uv run hass-cli template /tmp/r.tpl
```
Expected: `latch off`, `ensuite_group off`, bulbs off, but `relay on` and bulbs **available** (not `unavailable`).

- [ ] **Step 3: Open-door exit (safety timeout)**

Enter, leave door open, do not re-enter. After ~10 min with both sensors quiet, latch clears and bulbs go off. Confirm via logbook entry for `ensuite_occupancy_state_machine` exit_safety.

- [ ] **Step 4: Wall switch override holds**

Press the wall button (on). Confirm `input_boolean.ensuite_manual_override` = `on`. Then move (trigger motion) and confirm the presence automation does NOT change the bulbs (logbook shows no `En suite Bathroom lights` action). Press off → override clears (`off`) and bulbs off.

- [ ] **Step 5: Override safety auto-clear**

With override on and the room left empty, after 15 min of no presence/motion confirm `ensuite_manual_override` → `off` (logbook entry from `Ensuite manual override safety timeout`).

- [ ] **Step 6: Cold relay — smooth start**

Manually turn the relay off (`light.turn_off light.ensuite_bathroom_main_power`); bulbs go `unavailable`. Then trigger entry (open door). Expected: relay turns on, 1s settle, bulbs come on (may need a 2nd entry event if 1s is too short for Zigbee rejoin — note in findings if so).
```bash
# force relay off to simulate edge case
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"light.ensuite_bathroom_main_power"}' \
  "$HA_URL/api/services/light/turn_off"
```

- [ ] **Step 7: Reload does not flip lights**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload"
```
Expected: ensuite bulbs unchanged (no `homeassistant start` / `automation_reloaded` trigger anymore).

- [ ] **Step 8: Tune settle delay if needed**

If Step 6 showed bulbs failing to come on at first entry (Zigbee rejoin slower than 1s), bump the `delay: "00:00:01"` in `ensuite_bathroom_presence.yaml` and `ensuite_bathroom_lights_switch.yaml` to `00:00:02`, then `just check`, commit (`fix(ensuite): lengthen relay-wake settle to 2s`), push, reload, re-test.

---

## Task 10: Regenerate the bedroom README

**Files:**
- Modify: `packages/areas/first-floor/bedroom/README.md` (generated)

- [ ] **Step 1: Regenerate area docs**

Invoke the `/ha-area-docs` skill for the bedroom area (it covers ensuite). It will pick up the new automations, booleans, and the rewritten occupancy sensor.

- [ ] **Step 2: Commit**

```bash
git add packages/areas/first-floor/bedroom/README.md
git commit -m "docs(bedroom): regenerate README after ensuite rebuild"
```

---

## Task 11: Capture the relay-feeds-bulbs gotcha as a knowledge leaf

**Files:** handled by the knowledge-author skill (do not hand-write leaves).

- [ ] **Step 1: Invoke knowledge-author**

Invoke the `knowledge-author` skill with this fact: *In the ensuite, `light.ensuite_bathroom_main_power` ("Main") is an on/off relay that is the hard power feed for the six `light.en_suite_bulb_*` Zigbee bulbs — cutting it makes the bulbs go `unavailable` and drop off the Zigbee mesh (verified by history correlation). Therefore automations must never cut the relay to turn lights "off"; turn the bulbs off via bulb commands and leave the relay on. Any "on" path must ensure the relay is on (and settle ~1–2s) before commanding bulbs, so it recovers smoothly from a cold relay after restart.* Bucket: `areas/`. Let knowledge-author handle dedup, frontmatter, INDEX rebuild, validation, and commit.

---

## Done when

- All 7 config files committed and pushed; HA reloaded with no errors.
- Live checks (Task 9) pass: no flapping, no stuck relay, override holds + auto-clears, smooth cold-relay start, reload-safe.
- README regenerated; knowledge leaf captured.
