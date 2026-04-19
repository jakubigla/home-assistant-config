# Living Room Floor Heating Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `climate.living_room_floor_heating` — an abstract climate entity that wraps the Bosch `climate.floor_heating`, shows the living-room zigbee hygrometer as current temperature, forwards controls 1:1 to the underlying entity, and does not expose the unreliable `hvac_action` attribute.

**Architecture:** Single `platform: climate_template` entity in a new area-package YAML file, included from the living-room area config. State is read via templates (zigbee sensor for current temperature, underlying climate attrs for everything else); writes are forwarded via `climate.set_*` action blocks. No `hvac_action_template` → attribute is absent. Availability is gated on both the zigbee sensor and the underlying Bosch climate being usable.

**Tech Stack:** Home Assistant YAML packages, HACS custom integration [`jcwillox/hass-template-climate`](https://github.com/jcwillox/hass-template-climate) (provides `platform: climate_template`), `uv run yamllint` / pre-commit for local validation, HA REST API for post-push verification. Live HA instance pulls from the current git branch automatically — no deploy step beyond `git push`.

**Spec:** [`docs/superpowers/specs/2026-04-19-living-room-floor-heating-wrapper-design.md`](../specs/2026-04-19-living-room-floor-heating-wrapper-design.md)

**Repo conventions used below:**
- Env vars `$HA_TOKEN` and `$HA_URL` are pre-loaded via direnv. Never source `.env`.
- `homeassistant.local` is blocked by the shell sandbox — every `curl` to the HA API must be run with `dangerouslyDisableSandbox: true`.
- Always `git push` after a YAML change so HA auto-pulls. Then reload and check logs.
- This work targets the living room. The current branch is `chore/improve-ensuite-sensor`, whose name does not match. Task 0B addresses branch hygiene before any commits.

---

## File Structure

Files created / modified by this plan:

- **Create:** `packages/areas/ground-floor/living-room/climate.yaml`
  - One list-form YAML document defining the `climate_template` entity. One responsibility: the wrapper climate.
- **Modify:** `packages/areas/ground-floor/living-room/config.yaml`
  - Add a single `climate: !include climate.yaml` line near the existing domain-level includes.
- **Modify:** `packages/areas/ground-floor/living-room/README.md`
  - Add a short section documenting the wrapper and its HACS dependency so the custom-component dependency is discoverable.

No source-tree tests exist — this repo is a Home Assistant configuration, not an application. "Tests" in this plan are concrete post-deploy verifications against the running HA instance via its REST API.

---

## Task 0A: Prerequisite — install `hass-template-climate` via HACS (MANUAL)

**Blocking, manual, one-time.** The YAML introduced in later tasks will fail to load until this integration is installed on the running HA instance. This step cannot be automated from the repo.

**Files:** none

- [ ] **Step 1: Install the HACS custom repository**

Ask the user to perform, in the HA UI:

1. HACS → Integrations → three-dot menu → **Custom repositories**.
2. Repository: `https://github.com/jcwillox/hass-template-climate`
3. Category: **Integration**
4. Click **Add**.
5. Back in HACS, search for "Template Climate" → **Download** (accept latest version).
6. **Restart Home Assistant** (Settings → System → Restart).

- [ ] **Step 2: Verify the platform is registered**

Run (note the `dangerouslyDisableSandbox: true` requirement for `homeassistant.local`):

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); \
print('climate_template found' if any(s.get('domain')=='climate_template' for s in data) \
      else 'MISSING: climate_template domain not registered — HACS install incomplete')"
```

Expected: `climate_template found`

If `MISSING`, the HACS install did not complete or HA was not restarted. Do not proceed to Task 1 until this prints `climate_template found`. A faster cross-check: `curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" | grep -q climate_template && echo ok` — but the service-list check above is more definitive.

- [ ] **Step 3: No commit**

Nothing to commit in this task; the HACS install is server-side state.

---

## Task 0B: Ensure we are on an appropriately named branch

**Files:** none

- [ ] **Step 1: Check current branch**

```bash
git status --short --branch | head -1
```

- [ ] **Step 2: Decide branch strategy**

