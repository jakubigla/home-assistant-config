# Tablet Climate View Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `dashboards/tablet/climate.yaml` so the Homecome heating is finally first-class, ACs demote to a strip in winter (and vice-versa in summer), humidifiers become informational, and curtains leave the tab.

**Architecture:** Single-section vertical stack inside `type: sections` (`max_columns: 1`). A new `binary_sensor.cooling_season` (`on` May–Sep) drives `visibility:` conditions on two pairs of rows so only the seasonally-correct primary hero + secondary strip render.

**Tech Stack:** Home Assistant Lovelace (sections view), Mushroom custom cards (already installed), HA template `binary_sensor`.

**Spec:** `docs/superpowers/specs/2026-04-18-tablet-climate-redesign-design.md`

**Branch:** Currently on `chore/dashboard-redesign`. All work stays on this branch. PR into `main` at the end — never push to `main` directly (see `feedback_never_push_main`).

**Deployment note:** HA auto-pulls from the current git branch. Local edits are NOT live until pushed. After every push, reload HA templates + Lovelace and check logs (see `feedback_reload_ha_after_push`).

---

### Task 1: Add `binary_sensor.cooling_season` template

**Files:**
- Create: `packages/bootstrap/templates/binary_sensors/cooling_season.yaml`

**Why:** Drives the seasonal swap. `packages/bootstrap/config.yaml` already ships `template: !include_dir_list templates` so files under `templates/binary_sensors/` load automatically — no `configuration.yaml` edit needed.

- [ ] **Step 1: Create the template file**

Write `packages/bootstrap/templates/binary_sensors/cooling_season.yaml`:

```yaml
---
binary_sensor:
  - name: cooling_season
    state: >
      {{ now().month in [5, 6, 7, 8, 9] }}
    icon: >
      {{ 'mdi:snowflake' if now().month in [5, 6, 7, 8, 9] else 'mdi:radiator' }}
```

Structure mirrors `packages/bootstrap/templates/binary_sensors/office_hours.yaml`. No `template:` wrapper — the include directive in `config.yaml` adds it.

- [ ] **Step 2: Lint**

Run:
```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
uv run yamllint packages/bootstrap/templates/binary_sensors/cooling_season.yaml
```

Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git add packages/bootstrap/templates/binary_sensors/cooling_season.yaml
git commit -m "feat(templates): add cooling_season binary sensor

Drives seasonal swap between heating-primary and AC-primary layouts.
On May–Sep, off otherwise. Used by the redesigned tablet climate view."
```

- [ ] **Step 4: Push and reload HA**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git push
```

Then, in Home Assistant UI: Developer Tools → YAML → "Template Entities" → Reload.
(Alternatively, a full HA restart works.)

- [ ] **Step 5: Verify the sensor exists and resolves correctly**

```bash
source /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/.env
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states/binary_sensor.cooling_season \
  | python3 -m json.tool
```

Run this with `dangerouslyDisableSandbox: true` if using Claude's Bash tool (sandbox blocks `homeassistant.local`).

Expected (today 2026-04-18, April, heating season):
```json
{
  "entity_id": "binary_sensor.cooling_season",
  "state": "off",
  "attributes": {
    "icon": "mdi:radiator",
    "friendly_name": "cooling_season"
  },
  ...
}
```

If state is `unknown` or the entity is not found, check HA logs:
```bash
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/error_log | tail -50
```

- [ ] **Step 6: Sanity-check the summer path**

Render the template live (swaps nothing, just verifies the Jinja):
```bash
source /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/.env
curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "{{ 7 in [5, 6, 7, 8, 9] }}"}' \
  http://homeassistant.local:8123/api/template
```

Expected output: `True`. Confirms the month-in-list logic works; `now().month` returns the same kind of int.

---

### Task 2: Rewrite `dashboards/tablet/climate.yaml`

**Files:**
- Modify: `dashboards/tablet/climate.yaml` (full rewrite, 1–74 → new content below)

**Why:** Current file uses `climate.living_room`/`climate.bedroom` (the ACs) as thermostats, shows curtains, and gives humidifiers primary real estate. Replace with the season-aware hero+strip layout from the spec.

- [ ] **Step 1: Replace file contents**

Overwrite `dashboards/tablet/climate.yaml` with:

