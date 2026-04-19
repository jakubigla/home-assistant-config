# Laundry Notification Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user subscribe to mobile push notifications when the washer or dryer finishes, controlled from the Appliances dashboard — with per-appliance mode (off / one_cycle / always) and recipient (me / sona / both), plus a "Set both" shortcut.

**Architecture:** Pure Home Assistant YAML. Four `input_select` helpers hold subscription state. Two automations (one per appliance) fire on `binary_sensor.*_power` `on→off`, notify the selected recipient(s), and auto-reset `one_cycle` back to `off`. A small script writes both appliances' mode in one call for the combined shortcut. Dashboard binds to the helpers via `mushroom-select-card`.

**Tech Stack:** Home Assistant packages (`input_select`, `script`, `automation`, `notify.mobile_app_*`), Lovelace `sections` layout with Mushroom cards, pre-commit `yamllint`, direnv-loaded `$HA_URL` + `$HA_TOKEN` for reload/verification.

**Spec:** `docs/superpowers/specs/2026-04-19-laundry-notify-subscriptions-design.md`

---

## Conventions for this plan

- **Working directory:** repo root (`/Users/jakubigla/Project-Repositories/Personal/home-assistant-config`). All commands use relative paths.
- **YAML gotcha:** `off` must be quoted (`"off"`) everywhere — in `input_select.options`, in `state:` comparisons, in `option:` values. Unquoted, YAML parses it as boolean `false`.
- **Deploy model:** HA auto-pulls this branch. After every push, trigger the matching `*.reload` service and check logs. Use `curl` with direnv-loaded `$HA_URL` and `$HA_TOKEN` (bash tool needs `dangerouslyDisableSandbox: true` because the hostname `homeassistant.local` is sandbox-blocked).
- **Pre-commit:** run `uv run pre-commit run --files <paths>` on changed files before commit. Hooks include `yamllint`, JSON format, trailing whitespace, secret detection.
- **Branch:** commit to the current branch (`chore/dashboard-redesign`). Do NOT push to `main`.

## File structure

```
packages/areas/first-floor/laundry/
├── config.yaml                              # MODIFY: add input_select + script includes
├── helpers/
│   └── notify_subscriptions.yaml            # NEW — 4 input_selects (no top-level key)
├── scripts/
│   └── set_both_laundry_notify.yaml         # NEW — script definition (no top-level key)
├── automations/
│   ├── laundry_room_lights_on_when_occupied.yaml  # existing, untouched
│   ├── washer_notify_on_finish.yaml         # NEW
│   └── dryer_notify_on_finish.yaml          # NEW
└── README.md                                # MODIFY: regenerate via /ha-area-docs

dashboards/tablet/appliances.yaml            # MODIFY: add "Notifications" section after existing Laundry block
```

---

## Task 1: Add subscription helpers (input_selects)

**Files:**
- Create: `packages/areas/first-floor/laundry/helpers/notify_subscriptions.yaml`
- Modify: `packages/areas/first-floor/laundry/config.yaml`

- [ ] **Step 1: Create the helpers file**

Create `packages/areas/first-floor/laundry/helpers/notify_subscriptions.yaml` with:

```yaml
---
washer_notify_mode:
  name: Washer notify
  icon: mdi:washing-machine
  options:
    - "off"
    - one_cycle
    - always
  initial: "off"

dryer_notify_mode:
  name: Dryer notify
  icon: mdi:tumble-dryer
  options:
    - "off"
    - one_cycle
    - always
  initial: "off"

washer_notify_recipient:
  name: Washer recipient
  icon: mdi:cellphone-message
  options:
    - me
    - sona
    - both
  initial: me

dryer_notify_recipient:
  name: Dryer recipient
  icon: mdi:cellphone-message
  options:
    - me
    - sona
    - both
  initial: me
```

- [ ] **Step 2: Wire the include in `config.yaml`**

Replace the contents of `packages/areas/first-floor/laundry/config.yaml` with:

```yaml
---
automation: !include_dir_list automations
input_select: !include helpers/notify_subscriptions.yaml
```

- [ ] **Step 3: Lint**

Run:

```bash
uv run pre-commit run --files \
  packages/areas/first-floor/laundry/config.yaml \
  packages/areas/first-floor/laundry/helpers/notify_subscriptions.yaml
```

Expected: all hooks pass (may print "Skipped" for hooks that don't apply). No failures.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/laundry/config.yaml \
        packages/areas/first-floor/laundry/helpers/notify_subscriptions.yaml
git commit -m "$(cat <<'EOF'
✨ feat(laundry): add notify subscription input_select helpers

Four input_selects holding per-appliance mode (off/one_cycle/always)
and recipient (me/sona/both) for washer and dryer notifications.
Wired via `input_select: !include helpers/notify_subscriptions.yaml`.
EOF
)"
```

- [ ] **Step 5: Push**

```bash
git push
```

- [ ] **Step 6: Reload HA input_selects + verify no config errors**

Run (with `dangerouslyDisableSandbox: true`):

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/input_select/reload" -d '{}'
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" | tail -50
```

Expected: no ERROR lines mentioning `input_select`, `laundry`, or `notify_subscriptions`.

- [ ] **Step 7: Verify entities exist and initial state is correct**

```bash
for e in washer_notify_mode dryer_notify_mode washer_notify_recipient dryer_notify_recipient; do
  curl -s -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/states/input_select.$e" | jq '{id: .entity_id, state: .state, options: .attributes.options}'
done
```

Expected output for each: `state` is `"off"` (modes) or `"me"` (recipients); `options` array matches the file.

---

## Task 2: Add "Set both" script

**Files:**
- Create: `packages/areas/first-floor/laundry/scripts/set_both_laundry_notify.yaml`
- Modify: `packages/areas/first-floor/laundry/config.yaml`

- [ ] **Step 1: Create the script file**

Create `packages/areas/first-floor/laundry/scripts/set_both_laundry_notify.yaml` with:

```yaml
---
set_both_laundry_notify:
  alias: Set both laundry notify
  icon: mdi:bell-cog
  mode: single
  fields:
    mode:
      description: Mode to apply to both washer and dryer notify selectors.
      required: true
      selector:
        select:
          options:
            - "off"
            - one_cycle
            - always
  sequence:
    - action: input_select.select_option
      target:
        entity_id:
          - input_select.washer_notify_mode
          - input_select.dryer_notify_mode
      data:
        option: "{{ mode }}"
```

- [ ] **Step 2: Wire the scripts dir in `config.yaml`**

Update `packages/areas/first-floor/laundry/config.yaml` to:

```yaml
---
automation: !include_dir_list automations
input_select: !include helpers/notify_subscriptions.yaml
script: !include_dir_merge_named scripts
```

- [ ] **Step 3: Lint**

```bash
uv run pre-commit run --files \
  packages/areas/first-floor/laundry/config.yaml \
  packages/areas/first-floor/laundry/scripts/set_both_laundry_notify.yaml
```

Expected: all hooks pass.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/first-floor/laundry/config.yaml \
        packages/areas/first-floor/laundry/scripts/set_both_laundry_notify.yaml
git commit -m "$(cat <<'EOF'
✨ feat(laundry): add set_both_laundry_notify script

Single-call helper that writes both washer_notify_mode and
dryer_notify_mode in one shot. Backs the "Set both" dashboard shortcut.
EOF
)"
```

- [ ] **Step 5: Push and reload**

```bash
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/script/reload" -d '{}'
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" | tail -50
```

Expected: no ERROR lines about `script` or `set_both_laundry_notify`.

- [ ] **Step 6: Functional test — call the script with `one_cycle`**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/script/set_both_laundry_notify" \
  -d '{"mode": "one_cycle"}'

curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.washer_notify_mode" | jq -r .state
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.dryer_notify_mode" | jq -r .state
```

Expected: both return `one_cycle`.

- [ ] **Step 7: Reset both to `off`**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/script/set_both_laundry_notify" \
  -d '{"mode": "off"}'

curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.washer_notify_mode" | jq -r .state
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.dryer_notify_mode" | jq -r .state
```

Expected: both return `off`.

---

## Task 3: Washer notify automation

**Files:**
- Create: `packages/areas/first-floor/laundry/automations/washer_notify_on_finish.yaml`

- [ ] **Step 1: Create the automation file**

```yaml
---
alias: Washer notify on finish
id: washer_notify_on_finish
description: >-
  Push notification when the washer finishes a cycle, based on the
  subscription mode set via `input_select.washer_notify_mode`.
mode: single

trigger:
  - platform: state
    entity_id: binary_sensor.washer_power
    from: "on"
    to: "off"

condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.washer_notify_mode
        state: "off"

action:
  - choose:
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: me
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: &washer_payload
              title: Washer finished
              message: Time to unload the washer.
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: sona
        sequence:
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *washer_payload
      - conditions:
          - condition: state
            entity_id: input_select.washer_notify_recipient
            state: both
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: *washer_payload
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *washer_payload

  - if:
      - condition: state
        entity_id: input_select.washer_notify_mode
        state: one_cycle
    then:
      - action: input_select.select_option
        target:
          entity_id: input_select.washer_notify_mode
        data:
          option: "off"
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --files \
  packages/areas/first-floor/laundry/automations/washer_notify_on_finish.yaml
```

Expected: all hooks pass.

- [ ] **Step 3: Commit and push**

```bash
git add packages/areas/first-floor/laundry/automations/washer_notify_on_finish.yaml
git commit -m "$(cat <<'EOF'
✨ feat(laundry): add washer notify-on-finish automation

Fires on binary_sensor.washer_power on→off. Routes to the selected
recipient based on input_select.washer_notify_recipient. Auto-resets
the mode to off when it was one_cycle.
EOF
)"
git push
```

- [ ] **Step 4: Reload automations and check log**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/automation/reload" -d '{}'
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" | tail -50
```

Expected: no ERROR lines about `washer_notify_on_finish`.

- [ ] **Step 5: Verify the automation is loaded**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.washer_notify_on_finish" \
  | jq '{state, last_triggered: .attributes.last_triggered}'
```

Expected: `state` is `"on"`.

- [ ] **Step 6: Arm `one_cycle` for `me`, trigger, verify notify + auto-reset**

Arm the subscription:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.washer_notify_mode", "option": "one_cycle"}'
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.washer_notify_recipient", "option": "me"}'
```

Simulate an `on→off` transition by overriding `binary_sensor.washer_power`:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/states/binary_sensor.washer_power" \
  -d '{"state": "on"}'
sleep 1
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/states/binary_sensor.washer_power" \
  -d '{"state": "off"}'
sleep 2
```

Verify the automation fired (last_triggered updated) AND mode reset to off:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.washer_notify_on_finish" \
  | jq '.attributes.last_triggered'
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.washer_notify_mode" | jq -r .state
```

Expected: `last_triggered` is a timestamp within the last few seconds; `input_select.washer_notify_mode` state is `off`.

**On iPhone:** confirm a push notification titled "Washer finished" arrived. If it did not, inspect the HA logbook for the automation and verify the notify service resolved correctly.

Note: REST `/api/states` overrides are ephemeral — the real binary_sensor will reassert its physical state on the next update. That's fine for this test.

---

## Task 4: Dryer notify automation

**Files:**
- Create: `packages/areas/first-floor/laundry/automations/dryer_notify_on_finish.yaml`

- [ ] **Step 1: Create the automation file**

```yaml
---
alias: Dryer notify on finish
id: dryer_notify_on_finish
description: >-
  Push notification when the dryer finishes a cycle, based on the
  subscription mode set via `input_select.dryer_notify_mode`.
mode: single

trigger:
  - platform: state
    entity_id: binary_sensor.tumble_dryer_power
    from: "on"
    to: "off"

condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.dryer_notify_mode
        state: "off"

action:
  - choose:
      - conditions:
          - condition: state
            entity_id: input_select.dryer_notify_recipient
            state: me
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: &dryer_payload
              title: Dryer finished
              message: Time to unload the dryer.
      - conditions:
          - condition: state
            entity_id: input_select.dryer_notify_recipient
            state: sona
        sequence:
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *dryer_payload
      - conditions:
          - condition: state
            entity_id: input_select.dryer_notify_recipient
            state: both
        sequence:
          - action: notify.mobile_app_iglofon_new
            data: *dryer_payload
          - action: notify.mobile_app_iphone_uzivatela_sona
            data: *dryer_payload

  - if:
      - condition: state
        entity_id: input_select.dryer_notify_mode
        state: one_cycle
    then:
      - action: input_select.select_option
        target:
          entity_id: input_select.dryer_notify_mode
        data:
          option: "off"
```

