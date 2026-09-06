---
summary: OOM (exit 137) leaves add-ons in `error` for good — start Mosquitto first, Z2M last, via WS supervisor/api.
before_action:
  - About to check or start Home Assistant add-ons (Supervisor "apps") from a script
  - About to debug why SSH to homeassistant.local is refused
  - About to debug Zigbee2MQTT or Mosquitto being down
on_symptom:
  - "ssh: connect to host homeassistant.local port 22: Connection refused"
  - "add-on state error in Supervisor / Settings > Add-ons shows several apps stopped"
  - "z2m: MQTT failed to connect, exiting... (connect ECONNREFUSED 172.30.33.0:1883)"
  - "supervisor log: exited with non-zero exit code 137"
  - "many Zigbee update.* / mqtt entities unavailable at once"
  - "GET /api/hassio/addons returns 401 with an admin long-lived token"
---

# Add-ons stuck in `error` after a host OOM

- **Exit code 137 in the supervisor log = kernel OOM killer, not an add-on bug.** Host is a HA
  Yellow with 1886 MB RAM + 1 GB swap; one sweep kills HA core + several add-ons at once. HA core
  comes back (supervisor watchdog); **add-ons stay `error` until started by hand** (their watchdog
  is off by default; Z2M's is on but gives up after ~5 retries while Mosquitto is down).
  Confirm with `Range: entries=:-3000:` on `/api/hassio/supervisor/logs` and the kernel journal
  `/api/hassio/host/logs` (`Out of memory: Killed process`).
- **REST `/api/hassio/<anything-but-logs>` returns 401 even for an owner/admin token.** Use the WS
  command instead: `{"type":"supervisor/api","endpoint":"/addons","method":"get"}`,
  `endpoint:"/addons/<slug>/start", method:"post"`. Logs DO work over REST:
  `GET /api/hassio/addons/<slug>/logs`, `/supervisor/logs`, `/host/logs` (text, not JSON — the WS
  route errors on them).
- **Start order: `core_mosquitto` → `a0d7b954_ssh`, `d5369777_music_assistant`,
  `14caed58_flight-tracker` → `45df7312_zigbee2mqtt` last.** Z2M exits with `ECONNREFUSED
  172.30.33.0:1883` if the broker isn't up yet.
- **A start call can return `{'code': 'unknown_error', 'message': ''}` while the add-on is in fact
  coming up** (seen for Music Assistant and Z2M). Re-read `/addons` state before retrying.
- **Known memory hog (2026-09-06): go2rtc's `ffmpeg` for `camera.doorbell_rtsp`** (generic camera
  `01KGQEFHWK2FCN3G9XBQ5V0Q2K`, `#audio` producer) grew to ~970 MB RSS; core log shows recurring
  `stream_worker ... Timestamp discontinuity` and go2rtc `error=EOF url=ffmpeg:generic_...#audio`.
  Matter Server was also OOM-killed repeatedly the same hour. `free -m` over SSH + `docker stats
  --no-stream` show who is eating RAM.
- Recovery check: `mqtt` platform should have 0 unavailable entities within ~2 min of Z2M start
  (group unavailable states by `config/entity_registry/list` platform). Remaining unavailable
  `tplink` bulbs are relay-fed and expected when the relay is off — see relay-feeds-zigbee-bulbs.