If the current branch is `chore/improve-ensuite-sensor` (or any name that does not describe this work), create and switch to a dedicated branch:

```bash
git switch -c feat/living-room-floor-heating-wrapper
```

If the user has already switched to a descriptive branch, skip this step.

**Do not push yet** — we have nothing to push. No commit in this task.

---

## Task 1: Create `climate.yaml`

**Files:**
- Create: `packages/areas/ground-floor/living-room/climate.yaml`

- [ ] **Step 1: Write the climate_template entity**

Write the following file verbatim. Do not change attribute names or templates — they were validated against the spec and the HACS integration's schema.

```yaml
---
- platform: climate_template
  name: Living Room Floor Heating
  unique_id: living_room_floor_heating

  modes: ["off", "auto"]
  preset_modes: ["none", "away"]
  min_temp: 16
  max_temp: 30
  temp_step: 0.5

  current_temperature_template: >-
    {{ states('sensor.living_room_hygro_temperature') | float(none) }}
  target_temperature_template: >-
    {{ state_attr('climate.floor_heating', 'temperature') | float(none) }}
  hvac_mode_template: "{{ states('climate.floor_heating') }}"
  preset_mode_template: "{{ state_attr('climate.floor_heating', 'preset_mode') }}"

  availability_template: >-
    {{ states('sensor.living_room_hygro_temperature') not in
       ['unknown', 'unavailable', 'none', '']
       and states('climate.floor_heating') not in ['unknown', 'unavailable'] }}

  set_temperature:
    - service: climate.set_temperature
      target:
        entity_id: climate.floor_heating
      data:
        temperature: "{{ temperature }}"

  set_hvac_mode:
    - service: climate.set_hvac_mode
      target:
        entity_id: climate.floor_heating
      data:
        hvac_mode: "{{ hvac_mode }}"

  set_preset_mode:
    - service: climate.set_preset_mode
      target:
        entity_id: climate.floor_heating
      data:
        preset_mode: "{{ preset_mode }}"
```

Note: `hvac_action_template` is deliberately absent. This is what causes the wrapper to hide the (fabricated) heating signal. Do not add it.

- [ ] **Step 2: Lint only this file**

```bash
uv run yamllint packages/areas/ground-floor/living-room/climate.yaml
```

Expected: no output, exit 0.

If yamllint complains about a specific line, fix the reported issue (typically trailing whitespace or a missing newline) and re-run.

- [ ] **Step 3: Do not commit yet**

Task 2 introduces the include that activates this file. Commit both together for atomicity.

---

## Task 2: Include `climate.yaml` in the area config

**Files:**
- Modify: `packages/areas/ground-floor/living-room/config.yaml`

- [ ] **Step 1: Read the current file**

Inspect the top of the file — the domain-level include lines live at the top:

```bash
head -12 packages/areas/ground-floor/living-room/config.yaml
```

The existing top looks like this:

```yaml
---
automation: !include_dir_list automations
media_player: !include_dir_list media_players
light: !include_dir_list lights
cover:
  - platform: group
    name: ground_floor
    entities:
      - cover.living_room_main
      - cover.living_room_left
template: !include_dir_list templates
```

- [ ] **Step 2: Add the climate include**

Insert `climate: !include climate.yaml` on its own line, after the `template: !include_dir_list templates` line. The result should be:

```yaml
---
automation: !include_dir_list automations
media_player: !include_dir_list media_players
light: !include_dir_list lights
cover:
  - platform: group
    name: ground_floor
    entities:
      - cover.living_room_main
      - cover.living_room_left
template: !include_dir_list templates
climate: !include climate.yaml
```

Do not reorder existing lines — existing ordering is not alphabetical and matches other area packages' conventions.

- [ ] **Step 3: Lint the whole repo**

```bash
uv run pre-commit run --all-files
```

Expected: all hooks pass. yamllint should cleanly accept both files.

If yamllint complains about something unrelated in another file, do **not** fix unrelated issues — revert them and focus on the two files you introduced. Unrelated fixes belong in their own commits.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/ground-floor/living-room/climate.yaml \
        packages/areas/ground-floor/living-room/config.yaml
git commit -m "$(cat <<'EOF'
feat(living-room): add climate.living_room_floor_heating wrapper