```yaml
---
title: Climate
path: climate
icon: mdi:thermostat
type: sections
max_columns: 1
sections:
  - cards:
      # ===== Row 1: Weather strip =====
      - type: custom:mushroom-template-card
        entity: weather.forecast_home
        icon: >-
          mdi:weather-{{ states('weather.forecast_home')
          | replace('partlycloudy', 'partly-cloudy')
          | replace('clear-night', 'night') }}
        icon_color: >-
          {% set c = states('weather.forecast_home') %}
          {{ 'amber' if c == 'sunny' else 'blue' if c in ['rainy','pouring','snowy','lightning-rainy'] else 'disabled' }}
        primary: >-
          {{ state_attr('weather.forecast_home', 'temperature') | float(0) | round(1) }}°C · {{ states('weather.forecast_home') | capitalize }}
        secondary: >-
          Humidity {{ state_attr('weather.forecast_home', 'humidity') | float(0) | round(0) | int }}% · Wind {{ state_attr('weather.forecast_home', 'wind_speed') | float(0) | round(0) | int }} km/h
        layout: horizontal
        fill_container: true
        tap_action:
          action: more-info

      # ===== Row 2: Primary hero — HEATING (winter) =====
      - type: horizontal-stack
        visibility:
          - condition: state
            entity: binary_sensor.cooling_season
            state: "off"
        cards:
          - type: thermostat
            entity: climate.floor_heating
            name: Floor Heating
          - type: thermostat
            entity: climate.main_heating
            name: Radiators

      # ===== Row 2: Primary hero — AC (summer) =====
      - type: horizontal-stack
        visibility:
          - condition: state
            entity: binary_sensor.cooling_season
            state: "on"
        cards:
          - type: thermostat
            entity: climate.living_room
            name: Living Room AC
          - type: thermostat
            entity: climate.bedroom
            name: Bedroom AC

      # ===== Row 3: Secondary strip — AC chips (winter: AC is secondary) =====
      - type: horizontal-stack
        visibility:
          - condition: state
            entity: binary_sensor.cooling_season
            state: "off"
        cards:
          - type: custom:mushroom-template-card
            entity: climate.living_room
            icon: mdi:air-conditioner
            icon_color: >-
              {{ 'blue' if states('climate.living_room') not in ['off', 'unavailable'] else 'disabled' }}
            primary: Living Room AC
            secondary: >-
              {{ state_attr('climate.living_room', 'current_temperature') | float(0) | round(1) }}°C · {{ states('climate.living_room') | capitalize }}
            layout: horizontal
            tap_action:
              action: more-info
          - type: custom:mushroom-template-card
            entity: climate.bedroom
            icon: mdi:air-conditioner
            icon_color: >-
              {{ 'blue' if states('climate.bedroom') not in ['off', 'unavailable'] else 'disabled' }}
            primary: Bedroom AC
            secondary: >-
              {{ state_attr('climate.bedroom', 'current_temperature') | float(0) | round(1) }}°C · {{ states('climate.bedroom') | capitalize }}
            layout: horizontal
            tap_action:
              action: more-info

      # ===== Row 3: Secondary strip — heating chips (summer: heating is secondary) =====
      - type: horizontal-stack
        visibility:
          - condition: state
            entity: binary_sensor.cooling_season
            state: "on"
        cards:
          - type: custom:mushroom-template-card
            entity: climate.floor_heating
            icon: mdi:radiator
            icon_color: >-
              {{ 'orange' if state_attr('climate.floor_heating', 'hvac_action') == 'heating' else 'disabled' }}
            primary: Floor Heating
            secondary: >-
              {{ state_attr('climate.floor_heating', 'current_temperature') | float(0) | round(1) }}°C · {{ state_attr('climate.floor_heating', 'hvac_action') | default('idle') | capitalize }}
            layout: horizontal
            tap_action:
              action: more-info
          - type: custom:mushroom-template-card
            entity: climate.main_heating
            icon: mdi:radiator
            icon_color: >-
              {{ 'orange' if state_attr('climate.main_heating', 'hvac_action') == 'heating' else 'disabled' }}
            primary: Radiators
            secondary: >-
              {{ state_attr('climate.main_heating', 'current_temperature') | float(0) | round(1) }}°C · {{ state_attr('climate.main_heating', 'hvac_action') | default('idle') | capitalize }}
            layout: horizontal
            tap_action:
              action: more-info

      # ===== Row 4: Per-room environment =====
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            entity: sensor.living_room_hygro_temperature
            icon: mdi:sofa
            icon_color: >-
              {{ 'blue' if is_state('humidifier.living_room', 'on') else 'disabled' }}
            primary: Living Room
            secondary: >-
              {{ states('sensor.living_room_hygro_temperature') | float(0) | round(1) }}°C · {{ states('sensor.living_room_hygro_humidity') | float(0) | round(0) | int }}%
            layout: horizontal
            tap_action:
              action: more-info
              entity: humidifier.living_room
          - type: custom:mushroom-template-card
            entity: sensor.bedroom_hygro_temperature
            icon: mdi:bed
            icon_color: >-
              {{ 'blue' if is_state('humidifier.bedroom', 'on') else 'disabled' }}
            primary: Bedroom
            secondary: >-
              {{ states('sensor.bedroom_hygro_temperature') | float(0) | round(1) }}°C · {{ states('sensor.bedroom_hygro_humidity') | float(0) | round(0) | int }}%
            layout: horizontal
            tap_action:
              action: more-info
              entity: humidifier.bedroom

      # ===== Row 5: 24 h trend graphs =====
      - type: horizontal-stack
        cards:
          - type: history-graph
            title: Living Room (24h)
            hours_to_show: 24
            entities:
              - sensor.living_room_hygro_temperature
              - sensor.living_room_hygro_humidity
          - type: history-graph
            title: Bedroom (24h)
            hours_to_show: 24
            entities:
              - sensor.bedroom_hygro_temperature
              - sensor.bedroom_hygro_humidity
```

