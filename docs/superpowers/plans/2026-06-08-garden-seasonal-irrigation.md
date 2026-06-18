# Garden Seasonal Irrigation + Rain-Intensity Skip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "Seasonal" irrigation mode (twice-daily May–Sep schedule from a month/day table) and a smarter rain skip driven by Open-Meteo accumulated rainfall (mm), folded into the existing garden valve/profile system without disturbing other modes.

**Architecture:** Two `input_number` helpers feed a new `Seasonal` branch in the existing `sensor.garden_irrigation_profile` (durations, days, AM/PM session times, drip Mon/Thu, single-pass cycle_count). A new `rest:` sensor sums Open-Meteo precipitation over [now−24h, now+12h] (URL from a secret); the lawn skip sensor switches to a ≥3 mm threshold with fail-open. A new dual-session automation dispatches the existing irrigation scripts with night-guard / already-on / skip-notify guards. The existing 04:00 automation excludes Seasonal so they never double-fire.

**Tech Stack:** Home Assistant YAML packages (`packages/areas/outdoor/garden/`), `rest:` platform sensor, Open-Meteo free API (no key), `!secret`, `just` (`check`, `lint`), API/MCP for live reload + verification.

**Spec:** `docs/superpowers/specs/2026-06-08-garden-seasonal-irrigation-design.md`

> **Verification model:** HA config, not application code — no unit-test runner. "Test" = `just check` (config validity) + `uv run yamllint` + live verification against HA after push+reload (render `sensor.garden_irrigation_profile` attrs, check the rest sensor, trip skip thresholds, fire the automation). Deployment loop: commit on feature branch → `git push` → reload HA → check logs. **Never push to main.** Current branch: `chore/may-fixes`.

---

## File Structure

- **Modify** `secrets.yaml` (gitignored) + `secrets.fake.yaml` — add `garden_rain_url`.
- **Modify** `packages/areas/outdoor/garden/config.yaml` — add `Seasonal` option, 2 `input_number`s, and the `rest:` sensor block (HA `rest:` is a top-level platform — it CANNOT live in a file loaded by `template: !include_dir_list templates`, so it goes directly in `config.yaml`).
- **Modify** `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` — Seasonal branch in every attribute + `am_time`/`pm_time` + mode-aware `cycle_count`.
- **Modify** `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml` — ≥3 mm rule + soil-ready + new reasons.
- **Create** `packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml` — dual-session automation.
- **Modify** `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml` — exclude `Seasonal`.
- **Modify** `packages/areas/outdoor/garden/scripts/garden_ondemand_lawn.yaml` — add night-guard + already-on + skip checks (manual path).
- **Modify** `packages/areas/outdoor/garden/README.md` — document everything.

---

### Task 1: Add the Open-Meteo URL secret

**Files:**
- Modify: `secrets.yaml` (gitignored, real coords)
- Modify: `secrets.fake.yaml` (committed, zeroed placeholder)

- [ ] **Step 1: Add the real URL to `secrets.yaml`**

The repo's home coords are lat `52.2476`, lon `20.8362` (from HA config). Append to `secrets.yaml`:

```yaml
garden_rain_url: "https://api.open-meteo.com/v1/forecast?latitude=52.2476&longitude=20.8362&hourly=precipitation&past_days=1&forecast_days=2&timezone=auto"
```

`secrets.yaml` is gitignored — editing it does NOT get committed. Do NOT `git add` it. (The `.env` PreToolUse hook blocks dotenv reads but `secrets.yaml` is a normal YAML file — edit it directly with the Edit/Write tool.)

- [ ] **Step 2: Add the placeholder to `secrets.fake.yaml`**

Append to `secrets.fake.yaml` (this IS committed — must contain no real coords):

```yaml
garden_rain_url: "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&hourly=precipitation&past_days=1&forecast_days=2&timezone=auto"
```

- [ ] **Step 3: Verify the real URL returns data**

