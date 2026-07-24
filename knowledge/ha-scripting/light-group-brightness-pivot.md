---
summary: A light group's brightness is the avg of ON members only — a >=254 "at full" pivot misfires if a member is offline.
before_action:
  - About to branch automation logic on a light group's brightness attribute
  - About to write a toggle that treats "already at full" one way and "dimmed" another
on_symptom:
  - "pressing off on a light switch makes the light brighter instead of turning off"
  - "brightness threshold check on a light group behaves wrong when a bulb is unavailable"
---

# Light-group brightness pivots are fragile

A HA `platform: group` light reports `brightness` as the **average over its ON members only**, not a
reliable "all members at X" signal. Any threshold pivot on it can misread.

- **Don't trust `state_attr('<group>','brightness') >= 254` as "the group is at full."**
  If one member is unreachable / dropped off the mesh at command time, the group averages below the
  threshold (5×254 + 1×0 = 212) even though every reachable bulb is at 100%.
- **Concrete failure:** the ensuite switch pivot (`ensuite_bathroom_lights_switch.yaml`) uses
  `... | int(0) >= 254` to decide single-press = off (at full) vs raise-to-100% (below full). With a
  bulb offline, a "turn off" single press reads <254 → re-raises to full instead. User presses
  off, light gets brighter.
- **Rare, and backstopped** there by hold = kill-all group + the `ensuite_manual_override` safety
  timeout, so left as-is (spec fixed `>= 254` verbatim). If a pivot must be robust, gate on a single
  representative member (`is_state('<a_member>','on')` + its own brightness), not the group avg.
- `int(0)` correctly maps a fully-off group (no brightness attr → `None`) to 0, so the off-state
  routes fine — only the partial-offline case misreads.
