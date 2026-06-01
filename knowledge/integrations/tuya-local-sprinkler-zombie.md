---
summary: Tuya "Sprinker" valve controller wedges online-but-dead every few weeks — power-cycle, don't chase the key.
before_action:
  - About to debug garden irrigation buttons that do nothing when tapped
  - About to re-pair or reconfigure the tuya_local Sprinker valve controller
on_symptom:
  - "garden Lawn/Drip/Full dashboard buttons do nothing when tapped"
  - "valve.lawn_sprinkler_zone_1/2/3 or valve.drip_irrigation show unavailable"
  - "tuya_local config entry state setup_retry reason tuya-local device offline"
---

# Tuya Sprinkler controller zombie state

## Gotchas

- **First fix is power-cycle the controller, not the HA config.** The Tuya "Sprinker" 4-way valve
  controller (`tuya_local`) periodically wedges into a zombie state: still online (heartbeats cloud,
  answers TCP on 6668) but serves garbage on the local handshake, so `tuya_local` drops to
  `setup_retry` "tuya-local device offline" and every valve goes `unavailable`. A dashboard tap then
  calls `valve.open_valve` on an unavailable entity — a silent no-op. Unplug ~10s, replug, wait ~1
  min to rejoin Wi-Fi. After reboot the local handshake succeeds and valves return.
- **Don't chase the local_key or protocol version — both are correct.** Verified during one full
  incident: device pings + port 6668 open; the stored key matches all three cloud endpoints
  (`/v1.0/devices/{id}`, `/v1.0/iot-03/devices/{id}`, `/v2.0/cloud/thing/{id}`); handshake fails
  identically at every version (904 at 3.2/3.3, 914 at 3.4/3.5); fails even with the HA entry
  disabled (not contention); cloud says `online:True` yet `getstatus` is `[]` and `functions` is
  2009 "not support this device". All five rule-outs point at the device, not config.
- **Verified params if the entry was deleted and you must re-add tuya_local:** device_id
  `bf54c7941d4d3da58crgqy`, IP `192.168.107.230`, MAC `b8:06:0d:f2:1a:88`, **protocol 3.4 explicit**
  (not auto), category `sfkzq`, region EU. Working DPs at 3.4: `1/101/102/103` = the 4 valve
  channels, `108` = weather mode, `109`. A watchdog (`garden-valve-offline-watchdog`) now alerts
  when valves are unavailable >10 min; the lawn/drip scripts abort+notify instead of silent no-op.

## Tooling traps hit while diagnosing

- **The config entry's `.data` (host + local_key) is only readable on the HA host.** WS
  `config_entries/get` strips `.data`. Root-ssh `homeassistant.local` (HA OS SSH addon, key-based)
  and read `/mnt/data/supervisor/homeassistant/.storage/core.config_entries`.
- **Enable/disable a config entry is WS-only.** `config_entries/disable` with `disabled_by:null`
  re-enables. REST `/api/config/config_entries/entry/{id}/disable` returns 404.
- **tinytuya cloud key pull needs the Smart Life app account linked to the iot.tuya.com project**
  (project → Devices → Link App Account → scan QR in app), else `getdevices()` returns 0 devices in
  every region despite a valid token.