Run (sandbox blocks external? No — open-meteo is public; if blocked, add `dangerouslyDisableSandbox: true`):
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=52.2476&longitude=20.8362&hourly=precipitation&past_days=1&forecast_days=2&timezone=auto" | python3 -c "import sys,json; d=json.load(sys.stdin); print('hours:', len(d['hourly']['time']), 'unit:', d['hourly_units']['precipitation'])"
```
Expected: `hours: 72 unit: mm` (or similar non-zero count).

- [ ] **Step 4: Commit the fake only**

```bash
git add secrets.fake.yaml
git commit -m "feat(garden): add garden_rain_url secret placeholder"
```
Confirm `git status` shows `secrets.yaml` as NOT staged / ignored.

---

### Task 2: Add helpers + rest sensor to config.yaml

**Files:**
- Modify: `packages/areas/outdoor/garden/config.yaml`

- [ ] **Step 1: Add `Seasonal` to the mode options**

In `input_select.garden_irrigation_mode.options`, add `Seasonal` after `Smart` (read the file first; the list is Manual/Eco/Standard/Intensive/Testing/Smart). Result:

```yaml
    options:
      - Manual
      - Eco
      - Standard
      - Intensive
      - Testing
      - Smart
      - Seasonal
```

- [ ] **Step 2: Add the two `input_number` helpers**

The file already has an `input_number:` block (with `garden_ondemand_minutes`). Add two keys under it:

```yaml
  garden_lawn_minutes_standard:
    name: Garden Lawn Minutes (standard)
    min: 5
    max: 30
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline
  garden_lawn_minutes_july:
    name: Garden Lawn Minutes (July)
    min: 5
    max: 30
    step: 1
    unit_of_measurement: min
    icon: mdi:timer-outline
