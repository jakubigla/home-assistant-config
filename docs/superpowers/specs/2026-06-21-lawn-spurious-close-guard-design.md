# Lawn irrigation — spurious early-close guard

**Date:** 2026-06-21
**Status:** Approved

## Problem

On 2026-06-20 04:00 local, the lawn run *appeared* to start on zone 2. It did
not: `garden_lawn_irrigation` opened zone 1 first as always, but the Tuya
"Sprinker" controller emitted a bogus `closed` ~5.4 s after the open command
(no Home Assistant automation logged a close — auto-off computes 900 s for that
zone, proven by cycle 2 running the full 15 min). The script's
`wait_for_trigger: to: "closed"` accepted that spurious close and advanced to
zone 2. Net effect: zone 1 got ~5 s of water in cycle 1 instead of 15 min.

The schedule, durations, and zone order were all correct. The fault is a
device-side phantom close racing the real auto-off close.

See knowledge leaf `tuya-local-sprinkler-zombie` for the controller's history
of flaky multi-channel behaviour.

## Goal

Make `garden_lawn_irrigation` ignore a `closed` that arrives implausibly soon
after opening a zone, re-assert the open, and resume waiting for the real close
(the auto-off at the profile duration) — bounded so a genuinely dead channel
cannot hang the run.

## Design

Extract a reusable helper script `garden_open_zone_until_real_close` and call it
once per zone from `garden_lawn_irrigation` (replacing the three inlined
open/wait/close blocks).

### Helper: `garden_open_zone_until_real_close`

- **Input:** `zone` (a `valve.lawn_sprinkler_zone_*` entity_id), passed via the
  direct `action: script.garden_open_zone_until_real_close` call's `variables`.
- **Blocking is intended.** A direct (non-`turn_on`) script call blocks until it
  returns — exactly what the lawn sequence needs so the next zone only starts
  after this one finishes (the inverse of the `script-call-blocks-automation`
  gotcha, where blocking was unwanted).
- **`mode: single`** — never two helpers on the same zone at once.

Sequence:

```
MIN_OPEN_S  = 10     # below smallest legit open (Testing 15s), above echo (~5s)
MAX_ATTEMPTS = 3     # 1 normal open + up to 2 re-asserts

repeat (count = MAX_ATTEMPTS):
  - record opened_at = now() | as_timestamp
  - valve.open_valve  zone
  - wait_for_trigger: zone -> "closed", timeout 90 min   # real close = auto-off
  - if (now()|as_timestamp - opened_at) >= MIN_OPEN_S:
        # real close (or wait timed out — treat as done either way)
        break out of repeat
  - else:
        logbook.log: spurious early close on {zone}, re-asserting
        (loop continues -> reopens)
# idempotent safety close in case we exit on the timeout path with valve open
- valve.close_valve  zone
```

- **Mechanism: `repeat.until`** (avoids a cross-iteration mutable flag). Each
  iteration captures `opened_at` in a per-iteration `variables` block, opens,
  waits, then the `until:` condition ends the loop when either a real close was
  seen *or* attempts are exhausted:

  ```yaml
  - repeat:
      sequence:
        - variables:
            opened_at: "{{ now() | as_timestamp }}"
        - action: valve.open_valve
          target: { entity_id: "{{ zone }}" }
        - wait_for_trigger:
            - platform: state
              entity_id: "{{ zone }}"
              to: "closed"
          timeout: { minutes: 90 }
        - variables:
            held_s: "{{ (now() | as_timestamp) - opened_at }}"
        - if: "{{ held_s < MIN_OPEN_S }}"
          then:
            - action: logbook.log
              data: { name: Garden Lawn Spurious Close, ... }
      until:
        - >
          {{ held_s | float(0) >= MIN_OPEN_S
             or repeat.index >= MAX_ATTEMPTS }}
  ```

  `repeat.index` is the native attempt counter (1-based). `held_s` is read in
  the `until` from the iteration's `variables` scope. A real close (held ≥ 10 s)
  ends the loop immediately; a phantom (held < 10 s) re-iterates up to
  `MAX_ATTEMPTS`, then gives up and lets the caller advance.
- On exhausting attempts without a real close (dead channel): log it and return
  so the caller advances to the next zone — the run is not hung. The max-open
  watchdog and offline watchdog remain the backstops for a truly stuck valve.

### Threshold rationale

| Mode      | per-zone single open | vs MIN_OPEN_S=10s |
|-----------|----------------------|-------------------|
| Testing   | 0.5min×60 / 2cyc = **15 s** | above ✓ (not flagged) |
| Eco/Std   | 30min×60 / 2cyc = 900 s | well above ✓ |
| Intensive | 35min×60 / 2cyc = 1050 s | well above ✓ |
| Seasonal  | ≥15min, 1 cyc | well above ✓ |
| spurious echo | ~5 s | **below → flagged & re-asserted** |

10 s sits in the only safe gap: above the ~5 s phantom, below Testing's 15 s.

### Caller change: `garden_lawn_irrigation`

Inside the existing `repeat (cycles)` loop, replace the three
`open → wait_for_trigger → close → delay 5s` blocks with three calls:

```yaml
- action: script.garden_open_zone_until_real_close
  data: { zone: valve.lawn_sprinkler_zone_1 }
- delay: { seconds: 5 }
- action: script.garden_open_zone_until_real_close
  data: { zone: valve.lawn_sprinkler_zone_2 }
- delay: { seconds: 5 }
- action: script.garden_open_zone_until_real_close
  data: { zone: valve.lawn_sprinkler_zone_3 }
```

The `delay: 5s` between zones and the soak block stay unchanged. The offline
abort, no-watering abort, and cycle/soak variables at the top stay unchanged.

## Scope / non-goals

- **Only `garden_lawn_irrigation`.** `garden_ondemand_lawn` uses a fixed `delay`
  and owns its own close (no `wait_for_trigger`), so it cannot mis-advance —
  out of scope. `garden_drip_irrigation` is single-pass — out of scope.
- Auto-off still owns the duration; the helper only reopens, never sets a
  duration. Re-asserting open re-triggers `garden_valve_auto_off`, which re-arms
  the correct profile-driven close. (Acceptable: a re-assert resets the
  auto-off timer, so a zone that bounced once still gets a full duration from
  the re-open — slightly more total water than nominal on the rare bounce, which
  is the desired self-heal.)
- No new helper entities beyond the one script. No `input_*` added — threshold
  and attempt cap are literals in the helper.

## Verify

- `just check` (HA config check) parses both scripts.
- After push + reload: trace `garden_lawn_irrigation`, confirm it calls the
  helper per zone.
- Functional proof via Testing mode (15 s opens): each zone should open ~15 s
  and NOT be flagged spurious (15 ≥ 10). Then optionally simulate by closing a
  valve manually <10 s after it opens and confirm the helper re-asserts.
- Watch the next real 04:00 run's valve history: each zone open should last its
  full profile duration; any bounce should show a re-open in the logbook with
  the spurious-close log line.
