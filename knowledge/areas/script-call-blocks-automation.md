---
summary: Calling a script as an automation action blocks until it finishes — use script.turn_on to fire-and-forget.
before_action:
  - About to call a long-running script from an automation and run steps after it
  - About to clear a flag or set state after triggering an irrigation/sequence script
on_symptom:
  - "automation stuck at current=1 for the whole duration of a script it called"
  - "post-script step (clearing an input_boolean, notifying) only runs after the long run ends"
---

# Script call blocks the calling automation

## Gotchas

- **`- action: script.xxx` (script-as-action) blocks until that script returns.** For a long
  sequence (e.g. the ~55 min `garden_lawn_irrigation` zone run) the calling automation sits at
  `current: 1` the entire time, and every step *after* the script call is deferred until the run
  completes. A post-run `input_boolean.turn_off` (disarm flag) won't fire until the watering ends.
- **Fire-and-forget:** call `action: script.turn_on` targeting the script `entity_id` instead — it
  starts the script and returns immediately, so the automation finishes (and any cleanup/flag-clear
  runs) at trigger time.
- **Order cleanup before the call when it must happen at fire time.** Even with `script.turn_on`,
  put the disarm/flag step before the script start if you want it guaranteed regardless. See the
  garden one-off run automation.
