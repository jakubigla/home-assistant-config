# Garden On-demand Per-zone Lawn Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dashboard buttons (tablet + phone) to run any single lawn zone on demand for a duration set by a shared slider, without disturbing profile-driven runs, drip, or the one-off scheduler.

**Architecture:** Two new helpers (`input_number` minutes slider + `input_boolean` active flag) drive one parametrized script (`garden_ondemand_zone`, `mode: single`) that owns valve open→wait→close. The existing `garden_valve_auto_off` automation gains a gate that skips lawn valves while the flag is on, so the slider duration wins over the profile duration. `garden_valve_startup_close` also clears the flag on boot; the 30-min max-open watchdog stays unchanged as a backstop (slider capped at 25 min).

**Tech Stack:** Home Assistant YAML packages (`packages/areas/outdoor/garden/`), Lovelace dashboards (Mushroom cards), `just` recipes (`check`, `lint`), `homeassistant.reload_core_config` for live reload.

**Spec:** `docs/superpowers/specs/2026-06-08-garden-ondemand-zone-design.md`

> **Verification model:** This is HA config, not application code — there is no unit-test runner. "Test" = `just check` (HA config validity) + `just lint` (yamllint/pre-commit) + functional verification against the live HA instance after push+reload, plus Playwright visual checks on dashboards. The deployment loop is: commit on the feature branch → `git push` → reload HA → check logs. HA only sees changes after push (auto-pull); local edits are not live. **Never push to main.**

---

## File Structure

- **Create** `packages/areas/outdoor/garden/scripts/garden_ondemand_zone.yaml` — the parametrized run script. Merged into `script:` via `!include_dir_merge_named scripts`.
- **Modify** `packages/areas/outdoor/garden/config.yaml` — add `input_number` + extend `input_boolean`.
- **Modify** `packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml` — add the on-demand skip gate.
- **Modify** `packages/areas/outdoor/garden/automations/garden_valve_startup_close.yaml` — clear the flag on boot.
- **Modify** `dashboards/tablet/outdoor.yaml` — add "Run a zone now" block to the Garden section.
- **Modify** `dashboards/phone/rooms/garden.yaml` — add the same block.
- **Modify** `packages/areas/outdoor/garden/README.md` — document new entities + file index (via `/ha-area-docs`).

Current branch: `chore/may-fixes` (already a feature branch — fine to commit onto, or branch off it). Do NOT push to `main`.

---

### Task 1: Add helpers (slider + active flag)

**Files:**
- Modify: `packages/areas/outdoor/garden/config.yaml`

- [ ] **Step 1: Add the `input_number` block and extend `input_boolean`**

The file currently ends with the `input_boolean` block holding only `garden_oneoff_armed`. Add a new `input_number:` top-level key, and add `garden_ondemand_active` under the existing `input_boolean:`. Final state of the relevant sections:

```yaml
input_number:
  garden_ondemand_minutes:
    name: Garden On-demand Minutes
    min: 1
    max: 25
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline

input_boolean:
  garden_oneoff_armed:
    name: Garden One-off Armed
    icon: mdi:timer-sand
  garden_ondemand_active:
    name: Garden On-demand Active
    icon: mdi:water-pump
```

