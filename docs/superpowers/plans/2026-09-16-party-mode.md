# Party Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `input_boolean.party_mode` flag that stops guest-interrupting automations and locks the kitchen wall tablet on a read-only screen.

**Architecture:** Every gated automation gets a `condition: state` on the flag (self-healing, restart-safe, nothing to restore). Three small automations in `packages/misc/automations/` do the one-shot work: tablet lock/unlock, lights, 06:00 auto-off. Tablet read-only screen is the existing `/wall-tablet/clock` view. Phone Home view gets a toggle card.

**Tech Stack:** Home Assistant YAML packages, browser_mod (`browser_mod.navigate`), Mushroom cards, `uv run yamllint`, HA REST API via `curl` (needs `dangerouslyDisableSandbox: true`), SSH to the HA box.

**Spec:** `docs/superpowers/specs/2026-09-16-party-mode-design.md`

## Global Constraints

- Work on branch `feat/party-mode` (already exists, spec committed). Never commit to `main`.
- Lint before every commit: `uv run yamllint .` (dashboards/ are yamllint-ignored; pre-commit runs on commit anyway).
- Automation syntax: this repo mixes `trigger:`/`platform:` legacy and `trigger:`/`action:` modern forms. In NEW files use the modern form (`triggers:` is not used here — use `trigger:` list with `trigger: state`, `action: light.turn_on`). In EDITED files keep the file's existing style.
- Automation filenames in misc: `misc_<thing>.yaml`, descriptive `alias`, unique `id`.
- `input_boolean.party_mode`: no `initial:` key (durable helper; see `input_number initial` memory — `initial:` gets re-applied on restart).
- Every `curl` to HA: `-H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/..."` with `dangerouslyDisableSandbox: true`. Do not read `.env`.
- Non-invasive testing: no toggling lights/covers except the explicitly agreed party-mode toggle test (Task 8), and only after the user confirms timing.
- Tablet browser id variable: `tablet_browser_id: browser_mod_c6830995_0bc293d0` (copied from the doorbell automation). Verify at Task 8 via `sensor.browser_mod_c6830995_0bc293d0_browser_useragent` (expect `Android 10; SM-T595`) once the screen is on. If it rotated, update BOTH the doorbell automation and `misc_party_mode_tablet_lock.yaml`.

---

### Task 1: Helper + auto-off automation

**Files:**
- Modify: `packages/misc/config.yaml` (append `input_boolean:` block)
- Create: `packages/misc/automations/misc_party_mode_auto_off.yaml`

**Interfaces:**
- Produces: `input_boolean.party_mode` — every later task conditions on it.

- [ ] **Step 1: Add the helper**

Append to the end of `packages/misc/config.yaml`:

```yaml

# Party mode — house-wide flag. Gated automations check it is "off"; see
# docs/superpowers/specs/2026-09-16-party-mode-design.md. No initial: on
# purpose — a restart must not silently flip the mode.
input_boolean:
  party_mode:
    name: Party Mode
    icon: mdi:party-popper
```

- [ ] **Step 2: Create the auto-off automation**

`packages/misc/automations/misc_party_mode_auto_off.yaml`:

```yaml
---
alias: Party mode auto-off
description: >-
  Safety net: nobody remembers to turn party mode off at 3 am. At 06:00 the
  flag is cleared so curtains, presence sweeps and the tablet go back to
  normal for the day.
id: misc-party-mode-auto-off

mode: single
max_exceeded: silent

trigger:
  - trigger: time
    at: "06:00:00"

condition:
  - condition: state
    entity_id: input_boolean.party_mode
    state: "on"

action:
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.party_mode
  - action: logbook.log
    data:
      name: Party Mode
      message: Auto-off at 06:00.
```

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/misc`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add packages/misc/config.yaml packages/misc/automations/misc_party_mode_auto_off.yaml
git commit -m "feat(misc): party mode flag with 06:00 auto-off"
```

---

### Task 2: Gate the nine automations

