# Smart-Mode Heat-Aware Lawn Irrigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Garden Smart irrigation mode flex lawn cadence, morning duration, and an optional evening top-up off a forecast-derived heat tier — instead of a fixed Tue/Thu/Sat calendar schedule.

**Architecture:** A trigger-based helper sensor exposes today's forecast (high temp, UV, condition). The schedule brain (`garden_schedule_brain`) reads it and, only when mode is Smart, applies a heat overlay (Mild/Hot/Scorcher) that overrides cadence (day-of-year parity), morning duration, and evening PM session. The 04:00 morning automation gains a min-gap guard; a new 17:00 automation reuses the existing PM script for the evening top-up. All non-Smart modes and all drip logic are untouched.

**Tech Stack:** Home Assistant YAML packages, Jinja2 templates (template + trigger-based sensors), `weather.get_forecasts` service, `uv` for tooling. No Python test harness — verification is `/api/template` render assertions, `just check` (HA config check), and Playwright dashboard checks.

## Global Constraints

- **Branch:** `chore/june-features` (current). **Never push to `main`** — feature branch only.
- **Deploy loop:** HA auto-pulls the tracked branch. After **every** push: reload core config (`homeassistant.reload_core_config` via API/MCP) and check logs — errors stay invisible until reload. No pull lag — if a change isn't live after reload, the addon/branch is wrong, don't wait.
- **Sandbox:** `homeassistant.local` is blocked — every `curl` against HA needs `dangerouslyDisableSandbox: true`. Env vars `$HA_URL`, `$HA_TOKEN` are preloaded via direnv; never read `.env`.
- **Tooling:** `uv run …` for all Python/yamllint. Never `pip`. Run git from the working dir, never `git -C`.
- **Lint before commit:** pre-commit runs on commit (yamllint etc.). `uv run yamllint <file>` to pre-check.
- **YAML brain duplication:** `garden_schedule_brain` `today` and `schedule_7day` attributes have **no shared scope** — every macro must be copied **verbatim into both**. Keep both in sync in the same task.
- **Scope:** changes gate on `eff == 'Smart'`. Eco / Standard / Intensive / Seasonal / Testing must render byte-identical to before.
- **Fail-safe:** missing/bad forecast → Mild tier + no evening. Never escalate watering on bad data.
- **Heat cuts:** Mild `high < 26`, Hot `26 <= high < 31`, Scorcher `high >= 31`. Hot evening gate: `condition in [sunny, partlycloudy]` AND `uv >= 6`. Scorcher evening: always.
- **Cadence:** Mild `yday % 3 == 0`, Hot/Scorcher `yday % 2 == 0`. Min-gap: Mild 44h, Hot/Scorcher 20h.
- **Evening:** `pm_ratio = 0.4`, single pass, fires 17:00. Scorcher morning bump: z1 +5 min, capped at 35.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml` | Add daily `weather.get_forecasts` call + new `sensor.garden_forecast_today` | Modify |
| `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` | `heat_tier` macro + Smart overlay in `today` & `schedule_7day`; new profile attrs `heat_tier`, `min_gap_hours` | Modify |
| `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml` | Add min-gap guard to `run_lawn` | Modify |
| `packages/areas/outdoor/garden/automations/garden_smart_evening.yaml` | New 17:00 Smart evening top-up automation | Create |
| `packages/areas/outdoor/garden/README.md` | Regen via `/ha-area-docs` after logic lands | Modify (final task) |

Note: `sensor.garden_forecast_today` is added inside the **existing** skip-sensor file because that trigger already calls `weather.get_forecasts` — one polling block, two forecast types. Do NOT create a new standalone sensor file.

---

### Task 1: Forecast helper sensor (`sensor.garden_forecast_today`)

Add a daily-forecast service call + a template sensor exposing today's high/uv/condition. This is the new signal the brain reads.

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`

**Interfaces:**
- Consumes: `weather.get_forecasts` (type: daily) on `weather.forecast_home`. Daily forecast item fields confirmed live: `condition`, `temperature` (daily high), `templow`, `precipitation`, `uv_index`.
- Produces: `sensor.garden_forecast_today` with attributes `high` (float °C), `uv` (float), `condition` (str). State = `high` rounded. On missing data: `high=0`, `uv=0`, `condition='unknown'` → resolves to Mild tier downstream.

