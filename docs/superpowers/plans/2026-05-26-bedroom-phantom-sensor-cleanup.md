# Bedroom Phantom Presence-Sensor Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove references to three gone-for-good bedroom presence sensors (`bedroom_walking_area_presence`, `presence_sensor_bedroom_jakub_side`, `presence_sensor_bedroom_sona_side`) while preserving every `bedroom_presence` reference (a whole-room sensor returning under that same id later), and delete the now-dead bed-movement nightlight automation.

**Architecture:** Pure deletion/trim of dead entity references in a Home Assistant YAML package. `bedroom_presence` references are intentionally left in place so the relevant automations auto-revive when the user re-adds the whole-room sensor. No logic redesign.

**Tech Stack:** Home Assistant YAML (`packages/areas/first-floor/bedroom/`). Verification via `uv run yamllint`, `grep`, push + `automation/reload`/`template/reload` + `error_log`. No unit-test framework — "tests" are lint, grep assertions, and observed reload behavior.

**Spec:** `docs/superpowers/specs/2026-05-26-bedroom-phantom-sensor-cleanup-design.md`

**Branch:** already on `chore/may-fixes` (feature branch). Never push to `main`.

---

## Conventions

- After any YAML change: `uv run yamllint <file>` must pass before commit. `just check` can't run locally (no `hass` binary) — config validity is checked post-push via reload + `error_log`.
- Leave **every** `binary_sensor.bedroom_presence` reference untouched. Only remove the three gone-for-good sensors. Do not substitute `bedroom_presence` with `bedroom_entrance_presence`.
- `curl`/`hass-cli` against HA assume env vars (`$HA_URL`, `$HA_TOKEN`); `curl` needs `dangerouslyDisableSandbox: true`.

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml` | bedroom bed-stripe presence lighting | Modify (drop `walking_area` in 3 spots) |
| `packages/areas/first-floor/bedroom/automations/bedroom_bed_presence_sleeping.yaml` | dead bed-movement nightlight | Delete |
| `packages/areas/first-floor/bedroom/README.md` | area docs | Modify (drop deleted automation + dead deps, soften gotcha, fix narrative) |

Not touched (intentional): `bedroom_vacancy_timeout.yaml`, `templates/sensors/bedroom_humidifier_target_speed.yaml`, `bootstrap/templates/binary_sensors/home_ready_to_arm.yaml`.

---

## Task 1: Trim `walking_area` from the bedroom presence automation

**Files:**
- Modify: `packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml`

The file references `binary_sensor.bedroom_walking_area_presence` in two trigger lists and one OR condition. Remove only those lines. Keep `bedroom_entrance_presence` and `bedroom_presence` everywhere they appear.

- [ ] **Step 1: Drop `walking_area` from trigger list 1 (off→on)**

Change:

```yaml
  - platform: state
    entity_id:
      - binary_sensor.bedroom_entrance_presence
      - binary_sensor.bedroom_presence
      - binary_sensor.bedroom_walking_area_presence
    from: "off"
    to: "on"
```

to:

```yaml
  - platform: state
    entity_id:
      - binary_sensor.bedroom_entrance_presence
      - binary_sensor.bedroom_presence
    from: "off"
    to: "on"
```

- [ ] **Step 2: Drop `walking_area` from trigger list 2 (on→off, for 5s)**

Change:

```yaml
  - platform: state
    entity_id:
      - binary_sensor.bedroom_entrance_presence
      - binary_sensor.bedroom_presence
      - binary_sensor.bedroom_walking_area_presence
    from: "on"
    to: "off"
    for:
      hours: 0
      minutes: 0
      seconds: 5
```

to:

```yaml
  - platform: state
    entity_id:
      - binary_sensor.bedroom_entrance_presence
      - binary_sensor.bedroom_presence
    from: "on"
    to: "off"
    for:
      hours: 0
      minutes: 0
      seconds: 5
```

- [ ] **Step 3: Drop the `walking_area` arm from the daytime OR condition**

Change:

```yaml
          - condition: or
            conditions:
              - condition: state
                entity_id: binary_sensor.bedroom_entrance_presence
                state: "on"
              - condition: state
                entity_id: binary_sensor.bedroom_walking_area_presence
                state: "on"
```

to:

```yaml
          - condition: or
            conditions:
              - condition: state
                entity_id: binary_sensor.bedroom_entrance_presence
                state: "on"