- [ ] **Step 2: Lint**

```bash
uv run pre-commit run --files \
  packages/areas/first-floor/laundry/automations/dryer_notify_on_finish.yaml
```

Expected: all hooks pass.

- [ ] **Step 3: Commit and push**

```bash
git add packages/areas/first-floor/laundry/automations/dryer_notify_on_finish.yaml
git commit -m "$(cat <<'EOF'
✨ feat(laundry): add dryer notify-on-finish automation

Fires on binary_sensor.tumble_dryer_power on→off. Routes to the
selected recipient based on input_select.dryer_notify_recipient.
Auto-resets the mode to off when it was one_cycle.
EOF
)"
git push
```

- [ ] **Step 4: Reload and verify**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/automation/reload" -d '{}'
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" | tail -50
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/automation.dryer_notify_on_finish" | jq -r .state
```

Expected: no ERROR lines; automation state `on`.

- [ ] **Step 5: Functional test — `always` mode, recipient `both`**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.dryer_notify_mode", "option": "always"}'
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.dryer_notify_recipient", "option": "both"}'

curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/states/binary_sensor.tumble_dryer_power" -d '{"state": "on"}'
sleep 1
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/states/binary_sensor.tumble_dryer_power" -d '{"state": "off"}'
sleep 2

curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/input_select.dryer_notify_mode" | jq -r .state
```

Expected: both phones receive "Dryer finished" push; `input_select.dryer_notify_mode` state remains `always` (not reset, because it wasn't `one_cycle`).

- [ ] **Step 6: Reset mode to `off` and recipient to `me`**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.dryer_notify_mode", "option": "off"}'
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id": "input_select.dryer_notify_recipient", "option": "me"}'
```

---

## Task 5: Dashboard — "Notifications" section on Appliances tab

**Files:**
- Modify: `dashboards/tablet/appliances.yaml` (append a new block inside the existing `sections[0].cards` list, after line 750)

- [ ] **Step 1: Append the Notifications block**

Open `dashboards/tablet/appliances.yaml`. After the final card (line 750, the `binary_sensor.laundry_doors` mushroom-template-card) and still inside the same `cards:` list, append:

```yaml

      - type: heading
        heading: Notifications
        heading_style: title
        icon: mdi:bell
        grid_options:
          columns: full
        card_mod:
          style: |
            ha-card {
              padding-top: 24px !important;
            }

      - type: horizontal-stack
        grid_options:
          columns: full
        cards:
          - type: vertical-stack
            cards:
              - type: custom:mushroom-select-card
                entity: input_select.washer_notify_mode
                name: Washer
                icon: mdi:washing-machine
                layout: horizontal
              - type: custom:mushroom-select-card
                entity: input_select.washer_notify_recipient
                name: Recipient
                icon: mdi:cellphone-message
                layout: horizontal

          - type: vertical-stack
            cards:
              - type: custom:mushroom-select-card
                entity: input_select.dryer_notify_mode
                name: Dryer
                icon: mdi:tumble-dryer
                layout: horizontal
              - type: custom:mushroom-select-card
                entity: input_select.dryer_notify_recipient
                name: Recipient
                icon: mdi:cellphone-message
                layout: horizontal

      - type: grid
        grid_options:
          columns: full
        columns: 3
        square: false
        cards:
          - type: custom:mushroom-template-card
            primary: Set both — Off
            icon: mdi:bell-off
            icon_color: disabled
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: script.set_both_laundry_notify
              data:
                mode: "off"
          - type: custom:mushroom-template-card
            primary: Set both — One cycle
            icon: mdi:bell-ring-outline
            icon_color: amber
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: script.set_both_laundry_notify
              data:
                mode: one_cycle
          - type: custom:mushroom-template-card
            primary: Set both — Always
            icon: mdi:bell
            icon_color: blue
            layout: horizontal
            tap_action:
              action: perform-action
              perform_action: script.set_both_laundry_notify
              data:
                mode: always
```

Indentation must match the preceding card (the final one at line 734 starts with `      - type:` — six spaces of indent). The `cards` list this appends to is `sections[0].cards`, NOT a nested card's children.

- [ ] **Step 2: Lint the dashboard file**

```bash
uv run pre-commit run --files dashboards/tablet/appliances.yaml
```

Expected: all hooks pass.

- [ ] **Step 3: Commit and push**

```bash
git add dashboards/tablet/appliances.yaml
git commit -m "$(cat <<'EOF'
✨ feat(dashboard): Appliances — add laundry notification controls

Notifications section with per-appliance mode + recipient selects
(mushroom-select-card) and a "Set both" shortcut row that calls
script.set_both_laundry_notify.
EOF
)"
git push
```

- [ ] **Step 4: Playwright visual verification**

Navigate to `$HA_URL/wall-tablet/appliances` and visually confirm:
1. A new "Notifications" heading appears after the existing Laundry block.
2. Two columns of selects render: Washer/Recipient and Dryer/Recipient.
3. Each select shows three segment options and the current value is highlighted (default state should be "off" / "me").
4. Three "Set both" buttons are laid out in a 3-column grid below.
5. Tapping "Set both — One cycle" updates both mode selects to `one_cycle` live (no refresh).
6. Tapping "Set both — Off" resets both to `off`.
7. No card crashes (no red error borders, no missing card errors in browser console).

If any card fails to render, fix in place and re-push before continuing.

- [ ] **Step 5: Reset all selects to initial state after the test**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/script/set_both_laundry_notify" \
  -d '{"mode": "off"}'
```