- [ ] **Step 1: Capture the BEFORE state (sensor must not yet exist)**

Run:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_forecast_today"
```
(use `dangerouslyDisableSandbox: true`)
Expected: `{"message":"Entity not found."}` — confirms we're adding something new.

- [ ] **Step 2: Add the daily forecast call + sensor**

The file's existing `trigger:` block already has a time_pattern `/30`, a homeassistant start, and state triggers, plus an `action:` that calls `weather.get_forecasts` (type: hourly) into `forecast_response`. Add a **second** action calling the daily forecast, and add the new sensor to the `binary_sensor:`-sibling `sensor:` list (the file currently has only `binary_sensor:` — add a `sensor:` top-level key).

Edit the `action:` list — after the existing hourly call, append:

```yaml
  - action: weather.get_forecasts
    target:
      entity_id: weather.forecast_home
    data:
      type: daily
    response_variable: daily_response
```

Then add a new top-level `sensor:` key (sibling of `binary_sensor:`, place it directly above `binary_sensor:`):

```yaml
sensor:
  - name: Garden Forecast Today
    unique_id: garden_forecast_today
    icon: mdi:weather-sunny-alert
    unit_of_measurement: "°C"
    # Today's daily forecast, surfaced as attributes for the schedule brain.
    # The brain is a plain template sensor and cannot call weather.get_forecasts,
    # so the call lives here (this file's trigger already fetches the hourly
    # forecast) and the brain reads these attributes. Fail-safe: missing data
    # yields high=0/uv=0 -> Mild tier + no evening downstream.
    state: >
      {% set f = (daily_response['weather.forecast_home'].forecast
         if daily_response is defined else []) %}
      {{ (f[0].temperature | float(0)) if f | count > 0 else 0 }}
    attributes:
      high: >
        {% set f = (daily_response['weather.forecast_home'].forecast
           if daily_response is defined else []) %}
        {{ (f[0].temperature | float(0)) if f | count > 0 else 0 }}
      uv: >
        {% set f = (daily_response['weather.forecast_home'].forecast
           if daily_response is defined else []) %}
        {{ (f[0].uv_index | float(0)) if f | count > 0 else 0 }}
      condition: >
        {% set f = (daily_response['weather.forecast_home'].forecast
           if daily_response is defined else []) %}
        {{ f[0].condition if f | count > 0 else 'unknown' }}
```

> Note: `daily_response` is only defined during a trigger run. On the homeassistant-start trigger it IS defined (start fires the action). Between triggers HA caches the last rendered attribute values — this is the same pattern the existing skip sensors rely on with `forecast_response`. No `is defined` failure at steady state because the value is cached from the last trigger render.

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no errors (or only pre-existing line-length warnings consistent with the file).

- [ ] **Step 4: Commit, push, reload**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): add garden_forecast_today helper for heat-aware Smart"
git push
```
Then reload core config:
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(`dangerouslyDisableSandbox: true`)

- [ ] **Step 5: Verify the sensor now exists and reads sane values**

Run:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_forecast_today" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("state",d["state"],"attrs",d["attributes"])'
```
Expected: `state` ≈ today's forecast high (e.g. ~29), attrs show `high`, `uv`, `condition` populated (not the 0/unknown fallback). If it shows the fallback, check HA logs for a forecast-call error before proceeding.

---

### Task 2: `heat_tier` macro + Smart cadence/duration overlay in the brain

Add the heat tier logic and wire it into `resolve_day` for the Smart branch only. Cadence + morning duration first; evening (PM) in Task 3 to keep tasks reviewable.

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` (both `today` and `schedule_7day` macros — verbatim copies)

**Interfaces:**
- Consumes: `sensor.garden_forecast_today` attrs `high`, `uv`, `condition` (Task 1).
- Produces: in the `today` result dict — new key `heat_tier` (str), new key `min_gap_hours` (int). `lawn_today` now reflects day-of-year parity in Smart mode. `durations`/`lawn_am_min` reflect Scorcher bump. Non-Smart modes unchanged.

- [ ] **Step 1: Capture BEFORE — Smart-mode today (regression baseline)**

