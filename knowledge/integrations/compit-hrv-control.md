---
summary: "Compit HRV: set gear via climate.hrv fan_mode (auto = schedule), not fan.hrv; ~80 s lag; rest lives in iNext."
before_action:
  - About to change the HRV ventilation gear or speed from an automation or script
  - About to add an automation that boosts or lowers house ventilation
  - About to change an HRV setting that Home Assistant does not expose
on_symptom:
  - "fan.hrv shows 20% while sensor.hrv_ventilation_gear shows 2"
  - "set the HRV fan speed and it never went back to its schedule"
  - "climate.set_fan_mode on climate.hrv returned 200 but the gear did not change"
  - "HRV controller clock is wrong / schedule switches at the wrong time"
---

Whole-house HRV = Compit Nano Color 2 + AERO 4, core `compit` integration (cloud, iNext).

- **Set the gear with `climate.set_fan_mode` on `climate.hrv`, never `fan.hrv`.** fan_mode is the
  unit's ventilation operating mode: `auto` = follow clock zones, `low`/`medium`/`high` = manual
  gear 1/2/3, `off` = gear 0. `auto` is the only way back to the schedule. `fan.hrv` percentage
  writes another register (20 % = gear 0 … 80 % = gear 3, 100 % = airing), reads 20 % while the
  unit runs gear 2 on schedule, and has no "schedule" value.
- **Wait ~80 s before judging a call.** The integration is cloud-polled; `fan_mode` and
  `sensor.hrv_ventilation_gear` flip together about 80 s after a 200 (verified 2026-11-16, both
  directions).
- **One writer only: the arbiter automation `misc_hrv_ventilation_mode`.** Add new reasons to
  boost/lower as branches of its `desired` variable; a second automation setting fan_mode will
  fight it.
- **`climate.hrv` preset `away` also flips the unit's out-of-home mode**, not just the thermostat.
  The thermostat itself appears to drive nothing (all EX4 relays off), so its setpoints are moot.
- **Everything else is only in iNext**
  (`https://inext.compit.pl/en#/8504D7A20E86/devices/22773`, needs the user's logged-in Chrome):
  comfort/eco/out-of-home gears, clock-zone schedule, season thresholds, supply/exhaust temps.
  Click the parameter **label** (not the value) to open its editor, Accept, then the yellow
  **Save**; the page keeps showing the old value until reloaded.
- **The controller clock cannot be set from iNext** (`__zegar` is read-only there; the `/date`
  editor reachable by URL is for another type — don't use it). Set it on the wall panel. It was
  ~1 h 40 min fast on 2026-11-16.