```

Leave the off-branch (lines referencing `bedroom_presence` + `bedroom_entrance_presence` + `ensuite_bathroom_occupancy`) unchanged.

- [ ] **Step 4: Verify no `walking_area` remains in the file**

Run: `grep -n walking_area packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml`
Expected: no output.

- [ ] **Step 5: Verify `bedroom_presence` is still referenced (must NOT have been removed)**

Run: `grep -c 'binary_sensor.bedroom_presence' packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml`
Expected: `3` (two trigger lists + the off-branch condition).

- [ ] **Step 6: Lint**

Run: `uv run yamllint packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml`
Expected: no output (pass).

- [ ] **Step 7: Commit**

```bash
git add packages/areas/first-floor/bedroom/automations/bedroom_presence.yaml
git commit -m "fix(bedroom): drop gone-for-good walking_area presence ref"
```

---

## Task 2: Delete the dead bed-movement nightlight automation

**Files:**
- Delete: `packages/areas/first-floor/bedroom/automations/bedroom_bed_presence_sleeping.yaml`

This automation triggers and conditions only on `presence_sensor_bedroom_jakub_side`, `presence_sensor_bedroom_sona_side`, and `bedroom_walking_area_presence` — all gone for good. The sleeping-time bed stripe is already handled by `bedroom_presence.yaml`'s sleeping-time branch.

- [ ] **Step 1: Delete the file**

```bash
git rm packages/areas/first-floor/bedroom/automations/bedroom_bed_presence_sleeping.yaml
```

- [ ] **Step 2: Verify the gone-for-good bed-side sensors are no longer referenced anywhere**

Run: `grep -rn 'presence_sensor_bedroom_jakub_side\|presence_sensor_bedroom_sona_side' packages/`
Expected: no output.

- [ ] **Step 3: Verify no `walking_area` remains in any automation/template (README handled in Task 3)**

Run: `grep -rn 'bedroom_walking_area_presence' packages/ --include='*.yaml'`
Expected: no output. (Only `.yaml` is checked here; the README — a `.md` file under `packages/areas/...` — still mentions these and is cleaned in Task 3.)

- [ ] **Step 4: Commit**

```bash
git commit -m "fix(bedroom): delete dead bed-movement nightlight (sensors gone for good)"
```

---

## Task 3: Update the bedroom README

**Files:**
- Modify: `packages/areas/first-floor/bedroom/README.md`

Four edits: remove the nightlight narrative paragraph, drop the deleted automation from the file index, remove the three dead dependency lines, and soften the phantom gotcha.

- [ ] **Step 1: Remove the bed-movement nightlight narrative paragraph**

Delete this paragraph (in the Lighting section):

```markdown
During sleeping time, any movement detected by the bed-side or walking-area presence sensors triggers a minimal nightlight: the bed stripe at 1% with a warm tint (RGB 249, 255, 194). It stays on while presence is detected and turns off 3 seconds after the last sensor clears (30-second timeout if sensors never clear).
```

(The preceding paragraph already documents the sleeping-time 20% bed stripe via `bedroom_presence.yaml`, so no replacement is needed.)

- [ ] **Step 2: Remove the deleted automation from the File Index table**

Delete this row:

```markdown
| `automations/bedroom_bed_presence_sleeping.yaml` | Nightlight on bed movement during sleeping time |
```

- [ ] **Step 3: Update the Dependencies list — drop the three gone-for-good sensors, relabel `bedroom_presence`**

Replace these four lines:

```markdown
- `binary_sensor.bedroom_entrance_presence` -- entrance presence sensor (FP2 zone; the only real room-level bedroom presence sensor)
- `binary_sensor.bedroom_presence` -- ⚠️ **phantom** (referenced but not defined live; see Gotchas)
- `binary_sensor.bedroom_walking_area_presence` -- ⚠️ **phantom** (referenced but not defined live)
- `binary_sensor.presence_sensor_bedroom_jakub_side` -- ⚠️ **phantom** (referenced but not defined live)
- `binary_sensor.presence_sensor_bedroom_sona_side` -- ⚠️ **phantom** (referenced but not defined live)
```

with:

```markdown
- `binary_sensor.bedroom_entrance_presence` -- FP2 whole-room presence sensor (currently the live bedroom presence source)
- `binary_sensor.bedroom_presence` -- whole-room presence; **temporarily absent**, pending re-install under this same entity id (refs intentionally kept so the presence/vacancy/humidifier logic auto-revives)
```

- [ ] **Step 4: Soften the phantom gotcha**

Replace the gotcha block:

```markdown
- **⚠️ Phantom bedroom presence sensors (needs cleanup)**: `binary_sensor.bedroom_presence`, `binary_sensor.bedroom_walking_area_presence`, `binary_sensor.presence_sensor_bedroom_jakub_side`, and `binary_sensor.presence_sensor_bedroom_sona_side` are referenced by `bedroom_presence.yaml`, `bedroom_bed_presence_sleeping.yaml`, the bedroom vacancy timeout, and the humidifier target-speed sensor -- but **do not exist on the live instance** (likely lost in an FP2 zone reconfig). As a result the bedroom presence automation, the bed-movement nightlight, and the bedroom vacancy timeout do not fire. Only `binary_sensor.bedroom_entrance_presence` and `binary_sensor.bedroom_wardrobe_occupancy` are real bedroom occupancy sensors. This is unresolved tech debt, tracked separately from the ensuite rebuild.
```

with:

```markdown
- **`bedroom_presence` is temporarily absent**: the whole-room presence sensor was lost in an FP2 reconfig and will be re-added under the same entity id `binary_sensor.bedroom_presence`. Its references are kept on purpose, so the bedroom presence off-branch, the vacancy timeout, and the humidifier occupied fan-cap all revive automatically once it returns. While absent, those three behaviours are dormant (vacancy never fires; humidifier uses the vacant fan caps). The gone-for-good zoned/bed-side sensors (`bedroom_walking_area_presence`, `presence_sensor_bedroom_jakub_side`, `presence_sensor_bedroom_sona_side`) have been removed from the config.
```

- [ ] **Step 5: Verify README no longer references the three gone-for-good sensors**

Run: `grep -n 'walking_area_presence\|presence_sensor_bedroom_jakub_side\|presence_sensor_bedroom_sona_side\|bed_presence_sleeping' packages/areas/first-floor/bedroom/README.md`
Expected: no output.

- [ ] **Step 6: Repo-wide grep — zero references to the three gone-for-good sensors and the deleted file**

Run: `grep -rn 'bedroom_walking_area_presence\|presence_sensor_bedroom_jakub_side\|presence_sensor_bedroom_sona_side\|bedroom_bed_presence_sleeping' packages/`
Expected: no output.

- [ ] **Step 7: Confirm `bedroom_presence` references still intact (intentional)**

Run: `grep -rln 'binary_sensor.bedroom_presence' packages/`
Expected: lists `bedroom_presence.yaml`, `bedroom_vacancy_timeout.yaml`, `bedroom_humidifier_target_speed.yaml`, and the `README.md`.

- [ ] **Step 8: Commit**

```bash
git add packages/areas/first-floor/bedroom/README.md
git commit -m "docs(bedroom): drop gone-for-good sensors, note bedroom_presence is returning"
```

---

## Task 4: Push, reload, verify

**Files:** none (deploy + verify)

- [ ] **Step 1: Push**

```bash
git push
```

- [ ] **Step 2: Wait for HA pull (3-6 min), then reload automations + templates**

```bash
curl -s -o /dev/null -w "automation/reload -> %{http_code}\n" -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/automation/reload"
curl -s -o /dev/null -w "template/reload -> %{http_code}\n" -X POST -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/services/template/reload"
```
Expected: both `200`.

- [ ] **Step 3: Confirm the deleted automation entity is gone**

```bash
uv run hass-cli template <(echo "{{ states('automation.bedroom_bed_presence_during_sleeping_time') }}")
```
Expected: `unknown` or `unavailable` (entity removed; the friendly automation id no longer loads). If it still reports `on`, the pull hasn't landed — wait and re-reload.

- [ ] **Step 4: Check error log for bedroom errors**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/error_log" | grep -iE 'bedroom|walking_area|jakub_side|sona_side' | tail -20
```
Expected: no new errors (no "entity not found" / template errors for the removed sensors).

- [ ] **Step 5: Confirm bedroom presence lighting still loads and is driven by the live sensor**

```bash
uv run hass-cli template <(cat <<'EOF'
bedroom_presence_auto={{ states('automation.bedroom_presence') }}
entrance={{ states('binary_sensor.bedroom_entrance_presence') }}
bedroom_presence_phantom={{ states('binary_sensor.bedroom_presence') }}
EOF
)
```
Expected: `bedroom_presence_auto` = `on` (automation loaded), `entrance` resolves to `on`/`off`, `bedroom_presence` still `unknown` (absent, as expected).

---

## Done when

- The three gone-for-good sensors and the deleted automation appear nowhere under `packages/` (Task 3 Step 6 grep empty).
- All `bedroom_presence` references preserved (Task 3 Step 7).
- Pushed, reloaded, error log clean, `bedroom_presence.yaml` still loads.