Adds a climate_template entity that wraps climate.floor_heating, takes
current_temperature from sensor.living_room_hygro_temperature, and omits
hvac_action (the Bosch boiler's heating indicator is not reliable).

Requires the HACS hass-template-climate integration to be installed on
the HA instance.
EOF
)"
```

---

## Task 3: Push and trigger a reload on the live HA instance

**Files:** none

- [ ] **Step 1: Push the branch**

```bash
git push -u origin HEAD
```

HA auto-pulls from the current branch, so within a few seconds the new YAML is present on disk. It is **not** yet applied — YAML changes need a reload.

- [ ] **Step 2: Trigger the reload**

First, try a core-config reload (faster, no restart):

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/reload_all"
```

Expected: HTTP 200, body is a JSON array (often empty) of affected entities. Runs with `dangerouslyDisableSandbox: true`.

Climate platforms under `climate:` (legacy list form) typically do reload via `reload_all` on modern HA, but not all third-party platforms honour it. If after Task 4 the entity is missing, fall back to a full restart:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/restart"
```

- [ ] **Step 3: Tail the log for platform-setup errors**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/error_log" \
  | tail -60
```

Expected: no errors mentioning `climate_template`, `living_room_floor_heating`, or `living-room/climate.yaml`.

If you see `Platform error climate.climate_template: ...` → the HACS integration is not installed (Task 0A not complete) or its version does not accept one of the YAML keys. If it rejects `temp_step`, remove that line, re-lint, re-commit with `fix: drop temp_step — rejected by installed climate_template version`, and re-push. Do **not** invent replacement keys.

- [ ] **Step 4: No commit**

This task is pure deployment — nothing to commit.

---

## Task 4: Verify the entity exists and has the expected shape

**Files:** none

- [ ] **Step 1: Fetch the wrapper's state**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.living_room_floor_heating"
```

Expected: a JSON object with `entity_id: "climate.living_room_floor_heating"`, `state` equal to either `off` or `auto` (mirrors `climate.floor_heating`), and an `attributes` object.

If you get `404` or `entity_id: null` → entity did not register. Re-check Task 3 step 3 logs, and try a full HA restart if only `reload_all` was run.

- [ ] **Step 2: Assert `hvac_action` is absent**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.living_room_floor_heating" \
  | python3 -c "import sys, json; a=json.load(sys.stdin)['attributes']; \
print('FAIL: hvac_action present =', a['hvac_action']) if 'hvac_action' in a else print('OK: no hvac_action')"
```

Expected: `OK: no hvac_action`.

If you see `FAIL`, the `climate_template` integration is defaulting `hvac_action` even without a template. Open the HACS integration's source to confirm; if confirmed, the spec's assumption is wrong and needs revisiting — pause and report back to the user rather than hacking a workaround.

- [ ] **Step 3: Assert `current_temperature` tracks the zigbee sensor**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -X POST \
  -H "Content-Type: application/json" \
  "$HA_URL/api/template" \
  -d '{"template": "wrapper={{ state_attr(\"climate.living_room_floor_heating\", \"current_temperature\") }} | zigbee={{ states(\"sensor.living_room_hygro_temperature\") }}"}'
```

Expected: the two numbers match within one decimal place of rounding (e.g. `wrapper=23.9 | zigbee=23.88`). The zigbee sensor currently reports 23.88 °C; the Bosch shows 22.8 °C. If the wrapper reports 22.8, the template is binding to the wrong source.

- [ ] **Step 4: Assert target temperature and modes mirror the Bosch**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" -X POST \
  -H "Content-Type: application/json" \
  "$HA_URL/api/template" \
  -d '{"template": "target={{ state_attr(\"climate.living_room_floor_heating\", \"temperature\") }}|{{ state_attr(\"climate.floor_heating\", \"temperature\") }}  mode={{ states(\"climate.living_room_floor_heating\") }}|{{ states(\"climate.floor_heating\") }}  preset={{ state_attr(\"climate.living_room_floor_heating\", \"preset_mode\") }}|{{ state_attr(\"climate.floor_heating\", \"preset_mode\") }}"}'
```

