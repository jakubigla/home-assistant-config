---
summary: "Bosch heat pump: hc2 setpoint writes 404 in auto (use manual); hc1 via comfort/eco numbers, ground-floor sensor."
before_action:
  - About to change the floor-heating (hc2) setpoint from an automation, script or dashboard card
  - About to change the wall-heater (hc1) setpoint or schedule from Home Assistant
  - About to use climate.main_heating or climate.floor_heating current_temperature as a room reading
on_symptom:
  - "Write to https://pointt-api.bosch-thermotechnology.com/.../heatingCircuits/hc2/manualRoomSetpoint was refused: 404"
  - "floor heating setpoint changed from HA reverts at 06:09 / 08:09 / 23:09"
  - "set the hc1 comfort setpoint but climate.main_heating still shows the old value"
---

Bosch/Junkers ground-source heat pump, custom `bosch_homecom` (K40 gateway, cloud-polled). Two
circuits: hc1 = wall heaters upstairs (`climate.main_heating`), hc2 = floor heating, whole ground
floor + first-floor bathroom (`climate.floor_heating`).

- **hc2 setpoint writes need `select.bosh_junkers_hc2` = `manual`.** On a K40,
  `climate.set_temperature` writes `manualRoomSetpoint`, which the cloud refuses with 404 while the
  circuit is in `auto`; with `manual` it is accepted (verified 2026-11-19). The integration exposes
  no hc2 comfort/eco numbers. Manual means no Bosch program: whoever writes must own the full
  schedule, night setback included (`boiler_room_floor_heating_schedule` does this while
  `input_boolean.heating_auto_control` is on, and puts hc2 back to `auto` when it is off).
- **Setpoint overrides made in the Bosch app (hc2 in auto) are temporary.** The program resets them
  at its switch points (~06:09 workdays, ~08:09 weekends, ~23:09).
- **Set hc1 with `number.boiler_room_bosh_junkers_hc1_comfort_setpoint` / `_eco_setpoint`.**
  These are the stored program levels (comfort 19.5–30, eco 5–25.5, step 0.5) and work in `auto`.
  `climate.main_heating` shows the new value about 60 s later, after the next poll.
- **hc1 control type is `roomflowtemp` against the Bosch room sensor, which is on the ground
  floor.** Both climates report that one sensor as `current_temperature`, so it is never an
  upstairs or bedroom reading. The hc1 setpoint is a lever on flow temperature, not a room target;
  `boiler_room_wall_heaters_follow_bedroom` trims it from `sensor.bedroom_temperature`.
- **The away preset is one device-wide flag** (`async_put_away_mode`). Setting it on either climate
  sets it for both.
