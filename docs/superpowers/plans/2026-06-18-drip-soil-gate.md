# 3-Sensor Combined Drip Soil Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the shared drip line on three flowerbed soil probes (pergola L/R + sona) via a driest-wins trigger plus a saturation cap, replacing the dead `sensor.garden_soil_moisture` term.

**Architecture:** One new template binary_sensor (`garden_drip_soil_skip`) computes the combined verdict. Its result OR-feeds the existing `garden_drip_should_skip`. The legacy alias `garden_should_skip_irrigation` is updated to mirror drip. Lawn skip is untouched. All edits in a single file. No automation changes — `garden_seasonal_irrigation` already reads `garden_drip_should_skip`.

**Tech Stack:** Home Assistant template binary_sensors (Jinja2), trigger-based template entity. "Tests" = `/api/template` renders against live + mocked sensor values (no pytest in this repo). Verify before push, reload after.

**Reference:** spec at `docs/superpowers/specs/2026-06-18-drip-soil-gate-design.md`.

**Key facts the engineer needs:**
- Probe entities: `sensor.pergola_left_flowerbed_soil_moisture`, `sensor.pergola_right_flowerbed_soil_moisture`, `sensor.sona_flowerbed_soil_moisture`. All report `%` (0–100). Current live values ~82/84/90.
- sona is structurally wetter → **excluded from the saturation cap**, included in driest-wins.
- Thresholds: `DRY = 50`, `SAT = 85`.
- Env vars `$HA_URL`, `$HA_TOKEN` are preloaded via direnv — use directly. Sandbox blocks `homeassistant.local` → every `curl` needs `dangerouslyDisableSandbox: true`.
- The file edited: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`. It is a single trigger-based template entry (one `trigger:` block, then `binary_sensor:` list). The new sensor is added to that same `binary_sensor:` list so it shares the existing `/30`-minute + state triggers.
- After push: reload via `homeassistant.reload_core_config` is NOT enough for template entities — use `template.reload`. See knowledge leaf **reload-after-push**.

---

## File Structure

- **Modify:** `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
  - Add `Garden Drip Soil Skip` binary_sensor to the existing `binary_sensor:` list.
  - Rewrite `garden_drip_should_skip` state + reason to consume the new helper.
  - Rewrite `garden_should_skip_irrigation` (legacy alias) to mirror drip.
- **Modify (after verify):** `knowledge/areas/garden-irrigation-schedule.md` — via knowledge-author, not inline.

No other files. No new automations.

---

### Task 1: Add the `garden_drip_soil_skip` helper sensor

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml` (append to `binary_sensor:` list, after the existing `garden_should_skip_irrigation` block, ~line 99)

- [ ] **Step 1: Dry-run the combined expression against LIVE values (expect skip today)**

This is the "failing test" — prove the logic renders the right verdict before writing it into the file. Run via `/api/template`. (curl needs `dangerouslyDisableSandbox: true`.)

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d @- <<'JSON'
{"template": "{% set DRY = 50 %}{% set SAT = 85 %}{% set probes = ['sensor.pergola_left_flowerbed_soil_moisture','sensor.pergola_right_flowerbed_soil_moisture','sensor.sona_flowerbed_soil_moisture'] %}{% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture','sensor.pergola_right_flowerbed_soil_moisture'] %}{% set bad = ['unknown','unavailable','none',''] %}{% set valid = probes | map('states') | reject('in', bad) | map('float',-1) | reject('eq',-1) | list %}{% set cap_valid = cap_probes | map('states') | reject('in', bad) | map('float',-1) | reject('eq',-1) | list %}{% if valid | length == 0 %}UNKNOWN{% else %}{% set driest = valid | min %}{% set wettest = cap_valid | max if cap_valid | length > 0 else -1 %}driest={{ driest }} wettest={{ wettest }} skip={{ driest >= DRY or wettest >= SAT }}{% endif %}"}
JSON
```

Expected output (with live ~82/84/90): `driest=82.0 wettest=84.0 skip=True`

- [ ] **Step 2: Dry-run the mocked failure / edge cases**

Confirm the four reason branches resolve correctly. Run each; they hard-code the inputs so no live state needed.

