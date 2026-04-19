# Security Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Security tab's Zones with security-relevant motion/presence sensors and add a derived "House Access Event" signal to the Recent Activity logbook so entries/exits render as human-readable lines.

**Architecture:** One new trigger-based template sensor (`sensor.house_access_event`) listens for a custom `house_access` event. One new automation watches exterior doors + the Satel `switch.garage_door` pulse and fires the event with direction (`Entry` / `Exit` / `Opened` / `Remote open`) inferred from temporal correlation with `binary_sensor.vestibule_motion`. The Security dashboard (`dashboards/tablet/security.yaml`) gets a rewritten Zones column and logbook card.

**Tech Stack:** Home Assistant YAML (template sensor, automation), Lovelace `sections` dashboard with Mushroom + built-in cards, `yamllint` + `pre-commit` for linting, Playwright MCP for visual validation. No Python, no pytest — verification is HA state inspection + UI check.

**Spec:** `docs/superpowers/specs/2026-04-19-security-dashboard-redesign-design.md`

**File Map:**
- Modify `packages/presence/config.yaml` — add `template:` block with `sensor.house_access_event`
- Create `packages/presence/automations/presence_log_entry_exit.yaml` — the new automation
- Modify `dashboards/tablet/security.yaml` — rewrite Zones cards + Recent Activity logbook

---

### Task 1: Add the `house_access_event` template sensor

**Files:**
- Modify: `packages/presence/config.yaml`

- [ ] **Step 1: Add the `template:` block**

Replace the current file contents with:

```yaml
---
automation: !include_dir_list automations

template:
  - trigger:
      - platform: event
        event_type: house_access
    sensor:
      - name: House Access Event
        state: "{{ trigger.event.data.direction }} via {{ trigger.event.data.via }}"
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/presence/config.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/presence/config.yaml
git commit -m "feat(presence): add house_access_event template sensor"
```

---

### Task 2: Create the entry/exit logging automation

**Files:**
- Create: `packages/presence/automations/presence_log_entry_exit.yaml`

- [ ] **Step 1: Write the automation**

```yaml
---
alias: Presence - log house entry/exit
description: >
  Fires a `house_access` event with direction (Entry/Exit/Opened/Remote open)
  whenever an exterior door opens or the Satel garage pulse is activated.
  Direction is inferred from vestibule motion within a 30s window around the door event.
id: 8d6b2a9f-2c15-4a4a-ae5a-5e9fbf7c2a31

mode: queued
max: 10

trigger:
  - platform: state
    entity_id:
      - binary_sensor.terrace_main_door
      - binary_sensor.terrace_left_door
      - binary_sensor.balcony_door
      - binary_sensor.garage_door
    from: "off"
    to: "on"
    id: door
  - platform: state
    entity_id: switch.garage_door
    from: "off"
    to: "on"
    id: garage_switch

action:
  - variables:
      door_name: >-
        {% if trigger.id == 'door' %}
          {{ trigger.to_state.attributes.friendly_name }}
        {% else %}
          Garage
        {% endif %}
      garage_remote_recent: >-
        {{ trigger.id == 'door'
           and trigger.entity_id == 'binary_sensor.garage_door'
           and (as_timestamp(now())
                - as_timestamp(states.switch.garage_door.last_changed | default(0))) < 60 }}
      vestibule_recent: >-
        {{ is_state('binary_sensor.vestibule_motion', 'on')
           or (as_timestamp(now())
               - as_timestamp(states.binary_sensor.vestibule_motion.last_changed | default(0))) < 30 }}

  - choose:
      - conditions: "{{ trigger.id == 'garage_switch' }}"
        sequence:
          - event: house_access
            event_data:
              direction: Remote open
              via: Garage

      - conditions: "{{ garage_remote_recent }}"
        sequence: []

      - conditions: "{{ vestibule_recent }}"
        sequence:
          - event: house_access
            event_data:
              direction: Exit
              via: "{{ door_name }}"

    default:
      - wait_for_trigger:
          - platform: state
            entity_id: binary_sensor.vestibule_motion
            to: "on"
        timeout: "00:00:30"
        continue_on_timeout: true
      - event: house_access
        event_data:
          direction: "{{ 'Entry' if wait.trigger is not none else 'Opened' }}"
          via: "{{ door_name }}"
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/presence/automations/presence_log_entry_exit.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/presence/automations/presence_log_entry_exit.yaml
git commit -m "feat(presence): log house entry/exit events with direction"
```

---

### Task 3: Deploy the backend changes + sanity-check HA

**Files:** none modified (push + HA check only)

- [ ] **Step 1: Push the branch**

```bash
git push
```
Expected: push succeeds to `chore/dashboard-redesign` (current branch).

- [ ] **Step 2: Tell HA to pull + reload**

Wait ~10s for HA's git-pull timer, then reload automations and templates via REST API:

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/automation/reload"
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_config_entry" \
  -H "Content-Type: application/json" -d '{}'
```

If the template sensor requires a restart to register (first time a trigger-based template is added in the package), run:

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/restart"
```

Wait ~60s for HA to come back up.

Note: curl must run with `dangerouslyDisableSandbox: true` because `homeassistant.local` is blocked by the sandbox.

- [ ] **Step 3: Verify the new entities exist and the automation loaded**

```bash
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.house_access_event" | jq .
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/automation.presence_log_house_entry_exit" | jq '.state, .attributes.last_triggered'
```
Expected:
- `sensor.house_access_event` returns a state (likely `unknown` until first trigger fires) — NOT 404.
- Automation returns `state: "on"`.

- [ ] **Step 4: Check HA logs for errors**

```bash
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -n 100
```
Expected: no lines mentioning `presence_log_entry_exit` or `house_access_event`.

