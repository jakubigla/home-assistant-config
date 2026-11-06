---
summary: Tapo (tplink) bulbs ignore a turn_on that carries brightness while off — send a plain turn_on.
before_action:
  - About to send brightness/brightness_pct in a light.turn_on to a Tapo (tplink) bulb or a group of them
  - About to write a toggle or presence "on" branch for Tapo bulbs
on_symptom:
  - "light.turn_on on a Tapo bulb or group returns 200 [] instantly and the bulbs stay off"
  - "automation trace shows turn_on with brightness_pct, no error, bulb state never changes"
  - "plain light.turn_on works on the bulb but the automation's turn_on does nothing"
---

# Tapo bulbs: brightness in turn_on is a no-op while off

- **Never put `brightness`/`brightness_pct` in a `light.turn_on` for an OFF Tapo bulb — send a plain
  `light.turn_on`.** HA returns 200 `[]`, logs nothing, state never changes. (2026-11-06, L610
  `light.attic_main_bulb_*`: 100% and 99% both no-ops on the group and on a single bulb; plain
  `turn_on` lit all three. The attic wall-switch right click "did nothing" for this reason.)
- **The same brightness works on a bulb that is already ON** (60% -> brightness 153). Need a level
  from off: plain `turn_on` first, then a second call with the brightness.
- **A `platform: group` forwards the same data, so the group is a no-op too.** The automation trace
  looks healthy (service called, no error) — only the unchanged logbook gives it away.
- **Bulbs come on at their stored brightness.** Verified on the AES-keyed L610s only.
- Different failure from [[onoff-light-ignores-brightness]] (there the light turns on, brightness is
  dropped).
