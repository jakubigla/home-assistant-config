---
summary: Tuya Sprinker valves go unavailable every few weeks - usually DHCP moved its IP; check IP/MAC first.
before_action:
  - About to debug garden irrigation buttons that do nothing when tapped
  - About to re-pair or reconfigure the tuya_local Sprinker valve controller
on_symptom:
  - "garden Lawn/Drip/Full dashboard buttons do nothing when tapped"
  - "valve.lawn_sprinkler_zone_1/2/3 or valve.drip_irrigation unavailable"
  - "sprinkler works in the Tuya app but valves unavailable in HA"
  - "tuya_local config entry state setup_retry reason tuya-local device offline"
---

# Tuya Sprinkler controller unavailable

## Gotchas

- **First check is the device's IP, NOT a power-cycle.** The recurring "every few weeks" failure is
  almost always **DHCP moving the controller to a new IP** while HA's stored host goes stale →
  entry drops to `setup_retry`, every valve `unavailable`, a dashboard tap is a silent no-op.
  Power-cycling does nothing - device is healthy, just answers on a different address.
  Verify by MAC, not IP: from the HA host (on `192.168.1.x`), `arp -an | grep b8:06:0d:f2:1a:88`
  shows the current IP. Confirmed incident: device moved `.107.230` to `192.168.1.230` (6668
  open there, full status returns); HA still pointed at the dead `.107.230`.
- **Prove the device is alive before touching HA.** With the real key + protocol 3.4 a local
  `tinytuya` status at the *current* IP returns the DPs (`1/101/102/103` valve channels, `108`
  weather, `109`); at the stale IP it errors `905 Device Unreachable`. App-still-works = hardware
  fine, problem is HA's host only.
- **Update the host THROUGH HA, never by editing `.storage` on disk.** HA holds config-entry
  `.data` in memory and rewrites the file on the next entry write - a disk edit to
  `core.config_entries` gets silently clobbered (any reload/disable-enable triggers a write). Fix
  the IP via Settings > Devices > tuya_local "Sprinker" > **Reconfigure** (or delete + re-add).
  Key + protocol unchanged. **Permanent fix: DHCP reservation for `b8:06:0d:f2:1a:88`** so it stays.
- **Only if the IP is correct and it still fails, suspect the zombie handshake.** Device online
  (heartbeats, 6668 open) but serves garbage on the local handshake → power-cycle (unplug ~10s,
  replug, ~1 min to rejoin Wi-Fi). Don't chase local_key/protocol — verified correct: key matches
  all three cloud endpoints, handshake fails identically at every version (904 at 3.2/3.3, 914 at
  3.4/3.5), fails even with the entry disabled (not contention).
- **Verified params if you must re-add tuya_local:** device_id `bf54c7941d4d3da58crgqy`,
  MAC `b8:06:0d:f2:1a:88` (IP is whatever ARP shows now - do NOT hardcode `.107.230`),
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