Run (renders the brain's `today` for current Smart routing):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{{ state_attr(\"sensor.garden_schedule_brain\",\"today\") }}"}' \
  "$HA_URL/api/template"
```
(`dangerouslyDisableSandbox: true`)
Record output. Note current keys (`effective_mode`, `lawn_today`, `durations`, …) — there is **no** `heat_tier`/`min_gap_hours` yet. After this task those two keys must appear when mode=Smart.

Also capture a non-Smart baseline to prove no regression later:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{% macro r() %}<paste resolve_day call for Standard via a 1-day render is awkward; instead capture the live Standard render by temporarily reading effective_mode>{% endmacro %}{{ r() }}"}' \
  "$HA_URL/api/template"
```
Simpler regression check deferred to Task 5 (full matrix). For now just record the Smart `today` dict.

- [ ] **Step 2: Add `heat_tier` macro + Smart overlay (in `today`)**

In `garden_irrigation_profile.yaml`, inside the `today:` attribute template, add the `heat_tier` macro right after the `smart_target` macro definition:

```jinja
{%- macro heat_tier(high, uv) -%}
{%- if high >= 31 -%}Scorcher{%- elif high >= 26 -%}Hot{%- else -%}Mild{%- endif -%}
{%- endmacro -%}
```

Then, inside `resolve_day`, locate the Smart resolution. Currently:
```jinja
{%- if mode == 'Smart' -%}{%- set eff = smart_target(mo) | trim -%}{%- endif -%}
```
Leave that line (it still picks the base month tier: Standard/Intensive/Eco/DripOnly/Off). After the existing `{%- elif eff in tbl -%}{%- set row = tbl[eff] -%}{%- endif -%}` block builds `row`, add a Smart-only overlay that mutates `row` BEFORE the `row is none` check consumes it. Insert immediately after the `{%- endif -%}` that closes the `eff` resolution chain and BEFORE `{%- if row is none -%}`:

```jinja
{#- Smart heat overlay: only when the user picked Smart and we resolved a real row -#}
{%- if mode == 'Smart' and row is not none -%}
  {%- set high = states('sensor.garden_forecast_today') | float(0) -%}
  {%- set uv = state_attr('sensor.garden_forecast_today', 'uv') | float(0) -%}
  {%- set cond = state_attr('sensor.garden_forecast_today', 'condition') | string -%}
  {%- set tier = heat_tier(high, uv) | trim -%}
  {%- set yday = d.timetuple().tm_yday -%}
  {%- set parity = 3 if tier == 'Mild' else 2 -%}
  {%- set lawn_today_heat = (yday % parity == 0) -%}
  {%- set sunny = (cond in ['sunny', 'partlycloudy']) and (uv >= 6) -%}
  {%- set wants_pm = (tier == 'Scorcher') or (tier == 'Hot' and sunny) -%}
  {%- set z1_base = row['z1'] -%}
  {%- set z1_heat = ([z1_base + 5, 35] | min) if tier == 'Scorcher' else z1_base -%}
  {%- set mingap = 44 if tier == 'Mild' else 20 -%}
  {%- set row = dict(row,
       days='heat', heat_today=lawn_today_heat, z1=z1_heat,
       heat_tier=tier, min_gap_hours=mingap,
       pm=('17:00' if wants_pm else ''),
       pm_ratio=(0.4 if wants_pm else 0),
       drip_days=row['drip_days']) -%}
{%- endif -%}
```

Now the `row` builder below must honor `days == 'heat'`. Find:
```jinja
{%- set lawn_today = true if days == 'daily' else (dow in days) -%}
```
Replace with:
```jinja
{%- set lawn_today = true if days == 'daily' else (row['heat_today'] if days == 'heat' else (dow in days)) -%}
```

And the result dict — add the two new keys. Find the `result = { ... }` mapping and add inside it (next to `effective_mode`):
```jinja
'heat_tier': row.get('heat_tier', 'n/a'),
'min_gap_hours': row.get('min_gap_hours', 44),
```

> `dict(row, key=val, …)` returns a NEW dict with overrides — Jinja-safe, no mutation of the table literal (important: `tbl[eff]` is shared, must not be mutated in place). `row.get(...)` is used in the result so non-Smart rows (no `heat_tier` key) fall back cleanly.

- [ ] **Step 3: Mirror the SAME edits verbatim into `schedule_7day`**

Apply Step 2's three edits identically inside the `schedule_7day:` attribute's macro copy (it has its own `smart_target`, `resolve_day`, result dict). The `schedule_7day` loop renders future days `d`; the overlay reads `sensor.garden_forecast_today` which is *today's* forecast — that's the documented "today's tier persists across the 7-day projection" limitation. No change needed to handle that; it's intentional/advisory.

- [ ] **Step 4: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`
Expected: clean (pre-existing long-line style only).

- [ ] **Step 5: Commit, push, reload**

```bash
git add packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git commit -m "feat(garden): Smart heat overlay — tier-driven cadence + morning duration"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(reload with `dangerouslyDisableSandbox: true`)

- [ ] **Step 6: Verify tier + cadence render (synthetic via live forecast)**

With mode=Smart, render the brain `today` and assert the new keys exist and are consistent with the live forecast:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"tier={{ state_attr(\"sensor.garden_schedule_brain\",\"today\")[\"heat_tier\"] }} gap={{ state_attr(\"sensor.garden_schedule_brain\",\"today\")[\"min_gap_hours\"] }} lawn={{ state_attr(\"sensor.garden_schedule_brain\",\"today\")[\"lawn_today\"] }} z1={{ state_attr(\"sensor.garden_schedule_brain\",\"today\")[\"lawn_am_min\"] }} high={{ states(\"sensor.garden_forecast_today\") }}"}' \
  "$HA_URL/api/template"