One-bed-dry (expect run):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d '{"template": "{% set DRY=50 %}{% set SAT=85 %}{% set valid=[35.0,84.0,90.0] %}{% set cap_valid=[35.0,84.0] %}{% set driest=valid|min %}{% set wettest=cap_valid|max %}skip={{ driest>=DRY or wettest>=SAT }}"}'
```
Expected: `skip=False` (driest 35 < 50, wettest 84 < 85 → run).

Pergola-saturated (expect skip):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d '{"template": "{% set DRY=50 %}{% set SAT=85 %}{% set valid=[40.0,88.0,90.0] %}{% set cap_valid=[40.0,88.0] %}{% set driest=valid|min %}{% set wettest=cap_valid|max %}skip={{ driest>=DRY or wettest>=SAT }}"}'
```
Expected: `skip=True` (wettest 88 ≥ 85 → drown-protection skip, even though driest 40 < 50).

sona-only-alive, pergola dead (expect cap can't trip, driest=sona):
```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/template" -d '{"template": "{% set DRY=50 %}{% set SAT=85 %}{% set valid=[90.0] %}{% set cap_valid=[] %}{% set driest=valid|min %}{% set wettest=(cap_valid|max if cap_valid|length>0 else -1) %}skip={{ driest>=DRY or wettest>=SAT }}"}'
```
Expected: `skip=True` (driest=sona 90 ≥ 50; wettest=-1 can't trip).

- [ ] **Step 3: Add the helper sensor to the file**

Append this block to the `binary_sensor:` list, immediately after the `garden_should_skip_irrigation` block (after the current line 99). Match the 2-space list indentation of the sibling sensors.

```yaml
  - name: Garden Drip Soil Skip
    unique_id: garden_drip_soil_skip
    icon: mdi:water-percent
    # Combined 3-bed verdict for the shared drip line.
    #   driest-wins: skip if the THIRSTIEST bed is already moist (>= DRY)
    #   saturation cap: skip if a PERGOLA bed is drowning (>= SAT)
    # sona is structurally wetter (more emitters) -> in driest-wins, NOT in the cap.
    # Fail-safe: invalid probes dropped; all invalid -> state 'unknown'.
    state: >
      {% set DRY = 50 %}
      {% set SAT = 85 %}
      {% set bad = ['unknown', 'unavailable', 'none', ''] %}
      {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                       'sensor.pergola_right_flowerbed_soil_moisture',
                       'sensor.sona_flowerbed_soil_moisture'] %}
      {% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                           'sensor.pergola_right_flowerbed_soil_moisture'] %}
      {% set valid = probes | map('states') | reject('in', bad)
         | map('float', -1) | reject('eq', -1) | list %}
      {% set cap_valid = cap_probes | map('states') | reject('in', bad)
         | map('float', -1) | reject('eq', -1) | list %}
      {% if valid | length == 0 %}
        {{ None }}
      {% else %}
        {% set driest = valid | min %}
        {% set wettest = cap_valid | max if cap_valid | length > 0 else -1 %}
        {{ driest >= DRY or wettest >= SAT }}
      {% endif %}
    attributes:
      driest: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {% set valid = probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (valid | min) if valid | length > 0 else None }}
      wettest: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                             'sensor.pergola_right_flowerbed_soil_moisture'] %}
        {% set cap_valid = cap_probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {{ (cap_valid | max) if cap_valid | length > 0 else None }}
      valid_count: >
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {{ probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list | length }}
      reason: >
        {% set DRY = 50 %}
        {% set SAT = 85 %}
        {% set bad = ['unknown', 'unavailable', 'none', ''] %}
        {% set probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                         'sensor.pergola_right_flowerbed_soil_moisture',
                         'sensor.sona_flowerbed_soil_moisture'] %}
        {% set cap_probes = ['sensor.pergola_left_flowerbed_soil_moisture',
                             'sensor.pergola_right_flowerbed_soil_moisture'] %}
        {% set valid = probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {% set cap_valid = cap_probes | map('states') | reject('in', bad)
           | map('float', -1) | reject('eq', -1) | list %}
        {% if valid | length == 0 %} no_valid_probes
        {% elif (cap_valid | length > 0) and (cap_valid | max) >= SAT %} pergola_saturated
        {% elif (valid | min) >= DRY %} driest_moist
        {% else %} soil_dry_ok {% endif %}
```

- [ ] **Step 4: Lint the file**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no errors (warnings about line-length on long Jinja lines are acceptable if the repo's `.yamllint` allows them; if it errors, wrap the offending lines).

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): add garden_drip_soil_skip 3-sensor combined verdict

Driest-wins (all 3 probes) + saturation cap (pergola L/R only, sona
excluded as structurally wetter). DRY=50/SAT=85, fail-safe on dead probes."
```

---

### Task 2: Wire the helper into `garden_drip_should_skip`

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml` (the `garden_drip_should_skip` block, current lines 50–74)

- [ ] **Step 1: Replace the `state:` body**

Replace the existing `state: >` block of `garden_drip_should_skip` (lines 53–61, the `soil`/`soil_wet`/`{{ ... }}` lines) with the version below. The new `drip_soil_skip` reads the helper from Task 1; `is_state(..., 'on')` is `False` when the helper is `unknown` (all probes dead) → fail-safe fallback to rain/season.

Old (remove lines 54–61):
```yaml
      {% set is_raining = is_state('binary_sensor.raining', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set rain_mm = states('sensor.garden_rain_accumulation') | float(0) %}
      {% set soil = states('sensor.garden_soil_moisture') %}
      {% set soil_wet = soil not in ['unknown', 'unavailable', 'none', '']
         and (soil | float(-1)) > 65 %}
      {{ not in_season or is_raining or rain_mm >= 3 or soil_wet }}
```

New:
```yaml
      {% set is_raining = is_state('binary_sensor.raining', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set rain_mm = states('sensor.garden_rain_accumulation') | float(0) %}
      {% set drip_soil_skip = is_state('binary_sensor.garden_drip_soil_skip', 'on') %}
      {{ not in_season or is_raining or rain_mm >= 3 or drip_soil_skip }}
```

- [ ] **Step 2: Replace the `reason:` body**

Replace the `reason:` attribute body of `garden_drip_should_skip` (lines 64–74) with:

```yaml
        {% set month = now().month %}
        {% set in_season = month >= 5 and month <= 9 %}
        {% set rain_mm = states('sensor.garden_rain_accumulation') | float(0) %}
        {% set drip_soil_skip = is_state('binary_sensor.garden_drip_soil_skip', 'on') %}
        {% if not in_season %} out_of_season
        {% elif is_state('binary_sensor.raining', 'on') %} raining_now
        {% elif rain_mm >= 3 %} rain_accumulation_3mm
        {% elif drip_soil_skip %} soil_{{ state_attr('binary_sensor.garden_drip_soil_skip', 'reason') | trim }}
        {% else %} none {% endif %}
```

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): wire garden_drip_soil_skip into garden_drip_should_skip

Replaces phantom sensor.garden_soil_moisture term with the real 3-sensor
combined verdict; rain/season remain independent OR-terms."
```

---

### Task 3: Update the legacy `garden_should_skip_irrigation` alias to mirror drip

**Files:**
- Modify: `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml` (the `garden_should_skip_irrigation` block, current lines 75–99)

- [ ] **Step 1: Replace its `state:` body**

The alias must stay honest now that drip uses real probes. Mirror Task 2's drip state. Replace the `soil`/`soil_wet`/final-`{{ }}` lines (83–86) with:

```yaml
      {% set is_raining = is_state('binary_sensor.raining', 'on') %}
      {% set month = now().month %}
      {% set in_season = month >= 5 and month <= 9 %}
      {% set rain_mm = states('sensor.garden_rain_accumulation') | float(0) %}
      {% set drip_soil_skip = is_state('binary_sensor.garden_drip_soil_skip', 'on') %}
      {{ not in_season or is_raining or rain_mm >= 3 or drip_soil_skip }}
```

- [ ] **Step 2: Replace its `reason:` body**

Replace lines 89–99 with the same reason logic as Task 2 Step 2:

```yaml
        {% set month = now().month %}
        {% set in_season = month >= 5 and month <= 9 %}
        {% set rain_mm = states('sensor.garden_rain_accumulation') | float(0) %}
        {% set drip_soil_skip = is_state('binary_sensor.garden_drip_soil_skip', 'on') %}
        {% if not in_season %} out_of_season
        {% elif is_state('binary_sensor.raining', 'on') %} raining_now
        {% elif rain_mm >= 3 %} rain_accumulation_3mm
        {% elif drip_soil_skip %} soil_{{ state_attr('binary_sensor.garden_drip_soil_skip', 'reason') | trim }}
        {% else %} none {% endif %}
```

- [ ] **Step 3: Lint**

Run: `uv run yamllint packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no errors.

- [ ] **Step 4: Verify no remaining reference to the phantom sensor**

Run: `grep -n "garden_soil_moisture" packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`
Expected: no output (the dead `sensor.garden_soil_moisture` is fully gone; lawn sensor never referenced it... wait — it does). **NOTE:** `garden_lawn_should_skip` still references `sensor.garden_soil_moisture` by design (lawn has no probe; the float guard keeps it inert). So expected output IS the two lawn lines only (state + reason). Confirm ONLY lawn lines remain, none in drip/alias blocks.

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml
git commit -m "feat(garden): mirror drip soil gate in legacy garden_should_skip_irrigation alias"
```

---

### Task 4: Push, reload, and verify live

**Files:** none (deployment + verification only)

- [ ] **Step 1: Push the branch**

Already on a feature branch (`chore/june-improvments` or similar — confirm with `git branch --show-current`; never push main). Run: `git push`

- [ ] **Step 2: Reload template entities**

Template sensors need `template.reload`, not just core-config reload. Run:
```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA_URL/api/services/template/reload" -d '{}'
```
Expected: `[]` or a list (no error). (curl needs `dangerouslyDisableSandbox: true`.)

- [ ] **Step 3: Check HA logs for template errors**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | grep -iE "garden_drip_soil_skip|garden_drip_should_skip|garden_should_skip|template" | tail -20
```
Expected: no new errors referencing these sensors.

- [ ] **Step 4: Verify the helper renders live**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/binary_sensor.garden_drip_soil_skip" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('state=',d['state']); print('attrs=',json.dumps(d['attributes'],indent=2))"
```
Expected (live ~82/84/90): `state= on`, attrs `driest=82.0`, `wettest=84.0`, `valid_count=3`, `reason=driest_moist`.

- [ ] **Step 5: Verify the drip skip sensor flips with it**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/binary_sensor.garden_drip_should_skip" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('state=',d['state'],'| reason=',d['attributes'].get('reason'))"
```
Expected: `state= on | reason= soil_driest_moist` (in-season June, no rain, beds wet).

- [ ] **Step 6: Confirm no regression on lawn**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states/binary_sensor.garden_lawn_should_skip" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('state=',d['state'],'| reason=',d['attributes'].get('reason'))"
```
Expected: lawn unchanged — reason should NOT be soil-based (lawn has no probe; expect `none` or rain/season as before).

---

### Task 5: Update the knowledge leaf

**Files:**
- Modify (via skill): `knowledge/areas/garden-irrigation-schedule.md`

- [ ] **Step 1: Invoke knowledge-author to update the skip-gating section**

Do NOT edit the leaf inline. Invoke the `knowledge-author` skill with this correction:

> The drip skip gate no longer uses `sensor.garden_soil_moisture` (phantom). It now uses `binary_sensor.garden_drip_soil_skip` — a 3-sensor combined verdict over `sensor.pergola_left_flowerbed_soil_moisture`, `sensor.pergola_right_flowerbed_soil_moisture`, `sensor.sona_flowerbed_soil_moisture`. Logic: driest-wins (skip if min of all 3 >= DRY=50) OR saturation cap (skip if max of pergola L/R only >= SAT=85; sona excluded from the cap because it is structurally wetter — more drip emitters). Fail-safe: invalid probes dropped, all-invalid → helper unknown → drip falls back to rain+season. Lawn skip STILL has no probe and still references the inert `sensor.garden_soil_moisture` by design (mower would hit a lawn probe).

- [ ] **Step 2: Confirm INDEX rebuilt + committed**

knowledge-author owns rebuild/commit. Verify with: `git log --oneline -1` shows the knowledge commit, and `grep -n garden-irrigation knowledge/INDEX.md` still resolves.

---

## Self-Review

**1. Spec coverage:**
- Hybrid combining (driest-wins + cap) → Task 1 ✅
- sona excluded from cap → Task 1 (`cap_probes` omits sona) ✅
- DRY=50/SAT=85 → Task 1 ✅
- Fail-safe A (drop invalid, all-dead→unknown→fallback) → Task 1 (`valid` filter, `None` state) + Task 2 (`is_state 'on'` false on unknown) ✅
- Integration option A (replace soil_wet, keep rain/season OR-terms) → Task 2 ✅
- Legacy alias mirrors drip → Task 3 ✅
- Lawn untouched → Task 3 Step 4 explicitly preserves lawn's phantom ref ✅
- Verification via /api/template + reload-after-push → Tasks 1, 4 ✅
- Knowledge follow-up → Task 5 ✅
- Today's sanity check (driest=82 skip) → Task 1 Step 1 + Task 4 Step 4 ✅

**2. Placeholder scan:** No TBD/TODO/"handle edge cases" — all Jinja shown in full, all commands concrete. ✅

**3. Type/name consistency:** `garden_drip_soil_skip` entity id, `driest`/`wettest`/`valid_count`/`reason` attrs, `DRY`/`SAT` consts — identical across Tasks 1–5. `is_state(..., 'on')` used consistently for the helper read in Tasks 2 & 3. ✅

**Note on `None` state:** a template binary_sensor returning `{{ None }}` resolves to `unknown` (not on/off) — that's the intended fail-safe; `is_state('on')` then yields false. Confirmed standard HA behavior.
