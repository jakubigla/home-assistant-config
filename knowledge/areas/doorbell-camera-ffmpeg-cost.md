---
summary: Aqara doorbell (generic RTSP, no still URL) spawns/leaks ffmpeg per viewer AND per snapshot — show camera.porch instead.
before_action:
  - About to put camera.doorbell_rtsp on an always-on dashboard view (tablet Home, kiosk)
  - About to switch a picture-entity card between camera_view live and auto
  - About to add a still_image_url or change the generic camera entry for the doorbell
on_symptom:
  - "several ffmpeg processes in the homeassistant container, RSS climbing, no go2rtc consumers"
  - "go2rtc: codecs not matched: audio:AAC, audio:OPUS => video:JPEG"
  - "go2rtc: error=EOF url=ffmpeg:generic_... #audio / [exec] timeout"
  - "stream_worker camera.doorbell_rtsp: Timestamp discontinuity detected"
  - "HA host OOM (exit 137) with a 900 MB+ ffmpeg in the kernel log"
---

# Doorbell camera is expensive in every mode

- **Never show `camera.doorbell_rtsp` on an always-on view.** It is a `generic` camera with only a
  `stream_source` (Aqara G4 at `rtsp://…@192.168.107.114:8554/ch2`, H264 + AAC, no HTTP
  snapshot endpoint, only port 8554 open). Live viewer → HA's go2rtc adds `ffmpeg:<rtsp>` (generic
  workaround) plus `ffmpeg:<id>#audio=opus` (AAC isn't WebRTC-capable) = 2–3 ffmpeg per session;
  one grew to ~970 MB and OOM-killed the 1.9 GB host (2026-09-06).
- **`camera_view: auto` is NOT the fix.** Snapshot → go2rtc `frame.jpeg` → spawns an RTSP puller,
  JPEG grab fails (`codecs not matched`), the puller is never reaped. One new ffmpeg per 10 s refresh,
  each growing; second OOM sweep 2026-09-07 09:24 within 80 min of enabling it.
- **Use the UniFi Protect G5 Dome `camera.porch` for tiles** (snapshot = Protect API JPEG, ~28 KB,
  no ffmpeg). Doorbell live stays only on transient views (`doorbell`, `security`, phone).
- Leaked pullers don't exit on their own: `docker exec homeassistant sh -c 'ps -o pid,args | grep
  ffmpeg'` → `kill` them, or restart HA core. HA-managed go2rtc API is a unix socket
  (`/tmp/go2rtc-*/go2rtc.sock`, creds in the yaml beside it); `/api/streams` shows producers with
  `consumers: []` when leaking.
- `camera.doorbell` in old docs never existed; the doorbell's press/motion entities came from a
  `homekit_controller` pairing that is gone (automation last fired 2026-03-12). Re-pairing is a
  user action.