```

- [ ] **Step 3: Add the `rest:` sensor block**

Add a new top-level `rest:` key to `config.yaml` (NOT in the templates dir — `rest:` is its own platform). Append at the end of the file:

```yaml
rest:
  - resource: !secret garden_rain_url
    scan_interval: 1800
    sensor:
      - name: Garden Rain Accumulation
        unique_id: garden_rain_accumulation_mm
        unit_of_measurement: mm
        value_template: >
          {% set t = value_json.hourly.time %}
          {% set p = value_json.hourly.precipitation %}
          {% set lo = (now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H') %}
          {% set hi = (now() + timedelta(hours=12)).strftime('%Y-%m-%dT%H') %}
          {% set ns = namespace(total=0.0) %}
          {% for i in range(t | count) %}
            {% if t[i][:13] >= lo and t[i][:13] <= hi %}
              {% set ns.total = ns.total + (p[i] | float(0)) %}
            {% endif %}
          {% endfor %}
          {{ ns.total | round(2) }}
        json_attributes_path: "$.hourly"
        json_attributes:
          - time
```

(The `value_template` sums precipitation for hours whose `YYYY-MM-DDTHH` prefix is within the window. Open-Meteo `time` strings are local with `timezone=auto`.)

- [ ] **Step 4: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/config.yaml`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/config.yaml
git commit -m "feat(garden): Seasonal mode option, duration helpers, Open-Meteo rain sensor"
```

---

### Task 3: Add the Seasonal branch to the profile

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

Read the whole file first — each attribute is an independent inline-computed Jinja block (no cross-attribute `this` reads, by design). You will add a `Seasonal` branch to: `effective_mode`, `lawn_durations`, `cycle_count`, `lawn_today`, `drip_today`, `drip_duration`, `drip_runs_per_day`, and add two NEW attributes `am_time`, `pm_time`.

- [ ] **Step 1: `effective_mode` — pass Seasonal through**

`effective_mode` currently maps Smart→tier and passes named modes through. Seasonal is a named mode, so it already passes through unchanged (it is not `Smart`). No edit needed — verify by reading. If the block has an explicit allow-list, add `Seasonal`; the current code uses `{% set effective = mode %}` default, so Seasonal passes through. **No change.**

- [ ] **Step 2: `lawn_durations` — Seasonal per-zone seconds from helpers**

In the `lawn_durations` attribute, add a Seasonal branch BEFORE the final `{% else %}`. Seasonal z1 base minutes = July helper in month 7, else standard helper; z2=z3 = `round(z1 × 0.6)`; zero outside May–Sep. Insert:

```jinja
        {% elif mode == 'Seasonal' %}
          {% set month = now().month %}
          {% if month >= 5 and month <= 9 %}
            {% set base = states('input_number.garden_lawn_minutes_july') | int(18)
               if month == 7
               else states('input_number.garden_lawn_minutes_standard') | int(15) %}
            {% set z1 = base * 60 %}
            {% set side = (base * 0.6) | round(0) | int * 60 %}
            {% set z = [z1, side, side] %}
          {% else %}
            {% set z = [0, 0, 0] %}
          {% endif %}
```

(Place it as another `{% elif %}` in the existing if/elif chain that sets `z`. The existing trailing `{% else %} {% set z = [0,0,0] %}` and the final dict output stay.)

- [ ] **Step 3: `cycle_count` — make it mode-aware (Seasonal = 1)**

`cycle_count` is currently the literal `"2"`. Replace it with a template so Seasonal returns 1, all else 2:

```yaml
      cycle_count: >
        {{ 1 if is_state('input_select.garden_irrigation_mode', 'Seasonal') else 2 }}
```

(Auto-off and the lawn script divide per-zone duration by `cycle_count`. Seasonal durations above are the TOTAL single-pass water, so cycle_count must be 1 — a value of 2 would halve each zone.)

- [ ] **Step 4: `lawn_today` — Seasonal day map**

Add a Seasonal branch to `lawn_today`. Days: May/Sep = Mon/Thu `[1,4]`; Jun/Jul/Aug = Mon/Wed/Fri `[1,3,5]`; false outside 5–9. Insert before the final `{% else %} false`:

```jinja
        {% elif mode == 'Seasonal' %}
          {% set month = now().month %}
          {% if month in [5, 9] %} {{ dow in [1, 4] }}
          {% elif month in [6, 7, 8] %} {{ dow in [1, 3, 5] }}
          {% else %} false {% endif %}
```

(The block already computes `{% set dow = now().isoweekday() %}` — reuse it.)

- [ ] **Step 5: `drip_today` — Seasonal Mon/Thu**

Add a Seasonal branch to `drip_today` (drip 2×/week fixed Mon+Thu, in season only):

```jinja
        {% elif mode == 'Seasonal' %}
          {% set month = now().month %}
          {{ dow in [1, 4] if (month >= 5 and month <= 9) else false }}
```

- [ ] **Step 6: `drip_duration` + `drip_runs_per_day` — Seasonal**

In `drip_duration`, add Seasonal → 2700 in season else 0:
```jinja
        {% elif mode == 'Seasonal' %}
          {% set month = now().month %}
          {% if month >= 5 and month <= 9 %} 2700 {% else %} 0 {% endif %}
```
In `drip_runs_per_day`, add Seasonal → 1 in season else 0 (mirror the same month guard with `1`/`0`).

- [ ] **Step 7: Add `am_time` and `pm_time` attributes**

Add two new attributes to the profile (the automation reads them to know which session times apply this month):

```yaml
      am_time: >
        {% set month = now().month %}
        {% if not is_state('input_select.garden_irrigation_mode', 'Seasonal') %} ''
        {% elif month == 9 %} 06:00
        {% elif month >= 5 and month <= 8 %} 05:00
        {% else %} '' {% endif %}
      pm_time: >
        {% set month = now().month %}
        {% if is_state('input_select.garden_irrigation_mode', 'Seasonal')
              and month in [6, 7, 8] %} 17:00
        {% else %} '' {% endif %}
```

- [ ] **Step 8: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`
Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git commit -m "feat(garden): Seasonal profile branch (twice-daily table, drip Mon/Thu, 1 cycle)"
```

---

### Task 4: Rework lawn skip to rain-accumulation ≥3 mm + soil-ready

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`

Read the file first. It has a `weather.get_forecasts` trigger action feeding `forecast_response`, then three binary_sensors. You replace the lawn 6h-forecast test with the 3 mm accumulation test, add a disabled-ready soil test, and update reasons. The trigger block + drip sensor stay; the `weather.get_forecasts` action can stay (harmless) or be removed since the rest sensor now provides forecast — **keep it** to avoid touching the drip sensor logic.

- [ ] **Step 1: Rewrite `Garden Lawn Should Skip` state**

Replace the `state:` of `garden_lawn_should_skip` with (season + raining-now + accumulation≥3 + soil>65 disabled-ready):

```yaml
    state: >
      {% set is_raining = is_state('binary_sensor.raining', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set rain_mm = states('sensor.garden_rain_accumulation_mm') | float(0) %}
      {% set soil = states('sensor.garden_soil_moisture') %}
      {% set soil_wet = soil not in ['unknown', 'unavailable', 'none', '']
         and (soil | float(-1)) > 65 %}
      {{ not in_season or is_raining or rain_mm >= 3 or soil_wet }}
```

(`float(0)` on the rest sensor = fail-open: if it is `unavailable`, `rain_mm` is 0, so it does not force a skip. Soil is disabled-ready: absent → `soil_wet` false.)

- [ ] **Step 2: Rewrite `Garden Lawn Should Skip` reason attribute**

Replace its `reason:` with priority-ordered reasons:

```yaml
      reason: >
        {% set month = now().month %}
        {% set in_season = month >= 5 and month <= 9 %}
        {% set rain_mm = states('sensor.garden_rain_accumulation_mm') | float(0) %}
        {% set soil = states('sensor.garden_soil_moisture') %}
        {% set soil_wet = soil not in ['unknown', 'unavailable', 'none', '']
           and (soil | float(-1)) > 65 %}
        {% if not in_season %} out_of_season
        {% elif is_state('binary_sensor.raining', 'on') %} raining_now
        {% elif rain_mm >= 3 %} rain_accumulation_3mm
        {% elif soil_wet %} soil_wet
        {% else %} none {% endif %}
```

- [ ] **Step 3: Mirror into the legacy alias `Garden Should Skip Irrigation`**

The legacy `garden_should_skip_irrigation` sensor mirrors lawn skip. Apply the EXACT same `state:` and `reason:` from Steps 1–2 to it (it currently duplicates the old lawn logic). This keeps dashboards/back-compat pointing at the new lawn rule.

- [ ] **Step 4: Leave `Garden Drip Should Skip` unchanged**

Confirm by reading that `garden_drip_should_skip` still uses only raining-now + season 5–10. Do NOT add the 3 mm rule to drip. No edit.

- [ ] **Step 5: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): lawn skip on rain accumulation >=3mm (fail-open) + soil-ready"
```

---

### Task 5: Create the Seasonal dual-session automation

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml`

- [ ] **Step 1: Write the automation**

```yaml
---
alias: Garden Seasonal Irrigation
description: >
  Twice-daily Seasonal-mode runs. Triggers at 05:00 / 06:00 / 17:00; each is a
  no-op unless it matches the current month's am_time/pm_time from the profile.
  Guards: mode is Seasonal, night-guard 22:00–04:30, no lawn valve already open.
  Resolves lawn/drip today + skip exactly like garden_scheduled_irrigation, and
  notifies (persistent + mobile) only on skip/abort. PM session is lawn-only;
  drip runs only on its AM day (profile drip_today = Mon/Thu).
id: garden-seasonal-irrigation

mode: single

trigger:
  - platform: time
    at: "05:00:00"
  - platform: time
    at: "06:00:00"
  - platform: time
    at: "17:00:00"

condition:
  - condition: state
    entity_id: input_select.garden_irrigation_mode
    state: "Seasonal"
  # Night guard 22:00–04:30 (scheduled times are outside it; defensive).
  - condition: template
    value_template: >
      {% set t = now().strftime('%H:%M') %}
      {{ not (t >= '22:00' or t < '04:30') }}

action:
  - variables:
      fired: "{{ now().strftime('%H:%M') }}"
      am_time: >
        {{ state_attr('sensor.garden_irrigation_profile', 'am_time')
           | string | trim }}
      pm_time: >
        {{ state_attr('sensor.garden_irrigation_profile', 'pm_time')
           | string | trim }}
  - variables:
      is_am: "{{ fired == am_time }}"
      is_pm: "{{ pm_time != '' and fired == pm_time }}"
  # No-op if this trigger time is not a valid session for the current month.
  - if:
      - "{{ not (is_am or is_pm) }}"
    then:
      - stop: "Not a valid Seasonal session time this month"
  # Abort + notify if any lawn valve is already open.
  - if:
      - >
        {{ expand('valve.lawn_sprinkler_zone_1',
                  'valve.lawn_sprinkler_zone_2',
                  'valve.lawn_sprinkler_zone_3')
           | selectattr('state', 'eq', 'open') | list | count > 0 }}
    then:
      - action: persistent_notification.create
        data:
          notification_id: garden_seasonal_already_running
          title: Seasonal irrigation aborted
          message: >
            A lawn valve was already open at {{ fired }} — Seasonal session
            aborted to avoid overlap.
      - action: notify.mobile_app_iglofon
        data:
          title: Seasonal irrigation aborted
          message: "A lawn valve was already open at {{ fired }} — session aborted."
      - stop: "Lawn valve already open"
  - variables:
      lawn_today: >
        {{ state_attr('sensor.garden_irrigation_profile', 'lawn_today')
           | string | trim | lower == 'true' }}
      drip_today: >
        {{ state_attr('sensor.garden_irrigation_profile', 'drip_today')
           | string | trim | lower == 'true' }}
      lawn_skip: "{{ is_state('binary_sensor.garden_lawn_should_skip', 'on') }}"
      drip_skip: "{{ is_state('binary_sensor.garden_drip_should_skip', 'on') }}"
      # PM session is lawn-only; drip only on the AM run of its day.
      run_lawn: "{{ lawn_today and not lawn_skip }}"
      run_drip: "{{ is_am and drip_today and not drip_skip }}"
  # Skip notify: a run day but skipped.
  - if:
      - "{{ lawn_today and not run_lawn }}"
    then:
      - action: persistent_notification.create
        data:
          notification_id: garden_seasonal_skipped
          title: Seasonal lawn skipped
          message: >
            Lawn skipped at {{ fired }} — reason:
            {{ state_attr('binary_sensor.garden_lawn_should_skip', 'reason')
               | string | trim }}.
      - action: notify.mobile_app_iglofon
        data:
          title: Seasonal lawn skipped
          message: >
            Lawn skipped — {{ state_attr('binary_sensor.garden_lawn_should_skip',
            'reason') | string | trim }}.
  - choose:
      - conditions:
          - "{{ run_lawn and run_drip }}"
        sequence:
          - action: script.garden_full_irrigation
      - conditions:
          - "{{ run_lawn }}"
        sequence:
          - action: script.garden_lawn_irrigation
      - conditions:
          - "{{ run_drip }}"
        sequence:
          - action: script.garden_drip_irrigation
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml
git commit -m "feat(garden): Seasonal dual-session automation with guards + skip notify"
```

---

### Task 6: Exclude Seasonal from the 04:00 automation

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`

- [ ] **Step 1: Add `Seasonal` to the mode exclusion**

The 04:00 automation has a `condition: not` excluding `Manual`. Add a second excluded state so Seasonal is handled solely by the new automation. Replace the condition block:

```yaml
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.garden_irrigation_mode
        state: "Manual"
      - condition: state
        entity_id: input_select.garden_irrigation_mode
        state: "Seasonal"
```

(`not` over multiple `state` conditions = NOR: passes only when mode is neither Manual nor Seasonal.)

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml
git commit -m "feat(garden): 04:00 automation skips Seasonal mode (no double-fire)"
```

---

### Task 7: Add guards to the manual on-demand path

**Files:**
- Modify: `packages/areas/outdoor/garden/scripts/garden_ondemand_lawn.yaml`

Read the file first. It currently: resolves `minutes`, offline-aborts if any zone unavailable, zero-guards, sets the flag, then repeats open/delay/close over the 3 zones, then clears the flag. Add a **night-guard** and a **lawn-skip** check BEFORE setting the flag. (Already-on / unavailable abort is already covered by the existing offline check + `mode: single`; add an explicit already-open abort too for parity with the scheduled path.)

- [ ] **Step 1: Insert guards after the zero-guard, before `input_boolean.turn_on`**

Find the existing zero-guard:
```yaml
    - if:
        - "{{ minutes < 1 }}"
      then:
        - stop: "On-demand run skipped — duration is zero"
```
Insert immediately AFTER it (and before the `- action: input_boolean.turn_on`):

```yaml
    # Night guard 22:00–04:30 — block manual runs overnight.
    - if:
        - >
          {% set t = now().strftime('%H:%M') %}
          {{ t >= '22:00' or t < '04:30' }}
      then:
        - action: persistent_notification.create
          data:
            notification_id: garden_ondemand_night_guard
            title: On-demand run blocked
            message: "Manual lawn run blocked by the 22:00–04:30 night guard."
        - stop: "Night guard active"
    # Already-open abort — avoid overlapping a run in progress.
    - if:
        - >
          {{ expand('valve.lawn_sprinkler_zone_1',
                    'valve.lawn_sprinkler_zone_2',
                    'valve.lawn_sprinkler_zone_3')
             | selectattr('state', 'eq', 'open') | list | count > 0 }}
      then:
        - action: persistent_notification.create
          data:
            notification_id: garden_ondemand_already_open
            title: On-demand run aborted
            message: "A lawn valve is already open — manual run aborted."
        - stop: "Lawn valve already open"
    # Respect lawn skip (rain accumulation / raining / soil / out of season).
    - if:
        - "{{ is_state('binary_sensor.garden_lawn_should_skip', 'on') }}"
      then:
        - action: persistent_notification.create
          data:
            notification_id: garden_ondemand_skipped
            title: On-demand lawn skipped
            message: >
              Manual lawn run skipped — reason:
              {{ state_attr('binary_sensor.garden_lawn_should_skip', 'reason')
                 | string | trim }}.
        - stop: "Lawn skip active"
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/scripts/garden_ondemand_lawn.yaml`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/scripts/garden_ondemand_lawn.yaml
git commit -m "feat(garden): manual lawn run respects night guard + already-open + skip"
```

---

### Task 8: Push + reload + backend verification

No new files. Verify everything on the live instance.

- [ ] **Step 1: Push**

```bash
git push
```
Expected: branch pushed (HA auto-pulls).

- [ ] **Step 2: Reload all relevant domains**

```bash
for svc in homeassistant/reload_core_config template/reload automation/reload script/reload input_number/reload input_select/reload; do
  curl -s -o /dev/null -w "$svc -> %{http_code}\n" -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/$svc"
done
```
Expected: all 200. (The `rest:` sensor is created on `homeassistant.reload_core_config` / restart; if it does not appear after core reload, `homeassistant.restart` — `rest:` platform sensors sometimes need a full restart to register.)
Use `dangerouslyDisableSandbox: true` (sandbox blocks `homeassistant.local`).

- [ ] **Step 3: Check logs**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | grep -iE "garden_seasonal|garden_rain|irrigation_profile|should_skip|ondemand_lawn|rest" | tail -30
```
Expected: no new errors. (HA pull lag: if changes not live, the git-pull addon is off/wrong-branch — fix it, don't wait. See prior session: confirm with a force/template render.)

- [ ] **Step 4: Verify the rain sensor populated**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_rain_accumulation_mm" | python3 -c "import sys,json;d=json.load(sys.stdin);print('state:',d['state'],d['attributes'].get('unit_of_measurement'))"
```
Expected: a numeric mm value (e.g. `state: 0.0 mm` or higher), NOT `unavailable`. If `unavailable`, check the secret URL + that `rest:` registered (restart).

- [ ] **Step 5: Verify the Seasonal profile resolves**

Set mode to Seasonal, render the profile attributes:
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Seasonal"}' \
  "$HA_URL/api/services/input_select/select_option" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"durations={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations\") }} cycles={{ state_attr(\"sensor.garden_irrigation_profile\",\"cycle_count\") }} am={{ state_attr(\"sensor.garden_irrigation_profile\",\"am_time\") }} pm={{ state_attr(\"sensor.garden_irrigation_profile\",\"pm_time\") }} drip_today={{ state_attr(\"sensor.garden_irrigation_profile\",\"drip_today\") }}"}' "$HA_URL/api/template"
```
Expected (June, month 6): durations z1=900 (15min), z2/z3=540 (9min); `cycles=1`; `am=05:00`; `pm=17:00`; `drip_today` true only Mon/Thu. (Adjust expectations to the actual current month — June 2026.)

- [ ] **Step 6: Verify the 3 mm skip rule + fail-open**

Render the lawn skip with the live rain sensor; then test fail-open by checking behavior reasoning:
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"skip={{ states(\"binary_sensor.garden_lawn_should_skip\") }} reason={{ state_attr(\"binary_sensor.garden_lawn_should_skip\",\"reason\") }} mm={{ states(\"sensor.garden_rain_accumulation_mm\") }}"}' "$HA_URL/api/template"
```
Expected: `reason` matches the mm value (≥3 → `rain_accumulation_3mm`; else `none`/`raining_now`/`out_of_season`). Confirm that with `mm` unavailable the float(0) keeps skip from tripping on rain (manually reason about it if you can't force unavailable).

- [ ] **Step 7: Functional automation test**

Temporarily set both duration helpers to a small value won't help (still minutes). Instead: confirm the guard logic without a long run — set mode Seasonal, and at a NON-session time manually trigger the automation; confirm it stops with "Not a valid Seasonal session time" (check trace/logbook). Then (optional, if you can wait) set a duration helper to its min and trigger near a real session time to watch one sequential pass.

Alternatively trigger via:
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"entity_id":"automation.garden_seasonal_irrigation"}' "$HA_URL/api/services/automation/trigger"
```
(Default `automation.trigger` skips conditions — to test the time/guard logic, pass `{"skip_condition": false}` in data.) Confirm via logbook/trace it took the expected branch.

- [ ] **Step 8: Regression — other modes unaffected**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Smart"}' "$HA_URL/api/services/input_select/select_option" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"smart_cycles={{ state_attr(\"sensor.garden_irrigation_profile\",\"cycle_count\") }} smart_dur={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations\") }}"}' "$HA_URL/api/template"
```
Expected: Smart still resolves `cycles=2` and its month-tier durations (unchanged). Then set mode back to whatever it was originally (note it at Step 5; likely Standard/Smart).

- [ ] **Step 9: Checkpoint**

If the rain sensor is live, the Seasonal profile resolves correctly, the skip rule reasons right, and Smart is unchanged → done. Any failure → fix the relevant task before proceeding.

---

### Task 9: Documentation

**Files:**
- Modify: `packages/areas/outdoor/garden/README.md`

- [ ] **Step 1: Update the README**

Add to the relevant sections (do NOT regenerate from scratch — patch like a human, matching the existing curated style):
- **Modes table:** add a `Seasonal` row — twice-daily May–Sep, durations from helpers, drip Mon/Thu, single pass.
- **A "Seasonal mode" subsection** under How It Works: month/day/time table, z1-base + 0.6 weighting, single pass (cycle_count 1), 05:00/06:00 AM + 17:00 PM.
- **Skip logic:** lawn now skips on rain accumulation ≥3 mm (Open-Meteo last-24h + next-12h, fail-open) + raining-now + soil>65% (disabled-ready) + season; drip unchanged.
- **Entities:** add `input_number.garden_lawn_minutes_standard` / `_july`, `sensor.garden_rain_accumulation_mm`, note the `garden_rain_url` secret.
- **File Index:** add `automations/garden_seasonal_irrigation.yaml`; note the `rest:` block + helpers live in `config.yaml`; note manual path guards in `garden_ondemand_lawn.yaml`.

(Optionally run `/ha-area-docs` for the garden area, then re-add any custom narrative it drops.)

- [ ] **Step 2: Commit + push**

```bash
git add packages/areas/outdoor/garden/README.md
git commit -m "docs(garden): document Seasonal mode + rain-accumulation skip"
git push
```

- [ ] **Step 3: Update the knowledge leaf**

The `garden-irrigation-schedule` leaf notes schedule logic is duplicated across files. The Seasonal branch + the new automation + the rain sensor are additional spots. Invoke the `knowledge-author` skill to update that leaf (do NOT patch inline) with the new duplication surface and the fail-open rain-sensor gotcha.

---

## Self-Review notes

- **Spec coverage:** Seasonal mode + table (Tasks 2,3) ✓; durations from helpers + z1-base 0.6 weighting (Task 3) ✓; cycle_count 1 mode-aware (Task 3) ✓; rain accumulation sensor via secret (Tasks 1,2) ✓; ≥3 mm fail-open lawn skip (Task 4) ✓; drip permissive unchanged (Task 4) ✓; drip Mon/Thu 2×/wk (Task 3) ✓; dual-session automation + night guard + already-on + skip notify (Task 5) ✓; 04:00 exclusion (Task 6) ✓; manual path guards reuse ondemand_lawn (Task 7) ✓; soil disabled-ready (Task 4) ✓; skip-only notify, no start/end (Tasks 5,7) ✓; live verify + regression (Task 8) ✓; README + knowledge (Task 9) ✓.
- **Entity/attr consistency:** `sensor.garden_rain_accumulation_mm`, `input_number.garden_lawn_minutes_standard`/`_july`, profile attrs `am_time`/`pm_time`/`cycle_count`/`lawn_durations`/`lawn_today`/`drip_today`, `binary_sensor.garden_lawn_should_skip` (+`reason`), `notify.mobile_app_iglofon`, secret `garden_rain_url` — used identically across tasks.
- **Known risks flagged:** `rest:` must be in `config.yaml` (not the template dir) and may need a full restart to register; `cycle_count` MUST be 1 for Seasonal or water halves; `!secret` is whole-value only (full-URL secret). All called out in-task.
- **Out of scope honored:** no soil hardware, no extra-month twice-daily, no mode removal, no dashboard cards, no start/end notify, no second manual script.