Expected: each pair (wrapper value, Bosch value) is identical.

- [ ] **Step 5: No commit**

Verification only.

---

## Task 5: Functional test — `set_temperature` passthrough

**Files:** none

- [ ] **Step 1: Capture the current target temperature**

```bash
ORIG_TEMP=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.floor_heating" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['attributes']['temperature'])")
echo "Original target: $ORIG_TEMP"
```

Save the value — we must restore it.

- [ ] **Step 2: Set a test value on the wrapper**

Pick a value that is clearly different from the current one (e.g. 21.0 if the current is 22.5, or 23.5 if the current is 22.5):

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/climate/set_temperature" \
  -d '{"entity_id": "climate.living_room_floor_heating", "temperature": 23.5}'
```

Expected: HTTP 200.

- [ ] **Step 3: Assert the Bosch followed within 5 seconds**

```bash
sleep 5 && curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.floor_heating" \
  | python3 -c "import sys,json; t=json.load(sys.stdin)['attributes']['temperature']; \
print('OK' if abs(t-23.5)<0.01 else f'FAIL target={t}')"
```

Expected: `OK`.

- [ ] **Step 4: Restore the original target**

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/climate/set_temperature" \
  -d "{\"entity_id\": \"climate.living_room_floor_heating\", \"temperature\": $ORIG_TEMP}"
```

Confirm with a second state read that `climate.floor_heating.temperature` is back to `$ORIG_TEMP`.

- [ ] **Step 5: No commit**

---

## Task 6: Functional test — `set_hvac_mode` passthrough

**Files:** none

- [ ] **Step 1: Capture the current hvac_mode**

```bash
ORIG_MODE=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.floor_heating" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['state'])")
echo "Original mode: $ORIG_MODE"
```

- [ ] **Step 2: Flip the wrapper to `off`**

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/climate/set_hvac_mode" \
  -d '{"entity_id": "climate.living_room_floor_heating", "hvac_mode": "off"}'
```

- [ ] **Step 3: Assert the Bosch is now `off`**

```bash
sleep 5 && curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.floor_heating" \
  | python3 -c "import sys,json; s=json.load(sys.stdin)['state']; \
print('OK' if s=='off' else f'FAIL state={s}')"
```

- [ ] **Step 4: Restore the original mode**

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/services/climate/set_hvac_mode" \
  -d "{\"entity_id\": \"climate.living_room_floor_heating\", \"hvac_mode\": \"$ORIG_MODE\"}"
```

Confirm with a second read.

- [ ] **Step 5: No commit**

---

## Task 7: Functional test — availability when zigbee sensor fails

**Files:** none

- [ ] **Step 1: Confirm wrapper is currently available**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.living_room_floor_heating" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])"
```

Expected: `off` or `auto` (not `unavailable`).

- [ ] **Step 2: Force the zigbee sensor into an unavailable state**

Do **not** physically tamper with the device. Instead, temporarily override its state via the state API:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  "$HA_URL/api/states/sensor.living_room_hygro_temperature" \
  -d '{"state": "unavailable", "attributes": {"device_class": "temperature", "unit_of_measurement": "°C"}}'
```

Note: this override is temporary — the zigbee integration will overwrite it the next time the device reports. That usually happens within 1–2 minutes for this hygrometer.

- [ ] **Step 3: Assert the wrapper went unavailable within ~3 seconds**

```bash
sleep 3 && curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.living_room_floor_heating" \
  | python3 -c "import sys,json; s=json.load(sys.stdin)['state']; \
print('OK' if s=='unavailable' else f'FAIL state={s}')"
```

Expected: `OK`.

- [ ] **Step 4: Wait for the zigbee sensor to report again, or force-restore it**

Easiest: wait 2 minutes and re-check `sensor.living_room_hygro_temperature`. If it has not reported, trigger the integration to poll, or live with a short gap — the device will report on its own schedule and the wrapper will return to available automatically.

