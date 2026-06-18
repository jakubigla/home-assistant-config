# Garden One-off Irrigation Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tablet-dashboard control to schedule a single, time-delayed garden irrigation run (Lawn / Drip / Full) that fires once at a chosen date+time then auto-disarms, without touching the recurring Tue/Fri schedule.

**Architecture:** Three native HA input helpers (`input_datetime`, `input_select`, `input_boolean`) feed one automation that triggers on the datetime, gates on the armed boolean, runs the chosen existing script, then clears the boolean. A new "Schedule One-off" block on the Outdoor view drives them.

**Tech Stack:** Home Assistant YAML packages (`!include_dir_list` automations, `!include_dir_merge_named` scripts), Mushroom + native Lovelace cards, `just` recipes, Playwright MCP for visual verify.

**Spec:** `docs/superpowers/specs/2026-05-25-garden-oneoff-irrigation-design.md`

**Note on testing:** This is HA config, not unit-testable code. "Verify" steps = `just check` (HA config validation), `just lint`, HA reload + log check, a live fire-test, and Playwright visual check. No pytest.

**Convention reminders (from the existing garden package):**
- Automation files have **no `- id:` list wrapper** — top-level keys directly (the dir is loaded via `!include_dir_list`). `id:` is kebab-case, `alias:` descriptive.
- Existing automations call scripts as a direct action (`- action: script.garden_lawn_irrigation`), not `script.turn_on`. Match that.
- Helpers live in `packages/areas/outdoor/garden/config.yaml` alongside `garden_irrigation_mode`.
- After any push: reload HA + check logs (see the **reload-after-push** leaf). Dashboard edits need a Playwright visual check (dashboard-validate rule).

---

### Task 1: Add the three input helpers

**Files:**
- Modify: `packages/areas/outdoor/garden/config.yaml`

- [ ] **Step 1: Add helpers below the existing `input_select` block**

The file currently ends with the `garden_irrigation_mode` input_select. Append the
new `input_datetime`, extend `input_select` with `garden_oneoff_type`, and add
`input_boolean`. Final file:

```yaml
---
automation: !include_dir_list automations
template: !include_dir_list templates
script: !include_dir_merge_named scripts

input_select:
  garden_irrigation_mode:
    name: Garden Irrigation Mode
    options:
      - Manual
      - Eco
      - Standard
      - Intensive
      - Testing
      - Smart
    icon: mdi:sprinkler
  garden_oneoff_type:
    name: Garden One-off Type
    options:
      - Lawn
      - Drip
      - Full
    icon: mdi:sprinkler-variant

input_datetime:
  garden_oneoff_at:
    name: Garden One-off Run At
    has_date: true
    has_time: true

input_boolean:
  garden_oneoff_armed:
    name: Garden One-off Armed
    icon: mdi:timer-sand
```

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS (config valid, no errors mentioning the new helpers).

- [ ] **Step 3: Lint**

Run: `just lint`
Expected: PASS (yamllint clean).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/config.yaml
git commit -m "feat(garden): add one-off irrigation helpers"
```

---

### Task 2: Add the one-off automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_oneoff_run.yaml`

- [ ] **Step 1: Write the automation**

Mirror the format of `garden_scheduled_irrigation.yaml` exactly — top-level keys, no
list wrapper, `action:` calling scripts directly, kebab `id`.

