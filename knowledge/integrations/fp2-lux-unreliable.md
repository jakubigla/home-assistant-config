---
summary: Aqara FP2 lux is unusable for darkness; FP300 lux works at < 5 but needs an own-lights latch.
before_action:
  - About to build an is_dark / darkness gate for a room
  - About to use an Aqara FP2 or FP300 illuminance sensor in an automation condition
on_symptom:
  - "presence lights turned on while the room was still daylit"
  - "sensor.*_illuminance flickers 0/5 lux"
  - "is_dark went off right after the room's lights came on"
---

- **Never threshold FP2 lux.** `sensor.gym_illuminance` / `sensor.office_illuminance` (FP2,
  homekit_controller) read 0-8 in daylight and flicker 0<->5 every second. (A `< 10` gate lit the
  office at 18:10 CEST — user: "not dark enough"; gym FP2 read 0 at 17:46 in daylight.)
- **Attic FP300s gate darkness at `< 5` lux (user call, 2026-10-12)** —
  `binary_sensor.attic_{gym,office,hall}_is_dark` read
  `sensor.gym_presence_multi_sensor_fp300_gym_illuminance`, `sensor.office_lluminance` (sic),
  `sensor.attic_illuminance`; fall back to `outdoor_is_dark` when lux isn't numeric. FP300 is
  battery/Matter: lux reports sparsely (minutes apart), coarse steps (1/3/4/5).
- **A lux gate must latch while the room's own lights are on** — they lift lux over the threshold,
  `is_dark` drops, and every `dark`-gated branch stalls (gym full -> ambient on gym vacancy would
  `hold` with full LEDs lit). Pattern: `lux < 5 or (this.state == 'on' and own_lights_on)`.
  `/api/template` has no `this` — substitute `'on'`/`'off'` to test.
- Contrast: `sensor.living_room_illuminance` (different hardware) is usable with a 7/10 lux
  hysteresis — don't generalise either way without checking the sensor's history.