Confirm:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/states/climate.living_room_floor_heating" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])"
```

Expected: `off` or `auto`.

- [ ] **Step 5: No commit**

---

## Task 8: Document the wrapper in the living-room README

**Files:**
- Modify: `packages/areas/ground-floor/living-room/README.md`

- [ ] **Step 1: Read the README to find a sensible insertion point**

```bash
head -60 packages/areas/ground-floor/living-room/README.md
```

Look for an existing section that lists the package's entities or integrations. If no such section exists, add a new top-level section titled `## Climate` after the opening overview.

- [ ] **Step 2: Insert the documentation block**

Add the following Markdown under the chosen section. Do not duplicate information that already exists elsewhere in the README.

```markdown
### Floor heating wrapper — `climate.living_room_floor_heating`

Abstract climate entity that wraps the Bosch `climate.floor_heating` so
the living-room UI surfaces the zigbee-hygrometer temperature and does
not show the boiler's fabricated "heating" signal. Commands
(`set_temperature`, `set_hvac_mode`, `set_preset_mode`) are forwarded
1:1 to `climate.floor_heating`.

**Dependency:** requires the HACS custom integration
[`jcwillox/hass-template-climate`](https://github.com/jcwillox/hass-template-climate).
If this integration is removed, reloading YAML will fail with
`Platform not found: climate.climate_template`.

Design: [`docs/superpowers/specs/2026-04-19-living-room-floor-heating-wrapper-design.md`](../../../../docs/superpowers/specs/2026-04-19-living-room-floor-heating-wrapper-design.md).
```

- [ ] **Step 3: Lint**

```bash
uv run pre-commit run --all-files
```

Expected: all hooks pass.

- [ ] **Step 4: Commit**

```bash
git add packages/areas/ground-floor/living-room/README.md
git commit -m "docs(living-room): document floor-heating wrapper and its HACS dep"
```

- [ ] **Step 5: Push**

```bash
git push
```

---

## Task 9: Open a pull request

**Files:** none

- [ ] **Step 1: Create the PR**

```bash
gh pr create --title "feat(living-room): abstract climate wrapper over floor heating" --body "$(cat <<'EOF'
## Summary

- New entity `climate.living_room_floor_heating` wrapping `climate.floor_heating`.
- `current_temperature` sourced from `sensor.living_room_hygro_temperature` (zigbee Aqara hygrometer) rather than the Bosch boiler's supply-side value.
- `hvac_action` omitted — the underlying Bosch does not reliably report when it is heating, so surfacing a fake signal is worse than surfacing none.
- Commands (`set_temperature`, `set_hvac_mode`, `set_preset_mode`) forward 1:1 to the Bosch entity. Wrapper mirrors its `hvac_modes` (`off`, `auto`) and `preset_modes` (`none`, `away`).
- Availability gated on both the hygrometer and the Bosch being online.

Requires the HACS integration [`jcwillox/hass-template-climate`](https://github.com/jcwillox/hass-template-climate), installed out-of-band on the HA instance.

Spec: `docs/superpowers/specs/2026-04-19-living-room-floor-heating-wrapper-design.md`
Plan: `docs/superpowers/plans/2026-04-19-living-room-floor-heating-wrapper.md`

## Test plan

- [x] `uv run pre-commit run --all-files` clean
- [x] HA reload; no `climate_template` errors in `/api/error_log`
- [x] `climate.living_room_floor_heating` exists with no `hvac_action` attribute
- [x] `current_temperature` tracks `sensor.living_room_hygro_temperature`
- [x] `target_temperature` / `hvac_mode` / `preset_mode` mirror `climate.floor_heating`
- [x] `climate.set_temperature` on wrapper propagates to Bosch within 5 s
- [x] `climate.set_hvac_mode` on wrapper propagates to Bosch within 5 s
- [x] Forcing `sensor.living_room_hygro_temperature` to `unavailable` flips wrapper to unavailable
EOF
)"
```

- [ ] **Step 2: Capture the PR URL**

The `gh pr create` output includes the URL. Report it back to the user.

---

## Done

All tasks complete when:

- `climate.living_room_floor_heating` exists on the live HA instance, tracks the zigbee sensor for `current_temperature`, has no `hvac_action` attribute, and forwards control calls to `climate.floor_heating`.
- `packages/areas/ground-floor/living-room/README.md` documents the wrapper and its HACS dependency.
- PR is open and its test-plan checklist all green.
