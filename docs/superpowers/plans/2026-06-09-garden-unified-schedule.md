# Garden Unified Irrigation Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the per-mode irrigation schedule logic (today duplicated across the profile, next-run sensor, dashboard table, and README) into one `resolve_day` macro that every consumer reads, behavior-preserving for existing modes, and add the asymmetric AM/PM Seasonal top-up as native data.

**Architecture:** A single Jinja macro `resolve_day(mode, date)` (holding the `SCHEDULE` dict + Smart resolver + zone-weighting formula) returns a day's full resolved schedule. Every `sensor.garden_irrigation_profile` attribute is a thin one-call reader of that macro (no cross-attribute reads). A new `schedule_7day` attribute is the shared contract that `garden_next_run` and the dashboard 7-day table render instead of re-deriving. Smart stays a dynamic resolver with a no-op `dynamic_adjust` placeholder for future soil/forecast logic.

**Tech Stack:** Home Assistant template sensors (Jinja2), `just lint` / `uv run yamllint`, `/api/template` for live behavior verification, Playwright for the dashboard table.

**Spec:** `docs/superpowers/specs/2026-06-09-garden-unified-schedule-design.md`

> **Verification model:** HA config, no unit runner. The macro IS independently testable: render it via `POST /api/template` against the live instance and diff against the captured before-snapshot. "Test" = `uv run yamllint` + `/api/template` behavior diff + Playwright table check. Deploy loop: commit on `chore/may-fixes` → push → reload (`template.reload`) → verify. **Never push to main.** Sandbox blocks `homeassistant.local` → curl needs `dangerouslyDisableSandbox: true`.

> **Before-snapshot (live 2026-06-09, June, the regression baseline).** Render after each profile change and diff:
> ```
> Eco       lawn 1800/1080/1080  cyc2   lawn_today(Tue=2)=True   drip_today=True
> Standard  lawn 1800/1080/1080  cyc2   lawn_today=True          drip_today=True
> Intensive lawn 2100/1200/1200  cyc2 → BECOMES 2100/1260/1260 (0.6 formula, expected)
> Testing   lawn   30/30/30      cyc1   (flat, weighted:false)   lawn_today=True
> Smart     = Standard params (June)    lawn 1800/1080/1080 cyc2
> Seasonal  lawn  900/540/540    cyc1   lawn_today(Jun,Tue)=False  drip_today=False
> ```
> Every value EXCEPT Intensive z2/z3 must be byte-identical after the refactor.

---

## File Structure

- **Modify** `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml` — add `resolve_day` macro (dict + Smart resolver + formula); rewrite every attribute as a thin caller; add `today` + `schedule_7day` + `lawn_durations_pm`.
- **Modify** `packages/areas/outdoor/garden/templates/garden_next_run.yaml` — scan `schedule_7day` instead of per-mode day maps.
- **Modify** `dashboards/tablet/outdoor.yaml` — render `schedule_7day`; delete the per-mode macros.
- **Create** `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation_pm.yaml` — single-pass PM top-up using `lawn_durations_pm`.
- **Modify** `packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml` — PM dispatches the PM script.
- **Modify** `packages/areas/outdoor/garden/README.md` + `knowledge/areas/garden-irrigation-schedule.md` — one-source model.

Each task ends with a behavior diff so a regression is caught at the task that caused it.

---

### Task 1: Add `resolve_day` macro + `today` attribute (parallel to existing attrs)

Build the macro and expose it as a NEW `today` attribute WITHOUT touching the existing attributes yet. This lets us verify the macro resolves correctly against the live snapshot before rewiring anything — if `today` disagrees with the live scalar attrs, the macro is wrong and nothing is broken yet.

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

- [ ] **Step 1: Add the macro + `today` attribute**

Read the file first. At the top of the `Garden Irrigation Profile` sensor's `attributes:` (before the existing ones), the macro can't be a top-level `{% macro %}` in a template-sensor attribute list — so define it INLINE inside the `today` attribute, and (Task 2) copy the same macro text into each attribute that calls it. To keep ONE definition, the macro lives in a Jinja string we repeat verbatim; the plan provides the canonical text below — every task that needs it pastes THIS EXACT block.

Canonical macro (call it CANON — reused verbatim in Tasks 1–3):