Key points:

- Two separate `horizontal-stack` rows for row 2 (heating + AC), each with its own `visibility:` block. Only one renders at a time.
- Same pattern for row 3's secondary strip.
- Weather template mirrors the one already in `dashboards/tablet/home.yaml:89–108`.
- Row 4 chip pattern is a simplified version of the per-room cards at `dashboards/tablet/home.yaml:440–486` (without the card_mod chain). Tap opens the humidifier more-info popup — the "control after you click something" the user asked for.
- Rows 4 and 5 have no `visibility:` — they render year-round.

- [ ] **Step 2: Lint**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
uv run yamllint dashboards/tablet/climate.yaml
```

Expected: no output.

- [ ] **Step 3: Run full repo lint to catch anything else**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
uv run pre-commit run --all-files
```

Expected: all hooks pass. If anything trips, fix and re-run.

- [ ] **Step 4: Commit**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git add dashboards/tablet/climate.yaml
git commit -m "feat(dashboard): redesign tablet climate view

Replace the old 3-column page (which incorrectly showed ACs as
thermostats and carried curtains) with a season-aware vertical stack:
heating hero + AC strip in winter, AC hero + heating strip in summer.
Humidifiers demote to per-room environment chips with tap-to-expand."
```

- [ ] **Step 5: Push and reload Lovelace**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git push
```

In the HA web UI: top-right avatar → "Refresh" (or ⌘-Shift-R / Ctrl-Shift-R in a loaded tab) to pull the new `climate.yaml`.

---

### Task 3: Live verification of the redesigned page

No code — this is browser + API verification. Run immediately after Task 2 so errors get caught before merging.

**Files:** none

- [ ] **Step 1: Check HA error log for YAML/template errors**

```bash
source /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/.env
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/error_log | tail -80
```

Run with `dangerouslyDisableSandbox: true` in Claude. Expected: no new ERROR/WARNING entries mentioning `climate.yaml`, `cooling_season`, or template rendering.

- [ ] **Step 2: Confirm `binary_sensor.cooling_season` is `off` (heating season today)**

```bash
source /Users/jakubigla/Project-Repositories/Personal/home-assistant-config/.env
curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  http://homeassistant.local:8123/api/states/binary_sensor.cooling_season \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['state'])"
```

Expected: `off`.

- [ ] **Step 3: Open the climate tab and visually verify**

Navigate to `http://homeassistant.local:8123/wall-tablet/climate` (or `/tablet/climate` — path depends on the dashboard URL slug; check `lovelace.dashboards` in `configuration.yaml`).

Verify, from top to bottom:

1. **Weather strip:** shows current temperature (≈ 21.9 °C today) + condition + humidity + wind. Icon matches condition.
2. **Row 2:** shows exactly **two heating thermostats** (Floor Heating + Radiators). Setpoints around 22.5 °C, current ≈ 23.1 °C. **Not** the ACs.
3. **Row 3:** shows **two AC chips** (Living Room AC + Bedroom AC) with current temperatures and the word `Off`. Icons muted (disabled color) because ACs are off.
4. **Row 4:** shows two environment chips (Living Room + Bedroom) with temperature + humidity. Icons muted because humidifiers are `unavailable`.
5. **Row 5:** shows two 24 h history graphs, one per room, with temperature + humidity traces.
6. **No curtains.** **No humidifier control cards.**

- [ ] **Step 4: Tap through the interactive elements**

