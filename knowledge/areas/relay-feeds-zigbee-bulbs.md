---
summary: A relay powering smart bulbs must never be cut to turn lights off — it kills the bulbs' radio.
before_action:
  - About to edit ensuite bathroom lighting automations
  - About to turn off a light group whose members are mains-fed via a relay
on_symptom:
  - "Zigbee bulbs go unavailable when lights turn off"
  - "light group stuck reporting on while bulbs are off"
---

# Relay feeding Zigbee bulbs

In the ensuite, `light.ensuite_bathroom_main_power` ("Main") is an on/off relay that is the **hard power feed** for the six `light.en_suite_bulb_*` Zigbee bulbs.

- **Never turn the relay off to turn lights "off".** Cutting it makes the bulbs go `unavailable` and drop off the Zigbee mesh (verified: every relay-off was followed within ~30s by all bulbs going `unavailable`; they returned only when the relay came back). Turn the bulbs off via bulb/group commands (`light.ensuite_bathroom`) and **leave the relay on**.
- **Every light-ON path turns the relay on first** (a no-op when it's already on, which is the normal state), then commands bulbs. No settle delay in the hot path — the relay stays on continuously, so bulbs are already powered/available. (A cold relay after a true restart takes several seconds to rejoin Zigbee; that rare case self-heals on the next entry, not worth slowing every turn-on for.)
- **`light.ensuite_bathroom_main_with_power` (relay + bulbs) is a trap.** Using it as the turn-on target but turning off only the bulbs leaves the group stuck reporting `on` forever (relay never cut). Don't target this group; it is retired from automations.
- Same hazard applies to any room where a relay/plug sits upstream of smart bulbs — the bulbs lose their radio when you cut power, so the relay is not a light switch.

See the ensuite presence/lighting rebuild spec (`docs/superpowers/specs/2026-05-26-ensuite-presence-lighting-rebuild-design.md`) for the full design that works around this.
