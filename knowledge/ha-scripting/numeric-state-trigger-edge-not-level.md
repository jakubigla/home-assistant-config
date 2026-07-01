---
summary: numeric_state above/below fires only on the crossing — a value that stays past the threshold never re-triggers.
before_action:
  - About to trigger an automation on a sensor being above/below a threshold (temp, humidity, battery, lux)
  - About to gate a "do X while the value is past N" action on a numeric_state trigger
on_symptom:
  - "threshold automation stopped firing / went silently dead during a heat wave or sustained extreme"
  - "AC / fan / alert never auto-started even though the sensor was clearly past the threshold"
  - "numeric_state automation only fires some days, not when the value is already past the threshold"
  - "automation last_triggered is days stale but the condition looks true right now"
---

**`numeric_state` `above:`/`below:` is EDGE-triggered — fires only at the instant the value
crosses the threshold, never while it merely sits past it.** Once above, it won't fire again until
the value drops back to ≤threshold and re-crosses upward. The automation carries a hidden assumption
that the value cycles back across the line every day. When it doesn't — a heat wave where the room
never cools below the setpoint — no crossing happens, so it goes **silently dead exactly when
needed** (`bedroom_ac_cooldown_on`: room 27–31°C for 3+ days, never dipped below 25, last real fire
2026-06-26; fixed in `680167a`).

- **Aggravated by slow sensor cadence.** A once-per-hour sensor (Zigbee temp reported ~58 min
  apart) can land its only in-window reading between checks, so even a *genuine* crossing can miss
  a time-bounded window. Slow reporting + edge trigger compounds.

- **Fix: make "is it past the threshold NOW" a LEVEL check, not an edge.** Move the
  `above:`/`below:` test into a `numeric_state` **condition**, and drive the trigger off a
  re-evaluating source: a `time` trigger at the window start + a `time_pattern` re-check (e.g.
  `minutes: "/15"`). Keep the original `numeric_state` crossing trigger too, so a genuine
  mid-window rise still fires promptly.
  Now it fires whenever the value is past the line, not only when it just became so.

- Same trap applies to any threshold domain — humidity dehumidifier, battery-low alert, lux-driven
  lights. If the driven action should run *whenever* past the line (not just on the transition), you
  want a level check. Related: [[restart-mode-pulse-thrash]] (trigger mode/thrash),
  [[wait-template-state-on-entry-race]] (state-on-entry read).