```jinja
{%- macro sched() -%}
{{
  {
    'Eco':       {'days':[2,6],     'am':'04:00','pm':'','z1':30, 'cycles':2,'soak':15,'drip_days':[2,6],    'drip':45, 'pm_ratio':0,  'weighted':true},
    'Standard':  {'days':[2,4,6],   'am':'04:00','pm':'','z1':30, 'cycles':2,'soak':15,'drip_days':[2,4,6],  'drip':45, 'pm_ratio':0,  'weighted':true},
    'Intensive': {'days':[1,2,4,5], 'am':'04:00','pm':'','z1':35, 'cycles':2,'soak':15,'drip_days':[1,2,4,5],'drip':45, 'pm_ratio':0,  'weighted':true},
    'Testing':   {'days':'daily',   'am':'04:00','pm':'','z1':0.5,'cycles':1,'soak':0, 'drip_days':'daily',  'drip':0.5,'pm_ratio':0,  'weighted':false}
  }
}}
{%- endmacro -%}
{%- macro smart_target(mo) -%}
{%- if mo in [5,6] -%}Standard{%- elif mo in [7,8] -%}Intensive{%- elif mo == 9 -%}Eco{%- elif mo == 10 -%}DripOnly{%- else -%}Off{%- endif -%}
{%- endmacro -%}
{%- macro resolve_day(mode, d) -%}
{%- set tbl = sched() | from_json if sched() is string else sched() -%}
{%- set dow = d.isoweekday() -%}
{%- set mo = d.month -%}
{%- set eff = mode -%}
{%- if mode == 'Smart' -%}{%- set eff = smart_target(mo) | trim -%}{%- endif -%}
{#- Seasonal: month-driven, durations from helpers -#}
{%- if eff == 'Seasonal' -%}
  {%- if mo >= 5 and mo <= 9 -%}
    {%- set z1 = states('input_number.garden_lawn_minutes_july') | int(18) if mo == 7 else states('input_number.garden_lawn_minutes_standard') | int(15) -%}
    {%- set days = [1,4] if mo in [5,9] else [1,3,5] -%}
    {%- set am = '06:00' if mo == 9 else '05:00' -%}
    {%- set pm = '17:00' if mo in [6,7,8] else '' -%}
    {%- set row = {'days':days,'am':am,'pm':pm,'z1':z1,'cycles':1,'soak':0,'drip_days':[1,4],'drip':45,'pm_ratio':0.6,'weighted':true} -%}
  {%- else -%}
    {%- set row = none -%}
  {%- endif -%}
{%- elif eff == 'DripOnly' -%}
  {%- set yday = d.timetuple().tm_yday -%}
  {%- set row = {'days':[],'am':'04:00','pm':'','z1':0,'cycles':1,'soak':0,'drip_days':([dow] if yday % 3 == 0 else []),'drip':45,'pm_ratio':0,'weighted':true} -%}
{%- elif eff in tbl -%}
  {%- set row = tbl[eff] -%}
{%- else -%}
  {%- set row = none -%}
{%- endif -%}
{%- if row is none -%}
  {{ {'effective_mode':eff,'lawn_today':false,'drip_today':false,'lawn_am_min':0,'lawn_pm_min':0,'cycles':1,'soak':0,'am':'','pm':'','drip_min':0,'sessions':0,'durations':{'valve.lawn_sprinkler_zone_1':0,'valve.lawn_sprinkler_zone_2':0,'valve.lawn_sprinkler_zone_3':0},'durations_pm':{'valve.lawn_sprinkler_zone_1':0,'valve.lawn_sprinkler_zone_2':0,'valve.lawn_sprinkler_zone_3':0}} }}
{%- else -%}
  {%- set days = row['days'] -%}
  {%- set lawn_today = true if days == 'daily' else (dow in days) -%}
  {%- set drip_today = true if row['drip_days'] == 'daily' else (dow in row['drip_days']) -%}
  {%- set z1 = row['z1'] -%}
  {%- set side = z1 if not row['weighted'] else ((z1 * 0.6) | round(0) | int) -%}
  {%- set am_s = (z1 * 60) | int -%}
  {%- set side_s = (side * 60) | int -%}
  {%- set pm_ratio = row['pm_ratio'] -%}
  {%- set has_pm = (row['pm'] != '') -%}
  {%- set sessions = (1 if lawn_today else 0) + (1 if (lawn_today and has_pm) else 0) -%}
  {{ {
    'effective_mode': eff,
    'lawn_today': lawn_today,
    'drip_today': drip_today,
    'lawn_am_min': (z1 if lawn_today else 0),
    'lawn_pm_min': ((z1 * pm_ratio) | round(0) | int if (lawn_today and has_pm) else 0),
    'cycles': row['cycles'],
    'soak': row['soak'],
    'am': row['am'],
    'pm': row['pm'],
    'drip_min': (row['drip'] if drip_today else 0),
    'sessions': sessions,
    'durations': {
      'valve.lawn_sprinkler_zone_1': (am_s if lawn_today else 0),
      'valve.lawn_sprinkler_zone_2': (side_s if lawn_today else 0),
      'valve.lawn_sprinkler_zone_3': (side_s if lawn_today else 0)
    },
    'durations_pm': {
      'valve.lawn_sprinkler_zone_1': ((am_s * pm_ratio) | round(0) | int if (lawn_today and has_pm) else 0),
      'valve.lawn_sprinkler_zone_2': ((side_s * pm_ratio) | round(0) | int if (lawn_today and has_pm) else 0),
      'valve.lawn_sprinkler_zone_3': ((side_s * pm_ratio) | round(0) | int if (lawn_today and has_pm) else 0)
    }
  } }}
{%- endif -%}
{%- endmacro -%}
```

