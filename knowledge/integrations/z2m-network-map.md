---
summary: Z2M mesh audit — request networkmap with routes:false, read the response from the Z2M log, LQI from state.json.
before_action:
  - About to analyze Zigbee mesh health, signal, LQI or routing
  - About to request a Zigbee2MQTT network map
on_symptom:
  - "networkmap request never returns / takes 15+ minutes"
  - "Failed to execute routing table for '<device>'"
  - "websocket closed 1000 (OK) while waiting for bridge/response/networkmap"
  - "sensor.<device>_linkquality does not exist"
---

# Zigbee2MQTT network map

- **Request with `routes: false`.** `mqtt.publish` topic `zigbee2mqtt/bridge/request/networkmap`,
  payload `{"type":"raw","routes":false}`. With `routes:true` every Tuya/Aqara router times out on
  the routing-table query (~37 s each → 17 min for 41 routers, commands lag meanwhile; 2026-09-17).
- **Don't wait for the response over HA WS.** `mqtt/subscribe` closes the socket (1000 OK) instead
  of delivering the ~340 KB payload. Z2M logs the full publish at `info` — read it on the box:
  `grep -h "bridge/response/networkmap" /config/zigbee2mqtt/log/<latest>/*.log | tail -1`, strip
  up to `payload '` and the trailing `'`.
- **Per-device `linkquality` sensors are disabled in HA.** Read LQI from
  `/config/zigbee2mqtt/state.json`, type/model/`lastSeen` from `database.db` (JSON lines) over SSH.
  The dir is gitignored — not in this repo.
- **Link direction:** `links[].lqi` is as heard by `target` (the router that reported its table);
  `source` is the neighbor. Check both directions — attic links differ by 50+ LQI each way.
- **Offline test = `failed: ["lqi"]` on the node AND no router lists it as neighbor.** Old
  `lastSeen` proves nothing for Tuya TS0505B LED routers (no periodic reports). A node that fails
  `lqi` but is heard at 255 by neighbors is alive, just not answering scans.
- **Coordinator neighbor table caps at 16 (ember).** A router missing from it is not a fault.
- State `linkquality` is the last hop into the coordinator, not the device's own link.
