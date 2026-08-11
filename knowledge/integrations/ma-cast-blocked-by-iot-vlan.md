---
summary: IoT-VLAN TVs must reach HA host tcp 8097/8095 or MA cast playback silently never starts.
before_action:
  - About to debug Music Assistant playback that never starts on a TV/cast player
  - About to add a cast/AirPlay device on the IoT VLAN to Music Assistant
on_symptom:
  - "MA player stays idle after play_media, no errors in MA logs"
  - "cast app launches on TV, artwork stuck loading, no audio"
  - "MA log stops after 'Setting active output protocol' with no 'Start Queue Flow stream'"
---

# MA cast blocked by IoT VLAN

## Gotchas

- **TVs on the IoT VLAN (192.168.107.x) must be able to reach the HA/MA host 192.168.1.183 on
  tcp 8097 (audio stream) and 8095 (webserver/artwork).** UniFi LAN_IN allow rules at index
  20002/20003 provide this, slotted before "Block IoT to Default" (index 20004). Without them the
  failure is fully silent: MA connects out to the TV (LAN→IoT is allowed), the cast app launches
  and shows track metadata, but the TV's stream fetch back to MA is dropped.
- **Diagnostic tell:** addon log shows `Setting active output protocol on <player> to Chromecast`
  but never `Start Queue Flow stream for Queue <player>`. A working start always logs both.
- **Isolate with the Web player** (MA UI, "This device"): if it plays where the TV doesn't, the
  queue/provider side is fine — problem is player output path (network), not Spotify/library.
- **Quirk:** if the TV powers off mid-play, MA keeps reporting `playing` into the dead cast
  session. Self-heals on the next play command (`enqueue: replace` relaunches app + wakes TV).