- Tap weather strip → more-info popup for `weather.forecast_home`.
- Tap each AC chip → more-info popup for that `climate.*` entity with full HVAC controls.
- Tap each room chip → more-info popup for the `humidifier.*` entity (even when unavailable, the popup opens).
- Tap a thermostat card → should interact as a thermostat (temperature adjustment).

- [ ] **Step 5: Simulate summer to verify the swap**

Temporarily edit `packages/bootstrap/templates/binary_sensors/cooling_season.yaml` — change the `state:` expression to a constant `true`:

```yaml
---
binary_sensor:
  - name: cooling_season
    state: >
      {{ true }}
    icon: >
      {{ 'mdi:snowflake' }}
```

Commit on a scratch commit, push, reload templates. Expected result on the climate tab:

- Row 2 now shows the **two AC thermostats** (Living Room AC, Bedroom AC).
- Row 3 now shows **two heating chips** (Floor Heating, Radiators) with current temperature + hvac_action.

Then restore the original logic by editing the same file back to:

```yaml
---
binary_sensor:
  - name: cooling_season
    state: >
      {{ now().month in [5, 6, 7, 8, 9] }}
    icon: >
      {{ 'mdi:snowflake' if now().month in [5, 6, 7, 8, 9] else 'mdi:radiator' }}
```

Then commit the revert as a normal commit (no force-push, clean history):

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git add packages/bootstrap/templates/binary_sensors/cooling_season.yaml
git commit -m "chore(templates): restore cooling_season after summer-swap verification"
git push
```

If the stub commit is still purely local and has not been pushed yet, `git reset --hard HEAD~1` is equivalent and leaves no trace.

Reload templates again and re-check that row 2 is back to heating thermostats.

Alternative (safer, no scratch commits at all): create `input_boolean.force_cooling_season` and OR it into the template (`{{ now().month in [5,6,7,8,9] or is_state('input_boolean.force_cooling_season','on') }}`). Only worth doing if you want a persistent override beyond one-off verification.

---

### Task 4: Open PR into `main`

**Files:** none (git/GitHub only)

- [ ] **Step 1: Confirm branch state is clean**

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git status
git log --oneline main..HEAD
```

Expected: working tree clean, commit list includes the spec (`ae5fec4`), the spec correction, the cooling_season feat, and the climate.yaml redesign feat.

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "Redesign tablet climate view (season-aware)" --body "$(cat <<'EOF'
## Summary
- Replace old 3-column tablet climate tab with a season-aware single-column layout
- Homecome heating (floor + radiators) is the primary hero in winter; ACs demote to a tap-to-expand chip row
- ACs become primary in summer; heating becomes the chip row
- Humidifiers move from primary controls to informational environment chips (tap opens full control)
- Curtains removed from the tab entirely
- Adds reusable `binary_sensor.cooling_season` (on May–Sep) driving the swap

Spec: `docs/superpowers/specs/2026-04-18-tablet-climate-redesign-design.md`

## Test plan
- [ ] `uv run pre-commit run --all-files` passes
- [ ] `binary_sensor.cooling_season` reports `off` in April
- [ ] Tablet `/climate` shows: weather strip → heating thermostats → AC chips → room env chips → 24 h graphs
- [ ] Tap AC chip opens more-info
- [ ] Tap room env chip opens humidifier more-info
- [ ] Simulated `cooling_season = on` renders AC thermostats + heating chips
EOF
)"
```

- [ ] **Step 3: Post-merge cleanup**

After the PR merges:

```bash
cd /Users/jakubigla/Project-Repositories/Personal/home-assistant-config
git checkout main
git pull
git branch -d chore/dashboard-redesign
```

HA auto-pulls from `main`, so the production wall-tablet picks up the new climate tab on its next sync.

---

## Self-Review Checklist

- [ ] Spec coverage: weather strip (Task 2 row 1), primary hero (Task 2 rows 2), secondary strip (Task 2 row 3), env chips (Task 2 row 4), graphs (Task 2 row 5), cooling_season sensor (Task 1), removed curtains (Task 2 — absent from new file), verification (Task 3) — all present.
- [ ] No placeholders — every step has exact code and commands.
- [ ] Type consistency: `binary_sensor.cooling_season` referenced identically in template and `visibility:` blocks; entity IDs cross-checked against live HA state query (`climate.floor_heating`, `climate.main_heating`, `climate.living_room`, `climate.bedroom`).
- [ ] Commit scope matches the spec's two-commit plan (cooling_season + climate.yaml). A third minor commit for the spec-path correction already landed.