---

## Task 6: Regenerate laundry package README

**Files:**
- Modify: `packages/areas/first-floor/laundry/README.md`

- [ ] **Step 1: Invoke the `ha-area-docs` skill**

Invoke the `ha-area-docs` skill and target the laundry area package. It will rewrite `README.md` to reflect the new helpers, script, and automations.

- [ ] **Step 2: Verify the README mentions the new pieces**

Confirm the regenerated `README.md` includes:
- The four `input_select` helpers (washer_notify_mode, dryer_notify_mode, washer_notify_recipient, dryer_notify_recipient)
- `script.set_both_laundry_notify`
- The two new automations (`washer_notify_on_finish`, `dryer_notify_on_finish`)
- `binary_sensor.washer_power` and `binary_sensor.tumble_dryer_power` as dependencies

If any are missing, edit the README by hand to include them.

- [ ] **Step 3: Lint and commit**

```bash
uv run pre-commit run --files packages/areas/first-floor/laundry/README.md
git add packages/areas/first-floor/laundry/README.md
git commit -m "$(cat <<'EOF'
📝 docs(laundry): regenerate README for notify subscriptions

Cover the new input_select helpers, set_both_laundry_notify script,
and the washer/dryer notify-on-finish automations.
EOF
)"
git push
```

---

## End-to-end acceptance checklist (run after all tasks)

- [ ] All four helpers exist with the correct options and initial values.
- [ ] `script.set_both_laundry_notify` exists and updates both mode selects in one call.
- [ ] Both notify automations are loaded and enabled (state `on`).
- [ ] Notifications tab on `/wall-tablet/appliances` renders without errors (Playwright check).
- [ ] Functional test: arm `washer_notify_mode=one_cycle`, recipient `me`, fake `on→off` on `binary_sensor.washer_power` → iPhone push arrives → mode resets to `off`.
- [ ] Functional test: arm `dryer_notify_mode=always`, recipient `both`, fake `on→off` on `binary_sensor.tumble_dryer_power` → both phones push → mode stays `always`.
- [ ] Functional test: `mode=off` → no notification on `on→off`.
- [ ] HA error log is clean (no new ERROR entries referencing any of the new entities).
- [ ] `packages/areas/first-floor/laundry/README.md` documents all new entities.
