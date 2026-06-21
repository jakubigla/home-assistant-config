# Lawn Spurious Early-Close Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `garden_lawn_irrigation` advancing to the next zone when the Tuya controller emits a bogus `closed` seconds after opening a zone, by re-asserting the open until a plausible close (the auto-off close) is seen.

**Architecture:** Extract a `mode: single` helper script `garden_open_zone_until_real_close(zone)` that opens a valve, waits for `closed`, and re-opens if the close arrived sooner than `MIN_OPEN_S`. `garden_lawn_irrigation` calls the helper once per zone inside its existing cycle loop. Auto-off still owns duration; the helper only reopens.

**Tech Stack:** Home Assistant YAML scripts (package-based config under `packages/areas/outdoor/garden/scripts/`). Validation via `just check` + live automation trace. No pytest — HA config has no unit-test harness.

## Global Constraints

- `MIN_OPEN_S = 10` (seconds) — above the ~5 s phantom close, below Testing mode's smallest legit per-zone open (15 s).
- `MAX_ATTEMPTS = 3` — 1 normal open + up to 2 re-asserts; bounded so a dead channel cannot hang the run.
- Helper is `mode: single`.
- Auto-off (`garden-valve-auto-off`) remains the duration owner — helper never sets a duration.
- Touch ONLY `garden_lawn_irrigation`. Do NOT modify `garden_ondemand_lawn` (fixed-delay, owns own close) or `garden_drip_irrigation` (single-pass).
- Follow the existing script-file convention: one top-level script key per file, `alias`/`description`/`icon`/`mode`/`sequence`.
- After push: reload HA core config + check logs (errors stay invisible until reload). Never push to `main` — current branch is `chore/june-features`.

---

### Task 1: Create the helper script `garden_open_zone_until_real_close`

**Files:**
- Create: `packages/areas/outdoor/garden/scripts/garden_open_zone_until_real_close.yaml`

**Interfaces:**
- Consumes: a `zone` variable (a `valve.lawn_sprinkler_zone_*` entity_id string), passed by the caller's `action: script.garden_open_zone_until_real_close` with `data: { zone: ... }`.
- Produces: script entity `script.garden_open_zone_until_real_close`. Blocking when called directly (caller awaits completion before next zone). Leaves the zone valve closed on return (real close by auto-off, or idempotent safety close on the timeout/give-up path).

- [ ] **Step 1: Write the helper script file**

Create `packages/areas/outdoor/garden/scripts/garden_open_zone_until_real_close.yaml`:

```yaml
---
garden_open_zone_until_real_close:
  alias: Garden Open Zone Until Real Close
  description: >
    Open one lawn zone valve and wait for it to close, ignoring a spurious
    device-side close. The Tuya "Sprinker" controller intermittently emits a
    bogus `closed` a few seconds after the open command (observed 2026-06-20:
    zone 1 reported closed 5.4 s after opening, with no HA close call). A plain
    wait_for_trigger would accept that and advance, under-watering the zone.
    This helper re-asserts the open if `closed` arrives sooner than MIN_OPEN_S
    (10 s) — below the smallest legit open (Testing 15 s), above the ~5 s
    phantom — for up to MAX_ATTEMPTS tries, then gives up so the caller can
    advance. Auto-off (garden-valve-auto-off) still owns the real duration; this
    only reopens. Called directly (blocking) per zone by garden_lawn_irrigation.
  icon: mdi:sprinkler
  mode: single
  fields:
    zone:
      description: The lawn zone valve entity_id to open and watch.
      example: valve.lawn_sprinkler_zone_1
  variables:
    min_open_s: 10
    max_attempts: 3
  sequence:
    - repeat:
        sequence:
          - variables:
              opened_at: "{{ now() | as_timestamp }}"
          - action: valve.open_valve
            target:
              entity_id: "{{ zone }}"
          - wait_for_trigger:
              - platform: state
                entity_id: "{{ zone }}"
                to: "closed"
            timeout:
              minutes: 90
          - variables:
              held_s: "{{ (now() | as_timestamp) - opened_at }}"
          - if:
              - "{{ held_s | float(0) < min_open_s and repeat.index < max_attempts }}"
            then:
              - action: logbook.log
                data:
                  name: Garden Lawn Spurious Close
                  message: >
                    {{ zone }} closed after {{ held_s | round(1) }}s
                    (< {{ min_open_s }}s) on attempt {{ repeat.index }} —
                    likely a spurious device-side close, re-asserting open.
                  entity_id: "{{ zone }}"
        until:
          - >
            {{ held_s | float(0) >= min_open_s
               or repeat.index >= max_attempts }}
    # Idempotent safety close: on the wait timeout path or after giving up, the
    # valve may still be open. A close on an already-closed valve is a no-op.
    - action: valve.close_valve
      target:
        entity_id: "{{ zone }}"
```

- [ ] **Step 2: Lint the new file (YAML only — fast)**

Run: `uv run yamllint packages/areas/outdoor/garden/scripts/garden_open_zone_until_real_close.yaml`
Expected: no errors (exit 0; empty output).

- [ ] **Step 3: Commit**

```bash
git add packages/areas/outdoor/garden/scripts/garden_open_zone_until_real_close.yaml
git commit -m "feat(garden): helper script reopens lawn zone on spurious early close"
```

---

### Task 2: Refactor `garden_lawn_irrigation` to call the helper per zone

**Files:**
- Modify: `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml` (the `repeat` cycle body, currently lines ~52–100)

**Interfaces:**
- Consumes: `script.garden_open_zone_until_real_close` from Task 1, called via `action:` with `data: { zone: ... }` (blocking).
- Produces: unchanged script entity `script.garden_lawn_irrigation` — same external behaviour (zones 1→2→3, `cycles` times, `soak_minutes` between cycles), now spurious-close-resilient.