```yaml
---
alias: Garden One-off Scheduled Run
description: >
  Fires a single user-scheduled irrigation run (Lawn / Drip / Full) at
  input_datetime.garden_oneoff_at when armed, then disarms. Ignores rain
  skip sensors by design — the user decides when arming. Independent of
  the recurring Tue/Fri schedule.
id: garden-oneoff-run

mode: single

trigger:
  - platform: time
    at: input_datetime.garden_oneoff_at

condition:
  - condition: state
    entity_id: input_boolean.garden_oneoff_armed
    state: "on"

action:
  - choose:
      - conditions:
          - "{{ is_state('input_select.garden_oneoff_type', 'Lawn') }}"
        sequence:
          - action: script.garden_lawn_irrigation
      - conditions:
          - "{{ is_state('input_select.garden_oneoff_type', 'Drip') }}"
        sequence:
          - action: script.garden_drip_irrigation
      - conditions:
          - "{{ is_state('input_select.garden_oneoff_type', 'Full') }}"
        sequence:
          - action: script.garden_full_irrigation
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.garden_oneoff_armed
```

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS. Confirms the `platform: time` `at:` referencing an `input_datetime`
entity is accepted (it is — native HA datetime trigger).

- [ ] **Step 3: Lint**

Run: `just lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_oneoff_run.yaml
git commit -m "feat(garden): one-off scheduled run automation"
```

---

### Task 3: Add the dashboard "Schedule One-off" block

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` (Garden section, immediately after the
  "Full Run" card at the end of the "Run Scripts" group — before the
  `- title: Pergola & Gate` section)

- [ ] **Step 1: Insert the block**

After the `script.garden_full_irrigation` `mushroom-template-card` (the one with
`grid_options: columns: full`, currently the last card before `- title: Pergola & Gate`),
add:

```yaml
      - type: heading
        heading: Schedule One-off
        heading_style: subtitle
      - type: custom:mushroom-select-card
        entity: input_select.garden_oneoff_type
        name: What
        icon: mdi:sprinkler-variant
        layout: horizontal
      - type: entities
        entities:
          - entity: input_datetime.garden_oneoff_at
            name: When
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            primary: >-
              {{ 'Armed' if is_state('input_boolean.garden_oneoff_armed', 'on')
                 else 'Schedule' }}
            secondary: >-
              {% if is_state('input_boolean.garden_oneoff_armed', 'on') %}
              {{ states('input_select.garden_oneoff_type') }} @
              {{ states('input_datetime.garden_oneoff_at')
                 | as_timestamp | timestamp_custom('%a %H:%M') }}
              {% else %}Tap to arm{% endif %}
            icon: mdi:timer-play
            icon_color: >-
              {{ 'orange' if is_state('input_boolean.garden_oneoff_armed', 'on')
                 else 'grey' }}
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: input_boolean.turn_on
              target:
                entity_id: input_boolean.garden_oneoff_armed
          - type: custom:mushroom-template-card
            primary: Cancel
            icon: mdi:timer-off
            icon_color: red
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: input_boolean.turn_off
              target:
                entity_id: input_boolean.garden_oneoff_armed
```

- [ ] **Step 2: Lint**

Run: `just lint`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "feat(garden): schedule one-off run dashboard block"
```

---

### Task 4: Push, reload, and verify live

**Files:** none (deployment + verification)

- [ ] **Step 1: Push the branch**

```bash
git push
```
(Branch `chore/may-fixes` — never main. HA auto-pulls.)

- [ ] **Step 2: Reload HA + check logs**