**Files (exact anchors, verified 2026-09-16):**
- Modify: `packages/areas/ground-floor/living-room/automations/living_room_curtains.yaml:23` (`conditions: []`)
- Modify: `packages/areas/ground-floor/kitchen/automations/kitchen_presence.yaml:41` (`conditions: []`)
- Modify: `packages/areas/first-floor/hall/automations/stairway_presence.yaml:30` (`conditions: []`)
- Modify: `packages/presence/automations/presence_turn_off_lights_and_media_when_away.yaml:46` (`condition: []`)
- Modify: `packages/areas/ground-floor/kitchen/automations/kitchen_dashboard_screen.yaml` (no condition block; insert before `action:`)
- Modify: `packages/areas/ground-floor/living-room/automations/living_room_scene_cube.yaml` (no condition block; insert before `action:`)
- Modify: `packages/presence/automations/presence_ground_floor_with_5_min_threshold.yaml` (no condition block; insert before `action:`)
- Modify: `packages/areas/outdoor/garden/automations/garden_lights_terrace_doors.yaml` (no condition block; insert before `action:`)
- Modify: `packages/areas/outdoor/terrace/automations/pergola_roof_control.yaml:121-134` (sunset branch conditions only)

**Interfaces:**
- Consumes: `input_boolean.party_mode` (Task 1).

- [ ] **Step 1: Replace the four empty condition lists**

In each of the first four files, replace the empty list line with a populated one. Keep the key spelling the file already uses (`conditions:` vs `condition:`).

`living_room_curtains.yaml`, `kitchen_presence.yaml`, `stairway_presence.yaml` — replace `conditions: []` with:

```yaml
conditions:
  # Party mode: guests must not be interrupted by this automation.
  - condition: state
    entity_id: input_boolean.party_mode
    state: "off"
```

`presence_turn_off_lights_and_media_when_away.yaml` — replace `condition: []` with:

```yaml
condition:
  # Party mode: hosts walking a guest to the car must not darken the house.
  - condition: state
    entity_id: input_boolean.party_mode
    state: "off"
```

- [ ] **Step 2: Insert a condition block in the four files that have none**

