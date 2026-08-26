---
summary: The legacy `kelvin:` shorthand can silently turn a light OFF; always use `color_temp_kelvin:`.
before_action:
  - About to set a colour temperature in a light.turn_on call
  - About to write a warm-white / daylight preset for an RGB+CCT light
on_symptom:
  - "light stays off after a turn_on that sets a colour temperature"
  - "automation trace looks healthy and fires, but the lamp never lights up"
  - "light turns on with brightness alone but goes off when kelvin is added"
---

**Never pass `kelvin:` in `light.turn_on` — use `color_temp_kelvin:`.** On some Zigbee lights the
legacy shorthand is mistranslated into a command that leaves the lamp **OFF**, with no error, no
warning, and a fully green automation trace.

- **Confirmed on the MiBoxer 5-in-1 controller** (`light.attic_bathroom_mirror`, also sold as the
  attic bathroom mirror LEDs). Three otherwise identical calls, device reachable throughout
  (linkquality 88–144):

  | data | result |
  |---|---|
  | `brightness_pct: 100` | `state=on`, bri 255 |
  | `brightness_pct: 100` + `kelvin: 2700` | **`state=off`** |
  | `brightness_pct: 100` + `color_temp_kelvin: 2700` | `state=on`, 2702K |

- **Zigbee2MQTT reports success either way** — it publishes `{"brightness":254,...,"state":"OFF"}`
  for the broken call, so the MQTT log and `linkquality` both look healthy. Only the resulting
  entity state reveals it. Don't debug this as a mesh/pairing problem: check the parameter name
  first, then confirm with a plain brightness-only `turn_on` to prove the lamp responds at all.
- **Same silent-acceptance family as the onoff-light-ignores-brightness and
  missing-entity-silent-noop leaves** — HA service calls validate shape, not effect. Distinct cause
  though: there the light *lacks* the capability, here it fully supports `color_temp` (2000–6535K)
  and still fails, so a `supported_color_modes` check does not predict it.
