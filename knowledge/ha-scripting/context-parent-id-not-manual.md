---
summary: context.parent_id can't detect manual changes — state changes within 5 s of a service call reuse its context.
before_action:
  - About to detect a physical switch press via trigger.to_state.context
  - About to make an automation react only to manual light changes
on_symptom:
  - "physical press logged as caused by an automation"
  - "manual-change automation ignores some switch presses"
---

**`trigger.to_state.context.parent_id is none` is not a reliable "changed by hand" test.** An
entity reuses the context of the last service call made to it for state writes within ~5 s, so
a physical press shortly after an automation commanded that entity carries the automation's
context (`parent_id` set) and the logbook attributes the press to the automation.

- **Seen on** `light.attic_bathroom_right` (Aqara H1 relay via Z2M): presses 4.7 s after the
  presence turn-on and 0.4 s after its door-timeout turn-off were filtered out; later presses
  worked — looks like flakiness, is timing.
- **Z2M press events are no backup.** In `control_relay` mode the H1 dropped `single_right`
  actions for some presses while `state_right` still changed.
- **Prefer designs that don't need the distinction:** if every automation touching the entity
  already leaves the dependents in the same state, follow every change (what the attic bathroom
  `lights follow main switch` automation does). Otherwise you need another discriminator (e.g. a
  decoupled rocker whose button event is the only input).
