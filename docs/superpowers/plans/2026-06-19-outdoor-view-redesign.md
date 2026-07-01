# Outdoor View Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Outdoor tablet view (`dashboards/tablet/outdoor.yaml`) into a real `type: sections` masonry layout that eliminates the dead-whitespace band, leads with an At-a-Glance status row, and tucks the Smart-drip threshold sliders behind a collapsible expander — keeping every existing function.

**Architecture:** The current view is one `column_span: 3` section wrapping rigid `horizontal-stack` two-column bands; uneven column heights leave a dead band. The rewrite splits content into independent `type: sections` sections at default span (plus two full-width spanners), letting HA's grid masonry-pack them. Cards move verbatim where possible; only the chip groupings and the threshold-panel wrapper change. No backend/automation/helper changes — pure presentation.

**Tech Stack:** Home Assistant Lovelace YAML; Mushroom cards; `custom:expander-card` (HACS, `lovelace-expander-card`); card-mod; verification via `yamllint`/pre-commit + `/api/template` server render + Playwright WS force-refetch + screenshot.

**Spec:** `docs/superpowers/specs/2026-06-18-outdoor-view-redesign-design.md`
**Branch:** `chore/june-features` (HA currently tracks this branch).

---

## Why this plan is not classic TDD

Lovelace YAML has no unit-test harness. The equivalent "test" gate for each task is:
1. **Lint** — `uv run pre-commit run --all-files` (yamllint ignores `dashboards/` but YAML-parse + other hooks still run).
2. **Render** — any Jinja-in-card is rendered server-side via `/api/template` to prove it produces the expected string before pushing.
3. **Visual** — once the full file is assembled, push → HA pull → WS force-refetch (`lovelace/config`, `force:true`) → navigate-away-and-back → full-page Playwright screenshot, checked against the spec.

