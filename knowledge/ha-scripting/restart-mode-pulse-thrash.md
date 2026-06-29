---
summary: mode restart + flappy triggers thrashes a fixed pulse — re-trips abort the delay mid-run. Use mode single + for:.
before_action:
  - About to drive a fixed-duration light/output pulse (turn on, delay, turn off) from an automation
  - About to put mode restart on an automation with multiple or motion/occupancy triggers
  - About to debounce a pulse that flickers on every re-trigger
on_symptom:
  - "a light pulses on/off/on/off every few seconds in bursts instead of one clean pulse"
  - "a 5s nightlight pulse flickers while still in bed / rolling / two sensors flapping"
  - "automation fires many times in seconds, each abort + re-command visible as flicker"
---

# restart-mode aborts a fixed-duration pulse on every re-trigger

- **`mode: restart` on a pulse automation (turn on → `delay` → turn off) restarts mid-`delay` on
  every re-trip, killing the in-flight run and re-commanding the light.** A flappy/multi trigger
  (two bedside motion sensors, mmWave) fires repeatedly within the pulse window → on/off/on/off
  thrash, not one pulse. (`bedroom_sleep_nightlight` on `light.bed_stripe`: history showed 5 on/off
  cycles in 28 s while rolling in bed — restart aborted each 5 s pulse, off fired early, next trip
  re-on'd.) A `light.bed_stripe` `state: off` entry condition does NOT save you: restart aborts the
  running instance *before* re-evaluating conditions.
- **Fix: `mode: single` so the first trip owns one clean pulse and re-trips are dropped while it
  runs; add `for: "00:00:02"` on each motion trigger to swallow sub-second flap.** Pair with
  `max_exceeded: silent` to keep the log quiet.
- **A re-trigger that SHOULD extend a hold wants restart, not single — keep the two legs separate.**
  Split outbound (one fixed pulse → `single`) from return/hold (re-fire re-extends the wait →
  `restart`). `bedroom_sleep_nightlight` was split into `_outbound` (single) and `_return` (restart)
  for exactly this — one automation can't be both.
- Add `transition: 1` to the on/off at 1 % brightness — a hard snap at night reads as flicker even
  without thrash.