In `kitchen_dashboard_screen.yaml`, `living_room_scene_cube.yaml`, `presence_ground_floor_with_5_min_threshold.yaml`, `garden_lights_terrace_doors.yaml`, insert immediately before the top-level `action:` line (blank line before it, matching the file's spacing):

```yaml
condition:
  # Party mode: guests must not be interrupted by this automation.
  - condition: state
    entity_id: input_boolean.party_mode
    state: "off"

```

`living_room_scene_cube.yaml` and `presence_ground_floor_with_5_min_threshold.yaml` use modern `trigger:` syntax — the key `condition:` works in both styles, so use `condition:` in all four.

- [ ] **Step 3: Gate only the sunset branch of the pergola**

In `pergola_roof_control.yaml`, inside the `- alias: "Sunset - close pergola"` branch, append one condition to its `conditions:` list (after the `value_template` condition ending at line 133, before `sequence:`):

```yaml
          # Party mode: never close the roof over guests. Rain-close and the
          # morning open branches stay active on purpose.
          - condition: state
            entity_id: input_boolean.party_mode
            state: "off"
```

- [ ] **Step 4: Sanity-check the diff**

Run: `git diff --stat && git diff | grep -c "input_boolean.party_mode"`
Expected: 9 files changed, count `9`.

- [ ] **Step 5: Lint**

Run: `uv run yamllint packages`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add packages
git commit -m "feat: gate guest-interrupting automations on party mode"
```

---

### Task 3: Tablet lock automation + doorbell return path

**Files:**
- Create: `packages/misc/automations/misc_party_mode_tablet_lock.yaml`
- Modify: `packages/areas/outdoor/porch/automations/porch_doorbell_notify_tablet.yaml:56-61`

**Interfaces:**
- Consumes: `input_boolean.party_mode`; `sensor.browser_mod_c6830995_0bc293d0_browser_path`; `switch.kitchen_dashboard_screen`.
- Allowed paths during party: `/wall-tablet/clock`, `/wall-tablet/doorbell`.

- [ ] **Step 1: Create the lock automation**

`packages/misc/automations/misc_party_mode_tablet_lock.yaml`:

```yaml
---
alias: Party mode tablet lock
description: >-
  While party mode is on the kitchen wall tablet shows the read-only clock
  view (/wall-tablet/clock — markdown only, nothing tappable). Any navigation
  away from it (a guest tapping a tab) is snapped back within a second. The
  doorbell view stays allowed so the porch popup keeps working. Party off
  returns the tablet to Home.
id: misc-party-mode-tablet-lock

# restart: a burst of path changes must not queue up navigates.
mode: restart
max_exceeded: silent

variables:
  # browser_mod id of the kitchen wall tablet (Fully Kiosk on the Galaxy Tab A).
  # Same value as in porch_doorbell_notify_tablet.yaml — keep them in sync.
  # Rotates when the tablet's browser storage is cleared; verify with
  # sensor.browser_mod_<id>_browser_useragent (Android; SM-T595).
  tablet_browser_id: browser_mod_c6830995_0bc293d0
  lock_path: /wall-tablet/clock
  allowed_paths:
    - /wall-tablet/clock
    - /wall-tablet/doorbell

trigger:
  - trigger: state
    entity_id: input_boolean.party_mode
    from: "off"
    to: "on"
    id: party_on
  - trigger: state
    entity_id: input_boolean.party_mode
    from: "on"
    to: "off"
    id: party_off
  - trigger: state
    entity_id: sensor.browser_mod_c6830995_0bc293d0_browser_path
    id: path_changed

action:
  - choose:
      - alias: "Party on - wake the screen and lock on the clock view"
        conditions:
          - condition: trigger
            id: party_on
        sequence:
          # Wake FIRST: Fully drops the browser_mod websocket while the screen
          # is off, so a navigate sent before wake-up is a silent no-op.
          - action: switch.turn_on
            target:
              entity_id: switch.kitchen_dashboard_screen
          - wait_template: >-
              {{ states('sensor.' ~ tablet_browser_id ~ '_browser_path')
                 != 'unavailable' }}
            timeout:
              seconds: 15
            continue_on_timeout: true
          - action: browser_mod.navigate
            data:
              browser_id:
                - "{{ tablet_browser_id }}"
              path: "{{ lock_path }}"

      - alias: "Party off - back to Home"
        conditions:
          - condition: trigger
            id: party_off
        sequence:
          - action: browser_mod.navigate
            data:
              browser_id:
                - "{{ tablet_browser_id }}"
              path: /wall-tablet/home

      - alias: "Guest navigated away during party - snap back"
        conditions:
          - condition: trigger
            id: path_changed
          - condition: state
            entity_id: input_boolean.party_mode
            state: "on"
          - condition: template
            value_template: >-
              {{ trigger.to_state is not none
                 and trigger.to_state.state not in ['unavailable', 'unknown']
                 and trigger.to_state.state not in allowed_paths }}
        sequence:
          - action: browser_mod.navigate
            data:
              browser_id:
                - "{{ tablet_browser_id }}"
              path: "{{ lock_path }}"
```

- [ ] **Step 2: Template the doorbell return path**

In `porch_doorbell_notify_tablet.yaml` replace the final block

```yaml
  # Return to home view
  - action: browser_mod.navigate
    data:
      browser_id:
        - "{{ tablet_browser_id }}"
      path: /wall-tablet/home
```

with

```yaml
  # Return to home view — or to the read-only clock while party mode locks
  # the tablet (misc_party_mode_tablet_lock.yaml would snap it back anyway;
  # going straight there avoids a one-second flash of the Home controls).
  - action: browser_mod.navigate
    data:
      browser_id:
        - "{{ tablet_browser_id }}"
      path: >-
        {{ '/wall-tablet/clock' if is_state('input_boolean.party_mode', 'on')
           else '/wall-tablet/home' }}
```

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/misc packages/areas/outdoor/porch`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add packages/misc/automations/misc_party_mode_tablet_lock.yaml packages/areas/outdoor/porch/automations/porch_doorbell_notify_tablet.yaml
git commit -m "feat(misc): lock kitchen tablet on clock view during party mode"
```

---

### Task 4: Lights one-shot automation

**Files:**
- Create: `packages/misc/automations/misc_party_mode_lights.yaml`

**Interfaces:**
- Consumes: `input_boolean.party_mode`, `light.kitchen_led` (on/off only — no brightness), `light.garden_lights`, `binary_sensor.outdoor_is_dark`.

- [ ] **Step 1: Create the automation**

`packages/misc/automations/misc_party_mode_lights.yaml`:

```yaml
---
alias: Party mode lights
description: >-
  Party on: kitchen LEDs on (their presence automation is gated, so without
  this the kitchen could sit dark) and garden lights on if it is dark (their
  door/presence automation is gated too). Party off: garden lights off — the
  off-edge that normally clears them was suppressed all night. Kitchen LEDs
  are left alone; kitchen_presence resumes on its next edge.
id: misc-party-mode-lights

mode: single
max_exceeded: silent

trigger:
  - trigger: state
    entity_id: input_boolean.party_mode
    from: "off"
    to: "on"
    id: party_on
  - trigger: state
    entity_id: input_boolean.party_mode
    from: "on"
    to: "off"
    id: party_off

action:
  - choose:
      - alias: "Party on"
        conditions:
          - condition: trigger
            id: party_on
        sequence:
          # light.kitchen_led is onoff-only — no brightness data on purpose.
          - action: light.turn_on
            target:
              entity_id: light.kitchen_led
          - if:
              - condition: state
                entity_id: binary_sensor.outdoor_is_dark
                state: "on"
            then:
              - action: light.turn_on
                target:
                  entity_id: light.garden_lights

      - alias: "Party off"
        conditions:
          - condition: trigger
            id: party_off
        sequence:
          - action: light.turn_off
            target:
              entity_id: light.garden_lights
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/misc`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add packages/misc/automations/misc_party_mode_lights.yaml
git commit -m "feat(misc): party mode one-shot lights"
```

---

### Task 5: Phone dashboard toggle

**Files:**
- Modify: `dashboards/phone/home.yaml:28-30` (after the alarm card, before the second `- cards:` section)

- [ ] **Step 1: Add the card**

After line 28 (`navigation_path: /mobile-phone/away`) and before the blank line + `  - cards:` that starts the second section, insert (indented to match the alarm card, i.e. 6 spaces before `- type`):

```yaml
      - type: custom:mushroom-template-card
        entity: input_boolean.party_mode
        icon: mdi:party-popper
        icon_color: "{{ 'pink' if is_state('input_boolean.party_mode', 'on') else 'grey' }}"
        primary: Party mode
        secondary: >-
          {{ 'ON — tablet locked, curtains & sweeps paused. Auto-off 06:00.'
             if is_state('input_boolean.party_mode', 'on') else 'Off' }}
        layout: horizontal
        tap_action:
          action: toggle
```

- [ ] **Step 2: Commit**

```bash
git add dashboards/phone/home.yaml
git commit -m "feat(phone): party mode toggle on Home"
```

---

### Task 6: Push, PR, point the box at the branch, reload

**Files:** none.

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/party-mode
gh pr create --title "feat: party mode" --body "$(cat <<'EOF'
## Summary
- `input_boolean.party_mode` + 06:00 auto-off
- Gates 9 automations (curtains, kitchen LED/screen, scene cube, stairway, ground-floor + away sweeps, garden door lights, pergola sunset-close) on the flag
- Kitchen tablet locked on the read-only clock view while on; doorbell popup still works
- One-shot: kitchen LED on, garden lights on if dark / off at end
- Phone Home toggle

Spec: docs/superpowers/specs/2026-09-16-party-mode-design.md

## Test plan
- [ ] Box on feat/party-mode, SHA verified
- [ ] input_boolean.reload + automation.reload, logs clean
- [ ] Toggle on: tablet path sensor reads /wall-tablet/clock; forced navigate to home snaps back
- [ ] Trace of a gated automation shows condition short-circuit
- [ ] Toggle off: tablet back on /wall-tablet/home
- [ ] Playwright screenshot of phone Home
EOF
)"
```

- [ ] **Step 2: Check the box is clean, then check out the branch**

```bash
ssh root@homeassistant.local 'cd /config && git status --porcelain'
```
Expected: only untracked runtime files (`.HA_VERSION`, `.cache/`, …). Any MODIFIED tracked file → stop and ask the user.

```bash
ssh root@homeassistant.local 'cd /config && git fetch -q origin && git checkout -q feat/party-mode && git reset --hard -q origin/feat/party-mode && git rev-parse --short HEAD'
git rev-parse --short HEAD
```
Expected: both SHAs identical.

- [ ] **Step 3: Reload the two domains (NOT reload_core_config alone)**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/input_boolean/reload"
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload"
```
(`dangerouslyDisableSandbox: true`.) Expected: HTTP 200 / `[]`.