We build the new file in ONE working copy, section by section, linting after each, then do the single push + visual verification at the end (a half-built sections view isn't independently shippable). Each task still commits so the history is bite-sized and revertible.

`curl` against `homeassistant.local` needs `dangerouslyDisableSandbox: true`. Env vars `$HA_URL`, `$HA_TOKEN` are preloaded via direnv.

---

## File Structure

- **Modify (full rewrite):** `dashboards/tablet/outdoor.yaml` — the entire Outdoor view. Same file, same `path: outdoor`, same nine logical groups re-expressed as real sections.

No other files change. The four `input_number` threshold helpers, the `garden_drip_soil_status` sensor, and all garden automations already exist on this branch and are untouched.

---

## Task 0: Pre-flight — confirm expander-card resource is loaded

**Files:** none (verification only).

The whole plan assumes `custom:expander-card` renders. If the HACS resource is not yet registered, the Soil & Drip section would ship a `custom:expander-card` text stub. Gate here.

- [ ] **Step 1: Query loaded Lovelace resources over the WS bridge**

Navigate Playwright to `http://homeassistant.local:8123/wall-tablet/outdoor` (log in if prompted), then evaluate:

```js
async () => {
  const hass = document.querySelector('home-assistant')?.hass;
  const res = await hass.connection.sendMessagePromise({ type: 'lovelace/resources' });
  const urls = (res || []).map(r => r.url);
  return JSON.stringify({ expander: urls.filter(u => /expander/i.test(u)), count: urls.length });
}
```

Expected: `expander` array contains `/hacsfiles/lovelace-expander-card/expander-card.js` (or similar).

- [ ] **Step 2: Branch on the result**

- If `expander` is non-empty → proceed to Task 1.
- If `expander` is empty → STOP. Tell the user: "Expander Card HACS resource isn't loaded yet — finish installing it (HACS → Frontend → Expander Card → install, then hard-refresh) and I'll continue." Do NOT build the expander section against a missing resource.

No commit (verification only).

---

## Task 1: Snapshot the current view and start the rewrite scaffold

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml`

- [ ] **Step 1: Keep a reference copy of the old file**

```bash
cp dashboards/tablet/outdoor.yaml /tmp/outdoor.old.yaml
```

This is the source of truth for every card's exact YAML as we move pieces. Not committed.

- [ ] **Step 2: Write the new top-level view scaffold + Weather + At-a-Glance sections**

Replace the ENTIRE contents of `dashboards/tablet/outdoor.yaml` with the scaffold below. (Later tasks append sections under `sections:`.)

```yaml
---
title: Outdoor
path: outdoor
icon: mdi:tree
type: sections
max_columns: 3
sections:
  # ── Weather hero (full width) ──────────────────────────────
  - type: grid
    column_span: 3
    cards:
      - type: weather-forecast
        grid_options:
          columns: full
        entity: weather.forecast_home
        show_current: true
        show_forecast: true
        forecast_type: hourly
        forecast_slots: 10

  # ── At a Glance: irrigation timings + gate status (full width) ──
  - type: grid
    column_span: 3
    cards:
      - type: custom:mushroom-chips-card
        alignment: justified
        grid_options:
          columns: full
        chips:
          - type: template
            icon: mdi:water
            icon_color: cyan
            content: >-
              {% set v = states('sensor.garden_drip_last_run') %}
              Drip: {% if v in ['unknown', 'unavailable', 'None', ''] %}
              never{% else %}{{ v | as_timestamp
                 | timestamp_custom('%a %H:%M') }}{% endif %}
          - type: template
            icon: mdi:sprinkler-variant
            icon_color: green
            content: >-
              {% set v = states('sensor.garden_lawn_last_run') %}
              Lawn: {% if v in ['unknown', 'unavailable', 'None', ''] %}
              never{% else %}{{ v | as_timestamp
                 | timestamp_custom('%a %H:%M') }}{% endif %}
          - type: template
            icon: mdi:clock-outline
            icon_color: green
            content: >-
              {% set v = states('sensor.garden_lawn_next_run') %}
              Next: {% if v in ['unknown', 'unavailable', 'None', ''] %}
              —{% else %}{{ v | as_timestamp
                 | timestamp_custom('%a %H:%M') }}{% endif %}
          - type: template
            entity: cover.garden_park_gate
            icon: >-
              {{ 'mdi:gate-open' if is_state('cover.garden_park_gate', 'open')
              else 'mdi:gate' }}
            icon_color: >-
              {{ 'red' if is_state('cover.garden_park_gate', 'open') else 'green' }}
            content: >-
              Park gate: {{ 'Open' if is_state('cover.garden_park_gate', 'open')
              else 'Closed' }}
            tap_action:
              action: more-info
          - type: template
            entity: cover.garage_door
            icon: >-
              {{ 'mdi:garage-open' if is_state('cover.garage_door', 'open')
              else 'mdi:garage' }}
            icon_color: >-
              {{ 'red' if is_state('cover.garage_door', 'open') else 'green' }}
            content: >-
              Garage: {{ 'Open' if is_state('cover.garage_door', 'open')
              else 'Closed' }}
            tap_action:
              action: more-info
```

> Note: `type: grid` is the canonical section type in this repo's sections views; `column_span: 3` on a grid section makes it span the full three-column width. Default-span sections (later tasks) omit `column_span` so HA masonry-packs them.

- [ ] **Step 3: Lint**

Run: `uv run pre-commit run --all-files`
Expected: all hooks Pass (or "no files to check" skips for non-YAML hooks).

- [ ] **Step 4: Render the At-a-Glance chip templates server-side**

Run (sandbox disabled):

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d @- <<'EOF'
{"template": "DRIP={% set v = states('sensor.garden_drip_last_run') %}{% if v in ['unknown','unavailable','None',''] %}never{% else %}{{ v | as_timestamp | timestamp_custom('%a %H:%M') }}{% endif %}\nPARK={{ 'Open' if is_state('cover.garden_park_gate','open') else 'Closed' }} GARAGE={{ 'Open' if is_state('cover.garage_door','open') else 'Closed' }}"}
EOF
```

Expected: a line like `DRIP=Thu 16:28` (or `never`) and `PARK=Closed GARAGE=Closed`. Confirms the entity ids resolve and the Jinja is valid. If `cover.garden_park_gate` / `cover.garage_door` render empty, re-confirm the cover entity ids in `/tmp/outdoor.old.yaml` (lines for Gates) and fix.

- [ ] **Step 5: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "refactor(outdoor): sections scaffold + weather + at-a-glance band"
```

---

## Task 2: Soil & Drip section (Smart-only, with expander tuning)

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` (append section under `sections:`)

- [ ] **Step 1: Append the Soil & Drip section**

Add this as the next list item under `sections:` (after the At-a-Glance grid). It carries the probe chips + verdict chip moved verbatim from the old file, plus the threshold sliders wrapped in `custom:expander-card`:

```yaml
  # ── Soil & Drip (Smart mode only) ──────────────────────────
  - type: grid
    visibility:
      - condition: state
        entity: input_select.garden_irrigation_mode
        state: Smart
    cards:
      - type: heading
        heading: Soil & Drip
        heading_style: title
      - type: custom:mushroom-chips-card
        alignment: justified
        chips:
          - type: template
            entity: sensor.pergola_left_flowerbed_soil_moisture
            icon: mdi:water-percent
            icon_color: >-
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) %}
              {{ 'red' if states('sensor.pergola_left_flowerbed_soil_moisture')
                 | float(99) < start else 'cyan' }}
            content: >-
              L {{ states('sensor.pergola_left_flowerbed_soil_moisture')
                 | float(0) | round(0) | int }}%
          - type: template
            entity: sensor.pergola_right_flowerbed_soil_moisture
            icon: mdi:water-percent
            icon_color: >-
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) %}
              {{ 'red' if states('sensor.pergola_right_flowerbed_soil_moisture')
                 | float(99) < start else 'cyan' }}
            content: >-
              R {{ states('sensor.pergola_right_flowerbed_soil_moisture')
                 | float(0) | round(0) | int }}%
          - type: template
            entity: sensor.sona_flowerbed_soil_moisture
            icon: mdi:water-percent
            icon_color: >-
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) %}
              {{ 'red' if states('sensor.sona_flowerbed_soil_moisture')
                 | float(99) < start else 'cyan' }}
            content: >-
              Sona {{ states('sensor.sona_flowerbed_soil_moisture')
                 | float(0) | round(0) | int }}%
          - type: template
            icon: >-
              {% set st = states('sensor.garden_drip_soil_status') %}
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) %}
              {% set dry = state_attr('sensor.garden_drip_soil_status', 'driest')
                 | float(99) %}
              {% if dry < start and st == 'armed' %}mdi:sprinkler
              {% elif dry < start %}mdi:cancel
              {% elif st == 'armed' %}mdi:water-alert
              {% else %}mdi:water-check{% endif %}
            icon_color: >-
              {% set st = states('sensor.garden_drip_soil_status') %}
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) %}
              {% set dry = state_attr('sensor.garden_drip_soil_status', 'driest')
                 | float(99) %}
              {% if dry < start and st == 'armed' %}blue
              {% elif dry < start %}orange
              {% elif st == 'armed' %}amber
              {% else %}green{% endif %}
            content: >-
              {% set st = states('sensor.garden_drip_soil_status') %}
              {% set start = state_attr('sensor.garden_drip_soil_status',
                 'start_pct') | float(35) | int %}
              {% set stop = state_attr('sensor.garden_drip_soil_status',
                 'stop_pct') | float(60) | int %}
              {% set dry = state_attr('sensor.garden_drip_soil_status', 'driest')
                 | float(-1) %}
              {% set reason = state_attr('sensor.garden_drip_soil_status',
                 'blocking_reason') %}
              {% if dry < 0 %}No probe data
              {% elif dry >= start and st != 'armed' %}Wet ({{ dry | int }}%) · waits for >{{ stop }}% recovery
              {% elif dry >= start %}Armed · waits until driest <{{ start }}% (now {{ dry | int }}%)
              {% elif reason == 'none' %}Dry {{ dry | int }}% · running now
              {% elif reason == 'rain' %}Dry {{ dry | int }}% · held: raining
              {% elif reason == 'out_of_season' %}Dry {{ dry | int }}% · held: off-season
              {% elif reason == 'saturation' %}Dry {{ dry | int }}% · held: pergola saturated
              {% elif reason == 'cooldown_days' %}Dry {{ dry | int }}% · held: daily cooldown
              {% elif reason == 'night' %}Dry {{ dry | int }}% · held: night quiet hours
              {% elif reason == 'valve_open' %}Dry {{ dry | int }}% · valve already open
              {% elif reason == 'disarmed' %}Dry {{ dry | int }}% · disarmed, ran recently
              {% else %}Dry {{ dry | int }}% · {{ reason }}{% endif %}
      - type: custom:expander-card
        title: Tuning
        icon: mdi:tune-variant
        expanded: false
        cards:
          - type: entities
            entities:
              - entity: input_number.garden_drip_soil_start
                name: Fire below
              - entity: input_number.garden_drip_soil_stop
                name: Re-arm above
              - entity: input_number.garden_drip_soil_sat
                name: Saturation veto
              - entity: input_number.garden_drip_min_days_between
                name: Min days between
```

> `custom:expander-card` uses `title`, `expanded: false`, and a nested `cards:` list (the `lovelace-expander-card` API). If during verification the accordion needs `clear: true` or different keys, that's the one spot to adjust.

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: all Pass.

- [ ] **Step 3: Render the verdict template to confirm thresholds resolve**

Run (sandbox disabled):

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d @- <<'EOF'
{"template": "{% set start = state_attr('sensor.garden_drip_soil_status','start_pct') | float(35) | int %}{% set stop = state_attr('sensor.garden_drip_soil_status','stop_pct') | float(60) | int %}{% set dry = state_attr('sensor.garden_drip_soil_status','driest') | float(-1) %}{% set st = states('sensor.garden_drip_soil_status') %}VERDICT={% if dry >= start and st != 'armed' %}Wet ({{ dry|int }}%) waits >{{ stop }}%{% elif dry >= start %}Armed waits <{{ start }}%{% else %}dry-path{% endif %}"}
EOF
```

Expected: e.g. `VERDICT=Wet (85%) waits >60%`. Confirms `start_pct`/`stop_pct`/`driest` attributes exist on the sensor and resolve.

- [ ] **Step 4: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "refactor(outdoor): soil & drip section with expander tuning panel"
```

---

## Task 3: 7-Day Schedule section

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` (append section)

- [ ] **Step 1: Append the 7-Day Schedule section**

Move the existing markdown table card verbatim from `/tmp/outdoor.old.yaml` (the `type: markdown` card with the `schedule_7day` table) into its own default-span section. Append under `sections:`:

```yaml
  # ── 7-Day Schedule ─────────────────────────────────────────
  - type: grid
    cards:
      - type: heading
        heading: 7-Day Schedule
        heading_style: title
      - type: markdown
        entities:
          - input_select.garden_irrigation_mode
          - sensor.garden_irrigation_profile
        card_mod:
          style:
            ha-markdown$: |
              ha-markdown-element table {
                width: 100%;
                border-collapse: collapse;
              }
              ha-markdown-element th,
              ha-markdown-element td {
                padding: 4px 6px;
                text-align: left;
              }
              ha-markdown-element tr.today td {
                font-weight: 600;
              }
              ha-markdown-element td.note {
                color: var(--secondary-text-color);
              }
        content: |
          {% set mode = states('input_select.garden_irrigation_mode') %}
          {% set sched = state_attr('sensor.garden_schedule_brain', 'schedule_7day') or [] %}
          {% set tz = now().tzinfo %}
          {% macro dur(s) -%}
          {%- if s >= 3600 -%}{{ (s / 3600) | round(1) }}h
          {%- elif s >= 60 -%}{{ (s // 60) | int }}m
          {%- else -%}{{ s | int }}s{%- endif -%}
          {%- endmacro %}
          {% if mode == 'Manual' %}
          _Manual mode — no scheduled runs._
          {% else %}
          | Day | Lawn | Zones (z1·z2·z3) | Drip |
          |---|---|---|---|
          {% for row in sched -%}
          {%- set d = strptime(row.date, '%Y-%m-%d').replace(tzinfo=tz) -%}
          {%- set side = (row.lawn_am_min * 0.6) | round(0) | int -%}
          {%- if row.sessions == 2 -%}
            {%- set lawn_cell = '✓ AM ' ~ row.lawn_am_min ~ 'm + PM ' ~ row.lawn_pm_min ~ 'm' -%}
            {%- set zones_cell = (row.lawn_am_min ~ '·' ~ side ~ '·' ~ side ~ ' +PM') -%}
          {%- elif row.sessions == 1 -%}
            {%- set lawn_cell = '✓ ' ~ row.lawn_am_min ~ 'm' -%}
            {%- set zones_cell = (row.lawn_am_min ~ '·' ~ side ~ '·' ~ side) -%}
          {%- else -%}
            {%- set lawn_cell = '—' -%}
            {%- set zones_cell = '—' -%}
          {%- endif -%}
          {%- if mode == 'Smart' -%}
            {%- set drip_cell = '💧 soil' -%}
          {%- else -%}
            {%- set drip_cell = ('✓ ' ~ dur(row.drip_min * 60)) if row.drip_min > 0 else '—' -%}
          {%- endif -%}
          | {% if loop.first %}**{{ d.strftime('%a %d') }}**{% else %}{{ d.strftime('%a %d') }}{% endif %} | {{ lawn_cell }} | {{ zones_cell }} | {{ drip_cell }} |
          {% endfor %}

          {% if mode == 'Seasonal' %}
          _Seasonal: deep AM soak + ~60% PM top-up on 2-session days. AM {{ state_attr('sensor.garden_irrigation_profile', 'am_time') | trim }}{% if state_attr('sensor.garden_irrigation_profile', 'pm_time') | trim %} + PM {{ state_attr('sensor.garden_irrigation_profile', 'pm_time') | trim }}{% endif %}. Drip Mon/Thu._
          {% elif mode == 'Smart' %}
          _Smart: drip is demand-based, not scheduled — fires when driest flowerbed &lt; {{ state_attr('sensor.garden_drip_soil_status', 'start_pct') | float(35) | int }}%. Status: {{ states('sensor.garden_drip_soil_status') }}{% set dry = state_attr('sensor.garden_drip_soil_status', 'driest') %}{% if dry is not none %} (driest {{ dry | int }}%){% endif %}. Lawn follows the schedule above._
          {% else %}
          _Lawn cycle &amp; soak; zone mins = total per run._
          {% endif %}
          {% endif %}
```

- [ ] **Step 2: Lint**

Run: `uv run pre-commit run --all-files`
Expected: all Pass. (This card was already live and valid; the only change is wrapping it in its own section.)

- [ ] **Step 3: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "refactor(outdoor): 7-day schedule in its own section"
```

---

## Task 4: Irrigation Control + Run Now sections

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` (append two sections)

- [ ] **Step 1: Append the Irrigation Control section**

Mode select + one-off scheduler, moved verbatim from `/tmp/outdoor.old.yaml`:

```yaml
  # ── Irrigation Control: mode + one-off scheduler ───────────
  - type: grid
    cards:
      - type: heading
        heading: Irrigation Control
        heading_style: title
      - type: custom:mushroom-select-card
        entity: input_select.garden_irrigation_mode
        name: Irrigation Mode
        icon: mdi:sprinkler
        layout: horizontal
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

- [ ] **Step 2: Append the Run Now section**

The three run buttons (Lawn/Drip/Full) PLUS the minutes-per-zone slider and Run-Lawn-now button — regrouped together (today they are split across the two old columns). Moved verbatim from `/tmp/outdoor.old.yaml`:

```yaml
  # ── Run Now: manual triggers + on-demand lawn ──────────────
  - type: grid
    cards:
      - type: heading
        heading: Run Now
        heading_style: title
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            entity: script.garden_lawn_irrigation
            primary: Lawn
            icon: mdi:sprinkler-variant
            icon_color: green
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_lawn_irrigation
          - type: custom:mushroom-template-card
            entity: script.garden_drip_irrigation
            primary: Drip
            icon: mdi:water
            icon_color: cyan
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_drip_irrigation
          - type: custom:mushroom-template-card
            entity: script.garden_full_irrigation
            primary: Full
            icon: mdi:sprinkler
            icon_color: teal
            layout: vertical
            tap_action:
              action: perform-action
              perform_action: script.turn_on
              target:
                entity_id: script.garden_full_irrigation
      - type: heading
        heading: Run Lawn Now
        heading_style: subtitle
      - type: custom:mushroom-number-card
        entity: input_number.garden_ondemand_minutes
        name: Minutes per zone
        display_mode: slider
        icon: mdi:timer-outline
      - type: custom:mushroom-template-card
        primary: >-
          {% if is_state('script.garden_ondemand_lawn', 'on') %}
          Running lawn…
          {% else %}Run Lawn{% endif %}
        secondary: >-
          {% if is_state('valve.lawn_sprinkler_zone_1', 'open') %}
          Zone 1 watering
          {% elif is_state('valve.lawn_sprinkler_zone_2', 'open') %}
          Zone 2 watering
          {% elif is_state('valve.lawn_sprinkler_zone_3', 'open') %}
          Zone 3 watering
          {% else %}
          Zones 1→2→3 · {{ states('input_number.garden_ondemand_minutes') | int }} min each
          {% endif %}
        icon: mdi:sprinkler
        icon_color: >-
          {{ 'blue' if is_state('script.garden_ondemand_lawn', 'on') else 'grey' }}
        layout: horizontal
        tap_action:
          action: perform-action
          perform_action: script.turn_on
          target:
            entity_id: script.garden_ondemand_lawn
```

- [ ] **Step 3: Lint**

Run: `uv run pre-commit run --all-files`
Expected: all Pass.

- [ ] **Step 4: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "refactor(outdoor): irrigation control + run now sections"
```

---

## Task 5: Structure sections — Pergola, Gates, Terrace

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml` (append three sections)

- [ ] **Step 1: Append Pergola, Gates, and Terrace sections**

Moved verbatim from `/tmp/outdoor.old.yaml` (the old bottom band), each now its own default-span section so masonry packs them:

```yaml
  # ── Pergola ────────────────────────────────────────────────
  - type: grid
    cards:
      - type: heading
        heading: Pergola
        heading_style: title
      - type: custom:mushroom-cover-card
        entity: cover.pergola_roof_proxy
        name: Pergola Roof
        icon: mdi:pergola
        show_buttons_control: true
        show_position_control: false
        layout: horizontal
      - type: custom:mushroom-select-card
        entity: input_select.pergola_weather_mode
        name: Weather Mode
        icon: mdi:weather-pouring
        layout: horizontal

  # ── Gates ──────────────────────────────────────────────────
  - type: grid
    cards:
      - type: heading
        heading: Gates
        heading_style: title
      - type: custom:mushroom-cover-card
        entity: cover.garden_park_gate
        name: Garden Park Gate
        icon: mdi:gate-arrow-right
        show_buttons_control: true
        show_position_control: false
        layout: horizontal
      - type: custom:mushroom-cover-card
        entity: cover.garage_door
        name: Garage Gate
        icon: mdi:garage
        show_buttons_control: true
        show_position_control: false
        layout: horizontal

  # ── Terrace ────────────────────────────────────────────────
  - type: grid
    cards:
      - type: heading
        heading: Terrace
        heading_style: title
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            entity: binary_sensor.terrace_main_door
            icon: >-
              {{ 'mdi:door-open' if
              is_state('binary_sensor.terrace_main_door', 'on')
              else 'mdi:door-closed' }}
            icon_color: >-
              {{ 'red' if is_state('binary_sensor.terrace_main_door', 'on')
              else 'green' }}
            content: >-
              Main: {{ 'Open' if
              is_state('binary_sensor.terrace_main_door', 'on')
              else 'Closed' }}
            tap_action:
              action: more-info
          - type: template
            entity: binary_sensor.terrace_left_door
            icon: >-
              {{ 'mdi:door-open' if
              is_state('binary_sensor.terrace_left_door', 'on')
              else 'mdi:door-closed' }}
            icon_color: >-
              {{ 'red' if is_state('binary_sensor.terrace_left_door', 'on')
              else 'green' }}
            content: >-
              Left: {{ 'Open' if
              is_state('binary_sensor.terrace_left_door', 'on')
              else 'Closed' }}
            tap_action:
              action: more-info
          - type: template
            entity: binary_sensor.porch_is_dark
            icon: >-
              {{ 'mdi:weather-night' if
              is_state('binary_sensor.porch_is_dark', 'on')
              else 'mdi:white-balance-sunny' }}
            icon_color: >-
              {{ 'indigo' if is_state('binary_sensor.porch_is_dark', 'on')
              else 'amber' }}
            content: >-
              Porch: {{ 'Dark' if is_state('binary_sensor.porch_is_dark', 'on')
              else 'Light' }}
            tap_action:
              action: more-info
```

- [ ] **Step 2: Lint the full assembled file**

Run: `uv run pre-commit run --all-files`
Expected: all Pass. The file is now complete — nine sections (two full-width spanners + seven default-span).

- [ ] **Step 3: Sanity-diff against the old file's entity set**

Confirm no entity was dropped in the move:

```bash
grep -oE "(sensor|cover|valve|script|input_[a-z]+|binary_sensor)\.[a-z0-9_]+" /tmp/outdoor.old.yaml | sort -u > /tmp/old.ents
grep -oE "(sensor|cover|valve|script|input_[a-z]+|binary_sensor)\.[a-z0-9_]+" dashboards/tablet/outdoor.yaml | sort -u > /tmp/new.ents
echo "=== In OLD but not NEW (should be empty) ==="
comm -23 /tmp/old.ents /tmp/new.ents
echo "=== In NEW but not OLD (expect: cover gate/garage now in glance band) ==="
comm -13 /tmp/old.ents /tmp/new.ents
```

Expected: "In OLD but not NEW" is empty (nothing lost). "In NEW but not OLD" may list the cover entities now also referenced by the new glance chips — that's intentional.

- [ ] **Step 4: Commit**

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "refactor(outdoor): pergola, gates, terrace structure sections"
```

---

## Task 6: Push, pull, and visual verification

**Files:** none (deploy + verify).

- [ ] **Step 1: Push**

```bash
git push
```

- [ ] **Step 2: Wait for HA pull**

Wait ~8–10 s. Lovelace YAML needs no reload, but the frontend caches the parsed config — the next steps force a re-fetch.

- [ ] **Step 3: Force-refetch the config over the WS bridge (bypass frontend cache)**

Navigate Playwright to `http://homeassistant.local:8123/wall-tablet/outdoor`, then evaluate:

```js
async () => {
  const hass = document.querySelector('home-assistant')?.hass;
  const resp = await hass.connection.sendMessagePromise({
    type: 'lovelace/config', url_path: 'wall-tablet', force: true,
  });
  const v = (resp.views || []).find(x => x.path === 'outdoor');
  return JSON.stringify({
    section_count: (v.sections || []).length,
    has_glance: JSON.stringify(v).includes('Park gate'),
    has_expander: JSON.stringify(v).includes('custom:expander-card'),
    has_terrace: JSON.stringify(v).includes('Terrace'),
  });
}
```

Expected: `section_count: 9`, all three booleans `true`. If `section_count` is wrong or a flag is false, the backend hasn't pulled the new file — wait and retry; if it persists, the addon's branch/pull is broken (not lag) — see the `ha-pull-branch` / no-pull-lag knowledge notes.

- [ ] **Step 4: Force a clean re-mount**

```js
// navigate away then back so the Lovelace view component remounts with fresh config
await mcp__playwright__browser_navigate({ url: 'http://homeassistant.local:8123/wall-tablet/home' });
await mcp__playwright__browser_navigate({ url: 'http://homeassistant.local:8123/wall-tablet/outdoor' });
```

- [ ] **Step 5: Screenshot and inspect**

```js
await mcp__playwright__browser_take_screenshot({
  fullPage: true, type: 'png', filename: '.playwright-mcp/outdoor.png',
});
```

Then Read `.playwright-mcp/outdoor.png` and check against the spec's verification list:
- No dead whitespace band; masonry packs columns evenly (short sections fill gaps).
- At-a-Glance band: drip/lawn/next + park-gate + garage chips, no wrap clipping.
- Soil & Drip section visible (mode is Smart): three probe chips + verdict + a **collapsed** "Tuning" expander — NOT a `custom:expander-card` text stub.
- 7-Day Schedule table renders with the Smart footnote.
- Irrigation Control: mode select + one-off scheduler.
- Run Now: three buttons + minutes slider + Run-Lawn button grouped together.
- Pergola / Gates / Terrace each render their controls/chips.
- 0 console errors (`mcp__playwright__browser_console_messages` level error).

- [ ] **Step 6: Verify the expander expands**

Take a snapshot, click the "Tuning" expander header, screenshot again. Confirm the four sliders (Fire below / Re-arm above / Saturation veto / Min days between) appear when expanded and are hidden when collapsed.

- [ ] **Step 7: Verify Smart-only visibility**

Temporarily switch the mode to confirm the Soil & Drip section hides:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Standard"}'
```

Re-mount (navigate away/back), screenshot — Soil & Drip section should be GONE, 7-Day table drip column should show schedule minutes (not `💧 soil`). Then restore:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/input_select/select_option" \
  -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Smart"}'
```

(Both curls need `dangerouslyDisableSandbox: true`.)

- [ ] **Step 8: If all checks pass, the rewrite is done**

No further commit needed (the file was committed in Task 5). If a fix was required during verification, commit it:

```bash
git add dashboards/tablet/outdoor.yaml
git commit -m "fix(outdoor): <what the visual check caught>"
git push
```

---

## Task 7: Regenerate area docs (if applicable)

**Files:**
- Possibly modify: the outdoor/garden area README.

- [ ] **Step 1: Check whether this view is covered by an area README**

The CLAUDE.md convention: after modifying an area package run `/ha-area-docs`. This change is a dashboard view, not an area package — but the garden README may reference the dashboard. Check:

```bash
grep -rl "outdoor" packages/areas/outdoor/*/README.md 2>/dev/null
```

- If a README references the Outdoor dashboard view, run the `/ha-area-docs` skill for that area to regenerate it.
- If nothing matches, skip — no docs to update.

No commit unless a README changed.

---

## Self-Review notes (for the executor)

- **Spec coverage:** Weather (T1), At-a-Glance (T1), Soil & Drip + expander (T2), 7-Day (T3), Irrigation Control (T4), Run Now (T4), Pergola/Gates/Terrace (T5), masonry + verify (T6). Terrace kept as own section (T5), glance band excludes terrace chips (T1) — matches the revised spec.
- **Entity preservation** is checked mechanically in T5 Step 3.
- **Expander dependency** is gated in T0 and re-confirmed in T6 Step 3/6.
- **No backend changes:** every garden helper/sensor/automation is referenced but never edited.