- [ ] **Step 5: Manually fire a test event to validate the sensor**

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/events/house_access" \
  -H "Content-Type: application/json" \
  -d '{"direction": "Entry", "via": "Test Door"}'
sleep 1
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.house_access_event" | jq '.state'
```
Expected: `"Entry via Test Door"`.

---

### Task 4: Rewrite the Zones column in the Security dashboard

**Files:**
- Modify: `dashboards/tablet/security.yaml:45-66`

- [ ] **Step 1: Replace the Zones section**

Replace lines 45-66 (the `- title: Zones` section, which currently holds two `entities` cards — Doors and Motion) with three `entities` cards:

```yaml
  - title: Zones
    cards:
      - type: entities
        title: Perimeter
        entities:
          - entity: binary_sensor.terrace_left_door
            name: Terrace Left
          - entity: binary_sensor.terrace_main_door
            name: Terrace Main
          - entity: binary_sensor.balcony_door
            name: Balcony
          - entity: binary_sensor.garage_door
            name: Garage
      - type: entities
        title: Entry & Outdoor
        entities:
          - entity: binary_sensor.g5_dome_motion
            name: Front Camera
          - entity: binary_sensor.garden_presence
            name: Garden Camera
          - entity: binary_sensor.vestibule_motion
            name: Vestibule (Satel)
          - entity: binary_sensor.vestibule_presence
            name: Vestibule (mmWave)
          - entity: binary_sensor.garage_motion
            name: Garage
      - type: entities
        title: Interior Transit
        entities:
          - entity: binary_sensor.living_room_motion
            name: Living Room (Satel)
          - entity: binary_sensor.living_room_presence
            name: Living Room (mmWave)
          - entity: binary_sensor.kitchen_presence
            name: Kitchen
          - entity: binary_sensor.stairway_presence
            name: Hall / Stairway
          - entity: binary_sensor.ground_floor_stairs_presence
            name: Ground Stairs
          - entity: binary_sensor.first_floor_corridor_presence
            name: First Floor Corridor
          - entity: binary_sensor.first_floor_stairs_presence
            name: First Floor Stairs
```

---

### Task 5: Update the Recent Activity logbook

**Files:**
- Modify: `dashboards/tablet/security.yaml` (the `logbook` card inside the `Doorbell` section)

- [ ] **Step 1: Replace the logbook card's entity list**

Find the card starting with `- type: logbook` and replace the full `entities:` list with:

```yaml
      - type: logbook
        title: Recent Activity
        hours_to_show: 24
        entities:
          - sensor.house_access_event
          - binary_sensor.presence_someone_at_home
          - alarm_control_panel.main
          - switch.garage_door
          - binary_sensor.terrace_left_door
          - binary_sensor.terrace_main_door
          - binary_sensor.balcony_door
          - binary_sensor.garage_door
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint dashboards/tablet/security.yaml`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/security.yaml
git commit -m "feat(dashboard): Security — expand zones and add entry/exit logbook"
```

---

### Task 6: Run the full pre-commit suite

**Files:** none modified

- [ ] **Step 1: Run all pre-commit hooks**

```bash
uv run pre-commit run --all-files
```
Expected: all hooks pass. If yamllint autofixes anything, re-stage and amend only if the fixes are trivial whitespace — otherwise commit as a separate "chore: yamllint fixes" commit.

---

### Task 7: Push and verify on the wall tablet

**Files:** none modified

- [ ] **Step 1: Push**

```bash
git push
```
Expected: push succeeds.

- [ ] **Step 2: Trigger HA to reload the dashboard (Lovelace reads YAML on refresh — no backend reload required)**

The dashboard YAML is served directly; a tablet reload picks up changes. Still, reload config entries to be safe:

```bash
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/frontend/reload_themes"
```

- [ ] **Step 3: Playwright-verify the Security tab**

Open the wall-tablet Security view via the Playwright MCP:

1. `mcp__playwright__browser_navigate` → `http://homeassistant.local:8123/wall-tablet/security`
2. `mcp__playwright__browser_wait_for` on text "Perimeter" (should appear in the new Zones card)
3. `mcp__playwright__browser_snapshot` to capture the full view
4. `mcp__playwright__browser_take_screenshot` for the record

Verify visually:
- Alarm column unchanged (alarm-panel + ready-to-arm + open-garage button).
- Zones column shows three cards: **Perimeter**, **Entry & Outdoor**, **Interior Transit** — in that order, all entities visible, no "Entity not available" warnings except the known-unavailable `binary_sensor.garden_presence`.
- Doorbell column shows the camera + logbook with `sensor.house_access_event` listed (may currently show only `unknown` state if no trigger has fired yet — fine).
- `mcp__playwright__browser_console_messages` shows no new errors.

- [ ] **Step 4: Trigger a live entry/exit to confirm the automation works end-to-end**

Physically open one of the exterior doors (e.g., terrace main), walk through the vestibule, and wait ~30s. Then:

```bash
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.house_access_event" | jq '.state, .last_changed'
```
Expected: a recent `last_changed` with a state like `"Entry via Terrace main door"` or `"Exit via Terrace main door"`.

Reload the dashboard — the event should appear as a line in the Recent Activity card.

- [ ] **Step 5: Final commit (if Playwright revealed tweaks)**

If visual check surfaced fixes (labels, card ordering), make them, lint, and commit:

```bash
git add dashboards/tablet/security.yaml
git commit -m "chore(dashboard): Security — Playwright-driven polish"
git push
```

---

## Rollback

Each task is an independent commit. Revert problematic commits with `git revert <sha>` and push. For the backend changes, `automation.reload` after revert; for dashboard changes, just reload the tablet.