```
(`dangerouslyDisableSandbox: true`)
Expected: `tier` ∈ {Mild,Hot,Scorcher} matching `high` (e.g. high≈29 → Hot), `gap` = 44 (Mild) or 20 (Hot/Scorcher), `lawn` = (today's yday % parity == 0). Manually confirm: `python3 -c "import datetime;print(datetime.date.today().timetuple().tm_yday)"` then `% 2` / `% 3`.

If mode is currently Standard not Smart, temporarily set it: `curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Smart"}' "$HA_URL/api/services/input_select/select_option"` (restore afterward).

---

### Task 3: Evening PM session in the profile (durations_pm + thin attrs)

Wire the PM session the overlay now requests (`pm='17:00'`, `pm_ratio=0.4`) through to `durations_pm`, and surface `heat_tier`/`min_gap_hours` as profile attributes.

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

**Interfaces:**
- Consumes: brain `today` keys `heat_tier`, `min_gap_hours`, `pm`, `pm_ratio`, `durations_pm` (Task 2 set pm/pm_ratio; durations_pm is computed by the EXISTING result-dict code which already multiplies by `pm_ratio` when `has_pm`).
- Produces: `sensor.garden_irrigation_profile` attributes `heat_tier`, `min_gap_hours`. `lawn_durations_pm`, `pm_time` (already exist) now non-zero in Smart when evening fires.

- [ ] **Step 1: Confirm durations_pm already flows from pm_ratio**

The existing result dict computes `durations_pm` as `am_s * pm_ratio` when `has_pm = (row['pm'] != '')`. Task 2 set `pm='17:00'`/`pm_ratio=0.4` for evening days, so `durations_pm` is ALREADY populated by existing code. Verify with a render (mode=Smart, on a day the overlay wants PM — force by checking a Scorcher: temporarily not possible without hot weather, so assert structurally):

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"pm_time={{ state_attr(\"sensor.garden_irrigation_profile\",\"pm_time\") }} pm_durs={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations_pm\") }}"}' \
  "$HA_URL/api/template"
```
Expected today (Hot, possibly not sunny / or cloudy): `pm_time` is `''` or `17:00` and `pm_durs` matches (`0`s if no PM). No code change needed if PM-day renders 17:00 + 40% durations. If `pm_time` is `17:00` but `pm_durs` are 0, the `has_pm` wiring is broken — fix the result dict's `durations_pm` branch.

- [ ] **Step 2: Add `heat_tier` + `min_gap_hours` profile attributes**

In the `Garden Irrigation Profile` sensor (Sensor B), add two thin cross-reads alongside the existing ones (e.g. after `pm_time:`):

```yaml
      heat_tier: >
        {%- set t = state_attr('sensor.garden_schedule_brain', 'today') or {} -%}
        {{ t.get('heat_tier', 'n/a') }}
      min_gap_hours: >
        {%- set t = state_attr('sensor.garden_schedule_brain', 'today') or {} -%}
        {{ t.get('min_gap_hours', 44) | int(44) }}