- [ ] **Step 1: Replace the per-zone open/wait/close blocks inside the cycle repeat**

In `packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml`, the `repeat: count: "{{ cycles }}"` `sequence:` currently contains three inlined blocks (zone 1, zone 2, zone 3), each:
`valve.open_valve → wait_for_trigger(closed, 90min) → valve.close_valve → delay 5s`, then the soak `if`.

Replace the whole inner `sequence:` (from the first `valve.open_valve` through the last `valve.close_valve` for zone 3, keeping the trailing soak `if` block) with:

```yaml
        sequence:
          - action: script.garden_open_zone_until_real_close
            data:
              zone: valve.lawn_sprinkler_zone_1
          - delay:
              seconds: 5
          - action: script.garden_open_zone_until_real_close
            data:
              zone: valve.lawn_sprinkler_zone_2
          - delay:
              seconds: 5
          - action: script.garden_open_zone_until_real_close
            data:
              zone: valve.lawn_sprinkler_zone_3
          # Soak pause between cycles, skipped after the final cycle.
          - if:
              - "{{ repeat.index < cycles }}"
            then:
              - delay:
                  minutes: "{{ soak_minutes }}"
```

Leave everything above the `repeat:` unchanged (offline abort, no-watering abort, `cycles`/`soak_minutes` variables). The `delay: seconds: 5` between zones and the soak `if` are preserved.

- [ ] **Step 2: Update the script `description` to mention the resilient call**

Change the `description:` so it no longer implies a bare open/wait. Replace the existing description block with:

```yaml
  description: >
    Cycle & soak: runs lawn zones 1→2→3 sequentially, repeated
    `cycle_count` times (from the profile) with a `soak_minutes` pause
    between cycles. Each zone is opened via
    script.garden_open_zone_until_real_close, which re-asserts the open if the
    controller emits a spurious early close. Each valve open is closed by the
    auto-off automation, which divides the per-zone duration by cycle_count so
    total water per zone equals the profile's lawn_durations.
```

- [ ] **Step 3: Lint both scripts**

Run: `uv run yamllint packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml packages/areas/outdoor/garden/scripts/garden_open_zone_until_real_close.yaml`
Expected: no errors (exit 0).

- [ ] **Step 4: Full HA config check**

Run: `just check`
Expected: config valid, no errors referencing either script.

- [ ] **Step 5: Commit**

```bash
git add packages/areas/outdoor/garden/scripts/garden_lawn_irrigation.yaml
git commit -m "refactor(garden): lawn irrigation calls spurious-close-guarded zone helper"
```

---

### Task 3: Deploy + verify live

**Files:** none (deploy + verify only).

- [ ] **Step 1: Push the branch**

```bash
git push
```
Expected: branch `chore/june-features` updated on remote.

- [ ] **Step 2: Reload HA + check logs**

Reload HA core config via MCP/API (`homeassistant.reload_core_config`), then check the log for errors. Reload the scripts so the new helper registers (a new script file needs the scripts reloaded / config reload).
Expected: no error mentioning `garden_open_zone_until_real_close` or `garden_lawn_irrigation`; `script.garden_open_zone_until_real_close` exists in the state machine.

- [ ] **Step 3: Confirm helper entity exists**

Query live HA for `script.garden_open_zone_until_real_close`.
Expected: state present (off/idle), not missing.

- [ ] **Step 4: Functional smoke test (manual close simulation)**

With the controller online, call `script.garden_open_zone_until_real_close` with `zone: valve.lawn_sprinkler_zone_1`, then within ~5 s manually `valve.close_valve` zone 1 to simulate the phantom close. Watch the logbook.
Expected: a "Garden Lawn Spurious Close" log line for zone 1, and zone 1 re-opens (re-assert). Then close it again after >10 s (or let auto-off close it) — the helper returns. Confirm it does NOT loop more than `MAX_ATTEMPTS` times.

- [ ] **Step 5: Confirm next scheduled run waters all zones fully**

After the next 04:00 run (or trigger `garden_lawn_irrigation` manually if in season + not skipped), pull valve history for zones 1/2/3. Expected: each zone open lasts its full profile duration (e.g. 900 s for zone 1 in Standard/Smart-June); any bounce shows a re-open + spurious-close log rather than a 5 s zone followed by the next zone.

---

## Self-Review

**Spec coverage:**
- Helper script with MIN_OPEN_S=10 / MAX_ATTEMPTS=3 / mode:single → Task 1 ✓
- `repeat.until` with `repeat.index` + per-iteration `held_s` → Task 1 Step 1 ✓
- Idempotent safety close on give-up/timeout → Task 1 Step 1 (trailing `valve.close_valve`) ✓
- Caller swaps 3 inline blocks for 3 helper calls, soak + 5 s delays + aborts unchanged → Task 2 ✓
- Scope: lawn only, on-demand/drip untouched → Global Constraints + Task 2 (only one file modified) ✓
- Auto-off still owns duration → helper never sets duration; verified Task 3 Step 5 ✓
- Verify via just check + live trace + Testing-mode/manual sim → Task 2 Step 4, Task 3 ✓

**Placeholder scan:** none — all YAML is concrete; the one `...`-free helper body is complete.

**Type consistency:** caller passes `data: { zone: ... }`; helper declares `fields: zone` and uses `{{ zone }}` throughout. Script id `garden_open_zone_until_real_close` consistent across both files and all references. `min_open_s`/`max_attempts`/`opened_at`/`held_s` variable names consistent within Task 1.
