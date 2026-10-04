---
summary: After a mains outage HA starts before Z2M and Z2M republishes cached state — self-on devices look OFF.
before_action:
  - About to add a homeassistant.start trigger that reads or fixes Zigbee device state
  - About to change a Tuya relay power_outage_memory or LED do_not_disturb setting
  - About to trust a Zigbee light/cover state right after a restart or power cut
on_symptom:
  - "lights or LEDs physically on after a power cut but HA shows them off"
  - "curtain opened by itself after power returned, HA still shows closed"
  - "select.*_power_outage_memory shows unknown"
  - "startup automation ran but devices still came on after outage"
---
# Z2M power-outage recovery

- **HA comes up ~30-60 s before Z2M after a power cut — `homeassistant.start` logic acts on stale
  cached state.** Trigger on MQTT `zigbee2mqtt/bridge/state` = `online` (`value_json.state`) plus a
  ~2 min delay; devices rejoin 20 s-2 min after Z2M. (2026-10-04: automations loaded 08:58:19-46,
  Z2M 08:59:12, devices self-on 08:59:32-09:01:21.)
  `binary_sensor.zigbee2mqtt_bridge_connection_state` reads `on` before Z2M runs (retained msg) —
  useless as a "Z2M is back" signal.
- **Z2M republishes its cached pre-outage state on startup, so a device that powered up ON shows
  OFF in HA.** Many Tuya devices never report the self-on. Fix at the device, not with HA sweeps:
  Tuya LED controllers `switch.*_do_not_disturb` ON (= stay off after power cut); relays
  `power_outage_memory` `off`. Enforced by `misc_power_outage_safe_defaults`.
- **Tuya 2-gang / TS0002 relays: HA `select.*_power_outage_memory` maps to the device-level key,
  which is `null` — the real value is `power_outage_memory_l1`.** The select shows `unknown`, but
  selecting via it DOES write `_l1` (verified in Z2M log). Read truth from the Z2M payload or
  `/homeassistant/zigbee2mqtt/state.json`, never the HA select. Factory default can be `on`
  (living_room_tv L1 was).
- **Exception: a relay that feeds smart bulbs must come back ON** — keep
  `ensuite_bathroom_switch` power-outage memory on (see relay-feeds-zigbee-bulbs).
- **Tuya curtain motors (TS0601_cover_8) have no power-on setting** — bedroom curtain opened on
  power return while Z2M reported position 0. Handled by `misc_curtains_reassert_after_reconnect`
  (re-sends last state on unavailable → available).