```

- [ ] **Step 3: Lint, commit, push, reload**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git add packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git commit -m "feat(garden): expose heat_tier + min_gap_hours on irrigation profile"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(reload `dangerouslyDisableSandbox: true`)

- [ ] **Step 4: Verify profile attrs**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/sensor.garden_irrigation_profile" \
  | python3 -c 'import sys,json;a=json.load(sys.stdin)["attributes"];print("heat_tier",a.get("heat_tier"),"min_gap",a.get("min_gap_hours"),"pm_time",a.get("pm_time"),"pm_durs",a.get("lawn_durations_pm"))'
```
Expected (mode=Smart): `heat_tier` matches today, `min_gap` = 44/20, `pm_time`/`pm_durs` consistent (both empty/zero OR `17:00`/40%).

---

### Task 4a: Min-gap guard on the morning automation

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`

**Interfaces:**
- Consumes: `sensor.garden_irrigation_profile` attr `min_gap_hours`; `sensor.garden_lawn_last_run` (timestamp).
- Produces: `run_lawn` now also requires `now - last_run >= min_gap_hours`.

- [ ] **Step 1: Add the guard variable + fold into `run_lawn`**

In the `action:` `variables:` block, alongside `lawn_today`, `lawn_skip`, add:

```yaml
      min_gap_h: >
        {{ state_attr('sensor.garden_irrigation_profile', 'min_gap_hours')
           | int(44) }}
      gap_ok: >
        {% set lr = states('sensor.garden_lawn_last_run') %}
        {% if lr in ['unknown','unavailable','none',''] %}
          {{ true }}
        {% else %}
          {{ (now() - as_datetime(lr)).total_seconds() / 3600
             >= (state_attr('sensor.garden_irrigation_profile','min_gap_hours') | int(44)) }}
        {% endif %}
```

Then change `run_lawn`:
```yaml
      run_lawn: "{{ lawn_today and not lawn_skip }}"
```
to:
```yaml
      run_lawn: "{{ lawn_today and not lawn_skip and gap_ok }}"
```

> Guard only applies here (Smart + every other mode's 04:00). For non-Smart modes `min_gap_hours` defaults to 44 via the profile fallback — but their fixed weekday schedules already space ≥ 2 days (Standard min gap is 2 days = 48h > 44h; Intensive Mon/Tue is 24h < 44h!). **Intensive Mon→Tue would be blocked.** To avoid regressing Intensive, gate the guard to Smart only:

Revise `gap_ok` to no-op unless Smart:
```yaml
      gap_ok: >
        {% if not is_state('input_select.garden_irrigation_mode','Smart') %}
          {{ true }}
        {% else %}
          {% set lr = states('sensor.garden_lawn_last_run') %}
          {% if lr in ['unknown','unavailable','none',''] %}
            {{ true }}
          {% else %}
            {{ (now() - as_datetime(lr)).total_seconds() / 3600
               >= (state_attr('sensor.garden_irrigation_profile','min_gap_hours') | int(44)) }}
          {% endif %}
        {% endif %}
```

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml`
Expected: clean.

- [ ] **Step 3: Verify guard logic renders (template the gap_ok expression)**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"mode={{ states(\"input_select.garden_irrigation_mode\") }} last={{ states(\"sensor.garden_lawn_last_run\") }} gap_h={{ state_attr(\"sensor.garden_irrigation_profile\",\"min_gap_hours\") }} hrs_since={% set lr=states(\"sensor.garden_lawn_last_run\") %}{{ ((now()-as_datetime(lr)).total_seconds()/3600) | round(1) if lr not in [\"unknown\",\"unavailable\",\"none\",\"\"] else \"n/a\" }}"}' \
  "$HA_URL/api/template"