- [ ] **Step 4: Verify entities exist**

```bash
for e in input_boolean.party_mode automation.party_mode_auto_off automation.party_mode_tablet_lock automation.party_mode_lights; do
  curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/$e" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["entity_id"], d["state"])'
done
```
Expected: `input_boolean.party_mode off`, the three automations `on`. A 404 → retry the reload once (post-push race), then check the box SHA.

- [ ] **Step 5: Check logs**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | grep -iE "party|misc_party|invalid config|error" | tail -20
```
Expected: nothing party-related.

---

### Task 7: Confirm test timing with the user

- [ ] **Step 1: Ask**

The live test toggles party mode ON for ~2 minutes. Physically observable effects: kitchen tablet jumps to the clock view, kitchen LED turns on (if off), garden lights turn on if it is dark outside, then garden lights off at toggle-off. Ask the user for an OK/time before Task 8. Do not proceed without it.

---

### Task 8: Live test (non-invasive beyond the agreed toggle)

- [ ] **Step 1: Verify the tablet browser id (screen must be on)**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"switch.kitchen_dashboard_screen"}' "$HA_URL/api/services/switch/turn_on"
sleep 10
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.browser_mod_c6830995_0bc293d0_browser_useragent" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state"])'
```
Expected: contains `SM-T595`. If `unavailable`, list all `sensor.browser_mod_*_browser_useragent` and find the one with `SM-T595`; if the id differs, update both automations, commit, push, re-run Task 6 steps 2–5.