(Leave `input_select`, `input_datetime`, and the top `automation/template/script` includes untouched.)

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS (`Configuration valid!`). If `just check` is slow/unavailable locally, at minimum run `uv run yamllint packages/areas/outdoor/garden/config.yaml` → no errors.

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/config.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/config.yaml
git commit -m "feat(garden): add on-demand minutes slider + active flag helpers"
```

---

### Task 2: Create the on-demand zone script

**Files:**
- Create: `packages/areas/outdoor/garden/scripts/garden_ondemand_zone.yaml`

- [ ] **Step 1: Write the script**

Mirror the offline-abort pattern from `garden_lawn_irrigation.yaml`. The script takes a `zone` field (`1`/`2`/`3`), resolves the valve entity, aborts if unavailable, then sets the flag → opens → waits the slider minutes → closes → clears the flag.

```yaml
---
garden_ondemand_zone:
  alias: Garden On-demand Zone
  description: >
    Run a single lawn zone on demand for the duration set by
    input_number.garden_ondemand_minutes. Sets garden_ondemand_active while
    running so garden_valve_auto_off skips this valve (the script owns the
    close, not the profile-driven timer). mode: single — a second invocation
    while one is running is ignored.
  icon: mdi:water-pump
  mode: single
  fields:
    zone:
      description: Lawn zone number (1, 2 or 3)
      required: true
      example: "1"
      selector:
        select:
          options: ["1", "2", "3"]
  sequence:
    - variables:
        valve_id: "valve.lawn_sprinkler_zone_{{ zone }}"
        minutes: "{{ states('input_number.garden_ondemand_minutes') | int(0) }}"
    # Abort + notify if the target zone valve is offline. valve.open_valve on an
    # unavailable entity is a silent no-op, so a tap would otherwise do nothing.
    - if:
        - "{{ states(valve_id) == 'unavailable' }}"
      then:
        - action: persistent_notification.create
          data:
            notification_id: garden_ondemand_zone_offline
            title: On-demand zone unavailable
            message: >
              Sprinkler controller offline — {{ valve_id }} is unavailable.
              On-demand run aborted. Check the Tuya "Sprinker" device.
        - stop: "On-demand run aborted — zone valve unavailable"
    # Guard against a zero/blank slider (would open the valve indefinitely until
    # the watchdog catches it).
    - if:
        - "{{ minutes < 1 }}"
      then:
        - stop: "On-demand run skipped — duration is zero"
    - action: input_boolean.turn_on
      target:
        entity_id: input_boolean.garden_ondemand_active
    - action: valve.open_valve
      target:
        entity_id: "{{ valve_id }}"
    - delay:
        minutes: "{{ minutes }}"
    - action: valve.close_valve
      target:
        entity_id: "{{ valve_id }}"
    - action: input_boolean.turn_off
      target:
        entity_id: input_boolean.garden_ondemand_active
```

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS. The script is picked up by `!include_dir_merge_named scripts`. If it errors on the `selector` under `fields`, that block is HA-valid for script fields — re-check indentation matches the example above.

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/scripts/garden_ondemand_zone.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/scripts/garden_ondemand_zone.yaml
git commit -m "feat(garden): on-demand per-zone run script (slider-driven duration)"
```

---

### Task 3: Gate auto-off while an on-demand run is active

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml:26-27` (insert at the top of `action:`)

- [ ] **Step 1: Add the skip gate as the first action step**

The current `action:` block starts with `- variables:` (line 27). Insert an `if/then` BEFORE it so an on-demand-owned lawn valve is left for the script to close. Resulting top of `action:`:

```yaml
action:
  # On-demand runs (script.garden_ondemand_zone) own the valve for the
  # slider duration. Skip the profile-driven auto-off for lawn valves while a
  # run is active, so the slider duration wins instead of the profile duration.
  # drip + profile-driven lawn + HomeKit-manual opens are unaffected (flag off).
  - if:
      - "{{ trigger.id == 'lawn'
            and is_state('input_boolean.garden_ondemand_active', 'on') }}"
    then:
      - stop: "On-demand run owns this lawn valve — auto-off skipped"
  - variables:
      duration: >
        {% if trigger.id == 'lawn' %}
          {% set durations = state_attr('sensor.garden_irrigation_profile',
             'lawn_durations') or {} %}
          {% set d = durations.get(trigger.entity_id, 0) | int %}
          {% set cycles = state_attr('sensor.garden_irrigation_profile',
             'cycle_count') | int(1) %}
          {% set cycles = cycles if cycles > 0 else 1 %}
          {{ (d / cycles) | int if d > 0 else (900 / cycles) | int }}
        {% else %}
          {% set d = state_attr('sensor.garden_irrigation_profile',
             'drip_duration') | int(0) %}
          {{ d if d > 0 else 2700 }}
        {% endif %}
  - delay:
      seconds: "{{ duration }}"
  - action: valve.close_valve
    target:
      entity_id: "{{ trigger.entity_id }}"
```

(Everything from `- variables:` down is unchanged — only the `if/then` gate is new.)

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS.

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_valve_auto_off.yaml
git commit -m "feat(garden): auto-off skips lawn valves during on-demand run"
```

---