Reload via MCP/API (sandbox blocks `homeassistant.local` — use `dangerouslyDisableSandbox: true` for curl). Reload core config, automations, and template entities, then check the error log.

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/input_boolean/reload"
```
Then check logs for errors referencing `garden_oneoff`. Expected: helpers + automation
load clean; entities `input_datetime.garden_oneoff_at`, `input_select.garden_oneoff_type`,
`input_boolean.garden_oneoff_armed`, `automation.garden_one_off_scheduled_run` exist.

- [ ] **Step 3: Functional fire-test**

Set the picker ~2 min ahead, type Lawn, arm, watch it fire and disarm:

```bash
# Set datetime to now+2min (Europe/Warsaw)
NEXT=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:00'))")
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_datetime/set_datetime" \
  -d "{\"entity_id\":\"input_datetime.garden_oneoff_at\",\"datetime\":\"$NEXT\"}"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id":"input_select.garden_oneoff_type","option":"Lawn"}'
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_boolean/turn_on" \
  -d '{"entity_id":"input_boolean.garden_oneoff_armed"}'
```
Expected at fire time: `script.garden_lawn_irrigation` runs (lawn zone 1 valve opens),
and `input_boolean.garden_oneoff_armed` returns to `off`. Verify via:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/input_boolean.garden_oneoff_armed"
```
Expected state after fire: `off`. **Then close any open valve** (tap the valve card or
`valve.close` `valve.garden_all`) so the test run doesn't water unintentionally — or run
the fire-test with type unset to a no-op... no: type must be Lawn to prove the path. Just
close the valves after confirming.

- [ ] **Step 4: Playwright visual check**

Navigate to `/wall-tablet` Outdoor view, screenshot the Garden section. Confirm the
"Schedule One-off" heading, What select, When picker, and Schedule/Cancel buttons render
and the Schedule button shows armed/idle state correctly. Save screenshots into
`.playwright-mcp/` only. Force-refetch (navigate away/back) to bypass frontend cache.

- [ ] **Step 5: Disarm + reset after verification**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_boolean/turn_off" \
  -d '{"entity_id":"input_boolean.garden_oneoff_armed"}'
```
Confirm no valves left open.

---

### Task 5: Update the README

**Files:**
- Modify: `packages/areas/outdoor/garden/README.md`

- [ ] **Step 1: Add helpers to the Entities section**

Under the existing **Mode:** / **Sensors:** listing, add:

```markdown
**One-off run:**
- `input_select.garden_oneoff_type` — Lawn / Drip / Full
- `input_datetime.garden_oneoff_at` — when the one-off fires
- `input_boolean.garden_oneoff_armed` — on = armed; auto-clears after firing
```

- [ ] **Step 2: Add the automation to the File Index table**

Add a row:

```markdown
| `automations/garden_oneoff_run.yaml` | Fires a single armed run (Lawn/Drip/Full) at the chosen datetime, then disarms. Ignores rain skip. |
```

- [ ] **Step 3: Add a one-line note to How It Works**

Under "Scheduled Irrigation", add a sentence:

```markdown
A **one-off run** can be armed from the dashboard (type + datetime); it fires once at the chosen time, independent of the recurring schedule and ignoring rain skip.
```

- [ ] **Step 4: Lint + commit**

Run: `just lint`
Expected: PASS.

```bash
git add packages/areas/outdoor/garden/README.md
git commit -m "docs(garden): document one-off scheduled run"
git push
```

---

## Self-Review

**Spec coverage:**
- Helpers (datetime + select + boolean) → Task 1. ✓
- Automation (time trigger, armed gate, choose-by-type, auto-disarm, no rain skip) → Task 2. ✓
- Dashboard block (select, native datetime card, Schedule/Cancel switching-content button) → Task 3. ✓
- Verification (just check/lint, reload+logs, fire-test, Playwright) → Task 4. ✓
- README update → Task 5. ✓
- Knowledge leaf untouched → confirmed, no task (correct per spec). ✓
- Always-run / explicit-arm / past-time-no-fire → encoded in Task 2 automation + verified Task 4. ✓

**Placeholder scan:** No TBD/TODO. Every code step shows full content. (Task 4 Step 3 has a verbal aside about valve cleanup — kept as explicit instruction, not a placeholder.)

**Type/name consistency:** Entity ids identical across tasks — `input_select.garden_oneoff_type`, `input_datetime.garden_oneoff_at`, `input_boolean.garden_oneoff_armed`, `automation` alias "Garden One-off Scheduled Run", scripts `garden_lawn_irrigation`/`garden_drip_irrigation`/`garden_full_irrigation`. ✓
- Note: HA slugifies the alias → `automation.garden_one_off_scheduled_run` (Step 2 of Task 4 references this; confirm exact slug from logs/states at verify time).
```
