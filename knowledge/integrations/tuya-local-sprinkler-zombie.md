---
summary: Tuya Sprinker valves go unavailable every few weeks - IP moved because fixed-IP lived on wrong VLAN.
before_action:
  - About to debug garden irrigation buttons that do nothing when tapped
  - About to re-pair or reconfigure the tuya_local Sprinker valve controller
on_symptom:
  - "garden Lawn/Drip/Full dashboard buttons do nothing when tapped"
  - "valve.lawn_sprinkler_zone_1/2/3 or valve.drip_irrigation unavailable"
  - "sprinkler works in the Tuya app but valves unavailable in HA"
  - "tuya_local config entry state setup_retry reason tuya-local device offline"
  - "sprinkler IP flips between 192.168.1.230 and 192.168.107.230"
  - "UniFi fixed-IP / DHCP reservation ignored, client got a different IP"
---

# Tuya Sprinkler controller unavailable

## Gotchas

- **First check is the device's IP, NOT a power-cycle.** The recurring "every few weeks" failure is
  **DHCP handing the controller a different IP** while HA's stored host goes stale →
  entry drops to `setup_retry`, every valve `unavailable`, a dashboard tap is a silent no-op.
  Power-cycling does nothing - device is healthy, just answers on a different address.
  HA-host ARP may be empty; authoritative lookup is the UDM's active-client list by MAC
  `b8:06:0d:f2:1a:88` (`/proxy/network/api/s/default/stat/sta`).
- **Root cause of the IP flip-flop (found 2026-08-26): the UniFi fixed-IP reservation lived on the
  wrong network.** Reservation said `192.168.1.230` on the Default LAN, but the device joins IoT
  SSID `sojaiot` → IoT VLAN `192.168.107.0/24`, where a Default-LAN reservation is silently
  ignored → plain DHCP lease `.107.x`. A reservation only applies when its `network_id` matches
  the VLAN the SSID maps to. Fixed: reservation moved to IoT network
  (`network_id 65d78c7e03ca350ecb3bbf4c`) with `fixed_ip 192.168.107.230`; HA host updated to
  match. Incidents before the fix flip-flopped between `.1.230` and `.107.230`.
- **Prove the device is alive before touching HA.** With the real key + protocol 3.4 a local
  `tinytuya` status at the *current* IP returns the DPs (`1/101/102/103` valve channels, `108`
  weather, `109`); at the stale IP it errors `905 Device Unreachable`. App-still-works = hardware
  fine, problem is HA's host only.
- **Update the host THROUGH HA, never by editing `.storage` on disk.** HA holds config-entry
  `.data` in memory and rewrites the file on the next entry write - a disk edit to
  `core.config_entries` gets silently clobbered (any reload/disable-enable triggers a write).
  tuya_local has **NO reconfigure step** ("Handler ConfigFlowHandler doesn't support step
  reconfigure") — use the **options flow** (UI "Configure", or REST
  `POST /api/config/config_entries/options/flow` with `handler=<entry_id>`), which edits
  `local_key`/`host`/`protocol_version`/`poll_only`, then **reload the entry**
  (`POST /api/config/config_entries/entry/<id>/reload`) — options submit alone left valves
  unavailable.
- **Only if the IP is correct and it still fails, suspect the zombie handshake.** Device online
  (heartbeats, 6668 open) but serves garbage on the local handshake → power-cycle (unplug ~10s,
  replug, ~1 min to rejoin Wi-Fi). Don't chase local_key/protocol — verified correct: key matches
  all three cloud endpoints, handshake fails identically at every version (904 at 3.2/3.3, 914 at
  3.4/3.5), fails even with the entry disabled (not contention).
- **Verified params if you must re-add tuya_local:** device_id `bf54c7941d4d3da58crgqy`,
  MAC `b8:06:0d:f2:1a:88`, reserved IP `192.168.107.230` (IoT VLAN, since 2026-08-26),
  **protocol 3.4 explicit** (not auto), category `sfkzq`, region EU. A watchdog
  (`garden-valve-offline-watchdog`) alerts when valves are unavailable >10 min; lawn/drip scripts
  abort+notify instead of silent no-op.

## Tooling traps hit while diagnosing

- **The config entry's `.data` (host + local_key) is only readable on the HA host.** WS
  `config_entries/get` strips `.data`. Root-ssh `homeassistant.local` (HA OS SSH addon, key-based)
  and read `/homeassistant/.storage/core.config_entries` (NOT `/mnt/data/supervisor/...`).
- **Enable/disable a config entry is WS-only.** `config_entries/disable` with `disabled_by:null`
  re-enables. REST `/api/config/config_entries/entry/{id}/disable` returns 404. But re-enable can
  return `require_restart:true` and does NOT reliably re-read a disk-edited host (see clobber rule).
- **tinytuya cloud key pull needs the Smart Life app account linked to the iot.tuya.com project**
  (project > Devices > Link App Account > scan QR in app), else `getdevices()` returns 0 devices in
  every region despite a valid token.