### Task 4: Clear the flag on HA startup

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_valve_startup_close.yaml:24-30` (extend the `action:`)

- [ ] **Step 1: Add a flag-clear step to the startup sequence**

The current `action:` is: `delay 30s` → `valve.close_valve` (all 4 valves). Add an `input_boolean.turn_off` for the flag so a crash mid-run cannot leave it stuck `on` (which would make profile-driven lawn runs skip auto-off forever). Resulting `action:`:

```yaml
action:
  # Give the Tuya valve entities a moment to come back as available before
  # commanding them — closing an `unavailable` valve is a silent no-op (this is
  # exactly why the on-stop cleanup failed to close zone 3).
  - delay:
      seconds: 30
  - action: valve.close_valve
    target:
      entity_id:
        - valve.lawn_sprinkler_zone_1
        - valve.lawn_sprinkler_zone_2
        - valve.lawn_sprinkler_zone_3
        - valve.drip_irrigation
  # An on-demand run's script context is dead after a restart; clear its flag
  # so profile-driven auto-off is not skipped indefinitely.
  - action: input_boolean.turn_off
    target:
      entity_id: input_boolean.garden_ondemand_active
```

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS.

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_valve_startup_close.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_valve_startup_close.yaml
git commit -m "feat(garden): clear on-demand flag on HA startup"
```

---

### Task 5: Push + reload + functional verification (backend)

No new files. Verify the helpers/script/automations work on the live instance BEFORE touching dashboards (so dashboard buttons have a confirmed-working backend to bind to).

- [ ] **Step 1: Push the branch**

```bash
git push
```
Expected: branch pushed. (HA auto-pulls the current branch.)

- [ ] **Step 2: Reload HA core config + automations/scripts**

Use the MCP `HassTurnOn`-style service call or API. Via API (sandbox blocks `homeassistant.local`, so use `dangerouslyDisableSandbox: true`):

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_core_config" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/automation/reload" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/script/reload" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/input_number/reload" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/input_boolean/reload" >/dev/null
```
Expected: no errors. (New `input_*` helpers may need `homeassistant.reload_core_config`; the per-domain reloads cover script/automation changes.)

- [ ] **Step 3: Check logs for errors**

Query the HA error log (MCP or API):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -40
```
Expected: no new errors referencing `garden_ondemand`, `garden_valve_auto_off`, or `garden_valve_startup_close`.

- [ ] **Step 4: Confirm entities exist**

Confirm via MCP `GetLiveContext` or API that these are present and in a sane state:
- `input_number.garden_ondemand_minutes` (numeric, 1–25)
- `input_boolean.garden_ondemand_active` (off)
- `script.garden_ondemand_zone`

```bash
for e in input_number.garden_ondemand_minutes input_boolean.garden_ondemand_active script.garden_ondemand_zone; do
  curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/$e" | head -c 300; echo
done
```
Expected: all three return valid state JSON (not 404).

- [ ] **Step 5: Functional run — short zone**

Set the slider to 1 min, fire zone 2, watch the flag + valve, confirm auto-off does NOT close it early:

```bash
# set slider to 1 minute
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"input_number.garden_ondemand_minutes","value":1}' \
  "$HA_URL/api/services/input_number/set_value" >/dev/null
# fire zone 2
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"script.garden_ondemand_zone","variables":{"zone":"2"}}' \
  "$HA_URL/api/services/script/turn_on" >/dev/null
```
Within a few seconds check `valve.lawn_sprinkler_zone_2` == `open` and `input_boolean.garden_ondemand_active` == `on`. After ~1 min, confirm the valve returns to `closed` and the flag returns to `off`. Confirm it did NOT close early at the profile duration (if profile zone-2 duration < 60s) — i.e. the slider won.

- [ ] **Step 6: Functional run — offline-abort path (optional, if controller can be powered off)**

If feasible, with the controller off, fire the script and confirm a `persistent_notification` appears and the flag stays `off`. Otherwise note as untested and rely on the shared pattern with `garden_lawn_irrigation`.

- [ ] **Step 7: No code change — checkpoint only**

If all checks pass, proceed. If the slider did NOT win (valve closed at profile duration), the gate in Task 3 is mis-wired — revisit `trigger.id`/flag-state condition before continuing.

---