Add the `today` attribute (paste CANON, then call it):

```yaml
      today: >
        {%- macro ... CANON BLOCK VERBATIM ... -%}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r }}
```

NOTE on `sched()` returning a string: a `{% macro %}` that emits `{{ {...} }}` returns a STRING. The `resolve_day` line `{%- set tbl = sched() | from_json if sched() is string else sched() -%}` handles that — but JSON requires double quotes; Jinja dict repr uses single quotes, so `from_json` fails. **Implementer: instead define `sched`/`resolve_day` to build and pass the dict as a real object, NOT via string emission.** Concretely: make `sched()` a macro whose body is `{% set t = {...} %}{{ t }}` returns string — avoid. Use this pattern instead: define the dict with `{% set tbl = {...} %}` directly INSIDE `resolve_day` (no separate `sched()` macro, no serialization). Replace the `sched()`/`from_json` lines with the dict literal inlined at the top of `resolve_day`. The canonical block above is the LOGIC; collapse `sched()` into `resolve_day` as a plain `{% set tbl = {...} %}` to avoid string round-trips. Verify the rendered `today` is a real dict in Step 3.

- [ ] **Step 2: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`
Expected: no output.

- [ ] **Step 3: Push + reload + verify `today` matches the live scalar attrs**

```bash
git add packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git commit -m "feat(garden): add resolve_day macro + today attribute (parallel, unwired)"
git push
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload"
```
Then for EACH mode, set it and compare `today` to the existing live scalar attributes:
```bash
for m in Eco Standard Intensive Testing Smart Seasonal; do
  curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"entity_id\":\"input_select.garden_irrigation_mode\",\"option\":\"$m\"}" "$HA_URL/api/services/input_select/select_option" >/dev/null; sleep 0.6
  curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"OLD dur={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations\") }} cyc={{ state_attr(\"sensor.garden_irrigation_profile\",\"cycle_count\") }} lt={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_today\") }} dt={{ state_attr(\"sensor.garden_irrigation_profile\",\"drip_today\") }}\nNEW today={{ state_attr(\"sensor.garden_irrigation_profile\",\"today\") }}"}' "$HA_URL/api/template" | sed "s/^/$m: /"
done
```
Expected: for each mode, `today.durations` == OLD `lawn_durations` (except Intensive z2/z3 = 1260), `today.cycles` == OLD `cycle_count`, `today.lawn_today`/`drip_today` match. If any disagree, FIX the macro before Task 2 — the scalar attrs are still the source of truth at this point, so nothing is broken live. Use `dangerouslyDisableSandbox: true`.

- [ ] **Step 4: Restore the original mode + commit if amended**

Set mode back to `Seasonal`. If the macro needed fixes, amend the commit and re-verify. Only proceed when all 6 modes match.

---

### Task 2: Rewire scalar attributes to call `resolve_day`

Now make each existing attribute a thin caller of the macro, so there's ONE definition. Paste CANON into each attribute (the macro is local to each attribute string — that's the HA constraint; the LOGIC is identical, defined once in this plan).

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

- [ ] **Step 1: Replace each attribute body with a macro call**

For `lawn_durations`, `cycle_count`, `lawn_today`, `drip_today`, `effective_mode`,
`drip_duration`, `drip_runs_per_day`, `soak_minutes` — replace the body with CANON + a pluck. Examples (CANON omitted for brevity here — paste the full block from Task 1 at the top of EACH):

```yaml
      lawn_durations: >
        {# CANON macro block here #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['durations'] }}
      cycle_count: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['cycles'] }}
      lawn_today: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['lawn_today'] }}
      drip_today: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['drip_today'] }}
      effective_mode: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['effective_mode'] }}
      drip_duration: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ (r['drip_min'] * 60) | int }}
      drip_runs_per_day: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ 1 if r['drip_min'] > 0 else 0 }}
      soak_minutes: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['soak'] }}