```
(`dangerouslyDisableSandbox: true`)
Expected: prints mode, last-run, gap threshold, hours-since. Manually confirm hrs_since ≥ gap_h ⟺ guard passes.

- [ ] **Step 4: Commit, push, reload**

```bash
git add packages/areas/outdoor/garden/automations/garden_scheduled_irrigation.yaml
git commit -m "feat(garden): Smart min-gap guard on morning lawn run"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(reload `dangerouslyDisableSandbox: true`)

---

### Task 4b: Evening top-up automation (`garden_smart_evening.yaml`)

New 17:00 automation for Smart mode that reuses the existing PM script. Mirrors `garden_seasonal_irrigation`'s PM guards.

**Files:**
- Create: `packages/areas/outdoor/garden/automations/garden_smart_evening.yaml`

**Interfaces:**
- Consumes: `sensor.garden_irrigation_profile` attr `pm_time` (='17:00' on evening days), `sensor.garden_lawn_last_run`, `binary_sensor.garden_lawn_should_skip`, valve states.
- Produces: calls `script.garden_lawn_irrigation_pm` (existing). No new entity.

- [ ] **Step 1: Capture BEFORE — automation must not exist**

Run:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/automation.garden_smart_evening"
```
Expected: `Entity not found.`

- [ ] **Step 2: Create the automation**

```yaml
---
alias: Garden Smart Evening Top-up
description: >
  Smart-mode evening lawn top-up at 17:00. Fires only when the schedule brain
  flagged an evening session today (heat tier Scorcher, or Hot + sunny), the
  morning lawn actually ran today, it isn't raining, and no lawn valve is
  already open. Reuses script.garden_lawn_irrigation_pm (single-pass 40% top-up).
id: garden-smart-evening

mode: single

trigger:
  - platform: time
    at: "17:00:00"

condition:
  - condition: state
    entity_id: input_select.garden_irrigation_mode
    state: "Smart"
  # Brain decided an evening session runs today.
  - condition: template
    value_template: >
      {{ state_attr('sensor.garden_irrigation_profile', 'pm_time')
         | string | trim == '17:00' }}
  # Morning lawn actually ran today (after 03:00 today).
  - condition: template
    value_template: >
      {% set lr = states('sensor.garden_lawn_last_run') %}
      {% if lr in ['unknown','unavailable','none',''] %}
        false
      {% else %}
        {% set t = as_datetime(lr) | as_local %}
        {{ t.date() == now().date() and t.hour >= 3 }}
      {% endif %}
  # Rain veto (reuse the lawn skip sensor — covers raining_now + accumulation).
  - condition: state
    entity_id: binary_sensor.garden_lawn_should_skip
    state: "off"

action:
  # Abort if a lawn valve is already open (mirror Seasonal PM guard).
  - if:
      - >
        {{ expand('valve.lawn_sprinkler_zone_1',
                  'valve.lawn_sprinkler_zone_2',
                  'valve.lawn_sprinkler_zone_3')
           | selectattr('state', 'eq', 'open') | list | count > 0 }}
    then:
      - action: persistent_notification.create
        data:
          notification_id: garden_smart_evening_busy
          title: Smart evening top-up aborted
          message: >
            A lawn valve was already open at 17:00 — Smart evening top-up
            aborted to avoid overlap.
      - stop: "Lawn valve already open"
  - action: script.garden_lawn_irrigation_pm
```

- [ ] **Step 3: Lint + HA config check**

```bash
uv run yamllint packages/areas/outdoor/garden/automations/garden_smart_evening.yaml
just check
```
Expected: yamllint clean; `just check` (HA config check) passes / "Configuration valid".

- [ ] **Step 4: Commit, push, reload**

```bash
git add packages/areas/outdoor/garden/automations/garden_smart_evening.yaml
git commit -m "feat(garden): Smart evening lawn top-up automation (17:00)"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(reload `dangerouslyDisableSandbox: true`)

- [ ] **Step 5: Verify automation loaded + condition gate**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/automation.garden_smart_evening" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("state",d["state"])'
```
Expected: `state on` (automation enabled). Then dry-check the condition gate via template (would it fire right now?):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"smart={{ is_state(\"input_select.garden_irrigation_mode\",\"Smart\") }} pm={{ state_attr(\"sensor.garden_irrigation_profile\",\"pm_time\") }} skip={{ states(\"binary_sensor.garden_lawn_should_skip\") }}"}' \
  "$HA_URL/api/template"
```
Expected: prints the gate inputs; reason it would/wouldn't fire is clear.