### Task 6: Tablet dashboard — "Run a zone now" block

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` — Garden section, after the existing "Schedule One-off" `horizontal-stack` (ends at line 140 `entity_id: input_boolean.garden_oneoff_armed`), before the next `vertical-stack` (line 141).

- [ ] **Step 1: Insert the block**

Add after the Schedule One-off `horizontal-stack` (i.e. as additional cards in the same `cards:` list, before the `- type: vertical-stack` that starts the 7-Day Schedule). Indentation must match the surrounding cards (the `horizontal-stack` at line 109 is indented 14 spaces under `cards:` — match it exactly).

```yaml
              - type: heading
                heading: Run a Zone Now
                heading_style: subtitle
              - type: custom:mushroom-number-card
                entity: input_number.garden_ondemand_minutes
                name: Minutes
                display_mode: slider
                icon: mdi:timer-outline
              - type: horizontal-stack
                cards:
                  - type: custom:mushroom-template-card
                    primary: Zone 1
                    secondary: >-
                      {{ 'Running' if is_state('valve.lawn_sprinkler_zone_1', 'open')
                         else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
                    icon: mdi:sprinkler
                    icon_color: >-
                      {{ 'blue' if is_state('valve.lawn_sprinkler_zone_1', 'open') else 'grey' }}
                    layout: vertical
                    tap_action:
                      action: perform-action
                      perform_action: script.turn_on
                      target:
                        entity_id: script.garden_ondemand_zone
                      data:
                        variables:
                          zone: "1"
                  - type: custom:mushroom-template-card
                    primary: Zone 2
                    secondary: >-
                      {{ 'Running' if is_state('valve.lawn_sprinkler_zone_2', 'open')
                         else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
                    icon: mdi:sprinkler
                    icon_color: >-
                      {{ 'blue' if is_state('valve.lawn_sprinkler_zone_2', 'open') else 'grey' }}
                    layout: vertical
                    tap_action:
                      action: perform-action
                      perform_action: script.turn_on
                      target:
                        entity_id: script.garden_ondemand_zone
                      data:
                        variables:
                          zone: "2"
                  - type: custom:mushroom-template-card
                    primary: Zone 3
                    secondary: >-
                      {{ 'Running' if is_state('valve.lawn_sprinkler_zone_3', 'open')
                         else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
                    icon: mdi:sprinkler
                    icon_color: >-
                      {{ 'blue' if is_state('valve.lawn_sprinkler_zone_3', 'open') else 'grey' }}
                    layout: vertical
                    tap_action:
                      action: perform-action
                      perform_action: script.turn_on
                      target:
                        entity_id: script.garden_ondemand_zone
                      data:
                        variables:
                          zone: "3"
```

> **Note on `data.variables`:** `script.turn_on` passes script `fields` via `variables:`. If the deployed HA build does not honor `data.variables` for `script.turn_on`, the fallback is to call `script.garden_ondemand_zone` directly as the action: `perform_action: script.garden_ondemand_zone` with `data: { zone: "1" }`. Verify in Task 8 Step 4 (tap a button, confirm the right valve opens); switch to the fallback form if the wrong/no zone fires.

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS (dashboards are checked too).

- [ ] **Step 3: Lint**

Run: `uv run yamllint dashboards/tablet/outdoor.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "feat(garden): tablet on-demand per-zone run buttons"
```

---

### Task 7: Phone dashboard — same block

**Files:**
- Modify: `dashboards/phone/rooms/garden.yaml` — add the on-demand block as additional cards in the single section's `cards:` list (after the existing status `mushroom-template-card`).

- [ ] **Step 1: Append the block**

The phone view has one section with `max_columns: 1` and a single status card (ends at the `layout: horizontal` on the last line). Add these cards to the same `cards:` list (indented 6 spaces, matching the existing `- type: custom:mushroom-template-card` at line 10):

```yaml
      - type: heading
        heading: Run a Zone Now
        heading_style: subtitle
      - type: custom:mushroom-number-card
        entity: input_number.garden_ondemand_minutes
        name: Minutes
        display_mode: slider
        icon: mdi:timer-outline
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            primary: Zone 1
            secondary: >-
              {{ 'Running' if is_state('valve.lawn_sprinkler_zone_1', 'open')
                 else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
            icon: mdi:sprinkler
            icon_color: >-
              {{ 'blue' if is_state('valve.lawn_sprinkler_zone_1', 'open') else 'grey' }}
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_ondemand_zone
              data:
                variables:
                  zone: "1"
          - type: custom:mushroom-template-card
            primary: Zone 2
            secondary: >-
              {{ 'Running' if is_state('valve.lawn_sprinkler_zone_2', 'open')
                 else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
            icon: mdi:sprinkler
            icon_color: >-
              {{ 'blue' if is_state('valve.lawn_sprinkler_zone_2', 'open') else 'grey' }}
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_ondemand_zone
              data:
                variables:
                  zone: "2"
          - type: custom:mushroom-template-card
            primary: Zone 3
            secondary: >-
              {{ 'Running' if is_state('valve.lawn_sprinkler_zone_3', 'open')
                 else states('input_number.garden_ondemand_minutes') | int ~ ' min' }}
            icon: mdi:sprinkler
            icon_color: >-
              {{ 'blue' if is_state('valve.lawn_sprinkler_zone_3', 'open') else 'grey' }}
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_ondemand_zone
              data:
                variables:
                  zone: "3"
```

(Use the same `data.variables` fallback note from Task 6 Step 1 if needed.)

- [ ] **Step 2: Validate config**

Run: `just check`
Expected: PASS.

- [ ] **Step 3: Lint**

Run: `uv run yamllint dashboards/phone/rooms/garden.yaml`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add dashboards/phone/rooms/garden.yaml
git commit -m "feat(garden): phone on-demand per-zone run buttons"
```

---

### Task 8: Push + dashboard reload + Playwright visual verification

- [ ] **Step 1: Push**

```bash
git push
```
Expected: branch pushed; HA auto-pulls.

- [ ] **Step 2: Reload + force-refresh lovelace**

Existing-dashboard YAML picks up after push without restart, BUT HA caches the parsed lovelace config — the frontend shows stale config until re-fetched with `force: true` (see memory: dashboard auto-reload gotcha). Reload core config, then hard-reload the browser/tablet page.

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_core_config" >/dev/null
```

- [ ] **Step 3: Check logs**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | tail -40
```
Expected: no new lovelace/card errors.

- [ ] **Step 4: Playwright visual check — tablet**

Navigate to `/wall-tablet/outdoor` (or the Outdoor view path), hard-refresh, snapshot. Confirm:
- "Run a Zone Now" heading + Minutes slider render.
- Three zone cards render side-by-side, grey when idle, secondary shows "<N> min".
- Tap **Zone 2** → confirm `valve.lawn_sprinkler_zone_2` goes `open`, card turns blue + "Running". (Then either let it finish at the slider duration or close manually.)
- If the wrong zone (or no zone) fires, switch all six buttons to the `data.variables` → direct-call fallback (Task 6 Step 1 note), re-commit, re-push, re-verify.

Save screenshots into `.playwright-mcp/` only (e.g. `.playwright-mcp/garden-ondemand-tablet.png`).

- [ ] **Step 5: Playwright visual check — phone**

Navigate to the phone garden room (`room-garden`), hard-refresh, snapshot. Confirm the same block renders single-column-friendly (three zone cards in a row fit; if cramped on phone width, that's acceptable — note it).

Save into `.playwright-mcp/garden-ondemand-phone.png`.

- [ ] **Step 6: Commit any fallback fixes** (only if Step 4/5 required changes)

```bash
git add dashboards/tablet/outdoor.yaml dashboards/phone/rooms/garden.yaml
git commit -m "fix(garden): on-demand button action form for live HA"
git push
```

---

### Task 9: Documentation

**Files:**
- Modify: `packages/areas/outdoor/garden/README.md`

- [ ] **Step 1: Regenerate area docs**

Invoke the `/ha-area-docs` skill for the garden area. It regenerates the README from the package, picking up the new `input_number.garden_ondemand_minutes`, `input_boolean.garden_ondemand_active`, `script.garden_ondemand_zone`, and the two modified automations.

- [ ] **Step 2: Verify the new entities + files appear**

Confirm the README's Entities table lists the slider, flag, and script, and the File Index lists `scripts/garden_ondemand_zone.yaml`. If `/ha-area-docs` missed anything, add it by hand following the existing table format.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/README.md
git commit -m "docs(garden): document on-demand per-zone run"
git push
```

---

## Self-Review notes

- **Spec coverage:** helpers (Task 1) ✓, parametrized script + offline abort + zero-guard (Task 2) ✓, auto-off skip gate (Task 3) ✓, startup flag-clear (Task 4) ✓, watchdog unchanged (no task — confirmed in spec, slider max 25 < 30) ✓, both dashboards (Tasks 6–7) ✓, one-at-a-time `mode: single` (Task 2) ✓, always-run/no rain skip (no condition added) ✓, README (Task 9) ✓, functional + Playwright verification (Tasks 5, 8) ✓.
- **Entity-name consistency:** `input_number.garden_ondemand_minutes`, `input_boolean.garden_ondemand_active`, `script.garden_ondemand_zone`, `valve.lawn_sprinkler_zone_{1,2,3}` used identically across all tasks.
- **Known live-HA risk flagged:** `script.turn_on` + `data.variables` for passing the `zone` field is the documented form, with an explicit direct-call fallback verified in Task 8 — not left as a silent assumption.
- **Out of scope honored:** no per-zone sliders, no queue, no presets, no drip on-demand, no rain logic, no watchdog cap change.