```

Keep `am_time`/`pm_time` (from Seasonal work) but rewire them too:
```yaml
      am_time: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['am'] }}
      pm_time: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['pm'] }}
```

- [ ] **Step 2: Add `lawn_durations_pm`**

```yaml
      lawn_durations_pm: >
        {# CANON #}
        {%- set r = resolve_day(states('input_select.garden_irrigation_mode'), now()) -%}
        {{ r['durations_pm'] }}
```

- [ ] **Step 3: Lint + push + reload**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git add -A && git commit -m "refactor(garden): profile attributes read resolve_day (one definition)"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload" >/dev/null
```

- [ ] **Step 4: Behavior diff vs before-snapshot (the critical gate)**

Render all 6 modes and compare to the before-snapshot in the header:
```bash
for m in Eco Standard Intensive Testing Smart Seasonal; do
  curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d "{\"entity_id\":\"input_select.garden_irrigation_mode\",\"option\":\"$m\"}" "$HA_URL/api/services/input_select/select_option" >/dev/null; sleep 0.6
  curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"dur={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations\") }} pm={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_durations_pm\") }} cyc={{ state_attr(\"sensor.garden_irrigation_profile\",\"cycle_count\") }} lt={{ state_attr(\"sensor.garden_irrigation_profile\",\"lawn_today\") }} dt={{ state_attr(\"sensor.garden_irrigation_profile\",\"drip_today\") }} dd={{ state_attr(\"sensor.garden_irrigation_profile\",\"drip_duration\") }}"}' "$HA_URL/api/template" | sed "s/^/$m: /"
done
```
Expected: matches the before-snapshot exactly EXCEPT Intensive z2/z3 = 1260 (was 1200). Seasonal `pm` non-zero only on a Jun–Aug run day. Any other diff = regression → fix the macro, re-verify. Restore mode to Seasonal after.

---

### Task 3: Add `schedule_7day` attribute

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml`

- [ ] **Step 1: Add the attribute**

```yaml
      schedule_7day: >
        {# CANON #}
        {%- set ns = namespace(rows=[]) -%}
        {%- set mode = states('input_select.garden_irrigation_mode') -%}
        {%- for i in range(0, 7) -%}
          {%- set d = now() + timedelta(days=i) -%}
          {%- set r = resolve_day(mode, d) -%}
          {%- set ns.rows = ns.rows + [{
            'date': d.strftime('%Y-%m-%d'),
            'dow': d.isoweekday(),
            'lawn_am_min': r['lawn_am_min'],
            'lawn_pm_min': r['lawn_pm_min'],
            'drip_min': r['drip_min'],
            'sessions': r['sessions']
          }] -%}
        {%- endfor -%}
        {{ ns.rows }}
```

- [ ] **Step 2: Lint + push + reload + verify**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_irrigation_profile.yaml
git add -A && git commit -m "feat(garden): profile exposes schedule_7day (shared contract)"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"{{ state_attr(\"sensor.garden_irrigation_profile\",\"schedule_7day\") }}"}' "$HA_URL/api/template"
```
Expected (Seasonal, June): 7 rows; Mon/Wed/Fri have `lawn_am_min=15, lawn_pm_min=9, sessions=2`; Mon/Thu have `drip_min=45`; off days zeros. Verify dates/dows align with the calendar.

---

### Task 4: Rewire `garden_next_run` to read `schedule_7day`

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_next_run.yaml`

- [ ] **Step 1: Replace both sensor bodies with a schedule_7day scan**

Read the file. Keep the trigger block + the one-off-armed priority logic (top of each sensor) unchanged. Replace the per-mode `eff`/`runs`/`slot` derivation in BOTH the lawn and drip sensors with a scan of `schedule_7day`.

Lawn sensor recurring-scan body (the `{% else %}` branch after the one-off check):
```jinja
        {% set sched = state_attr('sensor.garden_irrigation_profile', 'schedule_7day') or [] %}
        {% set skip = is_state('binary_sensor.garden_lawn_should_skip', 'on') %}
        {% set ns = namespace(found='none') %}
        {% for row in sched %}
          {% if ns.found == 'none' and row.lawn_am_min > 0 %}
            {% set d = strptime(row.date, '%Y-%m-%d') %}
            {% set h = state_attr('sensor.garden_irrigation_profile', 'am_time') %}
            {% set hh = (h.split(':')[0] | int) if (h and ':' in h) else 4 %}
            {% set slot = d.replace(hour=hh, minute=0, second=0, microsecond=0) %}
            {% if now() < slot and not skip %}{% set ns.found = slot.isoformat() %}{% endif %}
          {% endif %}
        {% endfor %}
        {{ ns.found }}
```
Drip sensor recurring-scan body — same shape but gate on `row.drip_min > 0`, skip = `binary_sensor.garden_drip_should_skip`, and use the AM slot hour.

NOTE: `am_time` is the CURRENT mode's AM; for the 7-day scan all rows share the active mode, so a single `am_time` read is correct (Seasonal AM is constant per month-in-window; acceptable — a month boundary mid-window is an edge the old code also ignored).

- [ ] **Step 2: Lint + push + reload + verify**

```bash
uv run yamllint packages/areas/outdoor/garden/templates/garden_next_run.yaml
git add -A && git commit -m "refactor(garden): next-run reads schedule_7day (no per-mode maps)"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload" >/dev/null
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" -d '{"template":"lawn={{ states(\"sensor.garden_lawn_next_run\") }} drip={{ states(\"sensor.garden_drip_next_run\") }}"}' "$HA_URL/api/template"
```
Expected: both timestamps in the future, on a valid run day for the current mode. Cross-check against `schedule_7day`. Test a single-session mode (set Standard) and Seasonal.

---

### Task 5: Create the PM top-up script

**Files:**
- Create: `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation_pm.yaml`

- [ ] **Step 1: Write the script**

Mirrors `garden_ondemand_lawn` (sets the `garden_ondemand_active` flag so `garden_valve_auto_off` skips, then per-zone open/wait/close single-pass) but reads `lawn_durations_pm` per zone instead of a slider.

```yaml
---
garden_lawn_irrigation_pm:
  alias: Garden Lawn Irrigation (PM top-up)
  description: >
    Seasonal PM top-up: zones 1→2→3 once, each for its lawn_durations_pm seconds
    (≈60% of the AM deep soak). Single pass, no soak. Sets garden_ondemand_active
    so garden_valve_auto_off skips these valves (this script owns the close).
  icon: mdi:weather-sunset
  mode: single
  sequence:
    - variables:
        pm: "{{ state_attr('sensor.garden_irrigation_profile', 'lawn_durations_pm') or {} }}"
    - if:
        - "{{ (pm.values() | sum) | int(0) == 0 }}"
      then:
        - stop: "PM top-up skipped — no PM duration"
    - if:
        - >
          {{ expand('valve.lawn_sprinkler_zone_1',
                    'valve.lawn_sprinkler_zone_2',
                    'valve.lawn_sprinkler_zone_3')
             | selectattr('state', 'eq', 'unavailable') | list | count > 0 }}
      then:
        - action: persistent_notification.create
          data:
            notification_id: garden_pm_offline
            title: PM top-up unavailable
            message: "Sprinkler controller offline — PM top-up aborted."
        - stop: "PM top-up aborted — valves unavailable"
    - action: input_boolean.turn_on
      target:
        entity_id: input_boolean.garden_ondemand_active
    - repeat:
        for_each:
          - valve.lawn_sprinkler_zone_1
          - valve.lawn_sprinkler_zone_2
          - valve.lawn_sprinkler_zone_3
        sequence:
          - variables:
              secs: "{{ pm.get(repeat.item, 0) | int(0) }}"
          - if:
              - "{{ secs > 0 }}"
            then:
              - action: valve.open_valve
                target:
                  entity_id: "{{ repeat.item }}"
              - delay:
                  seconds: "{{ secs }}"
              - action: valve.close_valve
                target:
                  entity_id: "{{ repeat.item }}"
              - delay:
                  seconds: 5
    - action: input_boolean.turn_off
      target:
        entity_id: input_boolean.garden_ondemand_active
```

- [ ] **Step 2: Lint + commit**

```bash
uv run yamllint packages/areas/outdoor/garden/scripts/garden_lawn_irrigation_pm.yaml
git add -A && git commit -m "feat(garden): PM top-up script (single-pass, lawn_durations_pm)"
```

---

### Task 6: Wire PM session in the Seasonal automation

**Files:**
- Modify: `packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml`

- [ ] **Step 1: Split AM vs PM dispatch**

Read the file. The `choose` at the end currently dispatches full/lawn/drip the same for AM and PM. Replace the final `choose` so the PM session runs the PM script (lawn-only), and AM keeps the deep run + drip:

```yaml
  - choose:
      # PM session — lawn-only top-up (no drip).
      - conditions:
          - "{{ is_pm }}"
          - "{{ run_lawn }}"
        sequence:
          - action: script.garden_lawn_irrigation_pm
      # AM with both lawn + drip.
      - conditions:
          - "{{ is_am and run_lawn and run_drip }}"
        sequence:
          - action: script.garden_full_irrigation
      # AM lawn only.
      - conditions:
          - "{{ is_am and run_lawn }}"
        sequence:
          - action: script.garden_lawn_irrigation
      # AM drip only.
      - conditions:
          - "{{ is_am and run_drip }}"
        sequence:
          - action: script.garden_drip_irrigation
```

(The existing `run_drip = is_am and drip_today and not drip_skip` already prevents PM drip.)

- [ ] **Step 2: Lint + push + reload + verify dispatch**

```bash
uv run yamllint packages/areas/outdoor/garden/automations/garden_seasonal_irrigation.yaml
git add -A && git commit -m "feat(garden): Seasonal PM session runs the 60% top-up script"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload" >/dev/null
```
Functional: with Seasonal mode and small helper durations, simulate a PM run — set helpers low, call `script.garden_lawn_irrigation_pm` directly, confirm each zone opens for ~pm seconds single-pass and the flag clears. Confirm `lawn_durations_pm` ≈ 60% of `lawn_durations`.

---

### Task 7: Rewire the dashboard 7-day table to `schedule_7day`

**Files:**
- Modify: `dashboards/tablet/outdoor.yaml`

- [ ] **Step 1: Replace the macro block + loop with a schedule_7day render**

Read the markdown card (the `content: |` block ~line 200). DELETE the macros `dur` may stay (formatting helper), but DELETE `lawn_total`, `lawn_zones`, `lawn_cycles`, `drip_dur`, `drip_runs`, `lawn_run`, `drip_run`. Replace the per-day loop with:

```jinja
                  {% set mode = states('input_select.garden_irrigation_mode') %}
                  {% set sched = state_attr('sensor.garden_irrigation_profile', 'schedule_7day') or [] %}
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
                  {%- set d = strptime(row.date, '%Y-%m-%d') -%}
                  {%- set side = (row.lawn_am_min * 0.6) | round(0) | int -%}
                  {%- if row.sessions == 2 -%}
                    {%- set lawn_cell = '✓ AM ' ~ row.lawn_am_min ~ 'm + PM ' ~ row.lawn_pm_min ~ 'm' -%}
                    {%- set zones_cell = row.lawn_am_min ~ '·' ~ side ~ '·' ~ side ~ ' +PM' -%}
                  {%- elif row.sessions == 1 -%}
                    {%- set lawn_cell = '✓ ' ~ row.lawn_am_min ~ 'm' -%}
                    {%- set zones_cell = row.lawn_am_min ~ '·' ~ side ~ '·' ~ side -%}
                  {%- else -%}
                    {%- set lawn_cell = '—' -%}
                    {%- set zones_cell = '—' -%}
                  {%- endif -%}
                  {%- set drip_cell = ('✓ ' ~ dur(row.drip_min * 60)) if row.drip_min > 0 else '—' -%}
                  | {% if loop.first %}**{{ d.strftime('%a %d') }}**{% else %}{{ d.strftime('%a %d') }}{% endif %} | {{ lawn_cell }} | {{ zones_cell }} | {{ drip_cell }} |
                  {% endfor %}

                  {% if mode == 'Seasonal' %}
                  _Seasonal: deep AM soak + ~60% PM top-up on 2-session days. AM {{ state_attr('sensor.garden_irrigation_profile', 'am_time') | trim }}{% if state_attr('sensor.garden_irrigation_profile', 'pm_time') | trim %} + PM {{ state_attr('sensor.garden_irrigation_profile', 'pm_time') | trim }}{% endif %}. Drip Mon/Thu._
                  {% else %}
                  _Lawn cycle &amp; soak; zone mins = total per run._
                  {% endif %}
                  {% endif %}
```

- [ ] **Step 2: Lint + push + reload + force lovelace cache + Playwright**

```bash
uv run yamllint dashboards/tablet/outdoor.yaml
git add -A && git commit -m "refactor(garden): 7-day table renders schedule_7day, AM+PM cells"
git push
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/homeassistant/reload_core_config" >/dev/null
```
Force-refresh the lovelace server cache (WS `lovelace/config` `url_path:'wall-tablet' force:true`), then Playwright `/wall-tablet/outdoor`: confirm Seasonal Jun rows show `✓ AM 15m + PM 9m` on Mon/Wed/Fri, drip ✓ on Mon/Thu. Switch to Standard, confirm single-session rows render unchanged. Screenshots → `.playwright-mcp/`.

---

### Task 8: Docs + knowledge

**Files:**
- Modify: `packages/areas/outdoor/garden/README.md`
- Modify: `knowledge/areas/garden-irrigation-schedule.md`

- [ ] **Step 1: README**

Update: modes table (note Intensive now 35/21/21); Seasonal AM/PM section; explain the unified model — one `resolve_day` macro + `schedule_7day`, consumers read it. Add `lawn_durations_pm`, `today`, `schedule_7day` to the profile attribute list and `scripts/garden_lawn_irrigation_pm.yaml` to the File Index.

- [ ] **Step 2: Knowledge leaf**

Invoke the `knowledge-author` skill to REWRITE `garden-irrigation-schedule`: the schedule is now ONE definition (the `resolve_day` macro in `garden_irrigation_profile.yaml`) exposed via `schedule_7day`; `next_run` + the dashboard table READ it (no longer re-derive). Update the summary + the "duplicated across 4 spots" gotcha to "one macro, N readers", and note the `cycle_count`-via-macro + macro-text-repeated-per-attribute HA constraint.

- [ ] **Step 3: Commit + push**

```bash
git add -A && git commit -m "docs(garden): document unified schedule model"
git push
```

---

## Self-Review notes

- **Spec coverage:** resolve_day macro single definition (T1) ✓; thin-caller attributes (T2) ✓; 0.6 formula everywhere incl. Intensive drift (T2, verified) ✓; Testing flat via weighted:false (T1 macro) ✓; Smart resolver + DripOnly + Off (T1 macro) ✓; dynamic_adjust placeholder — NOTE: folded into the Smart resolver as the `smart_target`/identity path; an explicit no-op `dynamic_adjust` wrapper should be added in T1 around the resolved row (see gap below); lawn_durations_pm (T2) ✓; schedule_7day contract (T3) ✓; next_run reads it (T4) ✓; dashboard reads it, macros deleted (T7) ✓; PM script single-pass (T5) + automation wiring (T6) ✓; behavior-preserving diff gates (T1,T2) ✓; docs + knowledge (T8) ✓.
- **GAP fixed inline:** add an explicit `{%- macro dynamic_adjust(row) -%}{{ row }}{%- endmacro -%}` to CANON and wrap the resolved row (`resolve_day` returns `dynamic_adjust(<computed dict>)`) so the soil/forecast seam is a named no-op now, per spec. Implementer: include it in the CANON block in Task 1.
- **Entity/attr consistency:** `resolve_day`, `schedule_7day`, `lawn_durations`/`_pm`, `cycle_count`, `am_time`/`pm_time`, `today`, `script.garden_lawn_irrigation_pm`, `input_boolean.garden_ondemand_active`, `binary_sensor.garden_lawn_should_skip`/`_drip` — consistent across tasks.
- **Key risk flagged:** macro returns a STRING if emitted via `{{ }}` — Task 1 Step 1 explicitly directs inlining the dict as a real `{% set tbl = {...} %}` object inside `resolve_day`, NOT a serialized `sched()`+from_json round-trip. Verify `today` renders as a real dict before rewiring.
- **Out of scope honored:** real soil/forecast Smart logic (placeholder only), Eco/Standard collapse, dry-patch hardware, non-Seasonal PM, heat-triggered PM.
