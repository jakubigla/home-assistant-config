---
summary: tuya_local climate drops hvac_mode inside climate.set_temperature — AC stays off; call set_hvac_mode first.
before_action:
  - About to turn on or start a tuya_local AC (climate.office_ac, climate.living_room) from an automation or script
  - About to pass hvac_mode in a climate.set_temperature call
on_symptom:
  - "climate.set_temperature returned 200, setpoint changed, but the AC stayed off"
  - "pre-heat / heat-hold automation fired and set its flag but the room never warmed"
  - "automation trace looks healthy yet climate entity state is still off"
---

# tuya_local: set_temperature ignores hvac_mode

## Gotchas

- **Never rely on `hvac_mode:` inside `climate.set_temperature` for a tuya_local climate — switch
  the unit on with its own `climate.set_hvac_mode` call, then set the setpoint.** tuya_local's
  `async_set_temperature` (`custom_components/tuya_local/climate.py`, 2026.10.0) handles only
  `preset_mode`, `temperature` and the target range; `hvac_mode` is dropped. The call returns 200,
  logs nothing, the trace is clean, the setpoint attribute updates — and the AC stays `off`.
  (Office heat hold set `input_boolean.office_ac_preheat_active` at 06:45 on 2026-11-17 and heated
  nothing; fixed in PR #112.)
- **A setpoint-diff regulator cannot recover from that failed start.** If the loop only writes when
  `wanted_sp != current_sp`, the setpoint already reads the heat value while the unit is off, so
  it sees nothing to do. Verify a start by the entity's **state** (`heat`), not its `temperature`
  attribute.
- **Core HA integrations differ** — many (e.g. `gree`) do honour `hvac_mode` in `set_temperature`,
  so the pattern copied from elsewhere looks correct. Check the integration, not the service schema.
