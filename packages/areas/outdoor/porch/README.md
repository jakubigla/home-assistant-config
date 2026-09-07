# Porch

> When the doorbell rings, the kitchen wall tablet wakes up and shows the porch camera, then returns to the home view once the visitor has moved on.

**Package:** `porch` | **Path:** `packages/areas/outdoor/porch/`

## How It Works

### Doorbell → wall tablet

A press on the doorbell (`event.doorbell`) wakes the kitchen tablet screen, waits for the tablet's browser to reconnect to Home Assistant, then navigates it to the dedicated `/wall-tablet/doorbell` view, a full-screen live stream of `camera.doorbell_rtsp`. The tablet stays on that view until the doorbell motion sensor has been clear for 10 seconds, or 30 seconds have passed, whichever comes first, and then goes back to `/wall-tablet/home`.

The screen is woken **before** navigating on purpose: Fully Kiosk drops the browser_mod websocket while the screen is off, so a navigate sent first is a silent no-op. The automation waits up to 15 seconds for the browser's path sensor to leave `unavailable` before sending the navigate.

A helper template sensor (`binary_sensor.doorbell_press`) stays `on` for 5 seconds after each doorbell event, giving other automations or cards a short window to react.

### Camera on dashboards

Two cameras watch the porch: the Aqara doorbell (`camera.doorbell_rtsp`, generic RTSP camera, AAC audio, no still-image URL) and the UniFi Protect G5 Dome (`camera.porch`). The doorbell is expensive to show: every live viewer makes HA's go2rtc spawn an ffmpeg RTSP puller plus an AAC→opus transcoder, and even snapshot mode leaks one ffmpeg per 10-second refresh because go2rtc cannot grab a JPEG from that stream. A permanent live tile of it OOM-killed the 2 GB host on 2026-09-06. So: the always-on tablet Home tile shows `camera.porch` in snapshot mode (cheap NVR API call), and only transient views (the ring-triggered doorbell view, security view, phone views) show the doorbell live.

## Gotchas

- The tablet is addressed by a hardcoded browser_mod id (`tablet_browser_id` variable at the top of the automation). It rotates whenever the tablet's browser storage is cleared (last time: the Fully Kiosk "clear browser cache" button on 2026-08-11). If the popup stops working, find the new id via the `sensor.browser_mod_<id>_browser_useragent` entity that reports `Android; SM-T595` while the screen is on, and update the variable.
- `mode: restart`: a second ring while the first is being handled restarts the sequence, so the tablet stays on the camera view for the later visitor.
- The doorbell press template sensor uses `device_class: occupancy` only to get a boolean on/off; it does not represent physical occupancy.
- Porch lighting is not handled here; there is no lights automation in this package.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.doorbell_press` | Template binary sensor (occupancy) | `on` for 5 seconds after the last `event.doorbell` state change |

## Dependencies

| Entity / service | Why |
|------------------|-----|
| `event.doorbell` | Doorbell press event that triggers the tablet popup |
| `camera.doorbell_rtsp` | Porch camera shown on the doorbell view (generic RTSP camera integration) |
| `binary_sensor.doorbell_motion_sensor` | Holds the tablet on the camera view until motion clears |
| `switch.kitchen_dashboard_screen` | Wakes the wall tablet screen (Fully Kiosk) |
| `sensor.browser_mod_c6830995_0bc293d0_browser_path` | Signals that the tablet browser has reconnected |
| `browser_mod.navigate` | Steers the tablet browser to the doorbell/home views |

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | Package entry point, includes automations and templates |
| `automations/porch_doorbell_notify_tablet.yaml` | Doorbell → tablet popup and return-to-home |
| `templates/binary_sensors/doorbell_press.yaml` | 5-second doorbell press indicator sensor |
