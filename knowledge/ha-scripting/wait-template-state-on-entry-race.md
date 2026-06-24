---
summary: wait_template checks state on entry — after an async command it sees the OLD state and returns instantly, not waiting.
before_action:
  - About to wait_template for a state right after a service call that changes that entity
  - About to use a templated entity_id in a state-wait (so you can't use wait_for_trigger)
  - About to write a re-assert / hold loop around a valve/switch/cover open
on_symptom:
  - "a scheduled run works when triggered manually but fails on its own / held duration is ~0s"
  - "wait_template completed instantly with no actual wait; a retry loop burned in milliseconds"
  - "valve/switch flaps open then closed and the script gives up in under a second"
---

# wait_template race: it checks state on ENTRY, not for an edge

- **`wait_template` evaluates its condition the instant it is reached and returns immediately if
  already true — it is NOT an edge/transition wait.** After a service call that mutates the entity
  (`valve.open_valve`, `light.turn_on`, …) the command is async: the entity still reports its OLD
  state when the action returns and for ~300–600 ms after (the device round-trips). So
  `wait_template: "{{ is_state(zone,'closed') }}"` placed right after `open_valve` completes in
  ~0.05 s on the pre-existing `closed`, never actually waiting. (Bit
  `garden_open_zone_until_real_close`: `held_s` was ~0 every attempt, all 3 retries fired in
  <200 ms, the script gave up before the valve opened — every scheduled lawn run after 2026-06-21
  watered nothing.)
- **Wait for the NEW state to APPEAR, not for the state you're leaving.** The leaving state is still
  present until the command lands, so waiting on it is a no-op. Fix pattern: after the command,
  `wait_template` for the target post-command state (`is_state(zone,'open')`) with a short timeout
  to confirm it landed, stamp your timer THEN, and only after that wait for the eventual return
  state (`'closed'`). A close arriving sooner than the floor *after a confirmed open* is a genuine
  early close worth re-asserting.
- **The tell: "works when I run it manually, fails when it runs itself."** The manual/on-demand path
  (`garden_ondemand_lawn`) uses a fixed `delay`, not a state-wait, so it never hits this race; the
  scheduled path used the racey wait. Same device, same `open_valve` — the difference is the wait,
  not the hardware. Don't chase a phantom device fault (see [[irrigation-run-cadence-gates]]).
- **`wait_for_trigger` is edge-based and race-free, but its `entity_id` can't be templated**
  (validated as a real entity at config load — `{{ zone }}` → None fails; see
  [[script-template-validation]]). That constraint is exactly why a templated-zone helper reaches
  for `wait_template` and inherits this trap. If the entity is static, prefer `wait_for_trigger`.