- [ ] **Step 2: Toggle on**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"input_boolean.party_mode"}' "$HA_URL/api/services/input_boolean/turn_on"
sleep 5
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.browser_mod_c6830995_0bc293d0_browser_path" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state"])'
```
Expected: `/wall-tablet/clock`.

- [ ] **Step 3: Force a navigation away, confirm snap-back**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"browser_id":["browser_mod_c6830995_0bc293d0"],"path":"/wall-tablet/home"}' "$HA_URL/api/services/browser_mod/navigate"
sleep 4
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.browser_mod_c6830995_0bc293d0_browser_path" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state"])'
```
Expected: `/wall-tablet/clock` again. Also check the trace of `automation.party_mode_tablet_lock` shows the snap-back branch ran:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/automation.party_mode_tablet_lock" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["attributes"]["last_triggered"])'
```

- [ ] **Step 4: Verify a gated automation short-circuits**

Pick `automation.kitchen_dashboard_screen` (fires on presence edges constantly). Read its `last_triggered` now, wait for a presence edge (or just check `binary_sensor.dashboard_presence` flips), and confirm `switch.kitchen_dashboard_screen` stays `on` and the automation's `last_triggered` does NOT advance past the toggle-on timestamp (a condition failure is not a run).

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/automation.kitchen_dashboard_screen" | python3 -c 'import sys,json; print(json.load(sys.stdin)["attributes"]["last_triggered"])'
```

Also render the condition directly:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{{ is_state(\"input_boolean.party_mode\",\"off\") }}"}' "$HA_URL/api/template"
```
Expected: `False` while on.

- [ ] **Step 5: Toggle off, confirm tablet returns**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"input_boolean.party_mode"}' "$HA_URL/api/services/input_boolean/turn_off"
sleep 5
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.browser_mod_c6830995_0bc293d0_browser_path" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state"])'
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/light.garden_lights" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state"])'
```
Expected: `/wall-tablet/home`, `off`.

- [ ] **Step 6: Logs again**

Same command as Task 6 step 5. Expected: clean. Report all observed values to the user verbatim.

---

### Task 9: Playwright check of the phone Home view

- [ ] **Step 1: Screenshot**

Navigate Playwright to `$HA_URL/mobile-phone/home`, resize to 390×844, screenshot to `.playwright-mcp/party-mode-phone-home.png`. If the card shows stale/missing, force the lovelace re-read in the page console:

```js
await hass.connection.sendMessagePromise({type:'lovelace/config', url_path:'mobile-phone', force:true})
```
then reload. Expected: "Party mode / Off" card with a grey party-popper icon under the alarm card.

---

### Task 10: Area docs

- [ ] **Step 1: Regenerate READMEs for the touched area packages**

Invoke the `ha-area-docs` skill for: `kitchen`, `living-room` (ground floor), `hall` (first floor), `garden`, `terrace`, `porch` (outdoor). Commit as `docs(areas): party mode gates`. Push.

---

### Task 11: Hand back

- [ ] **Step 1: Report**

Report to the user: PR URL, box SHA, every value observed in Task 8, screenshot path. Wait. On "merge": merge the PR, then point the box back at `main` with the same SSH command and verify the SHA.
