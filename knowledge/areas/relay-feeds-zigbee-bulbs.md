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

In the ensuite, `light.ensuite_bathroom_main_power` ("Main") is an on/off relay — the **hard power feed** for the six `light.en_suite_bulb_*` Zigbee bulbs.

- **Never cut the relay to turn lights "off".** Bulbs go `unavailable` and drop off the mesh within ~30s, returning only when the relay comes back. Turn bulbs off via the bulb group (`light.ensuite_bathroom`); leave the relay on.
- **Every light-ON path turns the relay on first** (no-op in the normal always-on state), then commands bulbs — no settle delay, bulbs already powered. (A cold relay after a true restart takes seconds to rejoin Zigbee; self-heals on next entry, not worth slowing every turn-on.)
- **`light.ensuite_bathroom_main_with_power` (relay + bulbs) is a trap** — targeting it for ON but turning off only the bulbs leaves the group stuck `on` forever (relay never cut). Retired from automations; don't target it.
- **Generalizes:** any relay/plug upstream of smart bulbs is not a light switch — cutting power kills the bulbs' radio.
