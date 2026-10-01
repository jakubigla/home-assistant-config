---
summary: Aqara FP2/FP300 built-in lux reads 0-8 in daylight and flickers — never gate "is dark" on it; use outdoor_is_dark.
before_action:
  - About to build an is_dark / darkness gate for a room
  - About to use an Aqara FP2 or FP300 illuminance sensor in an automation condition
on_symptom:
  - "presence lights turned on while the room was still daylit"
  - "sensor.*_illuminance flickers 0/5 lux"
---

- **Don't threshold FP2/FP300 lux for darkness — mirror `binary_sensor.outdoor_is_dark`
  (sun-based).** `sensor.gym_illuminance` / `sensor.office_illuminance` (FP2) and
  `sensor.attic_illuminance` (FP300) read 0-8 lux while the room is still daylit, step coarsely
  (0/5/8/12/16) and flicker 0<->5 every second. (A `< 10` lux gate lit the office at 18:10 CEST
  with sun at 0° — user: "not dark enough"; gym FP2 read 0 at 17:46 in daylight.)
- Keep lux as an attribute on the per-room `*_is_dark` sensor for observation only; the per-room
  wrapper is the place to tune a room later. Attic: `binary_sensor.attic_{gym,office,hall}_is_dark`.
- Contrast: `sensor.living_room_illuminance` (different hardware) is usable with a 7/10 lux
  hysteresis — don't generalise either way without checking the sensor's history.