---

### Task 5: Regression matrix + synthetic tier verification

Prove non-Smart modes are byte-identical and Smart tiers behave correctly across synthetic temps. No code change unless a check fails.

**Files:** none (verification only) — except fixes if a check fails.

- [ ] **Step 1: Non-Smart regression — render each mode's `today`**

For each mode in Eco, Standard, Intensive, Testing, Seasonal: set the mode, render `today`, confirm NO `heat_tier`/`min_gap_hours` change behavior (they appear only as fallback `'n/a'`/`44` and don't alter `lawn_today`/`durations`). Loop:
```bash
for M in Eco Standard Intensive Testing Seasonal; do
  curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
    -d "{\"entity_id\":\"input_select.garden_irrigation_mode\",\"option\":\"$M\"}" \
    "$HA_URL/api/services/input_select/select_option" >/dev/null
  sleep 1
  echo "== $M =="
  curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
    -d '{"template":"{{ state_attr(\"sensor.garden_schedule_brain\",\"today\") }}"}' \
    "$HA_URL/api/template"
  echo
done
```
(`dangerouslyDisableSandbox: true`)
Expected: each mode's `lawn_today`, `durations`, `am`, `drip_*` match the pre-change semantics (Standard z1=30 Tue/Thu/Sat etc.). `heat_tier='n/a'`, `min_gap_hours=44` present but inert. Compare against Task 2 Step 1 baseline.

- [ ] **Step 2: Smart synthetic tier check — verify the macro math directly**

Render `heat_tier` + parity + PM gate for synthetic highs by inlining the macro logic (independent of live weather), confirming the cut points and evening gate:
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{% macro tier(h) %}{% if h>=31 %}Scorcher{% elif h>=26 %}Hot{% else %}Mild{% endif %}{% endmacro %}{% for h in [20,26,30,31,35] %}{% set t=tier(h)|trim %}{% set sunny=true %}{% set wants_pm=(t==\"Scorcher\") or (t==\"Hot\" and sunny) %}{% set parity=3 if t==\"Mild\" else 2 %}{% set gap=44 if t==\"Mild\" else 20 %}h={{h}}->{{t}} parity={{parity}} gap={{gap}} pm={{wants_pm}}; {% endfor %}"}' \
  "$HA_URL/api/template"
```
Expected exactly:
`h=20->Mild parity=3 gap=44 pm=False; h=26->Hot parity=2 gap=20 pm=True; h=30->Hot parity=2 gap=20 pm=True; h=31->Scorcher parity=2 gap=20 pm=True; h=35->Scorcher parity=2 gap=20 pm=True;`
(pm for Hot depends on sunny — here sunny=true so True; with sunny=false Hot pm must be False — verify by flipping sunny to false: Hot→False, Scorcher→True.)

- [ ] **Step 3: Hot-not-sunny evening suppression check**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{% for cond in [\"sunny\",\"cloudy\",\"partlycloudy\"] %}{% for uv in [4,6] %}{% set sunny=(cond in [\"sunny\",\"partlycloudy\"]) and (uv>=6) %}{% set wants_pm=(\"Hot\"==\"Hot\" and sunny) %}{{cond}}/uv{{uv}}->pm={{wants_pm}}; {% endfor %}{% endfor %}"}' \
  "$HA_URL/api/template"
```
Expected: `sunny/uv4->pm=False; sunny/uv6->pm=True; cloudy/uv4->pm=False; cloudy/uv6->pm=False; partlycloudy/uv4->pm=False; partlycloudy/uv6->pm=True;`

- [ ] **Step 4: Restore mode to Smart**

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"input_select.garden_irrigation_mode","option":"Smart"}' \
  "$HA_URL/api/services/input_select/select_option"
```
(`dangerouslyDisableSandbox: true`)
Expected: mode back to Smart (this is the intended live mode).

- [ ] **Step 5: Commit any fixes**

If Steps 1–3 surfaced a discrepancy, fix the brain/profile/automation, re-lint, re-push, reload, re-run. Commit with `fix(garden): …`. If all passed, no commit.

---

### Task 6: Dashboard chip + README regen

Surface `heat_tier` on the Outdoor view and regenerate area docs.

**Files:**
- Modify: dashboard view showing garden irrigation (find under `dashboards/tablet/` — the Outdoor view; recent commits reference an "outdoor view redesign").
- Modify: `packages/areas/outdoor/garden/README.md` (via `/ha-area-docs`).

- [ ] **Step 1: Locate the Outdoor irrigation card**

Run:
```bash
grep -rln "garden_irrigation_profile\|garden_lawn_next_run\|heat_tier\|effective_mode" dashboards/
```
Expected: the Outdoor view file(s). Open and find where mode/next-run chips render.

- [ ] **Step 2: Add a heat_tier chip**

Add a chip/entity reading `state_attr('sensor.garden_irrigation_profile','heat_tier')` next to the existing mode chip (match the surrounding Mushroom chip style — copy an adjacent chip's structure). Show only when mode is Smart (template condition `is_state('input_select.garden_irrigation_mode','Smart')`), per the Mushroom-visibility gotcha: prefer one always-present chip whose content switches, not a mutually-exclusive pair.

- [ ] **Step 3: Lint, commit, push, reload**

```bash
uv run yamllint dashboards/
git add dashboards/
git commit -m "feat(outdoor): show Smart heat tier chip on garden irrigation"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config"
```
(reload `dangerouslyDisableSandbox: true`)

- [ ] **Step 4: Playwright visual check (required for dashboard edits)**

Navigate to `http://homeassistant.local:8123/wall-tablet/home` (or the Outdoor view path), screenshot into `.playwright-mcp/`, confirm the heat-tier chip renders correctly and the section layout isn't broken. (Per repo rule: dashboard edits MUST end with a Playwright visual check.)

- [ ] **Step 5: Regenerate README**

Invoke `/ha-area-docs` for the garden area. Commit:
```bash
git add packages/areas/outdoor/garden/README.md
git commit -m "docs(garden): regen README for heat-aware Smart irrigation"
git push
```

---

## Self-Review

**1. Spec coverage:**
- Forecast helper (high/uv/condition) → Task 1. ✓
- 3 tiers + cuts 26/31 → Task 2 `heat_tier`, verified Task 5. ✓
- Cadence parity (Mild %3, Hot/Scorcher %2) → Task 2. ✓
- Morning Scorcher bump → Task 2 (z1+5 cap 35). ✓
- Evening 40% single-pass 17:00 → Task 2 (pm/pm_ratio) + Task 3 (durations_pm) + Task 4b (automation reusing PM script). ✓
- Sunny gate (cond + uv≥6, Hot only; Scorcher always) → Task 2, verified Task 5 Step 3. ✓
- Min-gap guard (44/20h, Smart-only) → Task 4a. ✓
- Smart-only / lawn-only / drip untouched → overlay gated `mode=='Smart'`; no drip edits; regression Task 5 Step 1. ✓
- Fail-safe bad forecast → Mild → Task 1 (0/0/unknown defaults) + Task 2 (high=0→Mild). ✓
- next_run/schedule_7day advisory (today's tier persists) → Task 2 Step 3, documented. ✓
- Dashboard chip + README → Task 6. ✓
- Deploy/reload/Playwright rules → in Global Constraints + per-task. ✓

**2. Placeholder scan:** No TBD/TODO. Task 6 Step 1 uses `grep` to locate the dashboard file rather than hardcoding (file not yet confirmed) — acceptable: it's a discovery step with an exact command, not a vague instruction. Task 2 Step 1's awkward non-Smart baseline note defers the real regression to Task 5 (which has concrete commands) — acceptable.

**3. Type consistency:** Brain `today` keys: `heat_tier` (str), `min_gap_hours` (int) — same names in Task 2 (produce), Task 3 (profile cross-read), Task 4a (guard read via profile attr `min_gap_hours`), Task 4b (`pm_time`). Profile attrs `heat_tier`/`min_gap_hours` consistent. Script `script.garden_lawn_irrigation_pm` name verified against repo. `row` override key `heat_today` + `days='heat'` consistent between the overlay and the `lawn_today` builder. ✓

Known limitation accepted: `schedule_7day` projects today's tier across 7 days (advisory chips), re-decided at fire time — documented in spec + Task 2 Step 3.
